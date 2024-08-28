"""This module contains common utility functions used by other modules."""
# pylint: disable=C0302

import os
import logging
import socket
import subprocess
import shlex
import zipfile
import tarfile
import shutil
import tempfile
import json
import time
import ssl
from functools import wraps
from urllib.parse import urlparse
import urllib3
import semantic_version
from retrying import retry
import paramiko
from paramiko import SSHClient, SSHException
import timeout_decorator
import requests
from . import configuration


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


class CliNonZeroExitCodeException(Exception):
    """
    Custom exception for expressing non zero exit codes.

    This custom exception is used to convey when a cli command
    has executed and returned a non zero exit code
    """


def is_ssh_exception(exception):
    """bool: Return True if SSH exception."""
    return isinstance(exception, SSHException)


def is_cli_exit_code_exception(exception):
    """bool: Return True if SSH exception."""
    return isinstance(exception, CliNonZeroExitCodeException)


def run_cli_command(command):
    """
    Run the given cli command and return the result.

    Args:
        command (str): The first parameter

    Returns:
        dictionary containing two keys,
        the standard_error, and standard_output strings

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    LOG.info('Running cli command (%s)', command)
    run_cli_command.previous_command_successful = False
    process = subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    process_standard_output, process_standard_error = process.communicate()
    if process.returncode != 0:
        raise CliNonZeroExitCodeException(
            'The command failed with exit code ' + str(process.returncode) +
            '. Heres the output: ' + process_standard_output.decode('utf-8') +
            '\nError: ' + process_standard_error.decode('utf-8')
        )
    LOG.debug(process_standard_output.decode('utf-8'))
    LOG.debug(process_standard_error.decode('utf-8'))
    run_cli_command.previous_command_successful = True
    LOG.info('cli command completed')
    return {
        'standard_output': process_standard_output.decode('utf-8'),
        'standard_error': process_standard_error.decode('utf-8')
    }


def download_file(**kwargs):
    """
    Download a file to a given directory.

    Args:
        url (str): url
        destination_directory (str): destination directory

    Returns:
        (str): local file path
    """
    url = kwargs.pop('url')
    destination_directory = kwargs.pop('destination_directory')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    logging.getLogger('requests').setLevel(logging.WARNING)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    local_file_path = os.path.join(destination_directory, os.path.basename(url))
    LOG.info('Downloading: %s to %s', url, local_file_path)
    with open(local_file_path, 'wb') as handle:
        response = requests.get(url, stream=True, verify=False)
        if response.status_code != '200':
            response.raise_for_status()

        for block in response.iter_content(chunk_size=1 << 20):
            handle.write(block)

    LOG.info('Download complete')
    return local_file_path


def unzip_file(filename, extract_directory):
    """
    Unzip a given file to the given directory.

    Function to unzip a file

    Args:
        filename (str): Full directory path with file name
        extract_directory (str): the directory to extract to
    """
    with zipfile.ZipFile(filename, 'r') as zip_ref:
        zip_ref.extractall(extract_directory)


def unzip_tar_gz(filename, extract_directory):
    """Unzip a tar.gz file format to the given directory.

    Args:
        filename (str): Full directory path with file name
        extract_directory (str): the directory to extract to
    """
    tar = tarfile.open(filename, 'r:gz')
    tar.extractall(extract_directory)
    tar.close()


def load_json_file(**kwargs):
    """
    Create a json object of the json content within a file.

    Args:
        file_path (str): file directory path

    Returns:
        json_data (obj): json object
    """
    file_path = kwargs.pop('file_path')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    with open(file_path) as file_data:
        json_data = json.load(file_data)
    return json_data


def print_stacks_created_message():
    """Print the final message given to users after all operations are completed."""
    LOG.info(
        'All stacks have created successfully. Now follow the relevant documentation to determine \
when they are fully ready'
    )


def remove_temporary_directory():
    """Remove the temporary directory."""
    shutil.rmtree(get_temporary_directory_path())


def get_vio_ca_cert(**kwargs):
    """
    Return VIO CA cert.

    Args:
        os_auth_url (str): OS authentication url

    Returns:
        (str): Digital certificate of the server
    """
    os_auth_url = kwargs.pop('os_auth_url')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    network_location = urlparse(os_auth_url).netloc
    address, port = network_location.split(':')
    LOG.info('Obtaining VIO CA cert from: %s', network_location)
    return ssl.get_server_certificate((address, int(port)), ca_certs=None)


def write_data_file(**kwargs):
    """
    Write data to a file on the local file system.

    Args:
        file_path (str): file directory path
        file_data (str): data to write in file

    Returns:
        (str): file directory path
    """
    file_path = kwargs.pop('file_path')
    file_data = kwargs.pop('file_data')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    with open(file_path, 'w') as file_object:
        file_object.write(file_data)
    LOG.info('File created: %s', file_path)
    return file_path


def setup_openstack_env_variables(openstack_env_variables):
    """
    Set required openstack environment variables.

    This function sets the required openstack environment variables
    that are necessary for running openstack cli commands
    """
    os_cacert = openstack_env_variables['os_cacert']
    if not os_cacert and is_vio_deployment(openstack_env_variables['os_auth_url']):
        os_cacert_data = get_vio_ca_cert(
            os_auth_url=openstack_env_variables['os_auth_url']
        )
        os_cacert = write_data_file(
            file_data=os_cacert_data,
            file_path=os.path.join(get_temporary_directory_path(), 'publicOS-' +
                                   openstack_env_variables['os_project_name'] + '.cer')
        )

    os.environ["OS_AUTH_URL"] = openstack_env_variables['os_auth_url']
    os.environ["OS_TENANT_NAME"] = openstack_env_variables['os_project_name']
    os.environ["OS_PROJECT_NAME"] = openstack_env_variables['os_project_name']
    os.environ["OS_USERNAME"] = openstack_env_variables['os_username']
    os.environ["OS_PASSWORD"] = openstack_env_variables['os_password']
    os.environ["OS_CACERT"] = os_cacert
    if '/v3' in openstack_env_variables['os_auth_url']:
        os.environ['OS_IDENTITY_API_VERSION'] = '3'
        os.environ['OS_PROJECT_DOMAIN_ID'] = 'default'
        os.environ['OS_USER_DOMAIN_NAME'] = 'Default'


def create_keystone_file(**kwargs):
    """
    Create keystone project.rc file.

    Args:
        os_auth_url (str): os authentication url
        os_project_id (str): os project id
        os_project_name (str): os project name
        os_username (str): os username
        os_password (str): os password
        os_volume_api_version (int): volume API version
        os_cacert_filepath (str): os cacert file directory path
        destination_directory (str): destination path directory

    Returns:
        file path (str): keystone file path
    """
    os_auth_url = kwargs.pop('os_auth_url')
    os_project_id = kwargs.pop('os_project_id')
    os_project_name = kwargs.pop('os_project_name')
    os_username = kwargs.pop('os_username')
    os_password = kwargs.pop('os_password')
    os_volume_api_version = kwargs.pop('os_volume_api_version')
    os_cacert_filepath = kwargs.pop('os_cacert_filepath')
    destination_directory = kwargs.pop('destination_directory')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    keystone_data = f"""
export OS_AUTH_URL={os_auth_url}
export OS_PROJECT_ID={os_project_id}
export OS_PROJECT_NAME={os_project_name}
export OS_USERNAME={os_username}
export OS_PASSWORD={os_password}
export OS_VOLUME_API_VERSION={os_volume_api_version}
"""

    if os_cacert_filepath:
        keystone_data = f"""
{keystone_data}
export OS_CACERT={os_cacert_filepath}
"""

    if '/v3' in os_auth_url:
        keystone_data = f"""
{keystone_data}
export OS_IDENTITY_API_VERSION=3
export OS_INTERFACE=public
export OS_PROJECT_DOMAIN_ID=default
export OS_USER_DOMAIN_NAME=Default
"""

    keystone_file_path = os.path.join(destination_directory, os_project_name + '_project.rc')
    write_data_file(
        file_data=keystone_data.replace('  ', ''),
        file_path=keystone_file_path
    )
    return keystone_file_path


def cached(function):
    """
    Decorate a given function and arguments to cache its results.

    This decorator can be used on a function, to cache the results of that function
    """
    cache = {}

    @wraps(function)
    def wrapper(*args, **kwargs):
        """
        dict: Wrap the original function to cache its results.

        This wraps the original function passed in and performs the caching on it
        if it has not got the result already in memory
        """
        key = (args, frozenset(kwargs.items()))
        if key in cache:
            return cache[key]

        return_value = function(*args, **kwargs)
        cache[key] = return_value
        return return_value
    return wrapper


@cached
def get_product_offering_details(**kwargs):
    """
    Return a list of product offering details.

    This function returns the list of product offering details associated
    with the given product offering

    Args:
        product_offering (str): product offering

    Returns:
        (list): product offering details
    """
    product_offering = kwargs.pop('product_offering')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    rollout_details = json.loads(
        CONFIG.get('OFFERING_DETAILS', 'offering_details')
    )
    product_offering_details = {}
    product_offering_details.update(rollout_details['defaults'])
    product_offering_details.update(rollout_details[product_offering])
    return product_offering_details


@cached
def get_temporary_directory_path():
    """
    Create a temporary directory and returns the path.

    Returns:
        file path (str): temporary file directory path
    """
    return tempfile.mkdtemp()


@cached
def is_vio_deployment(os_auth_url):
    """
    Return true if VIO deployment.

    Args:
        os_auth_url (str): os authentication url

    Returns:
        (bool): True | False
    """
    network_location = urlparse(os_auth_url).netloc
    LOG.info('Checking if this deployment is a VIO deployment.')
    proc = subprocess.Popen([f'openssl s_client -connect {network_location} < /dev/null'],
                            stdout=subprocess.PIPE, shell=True)
    (output, _err) = proc.communicate()
    if 'O = VMware, OU = VIO' in str(output):
        LOG.info('VIO deployment type detected.')
        return True
    return False


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=120, wait_fixed=10000)
def sftp_file(**kwargs):
    """
    SFTP a file to a given destination.

    This function can ftp a local file to a remote server
    via sftp, with the given username and password

    Args:
        ip_address (str): ip address
        username (str): user name
        password (str, optional): user password, defaults to None
        private_key (str, optional): private key, defaults to None
        local_file_path (str): local file directory path
        remote_file_path (str): remote file directory path
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password', None)
    private_key = kwargs.pop('private_key', None)
    local_file_path = kwargs.pop('local_file_path')
    remote_file_path = kwargs.pop('remote_file_path')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info('Uploading: %s to %s into %s', local_file_path, ip_address, remote_file_path)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    transport = paramiko.Transport((ip_address, 22))
    if password is None:
        pkey = paramiko.RSAKey.from_private_key(open(private_key))
        transport.connect(username=username, pkey=pkey)
    else:
        transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.put(local_file_path, remote_file_path)
    sftp.close()
    transport.close()


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=120, wait_fixed=10000)
@retry(retry_on_exception=is_cli_exit_code_exception, stop_max_attempt_number=10, wait_fixed=10000)
def run_notimeout_ssh_command(**kwargs):
    """
    Run a given command on a remote server via ssh with no timeout decorator.

    If the return code is non zero and ignore_exit_code
    flag is False the function raises an exception

    Args:
        ip_address (str): ip address
        username (str): username
        password (str, optional): user password, defaults to None
        private_key (str, optional): private key, defaults to None
        command (str): command
        suppress_exception (boolean, optional): suppress_exception, defaults to False

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non zero exit code
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password', None)
    private_key = kwargs.pop('private_key', None)
    command = kwargs.pop('command')
    suppress_exception = kwargs.pop('suppress_exception', False)

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info('Running command (%s) over ssh on %s', command, ip_address)
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.getLogger('paramiko').setLevel(logging.WARNING)
    if password is None:
        pkey = paramiko.RSAKey.from_private_key(open(private_key))
        client.connect(ip_address, username=username, pkey=pkey, look_for_keys=False)
    else:
        client.connect(ip_address, username=username, password=password, look_for_keys=False)
    _, stdout, stderr = client.exec_command(command, get_pty=True)

    while not stdout.channel.exit_status_ready():
        print(stdout.channel.recv(1024).decode('utf-8'))
    if stdout.channel.recv_exit_status() != 0 and not suppress_exception:
        raise CliNonZeroExitCodeException(
            'The remote ssh command failed: %s' % str(stderr)
        )
    client.close()


def run_noretry_ssh_command(**kwargs):
    """
    Run a given command on a remote server via ssh with no retry decorators.

    If the return code is non zero and ignore_exit_code
    flag is False the function raises an exception

    Args:
        ip_address (str): ip address
        username (str): username
        password (str, optional): user password, defaults to None
        private_key (str, optional): private key, defaults to None
        command (str): command
        suppress_exception (boolean, optional): suppress_exception, defaults to False

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non zero exit code
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password', None)
    private_key = kwargs.pop('private_key', None)
    command = kwargs.pop('command')
    suppress_exception = kwargs.pop('suppress_exception', False)

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info('Running command (%s) over ssh on %s', command, ip_address)
    client = SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    logging.getLogger('paramiko').setLevel(logging.WARNING)
    if password is None:
        pkey = paramiko.RSAKey.from_private_key(open(private_key))
        client.connect(ip_address, username=username, pkey=pkey, look_for_keys=False)
    else:
        client.connect(ip_address, username=username, password=password, look_for_keys=False)
    _, stdout, stderr = client.exec_command(command, get_pty=True)

    while not stdout.channel.exit_status_ready():
        print(stdout.channel.recv(1024).decode('utf-8'))
    if stdout.channel.recv_exit_status() != 0 and not suppress_exception:
        raise CliNonZeroExitCodeException(
            'The remote ssh command failed: %s' % str(stderr)
        )
    client.close()


def run_ssh_command(**kwargs):
    """
    Run a given command on a remote server via ssh, timeout if takes longer than 300 seconds.

    If the return code is non zero and ignore_exit_code
    flag is False the function raises an exception

    Args:
        ip_address (str): ip address
        username (str): username
        password (str, optional): user password, defaults to None
        private_key (str, optional): private key, defaults to None
        command (str): command
        suppress_exception (boolean): suppress_exception, defaults to False
        timeout_value (int, optional): number in seconds for a timeout, defaults to 900
        max_attempts (int, optional): number of maximum attempts to retry command, defaults to 10

    Returns:
        (obj): SSH Response

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non zero exit code
    """
    timeout_value = kwargs.pop('timeout_value', 900)
    max_attempts = kwargs.pop('max_attempts', 10)

    @retry(
        retry_on_exception=is_ssh_exception,
        stop_max_attempt_number=120,
        wait_fixed=10000
    )
    @retry(
        retry_on_exception=is_cli_exit_code_exception,
        stop_max_attempt_number=max_attempts,
        wait_fixed=10000
    )
    @timeout_decorator.timeout(
        timeout_value,
        use_signals=False,
        timeout_exception=CliNonZeroExitCodeException
    )
    def inner(**kwargs):
        ip_address = kwargs.pop('ip_address')
        username = kwargs.pop('username')
        password = kwargs.pop('password', None)
        private_key = kwargs.pop('private_key', None)
        command = kwargs.pop('command')
        suppress_exception = kwargs.pop('suppress_exception', False)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info('Running command (%s) over ssh on %s', command, ip_address)
        logging.getLogger('paramiko').setLevel(logging.WARNING)
        transport = paramiko.Transport((ip_address, 22))
        if password is None:
            pkey = paramiko.RSAKey.from_private_key(open(private_key))
            transport.connect(username=username, pkey=pkey)
        else:
            transport.connect(username=username, password=password)
        channel = transport.open_channel('session')
        channel.set_combine_stderr(True)
        channel.get_pty()
        channel.exec_command(command)
        exit_code = channel.recv_exit_status()
        ssh_response = channel.recv(9999).decode('utf-8')
        transport.close()
        if exit_code != 0 and not suppress_exception:
            LOG.error(
                'The remote ssh command: %s failed with exit code: %s . Error message: %s',
                str(command), str(exit_code), str(ssh_response)
            )
            raise CliNonZeroExitCodeException
        return ssh_response
    return inner(**kwargs)


def reset_password(**kwargs):
    """
    Reset a servers password at initial login prompt if asked.

    This function will attempt to login with an existing password and if prompted
    change the password to the new password passed in. The password used is returned.

    Args:
        ip_address (str): ip address
        username (str): username
        current_password (str): user current password
        new_password (str): user new password

    Returns:
        (str): new password

    Raises:
        SSHException: if unable to establish SSH connection
        AuthenticationException: if the Authentication fails
        RuntimeError: if unable to establish SSH connection
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    current_password = kwargs.pop('current_password')
    new_password = kwargs.pop('new_password')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    logging.getLogger('paramiko').setLevel(logging.WARNING)
    max_check_attempts = 120
    check_attempt = 1
    ssh_connection_working = False
    while check_attempt < max_check_attempts:
        LOG.info(
            'Waiting for %s to to be sshable. Attempt %d of %d', ip_address, check_attempt,
            max_check_attempts
        )
        try:
            transport = paramiko.Transport((ip_address, 22))
            transport.connect(username=username, password=current_password)
            ssh_connection_working = True
            break
        except (
                paramiko.ssh_exception.SSHException,
                paramiko.ssh_exception.AuthenticationException
        ):
            pass

        LOG.info("Sleeping for 10 seconds as its not sshable yet")
        time.sleep(10)
        check_attempt += 1
        continue

    if not ssh_connection_working:
        raise RuntimeError(
            'Could not ssh after %d attempts, giving up' % max_check_attempts
        )

    channel = transport.open_channel(kind="session")
    channel.get_pty()
    channel.invoke_shell()
    shell_output = ''
    while 1:
        shell_output += channel.recv(9999).decode('utf-8')
        if shell_output.endswith('~]$ '):
            LOG.info('The current password %s didn\'t require resetting', current_password)
            return current_password
        if shell_output.endswith('UNIX password: '):
            break
    channel.send(current_password + '\n')

    shell_output = ''
    while not shell_output.endswith('New password: '):
        shell_output += channel.recv(9999).decode('utf-8')
    channel.send(new_password + '\n')

    shell_output = ''
    while not shell_output.endswith('Retype new password: '):
        shell_output += channel.recv(9999).decode('utf-8')
    channel.send(new_password + '\n')

    max_wait_attempts = 30
    wait_attempt = 1
    while wait_attempt < max_wait_attempts:
        if channel.closed:
            break
        time.sleep(1)

    LOG.info('Attempting to verify connection with the changed password now')
    transport = paramiko.Transport((ip_address, 22))
    transport.connect(username=username, password=new_password)
    transport.close()
    return new_password


def save_json_string_to_disk(**kwargs):
    """
    Save a given json string to the given file path.

    Args:
        file_path (str): file path to store json string
        json_string (obj): json string
    """
    file_path = kwargs.pop('file_path')
    json_string = kwargs.pop('json_string')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    with open(file_path, 'w') as file_object:
        file_object.write(
            json.dumps(
                json_string,
                indent=4,
                sort_keys=False
            )
        )


def get_artifact_version_from_url(url):
    """
    Return the version of an artifact from a given URL.

    Args:
        url (str): artifact url

    Returns:
        (str): artifact version from URL
    """
    filename = os.path.basename(url)
    if 'vnflcm-cloudtemplates' in filename:
        modified_filename = filename.replace('vnflcm-cloudtemplates-', '')
        version = modified_filename.replace('.tar.gz', '')
    else:
        filename_minus_extension = '.'.join(filename.split('.')[:-1]).replace('.tar', '')
        version = '-'.join(filename_minus_extension.split('-')[1::])
    return version


def get_template_by_ip_type(**kwargs):
    """
    Return intrastructure resource template based on network type dual, v4, 4 or 6.

    Args:
        infrastructure_resource (str): infrastructure resource
        ip_version (str): ip version

    Returns:
        resource template (str): resource template
    """
    infrastructure_resource = kwargs.pop('infrastructure_resource')
    ip_version = kwargs.pop('ip_version')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    resource_template = CONFIG.get(infrastructure_resource, ip_version.lower())

    return resource_template


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=10, wait_fixed=10000)
def get_installed_artifact_version(**kwargs):
    """
    Get installed artifact information using rpm command.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        artifact_name (str): artifact name

    Returns:
        (str): installed artifact version

    Raises:
        SSHException: if artifact is not installed or invalid artifact version
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    artifact_name = kwargs.pop('artifact_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    installed_artifact = run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command='rpm -q ' + artifact_name + ' --queryformat \'%{VERSION}-%{RELEASE}\'',
        suppress_exception=True
    )
    if ('is not installed' not in installed_artifact and not
            semantic_version.validate(installed_artifact)):
        LOG.info('Retrying to get information on %s...', artifact_name)
        raise SSHException()

    LOG.info('Artifact information on %s: %s', ip_address, installed_artifact)
    return installed_artifact.strip()


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=20, wait_fixed=10000)
def get_file_content(**kwargs):
    """
    Get file content.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        file_path (str): file directory path

    Raises:
        SSHException: if unable to retrieve file contents
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    file_path = kwargs.pop('file_path')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    file_contents = run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command='cat ' + file_path
    )

    if not file_contents:
        LOG.info('Retrying to get %s content...', file_path)
        raise SSHException()

    LOG.info('%s content: \n%s', file_path, file_contents)


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=10, wait_fixed=10000)
def get_latest_file_version(**kwargs):
    """
    str: Return the latest version of file.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        file_name_search (str): file name search
        location (str): file location

    Returns:
        (str): latest file name

    Raises:
        SSHException: if unable to get latest file name
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    file_name_search = kwargs.pop('file_name_search')
    location = kwargs.pop('location')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    ssh_command = f'ls -t {location}/{file_name_search} | head -n 1'
    file_name = run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command=ssh_command
    )

    if not file_name:
        LOG.info('Retrying to get latest file name...')
        raise SSHException()

    LOG.info('Got file name: %s', file_name)
    return file_name


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=20, wait_fixed=10000)
def media_already_exists(**kwargs):
    """
    Return True if media file already exists.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        location (str): media file location
        filename (str): media file name

    Returns:
        (bool): True | False

    Raises:
        SSHException: if unable to retrieve media file
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    location = kwargs.pop('location')
    filename = kwargs.pop('filename')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    command_output = run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command=f'[ -f {os.path.join(location, filename)} ] && echo "Found" || echo "Not found"'
    )

    if not command_output:
        LOG.info('Retrying: does "%s" exist in this location "%s"...', filename, location)
        raise SSHException()

    if 'Found' in str(command_output):
        LOG.info('%s exists in this location %s...', filename, location)
        return True
    return False


def remove_contents_of_directory(**kwargs):
    """
    Remove contents of directory.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        location (str): file location
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    location = kwargs.pop('location')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command=f'rm -rf {os.path.join(location, "*")}'
    )


def execute_uploaded_script(**kwargs):
    """
    Upload and execute a given script to the VNF-LCM VM.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        upload_script_path (str): upload script directory path
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    upload_script_path = kwargs.pop('upload_script_path')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    filename = os.path.basename(upload_script_path)
    base_filename = filename.split(".")[0]
    LOG.info(
        'Uploading the file: %s to lcm as user: %s and password: %s', upload_script_path,
        username, password
    )
    ssh_command = f'chmod 777 /home/{username}/{filename} ; sudo /home/{username}/{filename} > \
/tmp/{base_filename}.log'

    sftp_file(
        ip_address=ip_address,
        username=username,
        password=password,
        local_file_path=upload_script_path,
        remote_file_path=f'/home/{username}/{filename}'
    )
    run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command=ssh_command
    )


def save_private_key(**kwargs):
    """
    Save a local ssh key file.

    Args:
        private_key (str): local ssg private key
        file_path (str): ssh key file path

    Returns:
        (str): ssh key file path
    """
    private_key = kwargs.pop('private_key')
    file_path = kwargs.pop('file_path')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    key_file = open(file_path, 'w')
    key_file.write(private_key)
    os.system(f"chmod 600 {file_path}")
    return file_path


@retry(stop_max_attempt_number=10, wait_fixed=3000)
def get_host_response_time(**kwargs):
    """
    Return the time taken to recieve a ping response from a host.

    Args:
        hostname (str): host name

    Returns:
        (str): host response time

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non zero exit code
    """
    hostname = kwargs.pop('hostname')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    response_times = []
    while len(response_times) < 3:
        start_time = time.time()
        ping_process = subprocess.Popen(
            ['ping', '-c', '1', hostname],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process_standard_output, process_standard_error = ping_process.communicate()
        if ping_process.returncode != 0:
            raise CliNonZeroExitCodeException(
                'The command failed with exit code ' +
                str(ping_process.returncode) + '. Heres the output: ' +
                process_standard_output.decode() + '\nError: ' + process_standard_error.decode()
            )
        response_times.append(abs(start_time - time.time()))

    return min(response_times)


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=20, wait_fixed=10000)
def extract_gunzipfile_contents(**kwargs):
    """
    Return filename of extracted gunzip file.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        file_path (str): gunzip file path
        package_name (str): package name

    Returns:
        (str): gunzip filename
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    file_path = kwargs.pop('file_path')
    package_name = kwargs.pop('package_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    package_path = os.path.join(file_path, package_name)
    run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command=f'gunzip -fc {package_path} > {package_path.replace(".gz", "")}'
    )
    LOG.info('%s extracted...', package_name)
    return package_name.replace('.gz', '')


@retry(retry_on_exception=is_ssh_exception, stop_max_attempt_number=20, wait_fixed=10000)
def get_remote_tarfile_contents(**kwargs):
    """
    Return the contents of a given tar file.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        file_path (str): gunzip file path
        package_name (str): package name

    Returns:
        (list): Tar file content

    Raises:
        SSHException: if invalid/missing data exists
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    file_path = kwargs.pop('file_path')
    package_name = kwargs.pop('package_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    contents = run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command=f"echo $(tar -tf {os.path.join(file_path, package_name)})"
    )
    LOG.info('%s contains: %s', package_name, str(contents))
    if len(contents.split()) == 0:
        LOG.warning('Missing/Invalid data returned: %s', str(contents))
        raise SSHException()
    return contents.split()


def extract_remote_tarfile(**kwargs):
    """
    Extract the contents of a given tar file.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        file_path (str): gunzip file path
        package_name (str): package name

    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    file_path = kwargs.pop('file_path')
    package_name = kwargs.pop('package_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info(
        'Extracting package: %s on: %s as user: %s', ip_address, package_name, username
    )
    ssh_command = f'cd {file_path}; tar xvf {package_name}'
    run_ssh_command(
        ip_address=ip_address,
        username=username,
        password=password,
        command=ssh_command
    )


def install_rpm_package(**kwargs):
    """
    Install package.

    Args:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        file_path (str): gunzip file path
        package_name (str): package name
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    file_path = kwargs.pop('file_path')
    package_name = kwargs.pop('package_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info(
        'Installing package: %s on: %s as user: %s', package_name, ip_address, username
    )
    install_rpm = True
    yum_action = 'install'
    artifact_name = package_name.split('-')[0]
    installed_version = get_installed_artifact_version(
        ip_address=ip_address,
        username=username,
        password=password,
        artifact_name=artifact_name
    )
    artifact_version = get_artifact_version_from_url(package_name)
    artifact_version = artifact_version.replace('.noarch', '')
    if 'snapshot' not in installed_version.lower():
        installed_version = installed_version.split('-')[0]

    if 'is not installed' not in installed_version.lower():
        if (semantic_version.Version(installed_version) ==
                semantic_version.Version(artifact_version)):
            LOG.info('Versions are the same, not installing %s', package_name)
            install_rpm = False
        elif (semantic_version.Version(installed_version) >
              semantic_version.Version(artifact_version)):
            LOG.info('Downgrading %s version.', package_name)
            yum_action = 'downgrade'

    if install_rpm is True:
        ssh_command = f'yum {yum_action} -y {file_path}/{package_name}'
        run_ssh_command(
            ip_address=ip_address,
            username=username,
            password=password,
            command=ssh_command
        )


def copy_file(**kwargs):
    """
    Copy file source to destination directory.

    Args:
        src (str): source file pah
        dest (str): destination file path
    """
    src = kwargs.pop('src')
    dest = kwargs.pop('dest')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info('Copying %s to destination: %s', dest, src)
    shutil.copyfile(src, dest)


def is_valid_dns_hostname(**kwargs):
    """Return True if DNS hostname exists otherwise False."""
    hostname = kwargs.pop('hostname')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    try:
        socket.gethostbyname_ex(hostname)
        return True
    except socket.gaierror:
        return False
