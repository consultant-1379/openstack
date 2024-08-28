"""This file contains logic relating to the images."""

import logging
import re
import os
from deployer.openstack import openstack_client_command
from . import configuration
from . import openstack
from . import utils

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


class Image:
    """
    This object contains fields and methods relating to an image.

    It can contain fields relating to openstack and also ci related fields

    Attributes:
        cxp (str): image cxp number
        override_image (str, optional): override image, defaults to None
        artifact_json (obj): artifact json, defaults to None
        image_name_postfix (str, optional): image name postfix, defaults to None
    """

    temp_image_id = ''
    local_image_path = ''

    def __init__(self, **kwargs):
        """Initialize an Image object."""
        cxp = kwargs.pop('cxp')
        self.stack_param_name = kwargs.pop('stack_param_name')
        override_image = kwargs.pop('override_image', None)
        artifact_json = kwargs.pop('artifact_json', None)
        image_name_postfix = kwargs.pop('image_name_postfix', None)
        self.temp_directory = utils.get_temporary_directory_path()

        if override_image:
            self.nexus_url = os.path.basename(override_image)
        else:
            self.nexus_url = str(artifact_json['media_details'][cxp])

        self.image_name = os.path.basename(self.nexus_url)
        self.modified_image_name = self.image_name
        if image_name_postfix != 'no-postfix' and image_name_postfix is not None:
            image_name_postfix = image_name_postfix if image_name_postfix.startswith('_') or \
                image_name_postfix == '' else '_' + image_name_postfix
        else:
            image_name_postfix = ''
        if re.match(r'.*iso$', self.nexus_url):
            self.disk_format = 'iso'
            self.modified_image_name = self.image_name.replace(
                '.iso',
                image_name_postfix
            )
        elif re.match(r'.*qcow2$', self.nexus_url):
            self.disk_format = 'qcow2'
            self.modified_image_name = self.image_name.replace(
                '.qcow2',
                image_name_postfix
            )
        elif re.match(r'.*img$', self.nexus_url):
            self.disk_format = 'raw'
            if image_name_postfix:
                self.modified_image_name = self.image_name.replace(
                    '.img',
                    image_name_postfix
                )
        elif re.match(r'.*vmdk$', self.nexus_url):
            self.disk_format = 'vmdk'
            if image_name_postfix:
                self.modified_image_name = self.image_name.replace(
                    '.vmdk',
                    image_name_postfix
                )

    def download_required_image(self):
        """Download required image locally."""
        if self.already_exists() is False:
            self.create_temporary_glance_image()
            Image.temp_image_id = self.glance_image_details['id']
            Image.local_image_path = self.temp_directory + '/' + self.image_name
            try:
                if not os.path.isfile(Image.local_image_path):
                    utils.download_file(
                        url=self.nexus_url,
                        destination_directory=self.temp_directory
                    )
                self.create_image_from_local_file(Image.local_image_path)
            except Exception:
                self.temporary_image_cleanup(Image.temp_image_id)
                raise

            self.temporary_image_cleanup(Image.temp_image_id)

    @property
    def glance_image_details(self):
        """obj: Return glance image details."""
        return openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='show',
            arguments=self.modified_image_name
        )

    def create_temporary_glance_image(self):
        """Create temporary glance image."""
        openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='create',
            arguments=f'--public {self.modified_image_name}'
        )

    def create_image_from_local_file(self, local_file_path):
        """Create image in glance from local file."""
        extra_vmdk_properties = ''
        if self.disk_format == 'vmdk':
            extra_vmdk_properties = ' --property vmware_disktype="preallocated" ' + \
                                    '--property vmware_adaptertype="ide" '
        arguments = f'--public --container-format bare --disk-format {self.disk_format} \
{extra_vmdk_properties} --file {local_file_path} {self.modified_image_name}'
        openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='create',
            arguments=arguments
        )

    def wait(self):
        """Wait for the image to be in the desired completion state in glance."""
        openstack.wait_for_openstack_object_state(
            'image', self.glance_image_details['name'], 'active', 360, 10
        )

    def already_exists(self):
        """
        Return boolean based on if this image exists in glance or not.

        Returns:
            (bool): True | False
        """
        image_list = openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='list',
            arguments='--limit 1000000'
        )
        return any(image['Name'] == self.modified_image_name for image in image_list)

    @staticmethod
    def temporary_image_cleanup(image_id=None):
        """Delete temporary local and remote images."""
        if image_id is None:
            image_id = Image.temp_image_id
        if image_id:
            LOG.info("Deleting local and remote temporary images.")
            openstack.delete_image_in_glance(image_id)
            os.system(f'rm -rf {Image.local_image_path}')
            Image.temp_image_id = ''
            Image.local_image_path = ''


class ImageListFromConfig:
    """
    Class to create and manipulate lists of image objects.

    This class is used to create and manipulate a list of image objects
    which originate from a definition found in the configuration file

    Attributes:
        product_offering (str): product offering details
        artifact_json (obj): artifact json
        image_name_postfix (str, optional): image name postfix, defaults to None
    """

    def __init__(self, **kwargs):
        """Initialize an ImageListFromConfig object."""
        product_offering = kwargs.pop('product_offering')
        self.artifact_json = kwargs.pop('artifact_json')
        image_name_postfix = kwargs.pop('image_name_postfix', None)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.image_objects = []
        self.product_offering_details = utils.get_product_offering_details(
            product_offering=product_offering
        )
        image_definitions = self.product_offering_details['media_details']
        for image_definition in image_definitions:
            if self.artifact_json['media_details'].get(image_definition['cxp_number']):
                image_object = Image(
                    cxp=image_definition['cxp_number'],
                    stack_param_name=image_definition['stack_param_name'],
                    artifact_json=self.artifact_json,
                    image_name_postfix=image_name_postfix
                )
                self.image_objects.append(image_object)

    def upload_images_to_glance(self):
        """Upload all images into glance except tar.gz files."""
        for image in self.image_objects:
            image.download_required_image()

    def wait_for_images_in_glance(self):
        """Wait for all images associated with this class, to be ready in glance."""
        for image in self.image_objects:
            image.wait()

    def sed_key_values(self):
        """
        Return a list of key value pairs.

        Returns a list of key value pairs containing the image name
        and its corresponding key name found in the sed file

        Returns:
            sed_key_values (list): it returns a list of image SED key names and image file names
                eg: [[<image_sed_key_name>, <image_name>]]
        """
        sed_key_values_list = []
        for image in self.image_objects:
            sed_key_values_list.append([image.stack_param_name, image.modified_image_name])

        for media_name, media_details in self.product_offering_details.items():
            if isinstance(media_details, list):
                for media in media_details:
                    if media.get('media_param_name'):
                        sed_key_values_list.append([media.get('media_param_name'),
                                                    os.path.basename(self.artifact_json[media_name]
                                                                     [media.get('cxp_number')])])
            elif media_details.get('media_param_name'):
                sed_key_values_list.append([media_details.get('media_param_name'),
                                            os.path.basename(self.artifact_json[media_name]
                                                             [media_details.get('cxp_number')])])

        return sed_key_values_list
