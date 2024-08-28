"""This file contains logic relating to the life cycle manager."""

import os
import logging
import time
import timeout_decorator
import semantic_version
from deployer.utils import cached
from . import configuration
from . import openstack
from . import utils

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


class LifeCycleManager:
    """
    Represents a life cycle manager instance.

    This class represents a lcm instance and provides
    functions to manage lcm related tasks.

    Attributes:
        sed_object (str): SED object
        username (str): user name
        private_key (str): private key
        sed_file_path (str): sed file path
        heat_templates_url (str, optional): heat templates url, defaults to None
        media_version (str, optional): media version, defaults to None
    """

    # pylint: disable=R0904

    def __init__(self, **kwargs):
        """Initialize a LifeCycleManager object."""
        self.sed_object = kwargs.pop('sed_object')
        self.username = kwargs.pop('username')
        self.private_key = kwargs.pop('private_key')
        self.sed_file_path = kwargs.pop('sed_file_path')
        self.heat_templates_url = kwargs.pop('heat_templates_url', None)
        self.media_version = kwargs.pop('media_version', None)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.heat_templates_dir = utils.get_temporary_directory_path()

    @property
    @cached
    def vnflcm_stack(self):
        """obj: Return VNF-LCM Stack instance."""
        stack_template = utils.get_template_by_ip_type(
            infrastructure_resource='vnflcm',
            ip_version=self.ip_version
        )
        vnflcm_stack = openstack.Stack(
            name=self.sed_object.sed_data['parameter_defaults']['deployment_id'] + '_VNFLCM',
            stack_file_path=os.path.join(
                self.heat_templates_dir,
                stack_template
            ),
            param_file_path=self.sed_file_path
        )
        return vnflcm_stack

    @property
    @cached
    def security_group_stack(self):
        """obj: Return VNF-LCM security group instance."""
        stack_template = CONFIG.get('vnflcm', 'security')
        stack_name = self.sed_object.sed_data['parameter_defaults']['deployment_id'] + \
            '_vnflcm_security_group'
        security_group_stack = openstack.Stack(
            name=stack_name,
            stack_file_path=os.path.join(
                self.heat_templates_dir,
                stack_template
            ),
            param_file_path=self.sed_file_path
        )
        return security_group_stack

    @property
    @cached
    def vip_ports_stack(self):
        """obj: Return VNF-LCM vip ports stack instance."""
        template_name = utils.get_template_by_ip_type(
            infrastructure_resource='vnflcm_vip',
            ip_version=self.ip_version
        )
        stack_name = '_vnflcm_dual_vip'
        if self.ip_version != 'dual':
            stack_name = f'_vnflcm_ipv{self.ip_version}_vip'
        vip_stack = openstack.Stack(
            name=f'{self.sed_object.sed_data["parameter_defaults"]["deployment_id"]}{stack_name}',
            stack_file_path=os.path.join(
                self.heat_templates_dir,
                template_name
            ),
            param_file_path=self.sed_file_path,
        )
        return vip_stack

    @property
    @cached
    def server_group_stack(self):
        """obj: Return VNF-LCM server group stack instance."""
        stack_name = self.sed_object.sed_data['parameter_defaults']['deployment_id'] + \
            '_vnflcm_servergroup'
        stack_template = CONFIG.get('vnflcm', 'server_group')
        server_group_stack = openstack.Stack(
            name=stack_name,
            stack_file_path=os.path.join(
                self.heat_templates_dir,
                stack_template
            ),
            param_file_path=self.sed_file_path
        )
        return server_group_stack

    @property
    @cached
    def is_ha_configuration(self):
        """bool: Return true if VNF-LCM SED is configured for HA."""
        return (self.sed_object.sed_data['parameter_defaults']['db_vm_count'] == '2' or
                self.sed_object.sed_data['parameter_defaults']['services_vm_count'] == '2')

    @property
    @cached
    def is_ha_deployment(self):
        """bool: Return true if VNF-LCM stack is HA."""
        stack_params = openstack.get_resource_attribute(
            identifier=self.vnflcm_stack.name,
            resource_type='stack',
            attribute='parameters'
        )
        return stack_params['db_vm_count'] == '2' or stack_params['services_vm_count'] == '2'

    @property
    def ip_address(self):
        """str: Return services ip address."""
        if self.is_ha_configuration is True:
            return (self.sed_object.sed_data['parameter_defaults']
                    ['external_ipv4_vip_for_services'])
        return (self.sed_object.sed_data['parameter_defaults']
                ['external_ipv4_for_services_vm'].split(',')[0])

    @property
    def ip_version(self):
        """str: Return ip version."""
        return self.sed_object.sed_data['parameter_defaults']['ip_version']

    @property
    def services_vm_ips(self):
        """list: Return services ip addresses."""
        return (self.sed_object.sed_data['parameter_defaults']
                ['external_ipv4_for_services_vm'].split(','))

    @property
    def vnf_lcm_version(self):
        """str: Return installed VNF-LCM media version."""
        max_attempts = 10
        attempt = 1
        vnf_lcm_version = ''
        while attempt <= max_attempts:
            vnf_lcm_version = utils.run_ssh_command(
                ip_address=self.sed_object.sed_data['parameter_defaults']
                ['external_ipv4_for_services_vm'].split(',')[0],
                username=self.username,
                private_key=self.private_key,
                command="sudo -i vnflcm version | grep -i \"vnflcm version\" "
            )
            LOG.info(vnf_lcm_version)
            if ':' not in vnf_lcm_version:
                time.sleep(10)
                LOG.info('Retrying retrieval of VNF-LCM version attempt: %d of %d',
                         attempt, max_attempts)
                attempt += 1
                continue
            vnf_lcm_version = vnf_lcm_version.split(':')[1].strip()
            if semantic_version.validate(vnf_lcm_version):
                LOG.info('Installed VNF-LCM artifacts version: %s', vnf_lcm_version)
                return vnf_lcm_version
            attempt += 1
        raise Exception('Unable to retrieve VNF-LCM version, check VNF-LCM services VM.')

    @property
    def ui_hostname(self):
        """str: Return UI hostname based on if FFE deployment or not."""
        ffe_hostname = f'{self.sed_object.sed_data["parameter_defaults"]["deployment_id"]}-vnflcm'
        if utils.is_valid_dns_hostname(hostname=ffe_hostname):
            return ffe_hostname
        return self.ip_address

    @property
    def is_vnf_lcm_upgrade_required(self):
        """bool: Return true if VNF-LCM media product set and installed versions are different."""
        if (semantic_version.Version(self.media_version) !=
                semantic_version.Version(self.vnf_lcm_version)):
            return True
        if self.is_ha_deployment is False and self.is_ha_configuration is True:
            return True
        return False

    @property
    def is_https_supported(self):
        """bool: Return true if VNF-LCM media version is an HTTPS supported version."""
        check_version = self.vnf_lcm_version if self.media_version is None else self.media_version

        if semantic_version.Version(check_version) >= semantic_version.Version('5.53.6'):
            return True
        return False

    def download_and_extract_templates(self, **kwargs):
        """
        Download and extract VNF-LCM templates.

        Args:
            destination_directory (str): download directory path
        """
        destination_directory = kwargs.pop('destination_directory')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        utils.download_file(
            url=self.heat_templates_url,
            destination_directory=destination_directory
        )
        LOG.info('VNF-LCM cloud templates download complete.')
        utils.unzip_tar_gz(os.path.join(destination_directory,
                                        os.path.basename(self.heat_templates_url)),
                           destination_directory)
        LOG.info('VNF-LCM cloud templates extracted to: %s', destination_directory)

    def create_security_group(self):
        """Create VNF-LCM security group stack."""
        self.security_group_stack.create()
        self.security_group_stack.wait_until_created()
        LOG.info('%s created.', self.security_group_stack.name)

    def update_security_group(self):
        """Update VNF-LCM security group stack."""
        self.security_group_stack.update()
        self.security_group_stack.wait_until_updated()
        LOG.info('%s updated.', self.security_group_stack.name)

    def create_vip_ports_stack(self):
        """Create virtual IP ports stack."""
        self.vip_ports_stack.create()
        self.vip_ports_stack.wait_until_created()
        LOG.info('%s created.', self.vip_ports_stack.name)

    def update_vip_ports_stack(self):
        """Update virtual IP ports stack."""
        self.vip_ports_stack.update()
        self.vip_ports_stack.wait_until_updated()
        LOG.info('%s updated.', self.vip_ports_stack.name)

    def delete_vip_ports_stack(self):
        """Delete virtual IP ports stack."""
        self.vip_ports_stack.delete()
        self.vip_ports_stack.wait_until_deleted()
        LOG.info('%s deleted.', self.vip_ports_stack.name)

    def create_server_group_stack(self):
        """Create VNF-LCM server group stack."""
        self.server_group_stack.create()
        self.server_group_stack.wait_until_created()
        LOG.info('%s created.', self.server_group_stack.name)

    def __update_server_group_resource(self):
        """Perform VNF-LCM server group workaround for VIO."""
        LOG.info('Performing VNF-LCM server group workaround for VIO.')
        server_group_resources = self.server_group_stack.get_resource_list(
            additional_arguments='-n3'
        )
        for resource in server_group_resources:
            if resource['resource_type'] == 'OS::Nova::ServerGroup':
                openstack.openstack_client_command(
                    command_type='openstack',
                    object_type='stack',
                    action='resource mark unhealthy',
                    arguments=f'{resource["stack_name"]} {resource["resource_name"]}',
                    return_an_object=False
                )
                openstack.wait_for_stack_resource_state(
                    identifier=self.server_group_stack.name,
                    arguments='-n3',
                    resource_type='OS::Nova::ServerGroup',
                    required_state='CHECK_FAILED',
                    attempts=360,
                    sleep_period=10
                )
        LOG.info('VNF-LCM server group upgrade workaround for VIO complete.')

    def update_server_group(self, **kwargs):
        """
        Update VNF-LCM server group stack.

        Args:
            is_vio_deployment (boolean): is vio deployment
        """
        is_vio_deployment = kwargs.pop('is_vio_deployment')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        if is_vio_deployment is True:
            self.__update_server_group_resource()
        self.server_group_stack.update()
        self.server_group_stack.wait_until_updated()

    def set_vnf_lcm_sed_values(self, **kwargs):
        """
        Set VNF-LCM SED values.

        Args:
            volume_0_id (str): id of volume-0
            volume_1_id (str): id of volume-1
            external_network_name (str): external network name
            internal_network_name (str): internal network name
            is_vio_deployment (boolean): is vio deployment
        """
        # pylint: disable=R0914
        volume_0_id = kwargs.pop('volume_0_id')
        volume_1_id = kwargs.pop('volume_1_id')
        external_network_name = kwargs.pop('external_network_name')
        internal_network_name = kwargs.pop('internal_network_name')
        is_vio_deployment = kwargs.pop('is_vio_deployment')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        db_volume_id = volume_0_id
        server_group_id = openstack.get_resource_attribute(
            identifier=self.sed_object.sed_data['parameter_defaults']['deployment_id'] +
            '_vnflcm_servergroup-0',
            resource_type='server group',
            attribute='id'
        )
        db_server_group_id = server_group_id
        if self.is_ha_configuration is True:
            db_volume_id = f'{db_volume_id},{volume_1_id}'
            db_server_group_id = openstack.get_resource_attribute(
                identifier=self.sed_object.sed_data['parameter_defaults']['deployment_id'] +
                '_vnflcm_servergroup-1',
                resource_type='server group',
                attribute='id'
            )
        vim_tenant_id = openstack.get_resource_attribute(
            identifier=self.sed_object.sed_data['parameter_defaults']['vim_tenant_name'],
            resource_type='project',
            attribute='id'
        )
        external_net_id = openstack.get_resource_attribute(
            identifier=external_network_name,
            resource_type='network',
            attribute='id'
        )
        external_mtu_value = openstack.get_resource_attribute(
            identifier=external_network_name,
            resource_type='network',
            attribute='mtu'
        )
        internal_net_id = openstack.get_resource_attribute(
            identifier=internal_network_name,
            resource_type='network',
            attribute='id'
        )
        internal_mtu_value = openstack.get_resource_attribute(
            identifier=internal_network_name,
            resource_type='network',
            attribute='mtu'
        )
        security_group_id = openstack.get_resource_attribute(
            identifier=self.security_group_stack.name,
            resource_type='security group',
            attribute='id'
        )
        if not is_vio_deployment:
            self.sed_object.sed_data['parameter_defaults']['external_mtu'] = external_mtu_value
            self.sed_object.sed_data['parameter_defaults']['internal_mtu'] = internal_mtu_value

        self.sed_object.sed_data['parameter_defaults']['cinder_volume_id'] = db_volume_id
        self.sed_object.sed_data['parameter_defaults']['vim_tenant_id'] = vim_tenant_id
        self.sed_object.sed_data['parameter_defaults']['external_net_id'] = external_net_id
        self.sed_object.sed_data['parameter_defaults']['internal_net_id'] = internal_net_id
        self.sed_object.sed_data['parameter_defaults']['security_group_id'] = security_group_id
        self.sed_object.sed_data['parameter_defaults']['server_group_for_svc_vm'] = server_group_id
        self.sed_object.sed_data['parameter_defaults']['server_group_for_db_vm'] = \
            db_server_group_id
        self.sed_object.save_to_disk_as_json(
            sed_file_path=self.sed_file_path
        )

    def delete_stack(self):
        """Delete the VNF-LCM stack."""
        self.vnflcm_stack.delete()
        self.vnflcm_stack.wait_until_deleted()
        LOG.info('%s deleted.', self.vnflcm_stack.name)

    def create_stack(self):
        """Create the VNF-LCM stack."""
        self.vnflcm_stack.create()
        self.vnflcm_stack.wait_until_created()
        LOG.info('Wait 10 mins before attempting to change the default VNF-LCM password...')
        time.sleep(600)
        for ip_address in self.services_vm_ips:
            self.__reset_password(
                ip_address=ip_address,
                current_password=CONFIG.get('vnflcm', 'initial_password'),
                new_password=CONFIG.get('vnflcm', 'password')
            )
            self.__wait_for_lcm_services_vm(
                ip_address=ip_address,
                max_attempts=360,
                wait_interval=10
            )
            self.__wait_for_jboss_instance(
                ip_address=ip_address,
                max_attempts=90,
                wait_interval=10
            )
        LOG.info('%s created.', self.vnflcm_stack.name)

    def is_upgrade_workaround_required(self):
        """
        Return True if installed VNF-LCM media version is backward incompatiable.

        Returns:
            (bool): True | False
        """
        installed_semantic_version = semantic_version.Version(self.vnf_lcm_version)
        incompatiable_version_1 = semantic_version.Version('5.4.1')
        if installed_semantic_version < incompatiable_version_1:
            return True
        return False

    def upgrade_workaround(self):
        """
        Workaround for upgrading to VNF-LCM media version >= 5.4.1.

        Returns:
            (bool): True | False
        """
        if self.is_upgrade_workaround_required() is True:
            LOG.info('Performing upgrade workaround backward incompatiable VNF-LCM media version \
                     found. creating VNF-LCM server group.')
            self.create_server_group_stack()
            return True
        return False

    def upload_sed(self, **kwargs):
        """
        Upload a given local sed file, to the correct location on the lcm vm.

        Args:
            sed_file_path (str): sed file path directory
            upload_path (str): upload path directory
        """
        sed_file_path = kwargs.pop('sed_file_path')
        upload_path = kwargs.pop('upload_path')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        filename = os.path.basename(sed_file_path)
        upload_file_path = os.path.join(upload_path, filename)
        LOG.info(
            'Uploading the sed file %s to lcm as  user: %s', sed_file_path, self.username
        )
        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            private_key=self.private_key,
            command=f'sudo mkdir -p {upload_path}'
        )
        utils.sftp_file(
            ip_address=self.ip_address,
            username=self.username,
            private_key=self.private_key,
            local_file_path=sed_file_path,
            remote_file_path=os.path.join('/home/' + self.username, filename)
        )
        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            private_key=self.private_key,
            command='sudo cp ' + os.path.join('/home/' + self.username, filename) + ' ' +
            upload_file_path
        )

    def __reset_password(self, **kwargs):
        """
        Reset the password on the VNF-LCM VM when it prompts for it to be changed.

        Args:
            ip_address (str): vm ip_address
            current_password (str): current vm password
            new_password (str): new password to change
        """
        ip_address = kwargs.pop('ip_address')
        current_password = kwargs.pop('current_password')
        new_password = kwargs.pop('new_password')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info(
            'Resetting the VNF-LCM ssh password for user %s from %s to %s',
            self.username, current_password, new_password
        )
        utils.reset_password(
            ip_address=ip_address,
            username=self.username,
            current_password=current_password,
            new_password=new_password
        )

    @timeout_decorator.timeout(3600)
    def __wait_for_lcm_services_vm(self, **kwargs):
        """
        Wait for running VNF-LCM services VM to be available.

        Args:
            ip_address (str): vm ip address
            max_attempts (int): number of attempts
            wait_interval (int): wait interval in seconds
        """
        ip_address = kwargs.pop('ip_address')
        max_attempts = kwargs.pop('max_attempts')
        wait_interval = kwargs.pop('wait_interval')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        attempt = 1
        ssh_command = 'systemctl list-unit-files | grep -i configenv'
        while attempt < max_attempts:
            LOG.info('waiting for VNF-LCM services VM to be available. Attempt: %d of %d',
                     attempt, max_attempts)
            status_check = utils.run_ssh_command(
                ip_address=ip_address,
                username=self.username,
                private_key=self.private_key,
                command=ssh_command,
                suppress_exception=True
            )
            if 'static' in status_check:
                break

            LOG.info('Sleeping for %d seconds as VNF-LCM services VM not available.', wait_interval)
            time.sleep(wait_interval)
            attempt = attempt + 1

    @timeout_decorator.timeout(1200)
    def __wait_for_jboss_instance(self, **kwargs):
        """
        Wait for running Jboss instance on VNF LAF services.

        Args:
            ip_address (str): vm ip address
            max_attempts (int): number of attempts
            wait_interval (int): wait interval in seconds
        """
        ip_address = kwargs.pop('ip_address')
        max_attempts = kwargs.pop('max_attempts')
        wait_interval = kwargs.pop('wait_interval')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        attempt = 1
        ssh_command = 'sudo service jboss status'
        while attempt < max_attempts:
            LOG.info('waiting for running Jboss instance on VNF-LCM services VM. Attempt: %d of %d',
                     attempt, max_attempts)
            jboss_status = utils.run_ssh_command(
                ip_address=ip_address,
                username=self.username,
                private_key=self.private_key,
                command=ssh_command,
                suppress_exception=True
            )
            if 'jboss-as is running' in jboss_status:
                break

            LOG.info('Sleeping for %d seconds as there is no running Jboss instance on the \
VNF-LCM services VM not available.', wait_interval)
            time.sleep(wait_interval)
            attempt = attempt + 1

    def enable_https(self):
        """Enable HTTPS."""
        if not self.is_https_supported:
            LOG.info('HTTPS is not supported by VNF-LCM media version: %s', self.media_version)
            return

        LOG.info(
            'Mount nfsdata:/ericsson/data/credm/ on /ericsson/tor/data/credm/ type nfs4 on: %s',
            self.ip_address
        )
        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            private_key=self.private_key,
            max_attempts=30,
            timeout_value=120,
            command='mountpoint -q /ericsson/tor/data/credm/ || \
sudo mount nfsdata:/ericsson/data/credm/ /ericsson/tor/data/credm/'
        )
        LOG.info('Generate signed certificate on: %s', self.ip_address)
        utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            private_key=self.private_key,
            command='sudo /opt/ericsson/ERICcredentialmanagercli/bin/credentialmanager.sh -i -x \
/ericsson/credm/data/xmlfiles/VNFLCM_CertRequest.xml'
        )


class LifeCycleManagerDb:
    """
    Represents a life cycle manager Database instance.

    This class represents a lcm DB instance and provides
    functions to manage lcm DB related tasks.

    Attributes:
        volume_instance_count (int): volume instance count identifier
        deployment_id (str): deployment id
        ip_address (str): ip address
        volume_size (str): size of the volume
    """

    def __init__(self, **kwargs):
        """Initialize a Life Cycle Manager DB object."""
        self.volume_instance_count = kwargs.pop('volume_instance_count')
        self.deployment_id = kwargs.pop('deployment_id')
        self.ip_address = kwargs.pop('ip_address')
        self.volume_size = kwargs.pop('volume_size')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def server_id(self):
        """str: Return VNF-LCM DB server id."""
        return openstack.get_server_id(
            ip_address=self.ip_address
        )

    @property
    def volume_id(self):
        """str: Return attached volume id."""
        server_details = openstack.openstack_client_command(
            command_type='openstack',
            object_type='server',
            action='show',
            arguments=self.server_id,
            return_an_object=True
        )
        try:
            attached_volume_id = server_details['volumes_attached'][0]['id']
        except IndexError:
            LOG.error('No volume is attached to the VNF-LCM DB with the ID: %s', self.server_id)
            raise

        return attached_volume_id

    @property
    def volume_name(self):
        """str: Return VNF-LCM DB volume name."""
        return f'{self.deployment_id}_vnflcm_volume_{self.volume_instance_count}'

    @property
    def volume_snapshot_name(self):
        """str: Return VNF-LCM DB volume snapshot name."""
        return f'{self.volume_name}_snapshot'

    @property
    def backup_volume_name(self):
        """str: Return VNF-LCM DB backup volume name."""
        return f'{self.volume_name}_backup'

    @property
    def backup_volume_id(self):
        """str: Return VNF-LCM DB volume id."""
        backup_volume_object = openstack.openstack_client_command(
            command_type='openstack',
            object_type='volume',
            action='show',
            arguments=self.backup_volume_name,
            return_an_object=True
        )
        return backup_volume_object['id']

    def create_snapshot_volume(self):
        """Create VNF-LCM volume snapshot."""
        openstack.delete_volume_snapshot(
            volume_snapshot_name=self.volume_snapshot_name
        )
        openstack.create_volume_snapshot(
            volume_id=self.volume_id,
            snapshot_name=self.volume_snapshot_name
        )

    def does_volume_snapshot_exist(self):
        """
        Return True if volume snapshot exists.

        Returns:
            (bool): True | False
        """
        snapshot_list = openstack.openstack_client_command(
            command_type='openstack',
            object_type='volume snapshot',
            action='list',
            arguments='--limit 1000000',
            return_an_object=True
        )
        return any(snapshot['Name'] == self.volume_snapshot_name for snapshot in snapshot_list)

    def create_backup_volume(self):
        """Create VNF-LCM backup volume."""
        openstack.delete_volume(
            volume_name=self.backup_volume_name
        )
        openstack.create_volume(
            volume_size=self.volume_size,
            volume_name=self.backup_volume_name,
            arguments=f'--snapshot {self.volume_snapshot_name}'
        )
        self.delete_volume_snapshot()

    def delete_volume(self):
        """Delete DB volume."""
        openstack.delete_volume(
            volume_name=self.volume_name
        )

    def delete_volume_snapshot(self):
        """Delete VNF-LCM volume snapshot."""
        openstack.delete_volume_snapshot(
            volume_snapshot_name=self.volume_snapshot_name
        )

    def reset_volume_name(self):
        """Reset backup volume name to volume name."""
        openstack.openstack_client_command(
            command_type='openstack',
            object_type='volume',
            action='set',
            arguments=f'{self.backup_volume_id} --name {self.volume_name}',
            return_an_object=False
        )
        LOG.info('%s name successfully reset to %s', self.backup_volume_name, self.volume_name)
