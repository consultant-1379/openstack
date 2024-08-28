"""This file contains logic relating to CI VIO DVMS deployment."""

import logging
import os
from cliff.command import Command
from deployer.openstack import OpenstackObjectDoesNotExist
from . import artifact
from . import ci
from . import configuration
from . import dit
from . import image_utils
from . import openstack
from . import utils
from . import cli_parameter

CONFIG = configuration.DeployerConfig()
AUTH = configuration.FunctionalIdConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIVIODvmsDeploy(Command):
    """
    Deploys VIO DVMS with the help of CI tools including DIT.

    Attributes:
        product_offering (str): ENM product offering
    """

    def __init__(self, *args, **kwargs):
        """Initialize a CIVIODeployDVMS Command object."""
        super().__init__(*args, **kwargs)
        self.product_offering = 'vio_dvms'

    def get_parser(self, prog_name):
        """
        Return the parser object for this command.

        Arguments:
            prog_name (str): deployer ci vio dvms deploy

        Returns:
            parser (object): list parameters for 'deployer ci vio dvms deploy --help'
            usage: deployer ci vio dvms deploy [-h] --deployment-name [DEPLOYMENT_NAME]
                                   --product-set [PRODUCT_SET_STRING]
                                   [--media-versions MEDIA_VERSIONS]
                                   [--image-name-postfix IMAGE_NAME_POSTFIX]

        """
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_product_set_params(parser)
        parser = cli_parameter.add_media_versions_param(parser)
        parser = cli_parameter.add_image_name_postfix_param(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Arguments:
            Passing values for following arguments from this command:
                deployment_name (str)
                product_set_string (str)
                image_name_postfix (str)
                media_versions (str)

        """
        # pylint: disable=R0914
        vio_deployment = dit.Deployment(deployment_name=args.deployment_name)
        dvms_doc_object = vio_deployment.vio_dvms_document.content
        dvms_project = dit.Project(
            project_name=vio_deployment.vio_dvms_document.content['openstack_project_name']
        )
        utils.setup_openstack_env_variables(dvms_project.credentials)
        artifacts = artifact.Artifacts(
            deployment_name=args.deployment_name,
            product_set_version=ci.get_product_set_version(args.product_set_string),
            product_offering=self.product_offering,
            image_name_postfix=args.image_name_postfix,
            media_versions=args.media_versions
        )
        media_key = list(artifacts.artifact_json['media_details'].keys())[0]
        media_url = artifacts.artifact_json['media_details'][media_key]
        artifacts.artifact_json['media_details'][media_key] = media_url.replace('.tar.gz', '.vmdk')
        media_details = image_utils.ImageListFromConfig(
            product_offering=self.product_offering,
            artifact_json=artifacts.artifact_json,
            image_name_postfix=args.image_name_postfix
        )
        dvms_image = media_details.image_objects[0]
        if dvms_image.already_exists() is False:
            dvms_image.create_temporary_glance_image()
            temp_image_id = dvms_image.glance_image_details['id']
            try:
                dvms_media_file_path = utils.download_file(
                    url=media_url,
                    destination_directory=utils.get_temporary_directory_path()
                )
                utils.unzip_tar_gz(dvms_media_file_path, utils.get_temporary_directory_path())
                dvms_image_file_path = f'{dvms_media_file_path.split("-", -1)[0]}.vmdk'
                dvms_image.create_image_from_local_file(dvms_image_file_path)
            except Exception:
                dvms_image.temporary_image_cleanup(temp_image_id)
                raise

            dvms_image.temporary_image_cleanup(temp_image_id)

        dvms_doc_object['dvms_image_name'] = dvms_image.modified_image_name
        stack_name = f'{dvms_doc_object["deployment_id"]}_dvms'
        stack_file_path = os.path.join(os.path.dirname(__file__),
                                       CONFIG.get('vio', 'dvms_template'))
        param_file_path = os.path.join(utils.get_temporary_directory_path(), 'dvms_sed.json')
        dvms_doc_object = {'parameter_defaults': dvms_doc_object}
        utils.save_json_string_to_disk(
            file_path=param_file_path,
            json_string=dvms_doc_object
        )
        dvms_stack = openstack.Stack(stack_name, stack_file_path, param_file_path)
        try:
            dvms_stack.delete()
            dvms_stack.wait_until_deleted()
        except OpenstackObjectDoesNotExist:
            pass

        dvms_stack.create()
        dvms_stack.wait_until_created()
        LOG.info(
            'The DVMS deploy has successfully completed. Now follow the relevant documentation \
to complete the DVMS configuration.'
        )
