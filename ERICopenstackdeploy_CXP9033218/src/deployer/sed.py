"""This file contains logic relating to the site engineering document."""

import logging
import json
import os
import yaml
from . import configuration
from . import dit
from . import openstack
from . import utils

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


class Sed:
    """
    This class represents a site engineering document.

    It provides functions to read / manipulate and save a sed file

    Attributes:
        product_offering (str): product offering
        media_details (obj, optional): media details, defaults to None
        sed_file_path (str, optional): sed file path, defaults to None
        sed_file_url (str, optional): sed file url, defaults to None
        sed_document (obj, optional): sed_document, defaults to None
        sed_document_path (str): sed document path
        schema_version (str, optional): schema version, defaults to None
    """

    def __init__(self, **kwargs):
        """Initialize a Sed object."""
        self.product_offering = kwargs.pop('product_offering')
        self.media_details = kwargs.pop('media_details', None)
        self.sed_file_path = kwargs.pop('sed_file_path', None)
        self.sed_file_url = kwargs.pop('sed_file_url', None)
        sed_document = kwargs.pop('sed_document', None)
        sed_document_path = kwargs.pop('sed_document_path')
        schema_version = kwargs.pop('schema_version', None)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.sed_data = {
            'parameter_defaults': {}
        }

        if sed_document:
            if schema_version:
                dit.update_sed_schema_version(
                    document=sed_document,
                    new_version=schema_version
                )
            sed_document = dit.execute_dit_get_rest_call(
                url_string=f'/api/documents/{sed_document.database_id}'
            )
            utils.save_json_string_to_disk(
                file_path=sed_document_path,
                json_string=sed_document['content']
            )
            self.sed_file_path = sed_document_path
        self.download_if_url_given()
        self.add_ci_floating_ip_keys()
        self.load_from_disk()
        if self.media_details:
            self.replace_values(keys_and_values=self.media_details)
            self.report_blank_values()
        self.save_to_disk_as_json(sed_file_path=sed_document_path)

    def download_if_url_given(self):
        """Download sed file from url to a temporary area."""
        if self.sed_file_url:
            self.sed_file_path = utils.download_file(
                url=self.sed_file_url,
                destination_directory=utils.get_temporary_directory_path()
            )

    def load_from_disk(self):
        """obj: Load the current sed from disk into an object in memory."""
        with open(self.sed_file_path, 'r') as file_object:
            file_contents = file_object.read()

        try:
            contents = json.loads(file_contents)
        except ValueError:
            # pylint: disable=E1120
            contents = yaml.load(file_contents)

        if not isinstance(contents, dict):
            raise RuntimeError(
                'The sed could not be parsed properly, please make sure its valid'
            )

        if 'parameters' in contents.keys():
            contents['parameter_defaults'] = contents.pop('parameters')

        for key, value in contents['parameter_defaults'].items():
            if value:
                self.sed_data['parameter_defaults'][key] = value
            else:
                self.sed_data['parameter_defaults'][key] = ''

    def add_ci_floating_ip_keys(self):
        """Add more supported keys to the sed from a configuration file."""
        unsupported_offerings = ['enm', 'vio_platform', 'vio_platform_ivms']
        if self.product_offering in unsupported_offerings or openstack.get_distro_type() == 'ecee':
            return
        product_offering_details = utils.get_product_offering_details(
            product_offering=self.product_offering
        )
        ci_floating_ip_key_details = product_offering_details['ci_floating_ip_keys']
        for key in ci_floating_ip_key_details:
            self.sed_data['parameter_defaults'][key] = ''

    def replace_values(self, **kwargs):
        """
        Replace a set of values in this sed object.

        Replaces the values loaded in memory for this sed, from the given list of keys and values

        Args:
            keys_and_values (str): Keys and Values
        """
        keys_and_values = kwargs.pop('keys_and_values')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        sed_filename = os.path.basename(self.sed_file_path)
        for key, value in keys_and_values:
            if key in self.sed_data['parameter_defaults']:
                if value != 'auto':
                    LOG.info('populate SED key: "%s" with value: "%s"', key, value)
                    self.sed_data['parameter_defaults'][key] = value
            else:
                LOG.warning(
                    '%s does not contain a key called: "%s", so skipping it', sed_filename, key
                )

    def key_values(self):
        """dict: Return a list of key value pairs belonging to this sed object."""
        return self.sed_data['parameter_defaults'].items()

    def report_blank_values(self):
        """Report any values in the sed that are not filled in."""
        for key, value in self.sed_data['parameter_defaults'].items():
            if not value:
                LOG.warning('This key in the sed is not filled in: %s', key)

    def save_to_disk_as_json(self, **kwargs):
        """
        Save the current sed details as json.

        The sed details will be saved from memory
        into the given file path on disk in json format

        Args:
            sed_file_path (str): sed file directory path
        """
        sed_file_path = kwargs.pop('sed_file_path')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info('Saving SED contents to: %s ', sed_file_path)

        # Convert values to strings to workaround issue with lcm
        # not being able to parse non string values
        for key, value in self.sed_data['parameter_defaults'].items():
            self.sed_data['parameter_defaults'][key] = str(value)
        utils.save_json_string_to_disk(
            file_path=sed_file_path,
            json_string={'parameter_defaults': self.sed_data['parameter_defaults']}
        )
