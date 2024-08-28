"""This file contains logic relating to CI ENM upgrade."""

import logging
import os
import sys
from cliff.command import Command
from . import artifact
from . import ci
from . import configuration
from . import dit
from . import openstack
from . import oqs
from . import lcm
from . import sed
from . import utils
from . import workflows
from . import vio
from . import cli_parameter


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIENMUpgrade(Command):
    """
    ENM upgrade.

    Attributes:
        cis_access (boolean): ENM cis access
        product_offering (str): ENM product offering
        lcm_username (str): LCM username
        private_key_file_path (str): Private key file path
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialize a CIENMUpgrade Command object."""
        super().__init__(*args, **kwargs)
        self.cis_access = True
        self.product_offering = 'enm'
        self.lcm_username = CONFIG.get('vnflcm', 'username')
        self.private_key_file_path = os.path.join(utils.get_temporary_directory_path(),
                                                  self.lcm_username + '.key')

    def get_parser(self, prog_name):
        """
        Return the parser object for this command.

        Arguments:
            prog_name (str): deployer ci enm upgrade

        Returns:
            parser (object): list parameters for 'deployer ci enm upgrade --help'
            usage: deployer ci enm upgrade [-h] --deployment-name [DEPLOYMENT_NAME]
                               [--image-name-postfix IMAGE_NAME_POSTFIX]
                               [--workflow-max-check-attempts WORKFLOW_MAX_CHECK_ATTEMPTS]
                               [--create-lcm-backup-volume]
                               [--product-option {ENM,VNF-LCM}]
                               --product-set [PRODUCT_SET_STRING]
                               [--rpm-versions RPM_VERSIONS]
                               [--media-versions MEDIA_VERSIONS]

        """
        parser = super().get_parser(prog_name)
        self.cis_access = 'nwci' not in prog_name
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_image_name_postfix_param(parser)
        parser = cli_parameter.add_workflow_max_check_attempts(parser)
        parser = cli_parameter.add_create_lcm_backup_volume(parser)
        parser = cli_parameter.add_product_option_param(parser)
        if self.cis_access is True:
            parser = cli_parameter.add_product_set_params(parser)
            parser = cli_parameter.add_rpm_versions_param(parser)
            parser = cli_parameter.add_media_versions_param(parser)
        else:
            parser = cli_parameter.add_openstack_credential_params(parser)
            parser = cli_parameter.add_sed_file_params(parser)
            parser = cli_parameter.add_lcm_sed_file_params(parser)
            parser = cli_parameter.add_artifact_json_file_param(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Arguments:
            Passing values for following arguments from this command:
                image_name_postfix (str)
                deployment_name (str)
                product_set_string (str)
                product_option (str)
                rpm_versions (str)
                media_versions (str)
                sed_file_path (str)
                sed_file_url (str)
                vnf_lcm_sed_file_path (str)
                vnf_lcm_sed_file_url (str)
                artifact_json_file (str)
                artifact_json_url (str)
                create_lcm_backup_volume (boolean)
                workflow_max_check_attempts (int)

        """
        # pylint: disable=R0912,R0914,R0915
        enm_upgrade = True
        lcm_upgrade = True
        image_name_postfix = args.image_name_postfix
        if args.product_option:
            enm_upgrade, lcm_upgrade = [True, False] if args.product_option == 'ENM' else [False,
                                                                                           True]
        if self.cis_access is True:
            deployment = dit.Deployment(deployment_name=args.deployment_name)
            is_vio_deployment = utils.is_vio_deployment(
                deployment.project.credentials['os_auth_url']
            )
            utils.setup_openstack_env_variables(deployment.project.credentials)
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
        if is_vio_deployment is False:
            artifacts.upload_media_artifacts()
            private_ssh_key = openstack.get_private_ssh_key(
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
            private_key_file_path = utils.save_private_key(
                private_key=private_ssh_key,
                file_path=os.path.join(utils.get_temporary_directory_path(),
                                       enm_sed_object.sed_data['parameter_defaults']['key_name'] +
                                       '.pem')
            )
            dvms.upload_private_key(private_key_file_path=private_key_file_path)
            dvms.upload_keystone_file()
            dvms.upload_cacert_file()
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
        workflow = workflows.Workflows(
            ip_address=life_cycle_manager.ip_address,
            username=self.lcm_username,
            private_key=self.private_key_file_path,
            https_enabled=life_cycle_manager.is_https_supported,
            ui_hostname=life_cycle_manager.ui_hostname
        )
        vnf_lcm_db_0 = lcm.LifeCycleManagerDb(
            volume_instance_count=0,
            deployment_id=vnf_lcm_sed_object.sed_data['parameter_defaults']['deployment_id'],
            ip_address=vnf_lcm_sed_object.sed_data['parameter_defaults']
            ['internal_ipv4_for_db_vm'].split(',')[0],
            volume_size=vnf_lcm_sed_object.sed_data['parameter_defaults']['vnflafdb_volume_size']
        )
        if life_cycle_manager.is_vnf_lcm_upgrade_required and lcm_upgrade is True:
            vnf_lcm_db_1 = None
            volume_1_id = None
            vnf_lcm_db_0.create_snapshot_volume()
            if (life_cycle_manager.is_ha_deployment is False and
                    life_cycle_manager.is_ha_configuration is True):
                volume_1_id = openstack.create_volume(
                    volume_name=vnf_lcm_sed_object.sed_data['parameter_defaults']['deployment_id'] +
                    '_vnflcm_volume_1',
                    volume_size=vnf_lcm_sed_object.sed_data['parameter_defaults']
                    ['vnflafdb_volume_size'],
                    arguments=f'--snapshot {vnf_lcm_db_0.volume_snapshot_name}'
                )
            life_cycle_manager.update_security_group()
            if life_cycle_manager.upgrade_workaround() is False:
                life_cycle_manager.update_server_group(
                    is_vio_deployment=is_vio_deployment
                )
            if (life_cycle_manager.is_ha_deployment is True and
                    life_cycle_manager.is_ha_configuration is True):
                vnf_lcm_db_1 = lcm.LifeCycleManagerDb(
                    volume_instance_count=1,
                    deployment_id=vnf_lcm_sed_object.sed_data['parameter_defaults']
                    ['deployment_id'],
                    ip_address=vnf_lcm_sed_object.sed_data['parameter_defaults']
                    ['internal_ipv4_for_db_vm'].split(',')[1],
                    volume_size=vnf_lcm_sed_object.sed_data['parameter_defaults']
                    ['vnflafdb_volume_size']
                )
                volume_1_id = vnf_lcm_db_1.volume_id
                vnf_lcm_db_1.create_snapshot_volume()
            life_cycle_manager.set_vnf_lcm_sed_values(
                volume_0_id=vnf_lcm_db_0.volume_id,
                volume_1_id=volume_1_id,
                external_network_name=enm_sed_object.sed_data['parameter_defaults']
                ['enm_external_network_name'],
                internal_network_name=enm_sed_object.sed_data['parameter_defaults']
                ['enm_internal_network_name'],
                is_vio_deployment=is_vio_deployment
            )
            if args.create_lcm_backup_volume is True:
                vnf_lcm_db_0.create_backup_volume()
                if life_cycle_manager.is_ha_deployment is True:
                    vnf_lcm_db_1.create_backup_volume()
            if (life_cycle_manager.is_ha_deployment is False and
                    life_cycle_manager.is_ha_configuration is True):
                life_cycle_manager.create_vip_ports_stack()
            if (life_cycle_manager.is_ha_deployment is True and
                    life_cycle_manager.is_ha_configuration is True):
                life_cycle_manager.update_vip_ports_stack()

            life_cycle_manager.delete_stack()
            life_cycle_manager.create_stack()

        if enm_upgrade is False:
            LOG.info(
                'The VNF-LCM upgrade has successfully completed. Now follow the relevant \
                documentation to determine when the environment is fully ready.'
            )
            sys.exit()

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
        workflow.wait_for_workflow_definition(
            workflow_id='deploystack__top'
        )
        life_cycle_manager.upload_sed(
            sed_file_path=enm_sed_file_path,
            upload_path=CONFIG.get('enm', 'sed_file_path')
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
        workflows_version = workflow.get_workflows_version(
            workflows_name='enmdeploymentworkflows',
            package_version=artifacts.get_artifact_version(
                artifact_name='deployment_workflows_details'
            )
        )
        workflow.wait_for_workflow_definition(
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.UpGradePrep__top'
        )

        if self.cis_access is True and not is_vio_deployment:
            oqs.begin_queue_handling(
                deployment=deployment,
                product_set=args.product_set_string,
                job_type='Upgrade'
            )

        workflow.execute_workflow_and_wait(
            workflow_name='Prepare For Upgrade',
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.UpGradePrep__top',
            max_check_attempts=args.workflow_max_check_attempts
        )
        workflow.execute_workflow_and_wait(
            workflow_name='Upgrade ENM',
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.Upgrade__top',
            max_check_attempts=args.workflow_max_check_attempts
        )
        workflow.cleanup_workflows_versions(
            workflows_name='enmdeploymentworkflows',
            retain_value=5
        )
        workflow.cleanup_workflows_versions(
            workflows_name='enmcloudmgmtworkflows',
            retain_value=2
        )
        workflow.cleanup_workflows_versions(
            workflows_name='enmcloudperformanceworkflows',
            retain_value=2
        )
        if self.cis_access is True and not is_vio_deployment:
            oqs.Deployment.finish_state = 'Finished'
        utils.remove_temporary_directory()
        LOG.info(
            'The ENM Upgrade workflow has successfully completed. Now follow the relevant \
documentation to determine when the environment is fully ready.'
        )
