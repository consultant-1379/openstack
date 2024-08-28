"""This file contains logic relating to the workflows."""

import os
import logging
import json
import time
import re
import requests
import urllib3
import simplejson
from packaging import version
from . import configuration
from . import utils
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


def log_progress(**kwargs):
    """
    Log the latest running workflow and latest completed workflow.

    Arguments:
        workflow_progress (list): list of workflow status json objects.
    """
    workflow_progress = kwargs.pop('workflow_progress')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    if not hasattr(log_progress, 'latest_workflow'):
        log_progress.latest_workflow = workflow_progress[-1]['definitionName']
        return

    if workflow_progress[-1]['definitionName'] != log_progress.latest_workflow:
        latest_completed_workflow = f"{workflow_progress[-2]['definitionName']:30} \
            -- start time: {str(workflow_progress[-2].get('startTime', 'unavailable'))} \
            -- end time: {str(workflow_progress[-2].get('endTime', 'unavailable'))}"
        LOG.info(latest_completed_workflow)

    latest_workflow_progress = f"{workflow_progress[-1]['definitionName']:30} \
        -- start time: {str(workflow_progress[-1].get('startTime', 'unavailable'))} \
        -- active: {str(workflow_progress[-1].get('active', 'unavailable'))}"
    LOG.info(latest_workflow_progress)

    log_progress.latest_workflow = workflow_progress[-1]['definitionName']


class Workflows:
    """
    Represents a workflows instance.

    This class represents a workflows instance and provides
    functions to execute workflows and wait for them to complete.

    Attributes:
        ip_address (str): ip address
        username (str): User name
        password (str, optional): user password, defaults to None
        private_key (str, optional): private key, defaults to None
    """

    def __init__(self, **kwargs):
        """Initialize a Workflows object."""
        self.ip_address = kwargs.pop('ip_address')
        self.username = kwargs.pop('username')
        self.password = kwargs.pop('password', None)
        self.private_key = kwargs.pop('private_key', None)
        self.https_enabled = kwargs.pop('https_enabled')
        self.ui_hostname = kwargs.pop('ui_hostname')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.base_url = f'http://{self.ip_address}'
        if self.https_enabled:
            self.base_url = f'https://{self.ip_address}'

    def download_workflows(self, **kwargs):
        """
        Download workflows RPM Package.

        Args:
            ip_address (str): instance ip address
            url (str): instance url
        """
        ip_address = kwargs.pop('ip_address')
        url = kwargs.pop('url')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        temp_directory = utils.get_temporary_directory_path()
        package_name = os.path.basename(url)
        worklfows_file_path = os.path.join(temp_directory, package_name)
        utils.download_file(
            url=url,
            destination_directory=temp_directory
        )
        LOG.info('Download %s complete.', package_name)
        utils.sftp_file(
            ip_address=ip_address,
            username=self.username,
            private_key=self.private_key,
            local_file_path=worklfows_file_path,
            remote_file_path=f'/home/{self.username}/{package_name}'
        )
        utils.run_ssh_command(
            ip_address=ip_address,
            username=self.username,
            private_key=self.private_key,
            command=f'sudo cp /home/{self.username}/{package_name} /tmp/{package_name}'
        )

    def install_workflows(self, **kwargs):
        """
        Install workflows.

        Args:
            package_name (str): instance package name
        """
        package_name = kwargs.pop('package_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        ssh_command = f'sudo /opt/ericsson/ERICwfmgrruntimetools_CXP9032765/wfmgr \
bundle install --package=/tmp/{package_name}'

        wfmgr_output = utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            private_key=self.private_key,
            command=ssh_command
        )
        LOG.info(wfmgr_output)
        LOG.info('Workflows: %s is installed', package_name)

    def wait_for_workflow_definition(self, **kwargs):
        """
        Wait for workflow definition to become available in the list of VNF-LCM workflows.

        Args:
            workflow_id (str): VNF-LCM workflow id

        Raises:
            RuntimeError: if workflow definition does not exists
        """
        workflow_id = kwargs.pop('workflow_id')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        max_check_attempts = 360
        check_attempt = 1
        found_workflow_definition = False
        while check_attempt < max_check_attempts:
            LOG.info(
                'Waiting for the "%s" workflow definition to be available in VNF-LCM.Attempt %d of \
%d', workflow_id, check_attempt, max_check_attempts
            )
            try:
                self.get_definition_containing_id(definition_id=workflow_id)
                found_workflow_definition = True
                LOG.info(
                    'The "%s" workflow definition is now available in VNF-LCM.', workflow_id
                )
                break
            except (
                    requests.exceptions.RequestException,
                    simplejson.scanner.JSONDecodeError,
                    RuntimeError
            ):
                pass

            LOG.info('Sleeping for 10 seconds as its not there yet')
            time.sleep(10)
            check_attempt += 1

        if not found_workflow_definition:
            raise RuntimeError(
                'Didn\'t find the "%s" workflow definition after %d attempts, giving up' %
                (workflow_id, max_check_attempts)
            )

    def execute_workflow_and_wait(self, **kwargs):
        """
        Execute a given VNF-LCM workflow and wait for it to complete.

        Args:
            workflow_name (str): workflow name
            workflow_id (str): workflow id
            workflow_data (str, optional): workflow data, defaults to None
            max_check_attempts (int, optional): maximum checking attempts, defaults to 1260
        """
        workflow_name = kwargs.pop('workflow_name')
        workflow_id = kwargs.pop('workflow_id')
        workflow_data = kwargs.pop('workflow_data', None)
        max_check_attempts = kwargs.pop('max_check_attempts', 1260)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        execute_lcm_workflow_response = self.execute_workflow(
            workflow_name=workflow_name,
            workflow_id=workflow_id,
            workflow_data=workflow_data
        )
        instance_id = execute_lcm_workflow_response['instanceId']
        self.wait_for_workflow_to_complete(
            instance_id=instance_id,
            max_check_attempts=max_check_attempts,
            workflow_data=workflow_data
        )
        workflow_progress_events = self.get_progress_events(
            instance_id=instance_id
        )
        self.log_progress_events(
            events=workflow_progress_events
        )
        self.search_for_failed_events(
            events=workflow_progress_events
        )

    def execute_workflow(self, **kwargs):
        """
        Execute a given workflow name.

        This function can execute a given VNF-LCM workflow
        It will return the response object given back from VNF-LCM

        Args:
            workflow_name (str): workflow name
            workflow_id (str): workflow id
            work_flow_data (str, Optional): workflow data, defaults to None

        Returns:
            (obj): REST request reponse
        """
        workflow_name = kwargs.pop('workflow_name')
        workflow_id = kwargs.pop('workflow_id')
        workflow_data = kwargs.pop('workflow_data', None)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        lcm_instances_url = f'{self.base_url}/wfs/rest/instances'
        LOG.info('Running GET REST call towards: %s', lcm_instances_url)
        definition_id = self.get_definition_containing_id(
            definition_id=workflow_id
        )['definitionId']

        data = {
            "definitionId": definition_id,
            "businessKey": workflow_name
        }

        if workflow_data:
            data['variables'] = workflow_data

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        LOG.info(
            'Executing workflow called "%s" with definition id of "%s"',
            workflow_name, definition_id
        )
        execute_workflow_response = requests.post(
            lcm_instances_url, data=json.dumps(data), headers=headers, verify=False
        )
        execute_workflow_response.raise_for_status()
        execute_workflow_response_json = execute_workflow_response.json()
        instance_id = execute_workflow_response_json['instanceId']
        LOG.info(
            'The "%s" workflow has started with an instance id of %s',
            workflow_name, instance_id
        )
        lcm_url = self.base_url.replace(self.ip_address, self.ui_hostname)
        LOG.info(
            'The "%s" progress can be followed at the following url: %s\
/index.html#workflows/workflow/workflowinstance/%s', workflow_name, lcm_url, instance_id
        )
        return execute_workflow_response_json

    def wait_for_workflow_to_complete(self, **kwargs):
        """
        Wait for the given workflow to complete.

        This function will wait for a workflow with
        a given id to complete. It will throw an exception
        if the workflow does not complete successfully

        Args:
            instance_id (str): workflow instance id
            max_check_attempts (str, optional): maximum checking attempts, defaults to 1260
            workflow_data (str): workflow data

        Raises:
            RuntimeError: if the workflows times out
        """
        # pylint: disable=R0914,R0915
        instance_id = kwargs.pop('instance_id')
        max_check_attempts = kwargs.pop('max_check_attempts', 1260)
        workflow_data = kwargs.pop('workflow_data')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        lcm_progress_summaries_url = f'{self.base_url}/wfs/rest/progresssummaries/'
        time.sleep(10)
        check_attempt = 1
        wait_time = 10
        workflow_completed = False
        exception_count = 0
        repeated_exception_limit = 30
        workflow_duration = '00:00:00'
        while check_attempt <= max_check_attempts:
            workflow_duration = time.strftime("%H:%M:%S", time.gmtime(check_attempt * wait_time))
            LOG.info(
                'Waiting for the workflow with instance id: %s to complete. Attempt %d of %d, \
current workflow duration: %s', instance_id, check_attempt, max_check_attempts, workflow_duration
            )
            if exception_count > repeated_exception_limit:
                LOG.error('VNF-LCM failed to start the workflow with instance ID: %s', instance_id)
                break
            try:
                workflow_response = requests.get(
                    lcm_progress_summaries_url, timeout=30, verify=False
                )
                workflow_response.raise_for_status()
                log_progress(workflow_progress=workflow_response.json())
                workflow_summary_response = requests.get(
                    f'{lcm_progress_summaries_url}{instance_id}', timeout=30, verify=False
                )
                workflow_summary_response.raise_for_status()
                workflow_summary_response_json = workflow_summary_response.json()
                workflow_instance_business_key = workflow_summary_response_json['businessKey']
                if workflow_instance_business_key == 'Restore Deployment':
                    self.check_and_complete_user_task(
                        instance_id=instance_id,
                        workflow_data=workflow_data
                    )
                if not workflow_summary_response_json['active']:
                    workflow_completed = True
                    break

                if workflow_summary_response_json['incidentActive']:
                    LOG.info('An incident has occurred in the workflow with an instance id of \
%s.', instance_id)
                    break

                LOG.info('Sleeping for %d seconds as its not complete yet', wait_time)
                time.sleep(wait_time)
                check_attempt += 1
            except requests.exceptions.RequestException:
                exception_count += 1
                LOG.info('workflow progress unavailable...retrying in 10 seconds, attempt: %d \
of %d', exception_count, repeated_exception_limit)
                time.sleep(10)
                continue
            exception_count = 0

        if not workflow_completed:
            raise RuntimeError(
                'The workflow did not complete within the expected time duration of: %s, ceasing \
monitoring of workflow as expected time duration exceeded. To check the workflow progress you must \
open VNF-LCM: %s/index.html#workflows/workflow/workflowinstance/%s' % (workflow_duration,
                                                                       self.base_url, instance_id)
            )

        workflow_summary_response = requests.get(lcm_progress_summaries_url + instance_id,
                                                 verify=False)
        workflow_summary_response.raise_for_status()
        workflow_summary_response_json = workflow_summary_response.json()
        if 'failure' in workflow_summary_response_json['endNodeId']:
            raise RuntimeError(
                'The workflow with an instance id of %s FAILED to complete successfully. Refer to \
the relevant logs for more information. To check the workflow log you must open VNF-LCM: \
%s/index.html#workflows/workflow/workflowinstance/%s' % (instance_id, self.base_url, instance_id)
            )

        LOG.info('The workflow with an instance id of %s is now completed.', instance_id)

    def check_and_complete_user_task(self, **kwargs):
        """
        Check for and complete the restore user task.

        This function check if a restore user task is waiting for input.
        It will post the backup tag name to the user task when found.

        Args:
            instance_id (str): instance id
            workflow_data (str): workflow data
        """
        instance_id = kwargs.pop('instance_id')
        workflow_data = kwargs.pop('workflow_data')
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)
        lcm_user_task_url = f'{self.base_url}/wfs/rest/usertasks/?instanceId={instance_id}'
        lcm_user_task = requests.get(lcm_user_task_url, verify=False)
        lcm_user_task.raise_for_status()
        lcm_user_task = lcm_user_task.json()
        if len(lcm_user_task) >= 1:
            user_task_id = lcm_user_task[0]['usertaskId']
            user_task_url = f'{self.base_url}/wfs/rest/usertasks/{user_task_id}/complete'
            data = {}
            if workflow_data:
                data['variables'] = workflow_data
            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
            requests.post(
                user_task_url, data=json.dumps(data), headers=headers, verify=False
            )

    def get_progress_events(self, **kwargs):
        """
        Return the list of progress events for the given workflow instance id.

        Args:
            instance_id (str): workflow instance id

        Returns:
            (obj): list of progress events
        """
        instance_id = kwargs.pop('instance_id')
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        lcm_progress_events_response = requests.get(
            f'{self.base_url}/wfs/rest/progressevents?instanceId={instance_id}',
            verify=False
        )
        lcm_progress_events_response.raise_for_status()
        return list(reversed(lcm_progress_events_response.json()))

    @classmethod
    def log_progress_events(cls, **kwargs):
        """
        Log details about the list of given events.

        Args:
            events (list): log events (list of dictionaries)
        """
        events = kwargs.pop('events')
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info('Please see below details about the events')
        for event in events:
            LOG.info(
                'Node ID: %s | Node Type: %s | Event Time: %s',
                event['nodeId'], event['nodeType'], event['eventTime']
            )

    def search_for_failed_events(self, **kwargs):
        """
        Search for failed events in the given event list.

        This function can search for any failed events
        in the given list of events and raise an exception
        if it finds one

        Args:
            events (list): log events (list of dictionaries)

        Raises:
            RuntimeError: if error found in given events list
        """
        events = kwargs.pop('events')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        for event in events:
            if 'error' in event['nodeType']:
                raise RuntimeError(
                    'There was an error found in the list of events, please refer to the relevant \
workflow log in VNF LCM: %s/index.html#workflows' % self.base_url
                )

    def get_definition_containing_id(self, **kwargs):
        """
        Return the definition details based on the given name.

        Args:
            definition_id (str): definition id

        Returns:
            definition (dict): definition details

        Raises:
            RuntimeError: if defination not exists
        """
        definition_id = kwargs.pop('definition_id')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        definitions_url = f'{self.base_url}/wfs/rest/definitions'
        LOG.info('Running GET REST towards: %s', definitions_url)
        response = requests.get(definitions_url, timeout=60, verify=False)
        definitions = response.json()
        for definition in definitions:
            if definition_id in definition['definitionId']:
                return definition

        raise RuntimeError(
            'There was no definition found containing "%s"' % definition_id
        )

    def get_installed_workflows_info(self, **kwargs):
        """
        Return installed workflows info.

        Args:
            workflow_name (str): workflow name

        Returns:
            (list): installed workflows info

        Raises:
            ValueError: if package not installed
        """
        workflows_name = kwargs.pop('workflows_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        installed_workflows_info = ''
        max_check_attempts = 10
        check_attempt = 1
        while check_attempt < max_check_attempts:
            ssh_command = f'sudo /opt/ericsson/ERICwfmgrruntimetools_CXP9032765/wfmgr bundle list \
--name={workflows_name}'
            installed_workflows_info = utils.run_ssh_command(
                ip_address=self.ip_address,
                username=self.username,
                private_key=self.private_key,
                command=ssh_command
            )
            if installed_workflows_info:
                break
            time.sleep(10)
            check_attempt += 1
        if 'No package installed' in installed_workflows_info or not installed_workflows_info:
            raise ValueError('VNF-LCM workflow Manager on %s is reporting no workflows are \
installed' % self.ip_address)

        LOG.info(installed_workflows_info)
        installed_workflows = installed_workflows_info.split('\n')
        installed_workflows_info = [workflow for workflow in installed_workflows
                                    if workflows_name in workflow]
        return installed_workflows_info

    def get_workflows_version(self, **kwargs):
        """
        Return the installed workflow versions associated with the workflows package name.

        Args:
            workflows_name (str): workflow name
            package_version (str): package version

        Returns:
            (str): workflow version
        """
        workflows_name = kwargs.pop('workflows_name')
        package_version = kwargs.pop('package_version')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        installed_workflows_info = self.get_installed_workflows_info(workflows_name=workflows_name)
        pattern = f"{workflows_name}.*{package_version}"
        version_pattern = re.compile(pattern)
        for workflow in installed_workflows_info:
            try:
                pattern_match = version_pattern.search(workflow).group()
                if pattern_match:
                    return pattern_match.split(' | ')[1].strip()
            except AttributeError:
                continue

        raise ValueError(
            f'Unable to retrieve expected installed {workflows_name}: {package_version} version '
            'as defined in the given ENM product set.'
        )

    def get_installed_workflow_versions(self, **kwargs):
        """
        Return a list of installed workflow versions.

        Args:
            workflows_name (str): workflow name

        Returns:
            (list): installed workflow versions
        """
        workflows_name = kwargs.pop('workflows_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        installed_workflows_versions = []
        installed_workflows_info = self.get_installed_workflows_info(workflows_name=workflows_name)
        pattern = "(\\s)(\\d+).(\\d+).(\\d+)"
        version_pattern = re.compile(pattern)
        for workflow in installed_workflows_info:
            try:
                pattern_match = version_pattern.search(workflow).group()
            except AttributeError:
                continue
            if pattern_match:
                installed_version = pattern_match.strip()
                if '-SNAPSHOT' in workflow:
                    installed_version = installed_version + '-SNAPSHOT'
                installed_workflows_versions.append(installed_version)
        return sorted(installed_workflows_versions, reverse=True)

    def rollback_workflows_versions(self, **kwargs):
        """
        Uninstall later workflow versions than a given workflows version.

        Args:
            workflows_name (str): workflow's name
            workflows_version (str): workflow's version
        """
        workflows_name = kwargs.pop('workflows_name')
        workflows_version = kwargs.pop('workflows_version')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        installed_workflows_versions = self.get_installed_workflow_versions(
            workflows_name=workflows_name
        )

        for installed_workflows_version in installed_workflows_versions:
            if ('SNAPSHOT' in installed_workflows_version or
                    version.parse(installed_workflows_version) > version.parse(workflows_version)):
                self.__uninstall_workflows(
                    workflows_name=workflows_name,
                    workflows_version=installed_workflows_version
                )

    def cleanup_workflows_versions(self, **kwargs):
        """
        Uninstall earlier workflow versions than a given workflows version.

        Args:
            workflows_name (str): workflow's name
            retain_value (int): retain value
            suppress_exception (boolean, optional): suppress exception, defaults to True
        """
        workflows_name = kwargs.pop('workflows_name')
        retain_value = kwargs.pop('retain_value')
        suppress_exception = kwargs.pop('suppress_exception', True)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        installed_workflows_versions = self.get_installed_workflow_versions(
            workflows_name=workflows_name
        )

        if len(installed_workflows_versions) > retain_value:
            LOG.info('Proceeding with uninstall of obsolete %s versions.', workflows_name)

        while range(len(installed_workflows_versions) - retain_value):
            self.__uninstall_workflows(
                workflows_name=workflows_name,
                workflows_version=installed_workflows_versions[-1],
                suppress_exception=suppress_exception
            )
            del installed_workflows_versions[-1]

    def __uninstall_workflows(self, **kwargs):
        """
        Uninstall VNF-LCM workflow.

        Args:
            workflows_name (str): workflows name
            workflows_version (str): workflows version
            suppress_exception (boolean, Optional): suppress exception, defaults to False
        """
        workflows_name = kwargs.pop('workflows_name')
        workflows_version = kwargs.pop('workflows_version')
        suppress_exception = kwargs.pop('suppress_exception', False)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        ssh_command = f'echo "yes" | sudo /opt/ericsson/ERICwfmgrruntimetools_CXP9032765/wfmgr \
bundle uninstall --name={workflows_name} --version={workflows_version}'
        wfmgr_output = utils.run_ssh_command(
            ip_address=self.ip_address,
            username=self.username,
            private_key=self.private_key,
            command=ssh_command,
            suppress_exception=suppress_exception
        )
        LOG.info(wfmgr_output)
