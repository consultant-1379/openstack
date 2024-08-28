"""This file contains logic for CI ENM restore."""

import logging
import os
from cliff.command import Command
from . import artifact
from . import ci
from . import configuration
from . import dit
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


class CIENMRestoreDeployment(Command):
    """
    ENM restore deployment.

    Attributes:
        cis_access (boolean): ENM cis access
        product_offering (str): ENM product offering
        lcm_username (str): LCM username
        private_key_file_path (str): Private key file path
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialize a CIENMRestoreDeployment Command object."""
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
            prog_name (str): Deployer ci enm restore deployment

        Returns:
            parser (object): list parameters for 'deployer ci enm restore deployment --help'
            usage: deployer ci enm restore deployment [-h] --deployment-name [DEPLOYMENT_NAME]
                               --backup-tag BACKUP_TAG
                               [--image-name-postfix IMAGE_NAME_POSTFIX]
                               [--workflow-max-check-attempts WORKFLOW_MAX_CHECK_ATTEMPTS]
                               --product-set [PRODUCT_SET_STRING]

        """
        self.cis_access = 'nwci' not in prog_name
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_backup_tag_param(parser)
        parser = cli_parameter.add_image_name_postfix_param(parser)
        parser = cli_parameter.add_workflow_max_check_attempts(parser)
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

        Arguments:
            Passing values for following arguments from this command:
                product_set_string (str)
                image_name_postfix (str)
                deployment_name (str)
                sed_file_path (str)
                sed_file_url (str)
                vnf_lcm_sed_file_path (str)
                vnf_lcm_sed_file_url (str)
                artifact_json_file (str)
                artifact_json_url (str)
                backup_tag (str)
                workflow_max_check_attempts (int)

        """
        # pylint: disable=R0914, R0915
        image_name_postfix = args.image_name_postfix
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
        life_cycle_manager.upload_sed(
            sed_file_path=enm_sed_file_path,
            upload_path=CONFIG.get('enm', 'sed_file_path')
        )
        life_cycle_manager.upload_sed(
            sed_file_path=vnf_lcm_sed_file_path,
            upload_path=os.path.join(CONFIG.get('vnflcm', 'sed_file_path'),
                                     life_cycle_manager.vnf_lcm_version)
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
        workflow.wait_for_workflow_definition(
            workflow_id='deploystack__top'
        )
        workflows_version = workflow.get_workflows_version(
            workflows_name='enmdeploymentworkflows',
            package_version=artifacts.get_artifact_version(
                artifact_name='deployment_workflows_details'
            )
        )
        workflow.wait_for_workflow_definition(
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.RestoreDeployment__top'
        )
        workflow.execute_workflow_and_wait(
            workflow_name='Restore Deployment',
            workflow_id=f'enmdeploymentworkflows.--.{workflows_version}.--.RestoreDeployment__top',
            workflow_data={"tagSelection": {"type": "String", "value": f'{args.backup_tag}'}},
            max_check_attempts=args.workflow_max_check_attempts
        )
        utils.remove_temporary_directory()
        LOG.info(
            'The Restore Deployment workflow has successfully completed. Now follow the relevant \
documentation to determine when the environment is fully ready.'
        )
