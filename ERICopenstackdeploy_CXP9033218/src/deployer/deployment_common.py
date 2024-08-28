"""This file contains common logic relating to deployment preparation."""

import logging

from . import configuration
from . import openstack
from . import utils


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


class PrepareDeployment:
    """
    Prepare deployment.

    Attributes:
        sed_object (obj): sed document object
        sed_file_path (str): sed document file path
        heat_templates_url (str): heat templates url
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, **kwargs):
        """Initialize a EnmDeployment object."""
        self.sed_object = kwargs.pop('sed_object')
        self.sed_file_path = kwargs.pop('sed_file_path')
        heat_templates_url = kwargs.pop('heat_templates_url')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.cloud_templates_extracted_dir = openstack.download_and_extract_templates(
            url=heat_templates_url
        )

    def create_internal_network(self, **kwargs):
        """
        Create internal network.

        Args:
            internal_network_key (str): internal network key
            infrastructure_resource (str): infrastructure resource
        """
        internal_network_key = kwargs.pop('internal_network_key')
        infrastructure_resource = kwargs.pop('infrastructure_resource')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        internal_network_template = utils.get_template_by_ip_type(
            infrastructure_resource=infrastructure_resource,
            ip_version=self.sed_object.sed_data['parameter_defaults']['ip_version']
        )
        internal_network = openstack.Stack(
            name=self.sed_object.sed_data['parameter_defaults']['deployment_id'] + '_' +
            self.sed_object.sed_data['parameter_defaults'][internal_network_key],
            param_file_path=self.sed_file_path,
            stack_file_path=self.cloud_templates_extracted_dir + internal_network_template
        )
        internal_network.create()
        internal_network.wait_until_created()

    def create_enm_security_group(self):
        """Create ENM security group."""
        security_stack_template = utils.get_template_by_ip_type(
            infrastructure_resource='enm_security_group',
            ip_version=self.sed_object.sed_data['parameter_defaults']['ip_version']
        )
        security_stack = openstack.Stack(
            name=self.sed_object.sed_data['parameter_defaults']['deployment_id'] +
            '_security_group',
            param_file_path=self.sed_file_path,
            stack_file_path=self.cloud_templates_extracted_dir + security_stack_template
        )
        security_stack.create()
        security_stack.wait_until_created()

    def create_key_pair(self, **kwargs):
        """
        Create key pair.

        Args:
            key_pair_name (str): Key-pair name
        """
        key_pair_name = kwargs.pop('key_pair_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        key_pair_stack = openstack.Stack(
            name=key_pair_name,
            stack_file_path=self.cloud_templates_extracted_dir +
            CONFIG.get('enm', 'key_pair_template'),
            param_file_path=self.sed_file_path
        )
        if not key_pair_stack.already_exists():
            key_pair_stack.create()
            key_pair_stack.wait_until_created()
