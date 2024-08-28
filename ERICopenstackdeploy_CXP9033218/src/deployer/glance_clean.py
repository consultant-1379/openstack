"""This file contains logic relating to glance clean."""

import logging
import collections
from cliff.command import Command
from . import openstack
from . import utils
from . import cli_parameter

LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class GlanceClean(Command):
    """Removes specified images from glance."""

    LOG = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        """Return the parser object for this command."""
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_openstack_credential_params(parser)
        parser = cli_parameter.add_delete_image_param(parser)
        parser = cli_parameter.add_retain_images_param(parser)
        return parser

    def take_action(self, args):
        """Execute the relevant steps for this command."""
        utils.setup_openstack_env_variables(vars(args))
        defined_images = args.delete_images
        retain_num = args.retain_latest

        glance_images = openstack.get_glance_image_list('desc')
        delete_params = defined_images.split(',')

        for delete_param in delete_params:
            delete_param = delete_param.split('*')
            delete_param = filter(None, delete_param)
            delete_list = collections.OrderedDict()
            for image in glance_images:
                if all(param.lower().strip() in image['Name'].lower() for param in delete_param):
                    delete_list[image['ID']] = image['Name']

            retain = int(retain_num)
            num_of_images = len(delete_list)
            delete_param = "".join(delete_param)

            if num_of_images != 0 and num_of_images > retain:
                retain_images = delete_list.keys()[: retain]
                for retain_image in retain_images:
                    del delete_list[retain_image]

                for image_id, image_name in delete_list.items():
                    LOG.info('deleting image %s from glance', image_name)
                    openstack.delete_image_in_glance(image_id)
                    openstack.wait_for_image_to_delete(image_id, 360, 2)

                LOG.info('All %s images as specified are now deleted from glance', delete_param)
            else:
                LOG.info('No images with the specified parameters of image name and retain-latest \
versions: %s exists', delete_param)
