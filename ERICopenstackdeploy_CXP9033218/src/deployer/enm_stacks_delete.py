"""This file contains logic relating to ENM stacks delete."""

import logging
from cliff.command import Command
from . import configuration
from . import dit
from . import openstack
from . import stack_group
from . import utils
from . import cli_parameter


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIENMStacksDelete(Command):
    """Delete all stacks in the project."""

    LOG = logging.getLogger(__name__)
    cis_access = True

    def get_parser(self, prog_name):
        """Return the parser object for this command."""
        parser = super().get_parser(prog_name)
        CIENMStacksDelete.cis_access = 'nwci' not in prog_name
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_wait(parser)
        parser = cli_parameter.add_exclude_server(parser)
        parser = cli_parameter.add_exclude_volume(parser)
        parser = cli_parameter.add_exclude_network(parser)

        if CIENMStacksDelete.cis_access is False:
            parser = cli_parameter.add_openstack_credential_params(parser)

        return parser

    def take_action(self, args):
        """Execute the relevant steps for this command."""
        if CIENMStacksDelete.cis_access is True:
            deployment = dit.Deployment(deployment_name=args.deployment_name)
            utils.setup_openstack_env_variables(deployment.project.credentials)
            is_vio_deployment = utils.is_vio_deployment(
                deployment.project.credentials['os_auth_url']
            )
            project_name = deployment.project.os_project_name
        else:
            is_vio_deployment = utils.is_vio_deployment(vars(args)['os_auth_url'])
            utils.setup_openstack_env_variables(vars(args))
            project_name = vars(args)['os_project_name']
        openstack.stop_servers_in_project(exclude_server=args.exclude_server)
        stack_group_list = stack_group.StackGroupListFromCurrentProject()
        stack_group_list.delete_stacks(
            wait_on_delete=args.wait
        )
        openstack.delete_project_volume_snapshots(
            wait_on_delete=args.wait,
            exclude_volume=args.exclude_volume
        )
        openstack.delete_volumes_in_project(
            wait_on_delete=args.wait,
            exclude_volume=args.exclude_volume
        )
        if CIENMStacksDelete.cis_access is True:
            openstack.check_if_project_is_clean(
                project_name=project_name,
                is_vio_deployment=is_vio_deployment,
                exclude_server=args.exclude_server,
                exclude_volume=args.exclude_volume,
                exclude_network=args.exclude_network
            )
        LOG.info('All stacks and volumes have been deleted successfully')
