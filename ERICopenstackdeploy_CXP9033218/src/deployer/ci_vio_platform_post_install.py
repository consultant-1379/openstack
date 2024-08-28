"""This file contains logic relating to CI VIO Platform Post Install."""

import logging
import os
from cliff.command import Command
from deployer.openstack import OpenstackObjectDoesNotExist
from deployer.utils import CliNonZeroExitCodeException
from . import artifact
from . import ci
from . import configuration
from . import dit
from . import lcm
from . import openstack
from . import sed
from . import utils
from . import vio
from . import cli_parameter

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221,R0914


class CIVIOPlatformPostInstall(Command):
    """
    Post Installs VIO Platform with the help of CI tools including DIT.

    Attributes:
        product_offering (str): ENM product offering
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialize a CIVIOPlatformPostInstall Command object."""
        super().__init__(*args, **kwargs)
        self.product_offering = 'vio_platform'
        self.lcm_username = CONFIG.get('vnflcm', 'username')

    def get_parser(self, prog_name):
        """
        Return the parser object for this command.

        Args:
            prog_name (str): ci vio platform post install

        Returns:
            parser (object): command line argument parser

        """
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_product_set_params(parser)
        parser = cli_parameter.add_delete_dvms_param(parser)
        parser = cli_parameter.add_skip_vio_cleanup_param(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Args:

            deployment_name (str)
            product_set_string (str)
            skip_vio_cleanup (boolean)
            delete_dvms (boolean)

        """
        deployment = dit.Deployment(deployment_name=args.deployment_name)
        is_vio_deployment = True
        artifacts = artifact.Artifacts(
            deployment_name=args.deployment_name,
            product_set_version=ci.get_product_set_version(args.product_set_string),
            product_offering=self.product_offering,
            is_vio_deployment=is_vio_deployment
        )
        enm_sed_file_path = os.path.join(utils.get_temporary_directory_path(), 'sed.json')
        enm_sed_object = sed.Sed(
            product_offering=self.product_offering,
            media_details=artifacts.media_details.sed_key_values(),
            sed_document=deployment.sed,
            sed_document_path=enm_sed_file_path
        )
        vnf_lcm_sed_file_path = os.path.join(utils.get_temporary_directory_path(),
                                             CONFIG.get('vnflcm', 'sed_file_name'))
        vnf_lcm_sed_object = sed.Sed(
            product_offering=self.product_offering,
            media_details=artifacts.media_details.sed_key_values(),
            sed_document=deployment.vnf_lcm_sed,
            sed_document_path=vnf_lcm_sed_file_path
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
        life_cycle_manager = lcm.LifeCycleManager(
            sed_object=vnf_lcm_sed_object,
            username=self.lcm_username,
            private_key=private_key_file_path,
            sed_file_path=vnf_lcm_sed_file_path
        )
        ivms.run_profile(
            profile=CONFIG.get('vio', 'install_ivms_software')
        )
        ivms.run_profile(
            profile=CONFIG.get('vio', 'post_install')
        )

        vms_enm_ip_internal = enm_sed_object.sed_data['parameter_defaults']['vms_enm_ip_internal']
        allow_vnflcm_access_commands = [
            'echo "y" | sudo -i vnflcm security allowaccess --interface eth0',
            f'sudo sh -c \"echo {vms_enm_ip_internal} > \
/vnflcm-ext/enm/platform_iptables_white_list.txt\"',
            'echo "y" | sudo -i vnflcm security allowaccess --interface eth0 \
--file /vnflcm-ext/enm/platform_iptables_white_list.txt',
            'echo "y" | sudo -i vnflcm security allowaccess --interface eth0 \
--port 443 --file /vnflcm-ext/enm/platform_iptables_white_list.txt'
        ]

        try:
            for command in allow_vnflcm_access_commands:
                utils.run_ssh_command(
                    ip_address=life_cycle_manager.ip_address,
                    username=self.lcm_username,
                    private_key=private_key_file_path,
                    command=command
                )
        except CliNonZeroExitCodeException:
            LOG.error('Post install step: Allow Access for ENM Whitelist VMs over Internal \
Network to VNF-LCM Failed')
            raise

        if args.skip_vio_cleanup is False:
            utils.remove_contents_of_directory(
                ip_address=enm_sed_object.sed_data['parameter_defaults']['vms_ip_vio_mgt'],
                username='root',
                password=enm_sed_object.sed_data['parameter_defaults']['vms_root_password'],
                location=CONFIG.get('vio', 'artifacts_dir')
            )
        if args.delete_dvms is True:
            LOG.info('Delete DVMS parameter specified, Deleting RHOS hosted DVMS.')
            dvms_doc_object = deployment.vio_dvms_document.content
            dvms_project = dit.Project(project_name=dvms_doc_object['openstack_project_name'])
            utils.setup_openstack_env_variables(dvms_project.credentials)
            dvms_server_name = f'{dvms_doc_object["deployment_id"]}_dvms'
            dvms_exists = openstack.does_openstack_object_exist(
                os_object_type='server',
                os_object_name=dvms_server_name
            )
            if dvms_exists is True:
                try:
                    openstack.delete_server(server_name=dvms_server_name)
                except OpenstackObjectDoesNotExist:
                    pass

                LOG.info('RHOS DVMS: %s successfully deleted.', dvms_server_name)
            security_group_name = f'{dvms_doc_object["deployment_id"]}_security_group_dvms'
            security_group_exists = openstack.does_openstack_object_exist(
                os_object_type='security group',
                os_object_name=security_group_name,
                arguments=''
            )
            if security_group_exists is True:
                security_group = openstack.SecurityGroup(
                    security_group_name=security_group_name
                )
                security_group.delete()
        LOG.info(
            'The Small Integrated ENM platform post-install has successfully completed. \
Now follow the relevant documentation to determine when the environment is fully ready.'
        )
