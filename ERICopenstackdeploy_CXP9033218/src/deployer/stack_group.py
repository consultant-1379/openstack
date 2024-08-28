"""StacksGroup."""

import logging
import os
from retrying import retry
from . import configuration
from . import utils
from . import openstack

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


def retry_stack_delete(exception):
    """Return True if stack delete fails."""
    return isinstance(exception, openstack.BadOpenstackObjectStateException)


class StackGroupList:
    """
    Provide functions that can be performed on a list of groups of stack objects.

    This class represents a list of groups of stacks, and provides functions on those
    lists, such as creating / deleting those stacks in groups sequentially, with each
    stack in the group itself being created / deleted in parallel.

    Attributes:
        stack_group_objects (list): list of stack objects
    """

    def __init__(self, **kwargs):
        """Initialize a StackGroupList object."""
        self.stack_group_objects = kwargs.pop('stack_group_objects')
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    def create_stacks(self):
        """Create all of the stacks in order, and waits for them to complete."""
        for stack_group in self.stack_group_objects:
            for stack in stack_group:
                stack.create()

            for stack in reversed(stack_group):
                stack.wait_until_created()

    @retry(retry_on_exception=retry_stack_delete,
           stop_max_attempt_number=3, wait_fixed=10000)
    def delete_stacks(self, **kwargs):
        """
        Delete all of the stacks in order, and waits for them to complete.

        Args:
            wait_on_delete (int): wait time period in seconds
        """
        wait_on_delete = kwargs.pop('wait_on_delete')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        for stack_group in reversed(self.stack_group_objects):
            for stack in stack_group:
                stack.delete()
                if wait_on_delete:
                    stack.wait_until_deleted()

            if not wait_on_delete:
                for stack in reversed(stack_group):
                    stack.wait_until_deleted()


class StackGroupListFromConfig(StackGroupList):
    """
    Represent a list of stack groups based from a definition stored in the configuration file.

    This class is used to represent a list of stack groups, taken from the
    stack definition found in the configuration file. It inherits from the
    generic StackGroupList object so that common functions can be run on
    these blocks of stacks.

    Attributes:
        include_optional (boolean): include optional
        stack_name_prefix (str): stack name prefix
        cloud_templates_extracted_dir (str, optional): cloud templates extracted directory path,
                                                       defaults to None
        sed_file_path (str): sed document file directory path
        product_offering (str): product offering details
        stacks_subdirectory (str): stacks sub directory
    """

    def __init__(self, **kwargs):
        """Initialize a StackGroupListFromConfig object."""
        self.include_optional = kwargs.pop('include_optional')
        self.stack_name_prefix = kwargs.pop('stack_name_prefix')
        self.cloud_templates_extracted_dir = kwargs.pop('cloud_templates_extracted_dir', None)
        self.sed_file_path = kwargs.pop('sed_file_path', "na")
        self.product_offering = kwargs.pop('product_offering')
        self.stacks_subdirectory = kwargs.pop('stacks_subdirectory')
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        stack_group_objects = []
        product_offering_details = utils.get_product_offering_details(
            product_offering=self.product_offering
        )
        stack_group_definitions = product_offering_details['stack_groups']

        stacks_subdirectory_prefix = ''

        for index, stack_group_definition in enumerate(stack_group_definitions):
            stack_objects = []

            if index == len(stack_group_definitions) - 1:
                if self.include_optional:
                    stacks_subdirectory_prefix = 'optional_'
                continue

            for stack_short_name in stack_group_definition:
                if self.cloud_templates_extracted_dir:
                    # If this stack file doesn't exist for this particular distro,
                    # skip it and continue to the next
                    stack_file_path = os.path.join(
                        self.cloud_templates_extracted_dir,
                        stacks_subdirectory_prefix + self.stacks_subdirectory,
                        stack_short_name + ".yaml"
                    )
                    if not os.path.isfile(stack_file_path):
                        LOG.info(
                            'A "%s" stack file does not exist, so skipping it', stack_file_path
                        )
                        continue
                else:
                    stack_file_path = 'na'

                stack_name = f'{self.stack_name_prefix}_{stack_short_name}'
                stack_object = openstack.Stack(
                    name=stack_name,
                    stack_file_path=stack_file_path,
                    param_file_path=self.sed_file_path
                )
                stack_objects.append(stack_object)
            stack_group_objects.append(stack_objects)
            super().__init__(
                stack_group_objects=stack_group_objects
            )


class StackGroupListFromCurrentProject(StackGroupList):
    """
    Class to represent a list of stack groups from an openstack project.

    This class is used to represent a list of stack groups, taken from the
    current openstack project. It inherits from the generic StackGroupList
    object so that common functions can be run on these blocks of stacks.
    """

    def __init__(self):
        """Initialize a StackGroupListFromCurrentProject object."""
        stack_group_objects = []
        internal_network = []
        security_stack = []
        block_storage_stacks = []
        application_stacks = []
        elasticsearch_stack = []
        stacks_in_project = openstack.get_stacks_in_project()
        for stack in stacks_in_project:
            stack_object = openstack.Stack(
                name=stack['Stack Name'],
                stack_file_path='na',
                param_file_path='na'
            )
            if 'elasticsearch' in stack['Stack Name']:
                elasticsearch_stack.append(stack_object)
            elif '_bs_' in stack['Stack Name']:
                block_storage_stacks.append(stack_object)
            elif 'internal_network' in stack['Stack Name']:
                internal_network.append(stack_object)
            elif 'security_group' in stack['Stack Name']:
                security_stack.append(stack_object)
            else:
                application_stacks.append(stack_object)

        stack_group_objects.append(internal_network)
        stack_group_objects.append(security_stack)
        stack_group_objects.append(block_storage_stacks)
        stack_group_objects.append(application_stacks)
        stack_group_objects.append(elasticsearch_stack)

        super().__init__(
            stack_group_objects=stack_group_objects
        )
