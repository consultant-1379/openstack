"""This file contains logic relating to the VIO Virtual Management Server."""

import json
import logging
import os
import re
import threading
import _thread

from . import configuration
from . import dit
from . import openstack
from . import utils

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


class InternalVirtualManagementServer:
    """Represents a VIO Internal Virtual Managment Server instance.

    This class represents a VIO Internal Virtual Managment Server instance and
    provides functions to manage VIO Internal Virtual Managment Server related tasks.

    Attributes:
        ip_address (str): ip address
        username (str): username
        password (str): user password
        artifact_json (dict, optional): artifact json, defaults to None
    """

    def __init__(self, **kwargs):
        """Initialize a VIO Internal Virtual Management Server object."""
        self.ip_address = kwargs.pop('ip_address')
        self.username = kwargs.pop('username')
        self.password = kwargs.pop('password')
        self.artifact_json = kwargs.pop('artifact_json', None)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.artifact_directory = CONFIG.get('vio', 'artifacts_dir')
        self.temp_directory = utils.get_temporary_directory_path()

    def get_private_ssh_key(self, **kwargs):
        """
        Return private ssh key.

        Args:
            key_pair_name (str): Key pair name

        Returns:
            (str): private ssh key
        """
        key_pair_name = kwargs.pop('key_pair_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        private_key = ''
        while private_key == '':
            private_key = utils.run_ssh_command(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
                command='cat ' + os.path.join(CONFIG.get('vio', 'config_dir'),
                                              key_pair_name + '.pem')
            )
        return private_key.strip()

    def create_artifact_directory(self):
        """Create artifact directory on VMS."""
        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command='mkdir -p ' + self.artifact_directory
        )

    def download_media(self):
        """Download required media."""
        media_url = self.artifact_json['media_details'][CONFIG.get('CXPNUMBERS', 'ENM_ISO')]
        media_file_name = os.path.basename(media_url)
        if '_KGB+N' in media_file_name:
            utils.sftp_file(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
                local_file_path=os.path.join(self.temp_directory, media_file_name),
                remote_file_path=os.path.join(self.artifact_directory, media_file_name)
            )
        else:
            vms_media_file_path = os.path.join(self.artifact_directory, media_file_name)
            utils.run_notimeout_ssh_command(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
                command=f'curl --fail --silent --show-error {media_url} -o {vms_media_file_path}'
            )

    def configure_openstack(self, **kwargs):
        """
        Execute configure openstack script.

        Args:
            action (str): action to configure
            task (str): adding task to configure
        """
        action = kwargs.pop('action')
        task = kwargs.pop('task')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        utils.run_notimeout_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=CONFIG.get('vio', 'configure_openstack') + ' -a ' + action + ' -e ' +
            CONFIG.get('vio', 'enm_sed_file_path') +
            ' -l ' + CONFIG.get('vio', 'lcm_sed_file_path') + ' -t \"' + task + '\" -y -d'
        )

    def run_profile(self, **kwargs):
        """
        Run a profile.

        Args:
            profile (str): vio profile name
        """
        profile = kwargs.pop('profile')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        ssh_command = (CONFIG.get('vio', 'deploy_senm') + ' -y -d -e ' +
                       CONFIG.get('vio', 'enm_sed_file_path') + ' -m ' +
                       CONFIG.get('vio', 'lcm_sed_file_path') +
                       ' -p ' + profile)

        utils.run_notimeout_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=ssh_command
        )


class DeploymentVirtualManagementServer:
    """Represents a VIO Deployment Virtual Management Server instance.

    This class represents a VIO Deployment Virtual Management Server
    instance and provides functions to manage
    VIO Deployment Virtual Management Server related tasks.

    Attributes:
        ip_address (str): ip address
        username (str): username
        password (str): password
        os_project_details (str): os project details
        artifact_json (obj): artifact json
    """

    def __init__(self, **kwargs):
        """Initialize a VIO Deployment Virtual Management Server object."""
        self.ip_address = kwargs.pop('ip_address')
        self.username = kwargs.pop('username')
        self.password = kwargs.pop('password')
        self.os_project_details = kwargs.pop('os_project_details')
        self.artifact_json = kwargs.pop('artifact_json')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.artifact_directory = CONFIG.get('vio', 'artifacts_dir')
        self.temp_directory = utils.get_temporary_directory_path()

    def update_resolv_config(self, **kwargs):
        """
        Update the /etc/resolv.config on DVMS.

        Args:
            vio_dvms_object (obj): vio dvms object to update on DVMS
        """
        vio_dvms_object = kwargs.pop('vio_dvms_object')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info(
            'Updating /etc/resolv.config on DVMS as user: ' +
            self.username + '. Input: ' + vio_dvms_object['ntp_ip_1'] +
            ' and ' + vio_dvms_object['ntp_ip_2']
        )

        ssh_commands = []
        ssh_commands.append('if ! grep -Fxq \"nameserver ' +
                            vio_dvms_object['ntp_ip_1'] +
                            '\" /etc/resolv.conf ; then echo -e nameserver ' +
                            vio_dvms_object['ntp_ip_1'] +
                            ' | tee -a /etc/resolv.conf ; fi')
        ssh_commands.append('if ! grep -Fxq \"nameserver ' +
                            vio_dvms_object['ntp_ip_2'] +
                            '\" /etc/resolv.conf ; then echo -e nameserver ' +
                            vio_dvms_object['ntp_ip_2'] +
                            ' | tee -a /etc/resolv.conf ; fi')

        for ssh_command in ssh_commands:
            utils.run_ssh_command(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
                command=ssh_command
            )

    def create_directories(self):
        """Create directories on DVMS."""
        LOG.info('Creating directories on DVMS as user: %s', self.username)
        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=f'mkdir -p {CONFIG.get("vio", "artifacts_dir")}'
        )
        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=f'mkdir -p {CONFIG.get("vio", "config_dir")}'
        )

    def download_vio_media(self):
        """Downloading Media to DVMS."""
        LOG.info('Downloading media on DVMS as as user: %s', self.username)
        media_threads = []
        thread_id = 1
        media_key = CONFIG.get('CXPNUMBERS', 'ENM_ISO')
        media_key_value = self.artifact_json['media_details'][media_key]
        media_file_name = os.path.basename(media_key_value)
        media_already_exists = utils.media_already_exists(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            location=CONFIG.get('vio', 'artifacts_dir'),
            filename=media_file_name
        )
        if '_KGB+N' in media_file_name:
            utils.sftp_file(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
                local_file_path=os.path.join(self.temp_directory, media_file_name),
                remote_file_path=os.path.join(self.artifact_directory, media_file_name)
            )
        elif not media_already_exists:
            media_thread = DownloadMediaThread(thread_id,
                                               media_key,
                                               media_key_value,
                                               self.ip_address,
                                               self.username,
                                               self.password)
            media_thread.daemon = True
            media_threads.append(media_thread)
            thread_id = thread_id + 1

        for media_key in self.artifact_json:
            if media_key in ('media_details', 'vnflcm_details'):
                continue

            media_key_value = list(self.artifact_json[media_key].values())[0]
            media_already_exists = utils.media_already_exists(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
                location=CONFIG.get('vio', 'artifacts_dir'),
                filename=os.path.basename(media_key_value)
            )
            if not media_already_exists:
                media_thread = DownloadMediaThread(thread_id,
                                                   media_key,
                                                   media_key_value,
                                                   self.ip_address,
                                                   self.username,
                                                   self.password)
                media_thread.daemon = True
                media_threads.append(media_thread)
                thread_id = thread_id + 1

        # Start Threads
        for item in media_threads:
            item.start()

        # Wait for all of them to finish
        for item in media_threads:
            item.join()

    def download_enm_media(self, **kwargs):
        """
        Download required media.

        Args:
            media_artifact_mappings (Str): ENM media artifact mappings
            image_name_postfix (str): image name postfix

        Returns:
            (bool): True | False
        """
        media_artifact_mappings = kwargs.pop('media_artifact_mappings')
        image_name_postfix = kwargs.pop('image_name_postfix')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        media_prep_required = False
        media_details = self.artifact_json['media_details']
        for cxp_number, media_url in media_details.items():
            media_file_name = os.path.basename(media_url)
            image_name = re.sub(r'\.iso|\.qcow2', '' if image_name_postfix is None
                                else image_name_postfix, media_file_name)
            if self.image_exists(image_name=image_name) is False:
                if CONFIG.get('CXPNUMBERS', 'ENM_ISO') in media_file_name:
                    media_prep_required = True
                if media_artifact_mappings.get(cxp_number):
                    continue
                if '_KGB+N' in media_file_name:
                    utils.sftp_file(
                        ip_address=self.ip_address,
                        username=self.username,
                        password=self.password,
                        local_file_path=os.path.join(self.temp_directory, media_file_name),
                        remote_file_path=os.path.join(self.artifact_directory, media_file_name)
                    )
                else:
                    media_file_path = os.path.join(self.artifact_directory, media_file_name)
                    utils.run_notimeout_ssh_command(
                        ip_address=self.ip_address,
                        username=self.username,
                        password=self.password,
                        command=f'curl --fail --silent --show-error {media_url} -o \
{media_file_path}'
                    )

        for artifact_json_key in ['vmware_guest_tools_details', 'vnflcm_details']:
            media_url = list(self.artifact_json[artifact_json_key].values())[0]
            media_file_name = os.path.basename(media_url)
            self.delete_image_on_dvms(
                image_path=os.path.join(self.artifact_directory, media_file_name)
            )
            utils.run_notimeout_ssh_command(
                ip_address=self.ip_address,
                username=self.username,
                password=self.password,
                command=f'curl --fail --silent --show-error {media_url} -o \
{os.path.join(self.artifact_directory, media_file_name)}'
            )
        return media_prep_required

    @classmethod
    def image_exists(cls, **kwargs):
        """
        Return True if image is already in glance.

        Args:
            image_name (str): image name

        Returns:
            (bool): True | False
        """
        image_name = kwargs.pop('image_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        image_list = openstack.openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='list',
            arguments='--limit 1000000'
        )
        return any(image['Name'] == image_name for image in image_list)

    def delete_image_on_dvms(self, **kwargs):
        """
        Delete image on DVMS.

        Args:
            image_path (str): image directory path
        """
        image_path = kwargs.pop('image_path')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=f'rm -f {image_path}'
        )

    def configure_dvms_for_platform(self, **kwargs):
        """
        Configure the DVMS for VIO Platform Installation.

        Args:
            profile (str): user profile
        """
        profile = kwargs.pop('profile')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info(
            'Configuring the DVMS for VIO Platform installation as user: %s', self.username
        )
        ssh_command = (CONFIG.get('vio', 'deploy_senm') + ' -y -d -e ' +
                       CONFIG.get('vio', 'enm_sed_file_path') + ' -m ' +
                       CONFIG.get('vio', 'lcm_sed_file_path') + ' -p ' + profile)

        utils.run_noretry_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=ssh_command
        )

    def install_vio_platform(self, **kwargs):
        """
        Install the VIO Platform.

        Args:
            vio_profile_list (str): list of vio profiles
        """
        vio_profile_list = kwargs.pop('vio_profile_list')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info('Installing the VIO Platform as user: %s', self.username)
        ssh_command = (CONFIG.get('vio', 'deploy_senm') + ' -y -d -e ' +
                       CONFIG.get('vio', 'enm_sed_file_path') + ' -m ' +
                       CONFIG.get('vio', 'lcm_sed_file_path') + ' -p ' +
                       vio_profile_list)

        utils.run_noretry_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=ssh_command
        )

        log_file_name = utils.get_latest_file_version(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            file_name_search='edp_autodeploy.*.log',
            location=CONFIG.get('vio', 'log_dir')
        )
        LOG.info(
            'Install VIO Platform command is complete. Log file: dvms: %s', log_file_name
        )

    def delete_stage_log(self):
        """Delete stage log."""
        utils.run_notimeout_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=f'rm -f {CONFIG.get("vio", "stage_log_path")}'
        )

    def upload_cacert_file(self):
        """Upload os ca cert file."""
        os_cacert_file_name = f'publicOS-{self.os_project_details["os_project_name"]}.cer'
        upload_file(
            name='OS CACERT',
            file_name=os_cacert_file_name,
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            document_file_path=os.path.join(self.temp_directory, os_cacert_file_name)
        )

    def upload_keystone_file(self):
        """Upload os keystone file."""
        os_project_id = openstack.get_resource_attribute(
            identifier=self.os_project_details['os_project_name'],
            resource_type='project',
            attribute='id'
        )
        os_cacert_filename = f'publicOS-{self.os_project_details["os_project_name"]}.cer'
        keystone_file_path = utils.create_keystone_file(
            os_auth_url=self.os_project_details['os_auth_url'],
            os_project_id=os_project_id,
            os_project_name=self.os_project_details['os_project_name'],
            os_username=self.os_project_details['os_username'],
            os_password=self.os_project_details['os_password'],
            os_cacert_filepath=os.path.join(CONFIG.get('vio', 'config_dir'), os_cacert_filename),
            os_volume_api_version=openstack.get_volume_api_version(),
            destination_directory=self.temp_directory
        )
        upload_file(
            name='OS keystone',
            file_name=os.path.basename(keystone_file_path),
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            document_file_path=keystone_file_path
        )

    def upload_private_key(self, **kwargs):
        """
        Upload private key file.

        Args:
            private_key_file_path (str): private key file directory path
        """
        private_key_file_path = kwargs.pop('private_key_file_path')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        upload_file(
            name='private key',
            file_name=os.path.basename(private_key_file_path),
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            document_file_path=private_key_file_path
        )

    def run_profile(self, **kwargs):
        """
        Run a profile.

        Args:
            profile (str): profile
        """
        profile = kwargs.pop('profile')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        keystone_file_name = self.os_project_details['os_project_name'] + '_project.rc'
        keystone_file_path = os.path.join(CONFIG.get('vio', 'config_dir'), keystone_file_name)
        key_pair_file_name = 'key_pair_' + self.os_project_details['os_project_name'] + '.pem'
        key_pair_file_path = os.path.join(CONFIG.get('vio', 'config_dir'), key_pair_file_name)

        ssh_command = (CONFIG.get('vio', 'deploy_senm') + ' -y -d -e ' +
                       CONFIG.get('vio', 'enm_sed_file_path') + ' -m ' +
                       CONFIG.get('vio', 'lcm_sed_file_path') + ' -O ' + keystone_file_path +
                       ' -k ' + key_pair_file_path + ' -p ' + profile)

        utils.run_noretry_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            password=self.password,
            command=ssh_command
        )


def upload_file(**kwargs):
    """
    Upload file to a VIO management server.

    Args:
        ip_address (str): vio magt server ip address
        username (str): user name
        password (str): user password
        name (str): name of the user
        file_name (str): file name
        document_file_path (str); file directory path
    """
    ip_address = kwargs.pop('ip_address')
    username = kwargs.pop('username')
    password = kwargs.pop('password')
    name = kwargs.pop('name')
    file_name = kwargs.pop('file_name')
    document_file_path = kwargs.pop('document_file_path')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    LOG.info(
        'Uploading the %s file %s to %s as user %s', name, document_file_path, ip_address, username
    )
    utils.sftp_file(
        ip_address=ip_address,
        username=username,
        password=password,
        local_file_path=document_file_path,
        remote_file_path=os.path.join(CONFIG.get('vio', 'config_dir'), file_name)
    )


def post_vio_key_pair_to_dit(**kwargs):
    """
    Post ENM key pair from VMS to DIT.

    Args:
        deployment_id (str): deployment id
        deployment_key_pair (str): deployment object
        vms_ip_address (str): vms ip address
        vms_username (str): vms username
        vms_password (str): vms password
        vio_key_pair_name (str): vio key pair name
    """
    deployment_id = kwargs.pop('deployment_id')
    deployment_key_pair = kwargs.pop('deployment_key_pair')
    vms_ip_address = kwargs.pop('vms_ip_address')
    vms_username = kwargs.pop('vms_username')
    vms_password = kwargs.pop('vms_password')
    vio_key_pair_name = kwargs.pop('vio_key_pair_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    private_key = ''
    while private_key == '':
        private_key = utils.run_ssh_command(
            ip_address=vms_ip_address,
            username=vms_username,
            password=vms_password,
            command='cat /vol1/senm/etc/' + vio_key_pair_name + '.pem'
        )
    deployment_key_pair['public_key'] = 'Not available'
    deployment_key_pair['private_key'] = private_key.strip()
    dit.execute_dit_put_rest_call(
        f'/api/deployments/{deployment_id}/',
        json.dumps({'enm': deployment_key_pair})
    )


class DownloadMediaThread(threading.Thread):
    """Thread for downloading media onto the DVMS."""

    def __init__(self, *args):
        """The _init_ for DownloadMediaThread."""
        self._stop_event = threading.Event()
        threading.Thread.__init__(self)
        self.args = args

    def run(self):
        """The run for DownloadMediaThread."""
        # pylint: disable=W0703
        try:
            LOG.info('Starting Thread %d: %s', self.args[0], os.path.basename(self.args[2]))
            ssh_command = ('curl --fail --silent --show-error -o ' +
                           os.path.join(CONFIG.get('vio', 'artifacts_dir'),
                                        os.path.basename(self.args[2])) + ' ' + self.args[2])

            utils.run_notimeout_ssh_command(
                ip_address=self.args[3],
                username=self.args[4],
                password=self.args[5],
                command=ssh_command
            )
            LOG.info('Exiting Thread %d: %s', self.args[0], os.path.basename(self.args[2]))
        except Exception as error_thrown:
            LOG.error('Interrupting main program from thread.....%s', str(error_thrown))
            _thread.interrupt_main()
            # pylint: disable=W0212
            os._exit(1)
