"""This file contains logic relating to CI ENM rollback."""

import logging
import os
import sys
from cliff.command import Command
from . import artifact
from . import dit
from . import configuration
from . import ci
from . import lcm
from . import openstack
from . import sed
from . import utils
from . import vio
from . import workflows
from . import cli_parameter


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIENMRollbackDeployment(Command):
    """
    ENM rollback deployment.

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

        Args:
            prog_name (str): deployer ci enm rollback deployment

        Returns:
            parser (object): command line argument parser

        """
        self.cis_access = 'nwci' not in prog_name
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_snapshot_tag_param(parser)
        parser = cli_parameter.add_image_name_postfix_param(parser)
        parser = cli_parameter.add_workflow_max_check_attempts(parser)
        parser = cli_parameter.add_product_option_param(parser)
        if self.cis_access is True:
            parser = cli_parameter.add_product_set_params(parser)
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
            Passing values for following arguments from this command:
                product_option (str)
                image_name_postfix (str)
                deployment_name (str)
                product_set_string (str)
                sed_file_path (str)
                sed_file_url (str)
                vnf_lcm_sed_file_path (str)
                vnf_lcm_sed_file_url (str)
                artifact_json_file (str)
                artifact_json_url (str)
                snapshot_tag (str)
                workflow_max_check_attempts (int)

        """
        # pylint: disable=R0912,R0914,R0915
        enm_rollback = True
        lcm_rollback = True
        image_name_postfix = args.image_name_postfix
        if args.product_option:
            enm_rollback, lcm_rollback = [True, False] if args.product_option == 'ENM' else [False,
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
        artifacts = artifact.Artifacts(
            deployment_name=args.deployment_name,
            product_set_version=product_set_version,
            product_offering=self.product_offering,
            artifact_json_file=artifact_json_file,
            artifact_json_url=artifact_json_url,
            image_name_postfix=image_name_postfix,
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
        private_ssh_key = None
        if is_vio_deployment is True:
            ivms = vio.InternalVirtualManagementServer(
                ip_address=enm_sed_object.sed_data['parameter_defaults']['vms_ip_vio_mgt'],
                username='root',
                password=enm_sed_object.sed_data['parameter_defaults']['vms_root_password'],
                artifact_json=artifacts.artifact_json
            )
            private_ssh_key = ivms.get_private_ssh_key(
                key_pair_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
            )
        else:
            private_ssh_key = openstack.get_private_ssh_key(
                key_pair_stack_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
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
        if life_cycle_manager.is_vnf_lcm_upgrade_required is True and lcm_rollback is True:
            vnf_lcm_db_1 = None
            volume_1_backup_id = None
            life_cycle_manager.download_and_extract_templates(
                destination_directory=utils.get_temporary_directory_path()
            )
            life_cycle_manager.update_server_group(is_vio_deployment=is_vio_deployment)
            life_cycle_manager.update_security_group()
            vnf_lcm_db_0 = lcm.LifeCycleManagerDb(
                volume_instance_count=0,
                deployment_id=vnf_lcm_sed_object.sed_data['parameter_defaults']['deployment_id'],
                ip_address=vnf_lcm_sed_object.sed_data['parameter_defaults']
                ['internal_ipv4_for_db_vm'].split(',')[0],
                volume_size=vnf_lcm_sed_object.sed_data['parameter_defaults']
                ['vnflafdb_volume_size']
            )
            if vnf_lcm_db_0.does_volume_snapshot_exist():
                vnf_lcm_db_0.create_backup_volume()
            if life_cycle_manager.is_ha_deployment is True:
                vnf_lcm_stack_params = openstack.get_resource_attribute(
                    identifier=life_cycle_manager.vnflcm_stack.name,
                    resource_type='stack',
                    attribute='parameters'
                )
                LOG.info('Retrieved internal_ipv4_for_db_vm from VNF-LCM stack: %s',
                         vnf_lcm_stack_params['internal_ipv4_for_db_vm'])
                db_1_ip_address = vnf_lcm_stack_params['internal_ipv4_for_db_vm'].split(',')[1]
                db_1_ip_address = db_1_ip_address.replace('u\'', '').replace('\']', '').strip()

                vnf_lcm_db_1 = lcm.LifeCycleManagerDb(
                    volume_instance_count=1,
                    deployment_id=vnf_lcm_sed_object.sed_data['parameter_defaults']
                    ['deployment_id'],
                    ip_address=db_1_ip_address,
                    volume_size=vnf_lcm_sed_object.sed_data['parameter_defaults']
                    ['vnflafdb_volume_size']
                )
                if life_cycle_manager.is_ha_configuration is True:
                    if vnf_lcm_db_1.does_volume_snapshot_exist():
                        vnf_lcm_db_1.create_backup_volume()
                    volume_1_backup_id = vnf_lcm_db_1.backup_volume_id
            life_cycle_manager.set_vnf_lcm_sed_values(
                volume_0_id=vnf_lcm_db_0.backup_volume_id,
                volume_1_id=volume_1_backup_id,
                external_network_name=enm_sed_object.sed_data['parameter_defaults']
                ['enm_external_network_name'],
                internal_network_name=enm_sed_object.sed_data['parameter_defaults']
                ['enm_internal_network_name'],
                is_vio_deployment=is_vio_deployment
            )
            life_cycle_manager.delete_stack()
            life_cycle_manager.create_stack()
            vnf_lcm_db_0.delete_volume()
            vnf_lcm_db_0.reset_volume_name()
            if life_cycle_manager.is_ha_deployment is True:
                if life_cycle_manager.is_ha_configuration is True:
                    vnf_lcm_db_1.delete_volume()
                    vnf_lcm_db_1.reset_volume_name()
                else:
                    vnf_lcm_db_1.delete_volume_snapshot()
                    vnf_lcm_db_1.delete_volume()
                    life_cycle_manager.delete_vip_ports_stack()

        if enm_rollback is False:
            LOG.info(
                'The VNF-LCM rollback has successfully completed. Now follow the relevant \
documentation to determine when the environment is fully ready.'
            )
            sys.exit()

        utils.run_ssh_command(
            ip_address=life_cycle_manager.ip_address,
            username=self.lcm_username,
            private_key=self.private_key_file_path,
            command='sudo -i cp -p {0}sed.json {0}sed.json.bkup'.format(CONFIG.get('enm',
                                                                                   'sed_file_path'))
        )
        life_cycle_manager.upload_sed(
            sed_file_path=enm_sed_file_path,
            upload_path=CONFIG.get('enm', 'sed_file_path')
        )
        workflow = workflows.Workflows(
            ip_address=life_cycle_manager.ip_address,
            username=self.lcm_username,
            private_key=self.private_key_file_path,
            https_enabled=life_cycle_manager.is_https_supported,
            ui_hostname=life_cycle_manager.ui_hostname
        )
        workflow.rollback_workflows_versions(
            workflows_name=CONFIG.get('workflows', 'deploy_ENM'),
            workflows_version=artifacts.get_artifact_version(
                artifact_name='deployment_workflows_details'
            )
        )
        workflow.rollback_workflows_versions(
            workflows_name=CONFIG.get('workflows', 'cloud_mgmt'),
            workflows_version=artifacts.get_artifact_version(
                artifact_name='cloud_mgmt_workflows_details'
            )
        )
        workflow.rollback_workflows_versions(
            workflows_name=CONFIG.get('workflows', 'cloud_performance'),
            workflows_version=artifacts.get_artifact_version(
                artifact_name='cloud_performance_workflows_details'
            )
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
        workflow.install_workflows(
            package_name=os.path.basename(
                artifacts.get_artifact_url(artifact_name='deployment_workflows_details')
            )
        )
        workflow.wait_for_workflow_definition(
            workflow_id='enmdeploymentworkflows.--.' +
            artifacts.get_artifact_version(artifact_name='deployment_workflows_details') +
            '.--.RollbackDeployment__top'
        )
        workflows_version = workflow.get_workflows_version(
            workflows_name='enmdeploymentworkflows',
            package_version=artifacts.get_artifact_version(
                artifact_name='deployment_workflows_details'
            )
        )
        workflow.execute_workflow_and_wait(
            workflow_name='Rollback ENM',
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.RollbackDeployment__top',
            workflow_data={"tag": {"type": "String", "value": f'{args.snapshot_tag}'}},
            max_check_attempts=args.workflow_max_check_attempts
        )
        LOG.info('The ENM Rollback workflow has successfully completed.')
        life_cycle_manager.enable_https()
        utils.remove_temporary_directory()
        LOG.info('Refer to the relevant documentation to determine when \
the environment is fully ready.')
