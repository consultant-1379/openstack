"""
This module contains functions relating specifically to openstack.

It contains logic relating to interaction with the openstack clients
"""

import logging
import json
import os.path
import time
import re
import pprint
import yaml
from deployer.utils import CliNonZeroExitCodeException
import deployer.utils as utils
from deployer.utils import cached
from . import configuration

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=C0302


class OpenstackObjectDoesNotExist(Exception):
    """
    A custom exception.

    This custom exception is used to convey that a particular
    openstack object does not exist
    """


class BadOpenstackObjectStateException(Exception):
    """
    A custom exception.

    This custom exception is used to convey that a particular
    openstack object is in a bad state
    """


class BadInternalNetworkObjectStateException(BadOpenstackObjectStateException):
    """
    A custom exception.

    This custom exception is used to convey that a internal
    network openstack object is in a bad state
    """


def openstack_client_command(**kwargs):
    """
    Run the openstack client cli command, with the given action and arguments.

    Args:
        command_type (str): openstack command type
        object_type (str): object type
        action (str): action
        command_requires_region (boolean, optional): command requires region, defaults to false
        arguments (str): arguments
        return_an_object (boolean, optional): return an object, defaults to True
        is_vio_deployment (boolean, optional): is vio deployment, defaults to False

    Returns:
        (obj): Command line response
    """
    command_type = kwargs.pop('command_type')
    object_type = kwargs.pop('object_type')
    action = kwargs.pop('action')
    command_requires_region = kwargs.pop('command_requires_region', False)
    arguments = kwargs.pop('arguments')
    return_an_object = kwargs.pop('return_an_object', True)
    is_vio_deployment = kwargs.pop('is_vio_deployment', False)

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    if command_type == 'openstack':
        command_and_arguments = f'{command_type} {object_type} {action} {arguments}'
    elif command_type == 'neutron':
        command_and_arguments = f'{command_type} {object_type} -{action} {arguments}'

    if return_an_object:
        command_and_arguments += ' -f json'

    if command_requires_region and is_vio_deployment is False:
        os.environ['OS_REGION_NAME'] = 'regionOne'
    elif command_requires_region and is_vio_deployment is True:
        os.environ['OS_REGION_NAME'] = 'nova'
    else:
        if 'OS_REGION_NAME' in os.environ:
            del os.environ['OS_REGION_NAME']

    cli_command_output = utils.run_cli_command(command_and_arguments)
    cli_command_standard_output = cli_command_output['standard_output']
    return json.loads(cli_command_standard_output) if return_an_object else None


def wait_for_openstack_object_state(
        object_type, identifier, required_state, attempts, sleep_period):
    """
    Wait for the given openstack object to be in the required state.

    Args:
        object_type (str): openstack object type
        identifier (str): object identifier
        required_state (str): object required state
        attempts (str): number of attempts
        sleep_period (str): sleep period in seconds

    Raises:
        OpenstackObjectDoesNotExist: if image id does not exists
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    is_image_object = False
    if object_type == 'image':
        image_name = identifier
        is_image_object = True

    openstack_object_states = {
        'stack': {
            'state_key': 'stack_status',
            'bad_states': ['CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED'],
            'does_not_exist_string': f"Stack not found: '{identifier}'"
        },
        'image': {
            'state_key': 'status',
            'bad_states': ['killed'],
            'does_not_exist_string': 'Could not find resource'
        },
        'volume': {
            'state_key': 'status',
            'bad_states': ['CREATE_FAILED', 'DELETE_FAILED'],
            'does_not_exist_string': f"No volume with a name or ID of '{identifier}' exists."
        },
        'volume snapshot': {
            'state_key': 'status',
            'bad_states': ['CREATE_FAILED', 'DELETE_FAILED'],
            'does_not_exist_string': f"No volume with a name or ID of '{identifier}' exists."
        },
        'server': {
            'state_key': 'status',
            'bad_states': ['CREATE_FAILED', 'DELETE_FAILED', 'ERROR'],
            'does_not_exist_string': f"No server with a name or ID of '{identifier}' exists."
        }
    }

    state_key = openstack_object_states[object_type]['state_key']
    bad_states = openstack_object_states[object_type]['bad_states']
    does_not_exist_string = openstack_object_states[object_type]['does_not_exist_string']

    LOG.info(
        'Waiting until %s (%s) is in the required state (%s)',
        object_type, identifier, required_state
    )
    count = 1
    while count < attempts:

        if is_image_object:
            identifier = get_image_id(image_name)

        try:
            object_details = openstack_client_command(
                command_type='openstack',
                object_type=object_type,
                action='show',
                arguments=identifier
            )
        except CliNonZeroExitCodeException as exception:
            if does_not_exist_string in str(exception):
                if not is_image_object:
                    raise OpenstackObjectDoesNotExist(
                        'The %s %s does not exist' % (object_type, identifier)
                    )
            else:
                raise

        if object_details[state_key] in bad_states:
            determine_and_raise_exception(object_details, object_type, identifier, state_key)

        if object_details[state_key] == required_state:
            LOG.info('Now the %s (%s) in the required state', object_type, identifier)
            return object_details

        if is_image_object and object_details[state_key] == 'queued':
            temp_image_id = object_details['id']

        LOG.info(
            'Sleeping as %s (%s) is not in the required state yet. Required State: %s. \
Current State: %s', identifier, object_type, required_state, object_details[state_key]
        )
        count += 1
        time.sleep(sleep_period)

    if is_image_object:
        LOG.error('Image: %s was not found.', image_name)
        delete_image_in_glance(temp_image_id)

    raise Exception('The object wasnt in a good state after the given number of attempts')


def wait_for_stack_resource_state(**kwargs):
    """
    Wait for the given openstack stack resource to be in the required state.

    Args:
        identifier (str): identifier
        arguments (str): additional arguments
        resource_type (str): stack resource type
        required_state (str): stack required state
        attempts (str): number of attempts
        sleep_period (str): sleep period in seconds

    Raises:
        OpenstackObjectDoesNotExist: if openstack object does not exists
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    identifier = kwargs.pop('identifier')
    arguments = kwargs.pop('arguments')
    resource_type = kwargs.pop('resource_type')
    required_state = kwargs.pop('required_state')
    attempts = kwargs.pop('attempts')
    sleep_period = kwargs.pop('sleep_period')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    bad_states = {'bad_states': ['CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']}
    does_not_exist_string = {'does_not_exist_string': f'Stack not found: {identifier}'}

    LOG.info(
        'Waiting until stack resource (%s) is in the required state (%s)',
        identifier, required_state
    )
    count = 1
    while count < attempts:
        try:
            stack_resource_details = openstack_client_command(
                command_type='openstack',
                object_type='stack',
                action='resource list',
                arguments=f'{identifier} {arguments}'
            )
            resource_details = next(resource for resource in stack_resource_details
                                    if resource['resource_type'] == resource_type)
        except CliNonZeroExitCodeException as exception:
            if does_not_exist_string in str(exception):
                raise OpenstackObjectDoesNotExist(
                    'The stack resource (%s) does not exist' % identifier
                )
            raise

        if resource_details['resource_status'] in bad_states:
            determine_and_raise_exception(resource_details, 'stack', identifier, 'resource_status')

        if resource_details['resource_status'] == required_state:
            LOG.info('Now the stack resource (%s) is in the required state.', identifier)
            return resource_details

        LOG.info(
            'Sleeping as stack resource (%s) is not in the required state yet. Required State: %s. \
            Current State: %s', required_state, identifier, resource_details['resource_status']
        )
        count += 1
        time.sleep(sleep_period)

    raise Exception('The object wasnt in the expected state after the given number of attempts')


def determine_and_raise_exception(object_details, object_type, identifier, state_key):
    """
    Determine what exception to raise and raises it.

    Args:
        object_details (obj): object details
        object_type (str): object type
        identifier (str): object identifier
        state_key (str): object state key

    Raises:
        BadOpenstackObjectStateException: if openstack object state is bad
        BadInternalNetworkObjectStateException: if internal network connection is bad
    """
    message = pprint.pformat(object_details) + '\n' \
        'The {0} ({1}) is in a bad state: {2}\n' \
        'See more details about the {0} above'\
        .format(object_type, identifier, object_details[state_key])

    if 'internal_network' in identifier:
        raise BadInternalNetworkObjectStateException(
            message
        )
    raise BadOpenstackObjectStateException(
        message
    )


def wait_for_os_object_to_delete(
        object_type, identifier, attempts, sleep_period):
    """
    Wait for an openstack object of the given type and identifier, to be deleted.

    Args:
        object_type (str): object type name
        identifier (str): object identifier
        attempts (str): number of attempts
        sleep_period (str): sleep period in seconds

    Raises:
        OpenstackObjectDoesNotExist: if openstack object does not exists
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    try:
        wait_for_openstack_object_state(
            object_type, identifier, 'DELETED', attempts, sleep_period
        )
    except (OpenstackObjectDoesNotExist, CliNonZeroExitCodeException):
        pass


def get_glance_image_list(list_order):
    """
    Return list of image objects from glance in either ascending or descending order.

    Args:
        list_order (str): list order in ascending | descending order
    """
    return openstack_client_command(
        command_type='openstack',
        object_type='image',
        action='list',
        arguments=f"--limit 1000000 --sort 'created_at:{list_order}'"
    )


def get_image_id(image_name):
    """
    Return latest image id for image name.

    Returns:
        image_id (str): image id

    Raises:
        IndexError: if image does not exist in glance
    """
    glance_image_list = get_glance_image_list('asc')
    image_list_info = [image for image in glance_image_list
                       if image['Name'] is not None and image_name in image['Name']]

    try:
        image_id = image_list_info[0]['ID']
    except IndexError:
        LOG.error('No image with the name: %s exists.', image_name)
        raise

    return image_id


def delete_image_in_glance(image_id):
    """
    Delete image from glance by image ID.

    Args:
        image_id (str): image id

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    try:
        openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='delete',
            arguments=f'{image_id} --insecure',
            return_an_object=False
        )
    except CliNonZeroExitCodeException as exception:
        if 'Forbidden' in str(exception):
            LOG.info('Cannot delete image: %s as it is protected.', image_id)


def wait_for_image_to_delete(image_id, attempts, sleep_period):
    """Wait for image to be deleted from glance."""
    count = 0
    image_deleted = False
    while count < attempts:
        image_list = openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='list',
            arguments='--limit 1000000'
        )
        if any(image['ID'] != image_id for image in image_list):
            image_deleted = True
            break
        count += 1
        time.sleep(sleep_period)

    if not image_deleted:
        raise Exception('The image %s failed to delete' % image_id)


def stop_servers_in_project(**kwargs):
    """Stop list of servers objects.

    Arguments:
        exclude_server (list): list of server name(s) to be excluded
    """
    exclude_server = kwargs.pop('exclude_server', list())

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    server_object_list = get_servers_in_project(exclude_server=exclude_server)
    for server in server_object_list:
        try:
            openstack_client_command(
                command_type='openstack',
                object_type='server',
                action='stop',
                arguments=server['ID'],
                return_an_object=False
            )
        except CliNonZeroExitCodeException:
            pass


def delete_project_volume_snapshots(**kwargs):
    """
    Delete a list of volume snapshot objects.

    Args:
        wait_on_delete (str): wait on delete in seconds
        exclude_volume (list): list of volume name(s) to be excluded

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    wait_on_delete = kwargs.pop('wait_on_delete')
    exclude_volume = kwargs.pop('exclude_volume')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    volume_snapshot_object_list = get_volume_snapshots_in_project(exclude_volume=exclude_volume)

    for volume_snapshot in volume_snapshot_object_list:

        try:
            openstack_client_command(
                command_type='openstack',
                object_type='volume snapshot',
                action='delete',
                arguments=f'{volume_snapshot["ID"]} --force',
                return_an_object=False
            )
            if wait_on_delete:
                wait_for_os_object_to_delete(
                    'volume snapshot', volume_snapshot['ID'], 360, 10
                )
        except CliNonZeroExitCodeException as error_message:
            if "No volume snapshot with a name or ID" not in str(error_message):
                raise

    if not wait_on_delete:
        for volume_snapshot in volume_snapshot_object_list:
            wait_for_os_object_to_delete(
                'volume snapshot', volume_snapshot['ID'], 360, 10
            )


def delete_volumes_in_project(**kwargs):
    """
    Delete a list of volume objects.

    Args:
        wait_on_delete (str): wait on delete in seconds
        exclude_volume (list): list volume name(s) to be excluded

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    wait_on_delete = kwargs.pop('wait_on_delete')
    exclude_volume = kwargs.pop('exclude_volume')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    volume_object_list = get_volumes_in_project(exclude_volume=exclude_volume)

    for volume in volume_object_list:

        try:
            openstack_client_command(
                command_type='openstack',
                object_type='volume',
                action='delete',
                arguments=f'{volume["ID"]} --force',
                return_an_object=False
            )
            if wait_on_delete:
                wait_for_os_object_to_delete(
                    'volume', volume['ID'], 360, 10
                )
        except CliNonZeroExitCodeException as error_message:
            if 'No volume with a name or ID' not in str(error_message):
                raise
    if not wait_on_delete:
        for volume in volume_object_list:
            wait_for_os_object_to_delete(
                'volume', volume['ID'], 360, 10
            )


def does_openstack_object_exist(**kwargs):
    """
    Check if openstack object type with a given name exists.

    Args:
        os_object_type (str): openstack object type
        os_object_name (str): openstack object name
        arguments (str): additional arguments

    Returns:
        (bool): True | False
    """
    os_object_type = kwargs.pop('os_object_type')
    os_object_name = kwargs.pop('os_object_name')
    arguments = kwargs.pop('arguments', '--limit 1000000')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    os_object_list = openstack_client_command(
        command_type='openstack',
        object_type=os_object_type,
        action='list',
        arguments=arguments
    )
    does_object_exist = any(os_object['Name'] == os_object_name for os_object in os_object_list)
    return does_object_exist


def delete_volume(**kwargs):
    """
    Delete a volume.

    Args:
        volume_name (str): volume name
    """
    volume_name = kwargs.pop('volume_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    volume_exists = does_openstack_object_exist(
        os_object_type='volume',
        os_object_name=volume_name
    )
    if volume_exists:
        openstack_client_command(
            command_type='openstack',
            object_type='volume',
            action='delete',
            arguments=f'{volume_name} --force',
            return_an_object=False
        )
        wait_for_os_object_to_delete(
            'volume', volume_name, 60, 10
        )
        LOG.info('Volume successfully deleted: %s', volume_name)


def delete_volume_snapshot(**kwargs):
    """
    Delete a volume snapshot.

    Args:
        volume_snapshot_name (str): volume snapshot name
    """
    volume_snapshot_name = kwargs.pop('volume_snapshot_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    snapshot_exists = does_openstack_object_exist(
        os_object_type='volume snapshot',
        os_object_name=volume_snapshot_name
    )
    if snapshot_exists:
        openstack_client_command(
            command_type='openstack',
            object_type='volume snapshot',
            action='delete',
            arguments=f'{volume_snapshot_name} --force',
            return_an_object=False
        )
        wait_for_os_object_to_delete(
            'volume snapshot', volume_snapshot_name, 60, 10
        )
        LOG.info('Volume snapshot successfully deleted: %s', volume_snapshot_name)


def download_and_extract_templates(**kwargs):
    """
    Download the cloud templates package and extracts them.

    Depending on whether the cloud templates are in zip or rpm format,
    they are either extracted, or yum installed

    Args:
        url (str): cloud templates url

    Returns:
        (str): cloud templates extracted directory
    """
    url = kwargs.pop('url')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    templates_extracted_dir_base = os.path.join(
        utils.get_temporary_directory_path(),
        'cloud-templates'
    )
    os.makedirs(templates_extracted_dir_base)
    cloud_templates_file_path = utils.download_file(
        url=url,
        destination_directory=templates_extracted_dir_base
    )
    if cloud_templates_file_path.endswith('.zip'):
        utils.unzip_file(cloud_templates_file_path, templates_extracted_dir_base)
        first_extracted_subdirectory = next(os.walk(templates_extracted_dir_base))[1][0]
        cloud_templates_extracted_dir = os.path.join(
            templates_extracted_dir_base,
            first_extracted_subdirectory
        )
    else:
        if os.geteuid() == 0:
            sudo_string = ''
        else:
            sudo_string = 'sudo'
        artifact_id = os.path.basename(url).split('-')[0]
        utils.run_cli_command(
            f'{sudo_string} yum remove -y {artifact_id}'
        )
        utils.run_cli_command(f'{sudo_string} rpm -iv --nodeps {cloud_templates_file_path}')
        cloud_templates_extracted_dir = os.path.join(CONFIG.get('enm', 'rpm_install_path'),
                                                     artifact_id)
    return cloud_templates_extracted_dir


@cached
def get_port_list_cached():
    """
    Return the list of all network ports.

    It caches the result so it doesn't need to get the list again

    Returns:
        (list): All network ports
    """
    return openstack_client_command(
        command_type='openstack',
        object_type='port',
        action='list',
        arguments=""
    )


@cached
def get_project_id_from_name(**kwargs):
    """
    Return the id of the given project.

    Args:
        project_name (str): project name
        is_vio_deployment (bool, optional): is vio deployment, defaults to False

    Returns:
        (str): project id
    """
    project_name = kwargs.pop('project_name')
    is_vio_deployment = kwargs.pop('is_vio_deployment', False)

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    project_details = openstack_client_command(
        command_type='openstack',
        object_type="project",
        action='show',
        command_requires_region=False,
        arguments=project_name,
        is_vio_deployment=is_vio_deployment
    )
    return project_details['id']


@cached
def get_resource_attribute(**kwargs):
    """
    Return the resource id of the given identifier.

    Args:
        identifier (str): resource identifier
        resource_type (str): resource type
        attribute (str): resource attribute
    """
    identifier = kwargs.pop('identifier')
    resource_type = kwargs.pop('resource_type')
    attribute = kwargs.pop('attribute')
    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    resource_details = openstack_client_command(
        command_type='openstack',
        object_type=resource_type,
        action='show',
        arguments=identifier
    )
    return resource_details[attribute]


def get_server_id(**kwargs):
    """
    Return the server id from a given ip address.

    Args:
        ip_address (str): ip address

    Raises:
        IndexError: if server not found
    """
    ip_address = kwargs.pop('ip_address')
    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    server_details = openstack_client_command(
        command_type='openstack',
        object_type='server',
        action='list',
        arguments=f'--ip {ip_address.strip()}'
    )
    if len(server_details) > 1:
        for server in server_details:
            if re.search(f'{ip_address}[\\D]', server['Networks']):
                return server['ID']
    try:
        return server_details[0]['ID']
    except IndexError:
        LOG.error('No server found with the following ip address: %s', ip_address)
        raise


@cached
def get_distro_type():
    """
    Return distro type based on openstack client output.

    Returns:
        (str): Distro type
    """
    orchestration_output = openstack_client_command(
        command_type='openstack',
        object_type='orchestration resource type',
        action='list',
        arguments=''
    )
    for resource_item in orchestration_output:
        for resource_value in resource_item.itervalues():
            if 'Ericsson' in resource_value:
                LOG.info('Distro detected : ECEE')
                return 'ecee'

    LOG.info('Distro detected : OTHER')
    return 'other'


@cached
def get_floating_ip_list_cached():
    """
    Return the list of all floating ips.

    It caches the result so it doesn't need to get the list again

    Returns:
        (list): All floating ip's
    """
    return openstack_client_command(
        command_type='openstack',
        object_type='floating ip',
        action='list',
        arguments=''
    )


def delete_existing_key_pair(key_pair_name):
    """
    Delete key pair if it already exists.

    Args:
        key_pair_name (str): key pair

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    try:
        openstack_client_command(
            command_type='openstack',
            object_type='keypair',
            action='show',
            arguments=key_pair_name
        )
    except CliNonZeroExitCodeException:
        LOG.info('No existing key pair called: %s', key_pair_name)
        return

    openstack_client_command(
        command_type='openstack',
        object_type='keypair',
        action='delete',
        arguments=key_pair_name,
        return_an_object=False
    )
    LOG.info('Existing key pair: %s deleted', key_pair_name)


class Stack:
    """
    This object contains fields and methods relating to a stack.

    Attributes:
        name (str): stack name
        stack_file_path (str): stack file path directory
        param_file_path (str, optional): parameter file path directory, defaults to None
        heat_stack_details (dict): heat stack details
        extra_arguments (str, optional): extra arguments, defaults to empty string
    """

    def __init__(self, name, stack_file_path, param_file_path=None, extra_arguments=''):
        """Initialize a stack object."""
        self.name = name
        self.stack_file_path = stack_file_path
        self.param_file_path = param_file_path
        self.heat_stack_details = {}
        self.extra_arguments = extra_arguments

    def create(self):
        """obj: Create the given stack in openstack."""
        param_file_args = f' -e {self.param_file_path}' if self.param_file_path is not None else ''
        self.heat_stack_details = openstack_client_command(
            command_type='openstack',
            object_type='stack',
            action='create',
            arguments=f'-t {self.stack_file_path} {param_file_args} {self.name} \
{self.extra_arguments}'
        )
        return self.heat_stack_details

    def update(self):
        """Update the given stack in openstack."""
        self.heat_stack_details = openstack_client_command(
            command_type='openstack',
            object_type='stack',
            action='update',
            arguments=f'-t {self.stack_file_path} -e {self.param_file_path} {self.name} \
{self.extra_arguments}'
        )

    def set_lvs_vip_to_fip_ips(self, port_id):
        """Set the floating ips for the lvs router."""
        floating_ip = \
            self.get_value_from_sed('lvs_floating_external_ip_address')
        fip_to_vip_cm_ip = self.get_value_from_sed('svc_CM_vip_to_fip')
        fip_to_vip_fm_ip = self.get_value_from_sed('svc_FM_vip_to_fip')
        fip_to_vip_pm_ip = self.get_value_from_sed('svc_PM_vip_to_fip')

        svc_cm_vip_external_ip = \
            self.get_value_from_sed('svc_CM_vip_external_ip_address')
        svc_fm_vip_external_ip = \
            self.get_value_from_sed('svc_FM_vip_external_ip_address')
        svc_pm_vip_external_ip = \
            self.get_value_from_sed('svc_PM_vip_external_ip_address')
        external_ip = self.get_value_from_sed('lvs_external_ip_address')

        floating_ip_id = self.get_floating_ip_id(str(floating_ip))
        svc_cm_floating_id = \
            self.get_floating_ip_id(str(svc_cm_vip_external_ip))
        svc_fm_floating_id = \
            self.get_floating_ip_id(str(svc_fm_vip_external_ip))
        svc_pm_floating_id = \
            self.get_floating_ip_id(str(svc_pm_vip_external_ip))

        self.floating_ip_stack_association(str(floating_ip_id), port_id,
                                           external_ip)
        self.floating_ip_stack_association(str(svc_cm_floating_id), port_id,
                                           fip_to_vip_cm_ip)
        self.floating_ip_stack_association(str(svc_fm_floating_id), port_id,
                                           fip_to_vip_fm_ip)
        self.floating_ip_stack_association(str(svc_pm_floating_id), port_id,
                                           fip_to_vip_pm_ip)

    def floating_ip_association(self, external_subnet_id):
        """Associate the appropriate floating ips to all instances in the stack."""
        port_list = get_port_list_cached()
        for port in port_list:
            if external_subnet_id in port['Fixed IP Addresses'] and self.name in port['Name']:
                vm_name = re.sub(
                    '_interface.*_port',
                    '',
                    port['Name']
                ).replace('-', ' ').split(' ')[1]
                if vm_name == 'lvs':
                    self.set_lvs_vip_to_fip_ips(str(port['ID']))
                else:
                    floating_ip_address_sed_key = f'{vm_name}_floating_external_ip_address'
                    floating_ip = self.get_value_from_sed(floating_ip_address_sed_key)
                    LOG.info('Assigning floating ip address %s to vm %s', floating_ip, vm_name)
                    floating_id = self.get_floating_ip_id(str(floating_ip))
                    self.floating_ip_stack_association(str(floating_id), str(port['ID']))

    @staticmethod
    def get_floating_ip_id(floating_ip):
        """str: Return the id of the given floating ip."""
        floating_list = get_floating_ip_list_cached()
        for floating_ip_address in floating_list:
            if floating_ip == floating_ip_address['Floating IP Address']:
                return floating_ip_address['ID']
        raise Exception('Couldn\'t find floating ip in openstack list: %d' % floating_ip)

    def get_value_from_sed(self, key_value):
        """str: Return the value for the given key."""
        with open(self.param_file_path, 'r') as file_object:
            # pylint: disable=E1120
            for key, value in yaml.load(file_object)['parameter_defaults'].items():
                if key_value == str(key):
                    return value
            raise Exception('Couldn\'t find key: [%s] in sed file' % key_value)

    @staticmethod
    def floating_ip_stack_association(floating_id, port_id, internal_ip=None):
        """Associate a floating ip to a port."""
        arguments = f'{floating_id} --port {port_id}'
        if internal_ip:
            arguments += f' --fixed-ip-address {internal_ip}'

        openstack_client_command(
            command_type='openstack',
            object_type='floating ip',
            action='set',
            arguments=arguments,
            return_an_object=False
        )

    def delete(self):
        """
        Delete the given stack.

        Raises:
            CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
        """
        if not self.already_exists():
            LOG.info('A stack of name %s does not exist, nothing to delete', self.name)
        else:
            try:
                openstack_client_command(
                    command_type='openstack',
                    object_type='stack',
                    action='delete',
                    arguments=f'{self.name} --yes',
                    return_an_object=False
                )
            except CliNonZeroExitCodeException as error_message:
                if 'Stack not found:' not in str(error_message):
                    raise

    def wait_until_created(self):
        """Wait for the stack to be created."""
        wait_for_openstack_object_state(
            'stack', self.heat_stack_details['stack_name'], 'CREATE_COMPLETE', 360, 10
        )

    def wait_until_updated(self):
        """Wait for the stack to be updated."""
        wait_for_openstack_object_state(
            'stack', self.heat_stack_details['stack_name'], 'UPDATE_COMPLETE', 360, 10
        )

    def wait_until_deleted(self):
        """Wait for the stack to be deleted."""
        wait_for_os_object_to_delete(
            'stack', self.name, 360, 10
        )

    def already_exists(self):
        """
        Check if the stack of this name already exists.

        Returns:
            (bool): True | False
        """
        stack_list = openstack_client_command(
            command_type='openstack',
            object_type='stack',
            action='list',
            arguments='--limit 1000000'
        )
        return any(stack['Stack Name'] == self.name for stack in stack_list)

    def get_stack_output(self, **kwargs):
        """
        Return the value of the stack output for the given key.

        Args:
            output_key (str): stack output key

        Returns:
            (str): stack output key
        """
        output_key = kwargs.pop('output_key')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        return openstack_client_command(
            command_type='openstack',
            object_type='stack',
            action='output show',
            arguments=f'{self.name} {output_key}'
        )['output_value']

    def get_resource_list(self, **kwargs):
        """
        Return the stack resource list.

        Args:
            additional_arguments (str, optional): additional arguments, defaults to empty string

        Returns:
            (obj): Command line response
        """
        additional_arguments = kwargs.pop('additional_arguments', '')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        return openstack_client_command(
            command_type='openstack',
            object_type='stack resource',
            action='list',
            arguments=f'{self.name} {additional_arguments}'
        )


def get_external_subnet_id(**kwargs):
    """
    str: Return the ENM external subnet id.

    Args:
        resource_list (list): list of resources

    Returns:
        (str): ENM external subnet resource id

    Raises:
        OpenstackObjectDoesNotExist: if openstack object does not exists
        IndexError: if ENM external subnet resource id not found
    """
    resource_list = kwargs.pop('resource_list')
    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    try:
        return [resource['physical_resource_id'] for resource in resource_list
                if 'enm_external_subnet' in resource.get('resource_name')][0]
    except IndexError:
        raise OpenstackObjectDoesNotExist(
            'Unable to find ENM external subnet resource id'
        )


def is_network_stack_required(is_vio_deployment, stack_list):
    """
    Check if internal network stack is required based on the deployment type.

    Returns:
        (bool): True | False
    """
    if is_vio_deployment and len(stack_list) == 1:
        return any('internal_network' in stack['Stack Name'] for stack in stack_list)
    return False


def get_stacks_in_project():
    """
    Return a list of stack objects from the current project, sorted by creation time.

    Returns:
        (obj): list of stack objects
    """
    return openstack_client_command(
        command_type='openstack',
        object_type='stack',
        action='list',
        arguments='--limit 1000000 --sort \'creation_time:asc\''
    )


def get_servers_in_project(**kwargs):
    """
    Return a list of server objects from the current project.

    Arguments:
        exclude_server (list): list server name(s) to be excluded

    Returns:
        (obj): list of server objects
    """
    exclude_server = kwargs.pop('exclude_server', list())

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    server_list = openstack_client_command(
        command_type='openstack',
        object_type='server',
        action='list',
        arguments='--limit 1000000'
    )
    return [server for server in server_list if server.get('Name') not in exclude_server]


def get_volumes_in_project(**kwargs):
    """
    Return a list of volume objects from the current project.

    Arguments:
        exclude_volume (list): list volume name(s) to be excluded

    Returns:
        (obj): volume objects
    """
    exclude_volume = kwargs.pop('exclude_volume', list())

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    volume_list = openstack_client_command(
        command_type='openstack',
        object_type='volume',
        action='list',
        arguments='--limit 1000000'
    )
    return [volume for volume in volume_list if volume.get('Name') not in exclude_volume]


def get_volume_snapshots_in_project(**kwargs):
    """
    Return a list of vol snapshot objects from current project.

    Arguments:
        exclude_volume (list): list of volume name(s) to be excluded

    Returns:
        (obj): volume snapshot objects
    """
    exclude_volume = kwargs.pop('exclude_volume', list())

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    volume_snapshot_list = openstack_client_command(
        command_type='openstack',
        object_type='volume snapshot',
        action='list',
        arguments='--limit 1000000'
    )
    return [volume for volume in volume_snapshot_list if volume.get('Name') not in exclude_volume]


def check_if_project_is_clean(**kwargs):
    """
    Report if the openstack project is not fully clean.

    Args:
        project_name (str): project name
        exclude_server (list): list server name(s) to be excluded
        exclude_volume (list): list of volume name(s) to be excluded
        exclude_network (list): list of network name(s) to be excluded
        is_vio_deployment (boolean): is project vio deployment

    Raises:
        RuntimeError: if issues found in project
    """
    # pylint: disable=R0914
    project_name = kwargs.pop('project_name')
    exclude_server = kwargs.pop('exclude_server')
    exclude_volume = kwargs.pop('exclude_volume')
    exclude_network = kwargs.pop('exclude_network')
    is_vio_deployment = kwargs.pop('is_vio_deployment')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info('Checking if the openstack project is fully clean before proceeding.')
    project_id = get_project_id_from_name(
        project_name=project_name,
        is_vio_deployment=is_vio_deployment
    )
    issues_found = 0
    stack_list = get_stacks_in_project()
    stack_list_count = len(stack_list)
    if stack_list_count != 0 and not is_network_stack_required(is_vio_deployment, stack_list):
        issues_found += 1
        LOG.error(
            'There are still %d stacks left in this project. %s',
            stack_list_count, json.dumps(stack_list, indent=4)
        )

    server_list = get_servers_in_project(exclude_server=exclude_server)
    server_list_count = len(server_list)
    if server_list_count != 0:
        issues_found += 1
        LOG.error(
            "There are still %d vms left in this project. %s",
            server_list_count, json.dumps(server_list, indent=4)
        )

    volume_list = get_volumes_in_project(exclude_volume=exclude_volume)
    volume_list_count = len(volume_list)
    if volume_list_count != 0:
        issues_found += 1
        LOG.error(
            'There are still %d volumes left in this project. %s',
            volume_list_count, json.dumps(volume_list, indent=4)
        )

    if not is_vio_deployment:
        network_list = openstack_client_command(
            command_type='openstack',
            object_type='network',
            action='list',
            arguments=f'--project {project_id}'
        )
        network_list_count = len(
            [network for network in network_list if network.get('Name') not in exclude_network]
        )
        if network_list_count != 0:
            issues_found += 1
            LOG.error(
                'There are still %d networks left in this project. %s',
                network_list_count, json.dumps(network_list, indent=4)
            )

    if issues_found != 0:
        raise RuntimeError(
            'A number of issues were found during the project checks (%d in total)' % issues_found
        )
    LOG.info('The project is fully clean')


def create_volume(**kwargs):
    """
    Create volume.

    Args:
        volume_name (str): volume name
        volume_size (str): size of the volume
        arguments (str, optional): arguments, defaults to empty string

    Returns:
        (str): volume id
    """
    volume_name = kwargs.pop('volume_name')
    volume_size = kwargs.pop('volume_size')
    arguments = kwargs.pop('arguments', '')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    volume = openstack_client_command(
        command_type='openstack',
        object_type='volume',
        action='create',
        arguments=f'--size {volume_size}  {arguments} {volume_name}'

    )
    wait_for_openstack_object_state(
        'volume', volume_name, 'available', 420, 10
    )
    LOG.info('Volume successfully created: %s', volume_name)
    return volume['id']


def create_volume_snapshot(**kwargs):
    """
    Create a volume snapshot.

    Args:
        volume_id (str): volume id
        snapshot_name (str): snapshot name
    """
    volume_id = kwargs.pop('volume_id')
    snapshot_name = kwargs.pop('snapshot_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    openstack_client_command(
        command_type='openstack',
        object_type='volume snapshot',
        action='create',
        arguments=f'--volume {volume_id} {snapshot_name} --force',
        return_an_object=False
    )
    wait_for_openstack_object_state(
        'volume snapshot', snapshot_name, 'available', 360, 10
    )
    LOG.info('Volume snapshot successfully created: %s', snapshot_name)


def create_image(image_name):
    """Create image.

    Returns:
        (obj): glance image details
    """
    glance_image_details = openstack_client_command(
        command_type='openstack',
        object_type='image',
        action='create',
        arguments=f'--public {image_name}'
    )
    return glance_image_details


def create_server(**kwargs):
    """
    Create server.

    Args:
        server_name (str): server name
        image_name (str): image name
        flavor (str): server flavor
        security_group_name (str): server security group name
        network_interface (str): server network interface
    """
    server_name = kwargs.pop('server_name')
    image_name = kwargs.pop('image_name')
    flavor = kwargs.pop('flavor')
    security_group_name = kwargs.pop('security_group_name')
    network_interface = kwargs.pop('network_interface')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    arguments = f'--image {image_name} --flavor {flavor} --nic {network_interface} \
--security-group {security_group_name} {server_name}'
    openstack_client_command(
        command_type='openstack',
        object_type='server',
        action='create',
        arguments=arguments
    )
    wait_for_openstack_object_state(
        'server', server_name, 'ACTIVE', 420, 10
    )
    LOG.info('Server successfully created: %s', server_name)


def delete_server(**kwargs):
    """
    Delete server.

    Args:
        server_name (str): server name
    """
    server_name = kwargs.pop('server_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    openstack_client_command(
        command_type='openstack',
        object_type='server',
        action='delete',
        arguments=server_name,
        return_an_object=False
    )
    wait_for_openstack_object_state(
        'server', server_name, 'DELETED', 420, 10
    )
    LOG.info('Server successfully deleted: %s', server_name)


class SecurityGroup:
    """
    This object contains fields and methods relating to a security group.

    Attributes:
        security_group_name (str): security group name
    """

    def __init__(self, **kwargs):
        """Create a security group rule."""
        self.security_group_name = kwargs.pop('security_group_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    def create(self):
        """Create security group."""
        openstack_client_command(
            command_type='openstack',
            object_type='security group',
            action='create',
            arguments=self.security_group_name
        )
        LOG.info('Security group successfully created: %s', self.security_group_name)

    def delete(self):
        """Delete security group."""
        openstack_client_command(
            command_type='openstack',
            object_type='security group',
            action='delete',
            arguments=self.security_group_name,
            return_an_object=False
        )
        LOG.info('Security group successfully deleted: %s', self.security_group_name)

    def create_rule(self, **kwargs):
        """
        Create security group rule.

        Args:
            security_group_rule (str): security group rule
        """
        security_group_rule = kwargs.pop('security_group_rule')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        openstack_client_command(
            command_type='openstack',
            object_type='security group rule',
            action='create',
            arguments=f'{security_group_rule} {self.security_group_name}'
        )
        LOG.info('Security group rule successfully created')


def get_private_ssh_key(**kwargs):
    """
    Return private SSH key from key pair stack.

    Args:
        key_pair_stack_name (str): key pair stack name

    Returns:
        (str): private ssh key

    Raises:
        KeyError: if unable to retrieve private key from key pair stack
    """
    key_pair_stack_name = kwargs.pop('key_pair_stack_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    stack = openstack_client_command(
        command_type='openstack',
        object_type='stack',
        action='show',
        arguments=key_pair_stack_name
    )
    try:
        return {'private_key': key.get('output_value') for key in stack.get('outputs')
                if 'private' in key.get('output_key')}['private_key']
    except KeyError:
        raise Exception('Unable to retrieve the private SSH key from: %s stack' %
                        key_pair_stack_name)


def get_public_ssh_key(**kwargs):
    """
    Return public SSH key from key pair stack.

    Args:
        key_pair_stack_name (str): key pair stack name

    Returns:
        (str): public ssh key

    Raises:
        KeyError: if unable to retrieve public key from key pair stack
    """
    key_pair_stack_name = kwargs.pop('key_pair_stack_name')
    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    stack = openstack_client_command(
        command_type='openstack',
        object_type='stack',
        action='show',
        arguments=key_pair_stack_name
    )
    try:
        return {'public_key': key.get('output_value') for key in stack.get('outputs')
                if 'public' in key.get('output_key')}['public_key']
    except KeyError:
        raise Exception(
            'Unable to retrieve the public SSH key from: %s stack' % key_pair_stack_name
        )


def get_volume_api_version():
    """Return the highest Cinder API version available.

    Returns:
        int: highest numeric version available
    """
    catalog_list = openstack_client_command(
        command_type='openstack',
        object_type='catalog',
        action='list',
        arguments='--column "Name"'
    )

    pattern = r"cinderv(\d+(\.\d+)?)$"
    available_volume_api_versions = []

    for catalog_item in catalog_list:
        match = re.search(pattern, catalog_item['Name'])
        if match:
            volume_api_version = match.group(1)
            available_volume_api_versions.append(volume_api_version)

    return max(available_volume_api_versions)
