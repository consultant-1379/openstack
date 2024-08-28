"""This file contains logic relating to CI ENM Schema upgrade."""


import logging

from cliff.command import Command

from . import ci
from . import configuration
from . import dit
from . import utils
from . import cli_parameter


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIENMSchemaUpgrade(Command):
    """Upgrade ENM and VNF-LCM SED DIT Schemas based on a given product set."""

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialise a CI ENM Schema upgrade Command object."""
        super().__init__(*args, **kwargs)

    def get_parser(self, prog_name):
        """
        Return the parser object for this command.

        Arguments:
            prog_name (str): deployer ci enm schema upgrade

        Returns:
            parser (object): list parameters for 'deployer ci enm schema upgrade --help'
            usage: deployer ci enm schema upgrade [-h] --deployment-name [DEPLOYMENT_NAME]
                               --product-set [PRODUCT_SET_STRING]

        """
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_product_set_params(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Arguments:
            Passing values for following arguments from this command:
                deployment_name (str)
                product_set_string (str)

        """
        deployment = dit.Deployment(deployment_name=args.deployment_name)
        product_set_version = ci.get_product_set_version(args.product_set_string)
        enm_heat_templates_url = ci.get_artifact_url(
            cxp_number=CONFIG.get('CXPNUMBERS', 'ENM_HEAT_TEMPLATES'),
            product_set_version=product_set_version
        )
        dit.update_sed_schema_version(
            document=deployment.sed,
            new_version=utils.get_artifact_version_from_url(enm_heat_templates_url)
        )
        vnflcm_media_url = ci.get_artifact_url(
            cxp_number=CONFIG.get('CXPNUMBERS', 'VNF_LCM'),
            product_set_version=product_set_version
        )
        dit.update_sed_schema_version(
            document=deployment.vnf_lcm_sed,
            new_version=utils.get_artifact_version_from_url(vnflcm_media_url)
        )
        LOG.info(
            'ENM and VNF-LCM SED Schema upgrade completed successfully.'
        )
