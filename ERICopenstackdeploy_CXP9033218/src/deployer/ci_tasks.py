"""This file contains logic relating to generic single instance CI Tasks."""

import logging
import os
from cliff.command import Command
from . import cli_parameter
from . import configuration
from . import dit
from . import openstack
from . import lcm
from . import sed
from . import utils
from . import vio
from . import workflows


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CITask(Command):
    """
    CI Task.

    Attributes:
        cis_access (boolean): ENM cis access
        product_offering (str): ENM product offering
        lcm_username (str): LCM username
        private_key_file_path (str): Private key file path
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialize a CIENMTask Command object."""
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
            prog_name (str): deployer ci task

        Returns:
            parser (object): list parameters for 'deployer ci task --help'
            usage: deployer ci task [-h] --deployment-name [DEPLOYMENT_NAME]
                        [--run-lcm-cmd RUN_LCM_CMD]
                        [--workflows-cleanup [WORKFLOWS_CLEANUP]]

        """
        parser = super().get_parser(prog_name)
        self.cis_access = 'nwci' not in prog_name
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_run_lcm_cmd_param(parser)
        parser = cli_parameter.add_workflows_cleanup_param(parser)
        if self.cis_access is False:
            parser = cli_parameter.add_openstack_credential_params(parser)
            parser = cli_parameter.add_sed_file_params(parser)
            parser = cli_parameter.add_lcm_sed_file_params(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Arguments:
            Passing values for following arguments from this command:
                deployment_name (str)
                sed_file_path (str)
                sed_file_url (str)
                vnf_lcm_sed_file_url (str)
                run_lcm_cmd (str)
                workflows_cleanup (int)

        """
        # pylint: disable=R0912,R0914,R0915
        if self.cis_access is True:
            deployment = dit.Deployment(deployment_name=args.deployment_name)
            is_vio_deployment = utils.is_vio_deployment(
                deployment.project.credentials['os_auth_url']
            )
            utils.setup_openstack_env_variables(deployment.project.credentials)
            enm_sed_document = deployment.sed
            enm_sed_file_arg = None
            enm_sed_file_url = None
            vnf_lcm_sed_document = deployment.vnf_lcm_sed
            vnf_lcm_sed_file_arg = None
            vnf_lcm_sed_file_url = None
        else:
            is_vio_deployment = utils.is_vio_deployment(vars(args)['os_auth_url'])
            utils.setup_openstack_env_variables(vars(args))
            enm_sed_document = None
            enm_sed_file_arg = args.sed_file_path
            enm_sed_file_url = args.sed_file_url
            vnf_lcm_sed_document = None
            vnf_lcm_sed_file_arg = args.sed_file_path
            vnf_lcm_sed_file_url = args.vnf_lcm_sed_file_url

        enm_sed_file_path = os.path.join(utils.get_temporary_directory_path(),
                                         CONFIG.get('enm', 'sed_file_name'))
        enm_sed_object = sed.Sed(
            product_offering=self.product_offering,
            sed_file_url=enm_sed_file_url,
            sed_document=enm_sed_document,
            sed_file_path=enm_sed_file_arg,
            sed_document_path=enm_sed_file_path
        )
        vnf_lcm_sed_file_path = os.path.join(utils.get_temporary_directory_path(),
                                             CONFIG.get('vnflcm', 'sed_file_name'))
        vnf_lcm_sed_object = sed.Sed(
            product_offering=self.product_offering,
            sed_file_url=vnf_lcm_sed_file_url,
            sed_document=vnf_lcm_sed_document,
            sed_file_path=vnf_lcm_sed_file_arg,
            sed_document_path=vnf_lcm_sed_file_path
        )
        if is_vio_deployment is False:
            private_ssh_key = openstack.get_private_ssh_key(
                key_pair_stack_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
            )
        else:
            ivms = vio.InternalVirtualManagementServer(
                ip_address=enm_sed_object.sed_data['parameter_defaults']['vms_ip_vio_mgt'],
                username='root',
                password=enm_sed_object.sed_data['parameter_defaults']['vms_root_password']
            )
            private_ssh_key = ivms.get_private_ssh_key(
                key_pair_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
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
        )
        workflow = workflows.Workflows(
            ip_address=life_cycle_manager.ip_address,
            username=self.lcm_username,
            private_key=self.private_key_file_path,
            https_enabled=life_cycle_manager.is_https_supported,
            ui_hostname=life_cycle_manager.ui_hostname
        )

        if args.run_lcm_cmd:
            utils.run_ssh_command(
                ip_address=life_cycle_manager.ip_address,
                username=self.lcm_username,
                private_key=self.private_key_file_path,
                command=args.run_lcm_cmd
            )
            LOG.info(
                'The command executed on the VNF-LCM services VM has successfully completed. \
Now follow the relevant documentation to determine when the environment is fully ready.'
            )

        if args.workflows_cleanup:
            workflow_rentention_values = {'enmdeploymentworkflows': 5,
                                          'enmcloudmgmtworkflows': 2,
                                          'enmcloudperformanceworkflows': 2}
            for workflow_arg in args.workflows_cleanup.split(','):
                workflow_name, retain_value = workflow_arg.split('=')
                if workflow_rentention_values.get(workflow_name.strip()):
                    try:
                        retain_value = int(retain_value)
                        workflow_rentention_values[workflow_name.strip()] = retain_value
                    except ValueError():
                        LOG.error('Invalid workflow retention value, \
                                   retention values must be integer values.')

            for workflow_name, retain_value in workflow_rentention_values.items():
                workflow.cleanup_workflows_versions(
                    workflows_name=workflow_name,
                    retain_value=retain_value,
                    suppress_exception=False
                )
            LOG.info('Workflows cleanup complete.')

        utils.remove_temporary_directory()
