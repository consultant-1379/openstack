"""Builds a snapshot Openstack Auto Deployer Docker image given a Gerrit commit."""
# pylint: disable=R0903,E0401,W0212
import argparse
import shlex
import ssl
import subprocess
import logging
import os
import urllib2

from ConfigParser import SafeConfigParser
from StringIO import StringIO


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s'
)
LOG = logging.getLogger(__name__)


class CliNonZeroExitCodeException(Exception):
    """
    Custom exception for expressing non zero exit codes.

    This custom exception is used to convey when a cli command
    has executed and returned a non zero exit code
    """


class FunctionalIdConfig(SafeConfigParser):
    """
    A class to read the functional ID and password to access REST API that require authentication.

    This class extends the SafeConfigParser
    and the read function reads the deployer
    functional id authentication config file.

    """

    def __init__(self):
        """Initialize a DeployerConfig object."""
        SafeConfigParser.__init__(self)
        auth_config_file = get_auth_config_file()
        self.readfp(auth_config_file)


def get_auth_config_file():
    """Retrieve authentication configuration file."""
    nexus_url = 'https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories'
    try:
        auth_config_file = urllib2.urlopen(
            nexus_url + '/releases/com/ericsson/de/ERICopenstackdeploy_CXP9033218/deployer_cfg.ini',
            context=ssl._create_unverified_context())
    except urllib2.HTTPError:
        raise Exception('Unable to retrieve functional ID authentication config file.')

    config_file_content = auth_config_file.read()
    config_file = StringIO(config_file_content)
    config_file.seek(0)
    return config_file


def run_cli_command(**kwargs):
    """
    Return result of given CLI command.

    Args:
        command (str): command to be executed

    Returns:
        command output (str):

    Raises:
        CliNonZeroExitCodeException: if the commands fails
        with a non-zero exit code

    """
    command = kwargs.pop('command')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    process = subprocess.Popen(
        shlex.split(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    process_std_out, process_std_error = process.communicate()
    if process.returncode != 0:
        raise CliNonZeroExitCodeException(
            'The command failed with exit code ' + str(process.returncode) +
            ', with the following output: ' + process_std_out +
            '\nError: ' + process_std_error
        )
    LOG.debug(process_std_out)
    LOG.debug(process_std_error)
    LOG.info('command execution complete.')
    return process_std_out


def main():
    """Build snapshot Openstack Auto Deployer Docker image from Gerrit commit."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--commit',
        help="""This is the Gerrit commit reference to be used to build a
                snapshot docker image e.g. refs/changes/44/10593144/1
        """,
        required=True
    )
    parser.add_argument(
        '--image-name',
        help="""This is the name given to the snapshot image, Default: deployer_snapshot
        """,
        default='deployer_snapshot',
        required=False
    )
    args = parser.parse_args()

    auth = FunctionalIdConfig()
    functional_id = auth.get('FUNCTIONAL_ID', 'user_id').lower()
    functional_id_password = auth.get('FUNCTIONAL_ID', 'password')
    dockerfile_path = os.path.join(os.getcwd(), 'docker/snapshot/Dockerfile')

    LOG.info('build Openstack Auto Deployer image with Gerrit commit: %s', args.commit)
    LOG.info('check for pre-existing docker images named: %s', args.image_name)
    image_filter_command = 'docker image ls --filter reference=' + args.image_name + \
        ' --format={{.ID}}'
    LOG.info(image_filter_command)
    existing_images = run_cli_command(command=image_filter_command)

    if existing_images:
        LOG.info('deleting pre-existing docker images named: %s', args.image_name)
        delete_image_command = 'docker image rm --force ' + existing_images.strip()
        LOG.info(delete_image_command)
        run_cli_command(command=delete_image_command)

    if not os.path.exists(dockerfile_path):
        raise IOError(
            'snapshot Dockerfile not found at the expected path: ' + dockerfile_path
        )

    build_image_command = 'docker build --build-arg COMMIT=' + args.commit + \
        ' --build-arg GIT_USER=' + functional_id + ' --build-arg GIT_PASSWORD=' + \
        functional_id_password + ' --tag ' + args.image_name + ':latest --file=' + \
        dockerfile_path + ' .'

    LOG.info(build_image_command.replace(functional_id_password, '*****'))
    run_cli_command(command=build_image_command)
    LOG.info('snapshot docker image: %s built successfully', args.image_name)


if __name__ == '__main__':
    main()
