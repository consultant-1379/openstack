"""This file contains logic relating to CI ENM rollout."""

import logging
import os
from cliff.command import Command
from . import artifact
from . import ci
from . import configuration
from . import dit
from . import oqs
from . import lcm
from . import openstack
from . import deployment_common
from . import sed
from . import utils
from . import vio
from . import workflows
from . import cli_parameter

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIENMRollout(Command):
    """
    Rolls out ENM.

    Attributes:
        cis_access (boolean): ENM cis access
        product_offering (str): ENM product offering
        lcm_username (str): LCM username
        private_key_file_path (str): Private key file path
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialize a CIENMRollout Command object."""
        super().__init__(*args, **kwargs)
        self.cis_access = True
        self.product_offering = 'enm'
        self.lcm_username = CONFIG.get('vnflcm', 'username')
        self.private_key_file_path = os.path.join(utils.get_temporary_directory_path(),
                                                  self.lcm_username + '.key')

    def get_parser(self, prog_name):
        """
        Return the parser object for this command.

        Args:
            prog_name (str): ci enm rollout

        Returns:
            parser (object): command line argument parser

        """
        self.cis_access = 'nwci' not in prog_name
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_image_name_postfix_param(parser)
        parser = cli_parameter.add_workflow_max_check_attempts(parser)
        parser = cli_parameter.add_external_script_param(parser)

        if self.cis_access is True:
            parser = cli_parameter.add_product_set_params(parser)
            parser = cli_parameter.add_rpm_versions_param(parser)
            parser = cli_parameter.add_media_versions_param(parser)
            parser = cli_parameter.add_exclude_server(parser)
            parser = cli_parameter.add_exclude_volume(parser)
            parser = cli_parameter.add_exclude_network(parser)
        else:
            parser = cli_parameter.add_openstack_credential_params(parser)
            parser = cli_parameter.add_sed_file_params(parser)
            parser = cli_parameter.add_lcm_sed_file_params(parser)
            parser = cli_parameter.add_artifact_json_file_param(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Args:

            image_name_postfix (str)
            deployment_name (str)
            product_set_string (str)
            rpm_versions (str)
            media_versions (str)
            sed_file_path (str)
            sed_file_url (str)
            vnf_lcm_sed_file_path (str)
            vnf_lcm_sed_file_url (str)
            artifact_json_file (str)
            artifact_json_url (str)
            upload_script_path (str)
            workflow_max_check_attempts (int)

        """
        # pylint: disable=R0912,R0914,R0915
        image_name_postfix = args.image_name_postfix
        if self.cis_access is True:
            deployment = dit.Deployment(deployment_name=args.deployment_name)
            is_vio_deployment = utils.is_vio_deployment(
                deployment.project.credentials['os_auth_url']
            )
            utils.setup_openstack_env_variables(deployment.project.credentials)
            openstack.check_if_project_is_clean(
                project_name=deployment.project.os_project_name,
                is_vio_deployment=is_vio_deployment,
                exclude_server=args.exclude_server,
                exclude_volume=args.exclude_volume,
                exclude_network=args.exclude_network
            )
            product_set_version = ci.get_product_set_version(args.product_set_string)
            enm_sed_document = deployment.sed
            enm_sed_file_arg = None
            enm_sed_file_url = None
            vnf_lcm_sed_document = deployment.vnf_lcm_sed
            vnf_lcm_sed_file_arg = None
            vnf_lcm_sed_file_url = None
            artifact_json_file = None
            artifact_json_url = None
            rpm_versions = args.rpm_versions
            media_versions = args.media_versions
            if is_vio_deployment:
                image_name_postfix = deployment.sed.content.get('parameters').get('image_postfix',
                                                                                  '')
        else:
            is_vio_deployment = utils.is_vio_deployment(vars(args)['os_auth_url'])
            utils.setup_openstack_env_variables(vars(args))
            product_set_version = None
            enm_sed_document = None
            enm_sed_file_arg = args.sed_file_path
            enm_sed_file_url = args.sed_file_url
            vnf_lcm_sed_document = None
            vnf_lcm_sed_file_arg = args.vnf_lcm_sed_file_path
            vnf_lcm_sed_file_url = args.vnf_lcm_sed_file_url
            artifact_json_file = args.artifact_json_file
            artifact_json_url = args.artifact_json_url
            rpm_versions = None
            media_versions = None
        artifacts = artifact.Artifacts(
            deployment_name=args.deployment_name,
            product_set_version=product_set_version,
            product_offering=self.product_offering,
            artifact_json_file=artifact_json_file,
            artifact_json_url=artifact_json_url,
            image_name_postfix=image_name_postfix,
            rpm_versions=rpm_versions,
            media_versions=media_versions,
            is_vio_deployment=is_vio_deployment
        )
        enm_sed_file_path = os.path.join(utils.get_temporary_directory_path(),
                                         CONFIG.get('enm', 'sed_file_name'))
        enm_sed_object = sed.Sed(
            product_offering=self.product_offering,
            media_details=artifacts.media_details.sed_key_values(),
            sed_file_url=enm_sed_file_url,
            sed_document=enm_sed_document,
            sed_file_path=enm_sed_file_arg,
            sed_document_path=enm_sed_file_path,
            schema_version=artifacts.get_artifact_version(artifact_name='cloud_templates_details')
        )
        vnf_lcm_sed_file_path = os.path.join(utils.get_temporary_directory_path(),
                                             CONFIG.get('vnflcm', 'sed_file_name'))
        vnf_lcm_sed_object = sed.Sed(
            product_offering=self.product_offering,
            media_details=artifacts.media_details.sed_key_values(),
            sed_file_url=vnf_lcm_sed_file_url,
            sed_document=vnf_lcm_sed_document,
            sed_file_path=vnf_lcm_sed_file_arg,
            sed_document_path=vnf_lcm_sed_file_path,
            schema_version=artifacts.get_artifact_version(
                artifact_name='vnflcm_cloudtemplates_details'
            )
        )
        prepare_enm_deployment = deployment_common.PrepareDeployment(
            sed_object=enm_sed_object,
            sed_file_path=enm_sed_file_path,
            heat_templates_url=artifacts.get_artifact_url(artifact_name='cloud_templates_details')
        )
        private_ssh_key = None
        public_ssh_key = 'Not available'
        if is_vio_deployment is False:
            artifacts.upload_media_artifacts()
            prepare_enm_deployment.create_internal_network(
                internal_network_key='enm_internal_network_name',
                infrastructure_resource='enm_internal_network'
            )
            prepare_enm_deployment.create_key_pair(
                key_pair_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
            )
            private_ssh_key = openstack.get_private_ssh_key(
                key_pair_stack_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
            )
            public_ssh_key = openstack.get_public_ssh_key(
                key_pair_stack_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
            )
        else:
            vio_dvms_object = deployment.vio_dvms_document.content
            dvms = vio.DeploymentVirtualManagementServer(
                ip_address=vio_dvms_object['dvms_ip_vio_mgt'],
                username=vio_dvms_object['dvms_username'],
                password=vio_dvms_object['dvms_password'],
                os_project_details=deployment.project.credentials,
                artifact_json=artifacts.artifact_json
            )
            ivms = vio.InternalVirtualManagementServer(
                ip_address=enm_sed_object.sed_data['parameter_defaults']['vms_ip_vio_mgt'],
                username='root',
                password=enm_sed_object.sed_data['parameter_defaults']['vms_root_password'],
                artifact_json=artifacts.artifact_json
            )
            private_ssh_key = ivms.get_private_ssh_key(
                key_pair_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
            )
            private_ssh_key = ivms.get_private_ssh_key(
                key_pair_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
            )
            private_key_file_path = utils.save_private_key(
                private_key=private_ssh_key,
                file_path=os.path.join(utils.get_temporary_directory_path(),
                                       enm_sed_object.sed_data['parameter_defaults']['key_name'] +
                                       '.pem')
            )
            dvms.upload_private_key(private_key_file_path=private_key_file_path)
            dvms.upload_cacert_file()
            dvms.upload_keystone_file()
            vio.upload_file(
                ip_address=vio_dvms_object['dvms_ip_vio_mgt'],
                username='root',
                password=vio_dvms_object['dvms_password'],
                name='ENM SED',
                file_name='sed.json',
                document_file_path=enm_sed_file_path
            )
            vio.upload_file(
                ip_address=vio_dvms_object['dvms_ip_vio_mgt'],
                username='root',
                password=vio_dvms_object['dvms_password'],
                name='VNF_LCM SED',
                file_name='lcm_sed.json',
                document_file_path=vnf_lcm_sed_file_path
            )
            media_prep_required = dvms.download_enm_media(
                media_artifact_mappings=artifacts.get_media_artifact_mappings(),
                image_name_postfix=image_name_postfix
            )
            if media_prep_required:
                dvms.delete_stage_log()
                dvms.run_profile(
                    profile=CONFIG.get('vio', 'software_prep')
                )
        utils.save_private_key(
            private_key=private_ssh_key,
            file_path=self.private_key_file_path
        )
        prepare_enm_deployment.create_enm_security_group()
        life_cycle_manager = lcm.LifeCycleManager(
            sed_object=vnf_lcm_sed_object,
            username=self.lcm_username,
            private_key=self.private_key_file_path,
            sed_file_path=vnf_lcm_sed_file_path,
            heat_templates_url=artifacts.get_artifact_url(
                artifact_name='vnflcm_cloudtemplates_details'
            ),
            media_version=artifacts.get_artifact_version(
                artifact_name='vnflcm_cloudtemplates_details'
            )
        )
        life_cycle_manager.download_and_extract_templates(
            destination_directory=utils.get_temporary_directory_path()
        )
        volume_0_id = openstack.create_volume(
            volume_name=vnf_lcm_sed_object.sed_data['parameter_defaults']['deployment_id'] +
            '_vnflcm_volume_0',
            volume_size=vnf_lcm_sed_object.sed_data['parameter_defaults']['vnflafdb_volume_size']
        )
        volume_1_id = None
        if life_cycle_manager.is_ha_configuration is True:
            volume_1_id = openstack.create_volume(
                volume_name=vnf_lcm_sed_object.sed_data['parameter_defaults']['deployment_id'] +
                '_vnflcm_volume_1',
                volume_size=vnf_lcm_sed_object.sed_data['parameter_defaults']
                ['vnflafdb_volume_size']
            )
        life_cycle_manager.create_security_group()
        life_cycle_manager.create_server_group_stack()
        life_cycle_manager.set_vnf_lcm_sed_values(
            volume_0_id=volume_0_id,
            volume_1_id=volume_1_id,
            external_network_name=enm_sed_object.sed_data['parameter_defaults']
            ['enm_external_network_name'],
            internal_network_name=enm_sed_object.sed_data['parameter_defaults']
            ['enm_internal_network_name'],
            is_vio_deployment=is_vio_deployment
        )
        if life_cycle_manager.is_ha_configuration is True:
            life_cycle_manager.create_vip_ports_stack()
        life_cycle_manager.create_stack()

        if args.upload_script_path is not None:
            utils.execute_uploaded_script(
                ip_address=life_cycle_manager.ip_address,
                username=self.lcm_username,
                private_key=self.private_key_file_path,
                upload_script_path=args.upload_script_path
            )

        workflow = workflows.Workflows(
            ip_address=life_cycle_manager.ip_address,
            username=self.lcm_username,
            private_key=self.private_key_file_path,
            https_enabled=life_cycle_manager.is_https_supported,
            ui_hostname=life_cycle_manager.ui_hostname
        )
        for ip_address in life_cycle_manager.services_vm_ips:
            workflow.download_workflows(
                ip_address=ip_address,
                url=artifacts.get_artifact_url(artifact_name='deployment_workflows_details')
            )
            workflow.download_workflows(
                ip_address=ip_address,
                url=artifacts.get_artifact_url(artifact_name='cloud_mgmt_workflows_details')
            )
            workflow.download_workflows(
                ip_address=ip_address,
                url=artifacts.get_artifact_url(artifact_name='cloud_performance_workflows_details')
            )
        workflow.install_workflows(
            package_name=os.path.basename(
                artifacts.get_artifact_url(artifact_name='deployment_workflows_details')
            )
        )
        workflow.install_workflows(
            package_name=os.path.basename(
                artifacts.get_artifact_url(artifact_name='cloud_mgmt_workflows_details')
            )
        )
        workflow.install_workflows(
            package_name=os.path.basename(
                artifacts.get_artifact_url(artifact_name='cloud_performance_workflows_details')
            )
        )
        life_cycle_manager.upload_sed(
            sed_file_path=enm_sed_file_path,
            upload_path=CONFIG.get('enm', 'sed_file_path')
        )
        life_cycle_manager.upload_sed(
            sed_file_path=vnf_lcm_sed_file_path,
            upload_path=os.path.join(CONFIG.get('vnflcm', 'sed_file_path'),
                                     life_cycle_manager.vnf_lcm_version)
        )
        if self.cis_access is True:
            dit.post_enm_key_pair_to_dit(
                deployment_id=deployment.deployment_id,
                deployment_key_pair=deployment.enm,
                public_key=public_ssh_key,
                private_key=private_ssh_key
            )
            if not is_vio_deployment:
                oqs.begin_queue_handling(
                    deployment=deployment,
                    product_set=args.product_set_string,
                    job_type='Install'
                )

        workflows_version = workflow.get_workflows_version(
            workflows_name='enmdeploymentworkflows',
            package_version=artifacts.get_artifact_version(
                artifact_name='deployment_workflows_details'
            )
        )
        workflow.wait_for_workflow_definition(
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.deploystack__top'
        )
        workflow.execute_workflow_and_wait(
            workflow_name='ENM Initial Install',
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.deploystack__top',
            max_check_attempts=args.workflow_max_check_attempts
        )

        if self.cis_access is True and not is_vio_deployment:
            oqs.Deployment.finish_state = 'Finished'
        LOG.info('The ENM Initial Install workflow has successfully completed.')
        life_cycle_manager.enable_https()
        utils.remove_temporary_directory()
        LOG.info('Refer to the relevant documentation to determine when \
the environment is fully ready.')
