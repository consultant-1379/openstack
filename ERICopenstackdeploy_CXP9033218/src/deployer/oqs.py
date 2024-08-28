"""This file contains logic relating to the OpenStack Queuing Solution."""

import json
import logging
import time
import requests
from requests.exceptions import RequestException
from retrying import retry
from . import configuration

AUTH = configuration.FunctionalIdConfig()
LOG = logging.getLogger(__name__)
MAX_RETRY = 3


class OqsException(Exception):
    """
    Custom exception for expressing OQS exception.

    This is custom exception for general OQS exceptions.
    """


class Deployment:
    """
    Represents a deployment from the openstack queuing solution.

    Attributes:
        deployment_name (str): Deployment name
        pod_name (str): Pod Name
        product_set (str): product set
        job_type (str): job type
    """

    deployment_id = None
    finish_state = 'Failed'

    def __init__(self, **kwargs):
        """Initialize a Deployment object."""
        deployment_name = kwargs.pop('deployment_name')
        pod_name = kwargs.pop('pod_name')
        product_set = kwargs.pop('product_set')
        job_type = kwargs.pop('job_type')

        if kwargs:
            LOG.warning("Unexpected **kwargs: %r", kwargs)

        try:
            Deployment.deployment_id = execute_oqs_post_rest_call(
                '/api/deployments',
                json.dumps({
                    "name": deployment_name,
                    "associatedPod": pod_name,
                    "productSet": product_set,
                    "jobType": job_type
                })
            )['newDeployment']['_id']
        except RequestException as err:
            raise err

    @staticmethod
    def get_deployment_queue_status():
        """str: Return the queue status for the Deployment object."""
        try:
            deployment = execute_oqs_get_rest_call('/api/deployments/' + Deployment.deployment_id)
            return deployment['queueStatus']
        except RequestException as err:
            LOG.warning("%s: Unable to retrieve Deployment from OpenStack Queuing Solution. %s",
                        type(err).__name__, str(err))

    @staticmethod
    def update_deployment_queue_status():
        """Update Deployment object queue status in OQS."""
        if Deployment.deployment_id:
            try:
                execute_oqs_put_rest_call(
                    f'/api/deployments/{Deployment.deployment_id}',
                    json.dumps({"queueStatus": Deployment.finish_state})
                )
            except RequestException as err:
                LOG.warning("%s: Unable to update Deployment in OpenStack Queuing Solution. %s",
                            type(err).__name__, str(err))


def get_deployment_by_name(deployment_name):
    """
    Return a given Deployment in OQS.

    Args:
        deployment_name (str): Deployment name

    Returns:
        Deployment (dict): Deployment details

    Raises:
        OqsException: if deployment does not exists in OQS
        RequestException: if deployment does not exists in OQS
    """
    try:
        deployments = execute_oqs_get_rest_call(
            f'/api/deployments/search?name={deployment_name}'
        )
        if len(deployments) == 0:
            raise OqsException()

        return deployments[0]
    except RequestException as err:
        LOG.warning('%s: Unable to retrieve Deployment from OpenStack Queuing Solution. %s',
                    type(err).__name__, str(err))
    except OqsException:
        LOG.warning('Deployment %s does not exist in OpenStack Queuing Solution.',
                    deployment_name)


def delete_deployment_by_name(deployment_name):
    """
    Delete Deployment object by name in OQS.

    Args:
        deployment_name (str): Deployment name

    Raises:
        RequestException: if unable to delete the Deployment from OQS
    """
    deployment = get_deployment_by_name(deployment_name)
    if deployment and deployment['_id']:
        try:
            execute_oqs_delete_rest_call(f'/api/deployments/{deployment["_id"]}')
        except RequestException as err:
            LOG.warning("%s: Unable to remove Deployment from OpenStack Queuing Solution. %s",
                        type(err).__name__, str(err))


def begin_queue_handling(**kwargs):
    """
    Add a Deployment to OQS and return when its Queue Status is set to 'Active'.

    Args:
        deployment (str): Deployment name
        product_set (str): product set
        job_type (str): job type
    """
    deployment = kwargs.pop('deployment')
    product_set = kwargs.pop('product_set')
    job_type = kwargs.pop('job_type')

    if kwargs:
        LOG.warning("Unexpected **kwargs: %r", kwargs)

    add_deployment_to_queue(
        deployment.deployment_name,
        deployment.project.pod.name,
        product_set,
        job_type
    )
    if not Deployment.deployment_id:
        LOG.warning('A problem occurred while queue-handling. Proceeding without queue-handling.')
    else:
        while Deployment.get_deployment_queue_status() != 'Active':
            LOG.info('Queue status: Queued. Checking OQS for status update every 10 seconds.')
            time.sleep(10)
        LOG.info('Queue status: Active. Proceeding with workflow.')


def add_deployment_to_queue(deployment_name, pod_name, product_set, job_type):
    """
    Add a Deployment to OQS, deleting old Deployment of the same name if needed.

    Args:
        deployment_name (str): Deployment name
        pod_name (str): Pod name
        product_set (str): product set
        job_type (str): job type

    Raises:
        RequestException: if unable to add the Deployment to OQS
    """
    for post_attempt in range(0, 3):
        LOG.info('Adding Deployment to OpenStack Queuing Solution. [Attempt No. %s/%s]',
                 post_attempt + 1, 3)
        try:
            Deployment(
                deployment_name=deployment_name,
                pod_name=pod_name,
                product_set=product_set,
                job_type=job_type
            )
            return
        except RequestException as err:
            LOG.warning('%s: Unable to add Deployment to OpenStack Queuing Solution.',
                        type(err).__name__)
            if is_connection_error(err):
                return

            delete_deployment_by_name(deployment_name)


def is_connection_error(exception):
    """
    Return True if ConnectionError exception.

    Returns:
        (bool): True | False
    """
    return isinstance(exception, requests.ConnectionError)


@retry(retry_on_exception=is_connection_error, stop_max_attempt_number=MAX_RETRY, wait_fixed=10000)
def execute_oqs_get_rest_call(query):
    """
    Execute a GET REST call to OQS.

    Args:
        query (str): query to get the data

    Returns:
        response (dict): REST request response

    Raises:
        RequestException: if REST request fails
    """
    base_url = AUTH.get('openstack_queuing_solution', 'base_url')
    user_id = AUTH.get('FUNCTIONAL_ID', 'user_id')
    password = AUTH.get('FUNCTIONAL_ID', 'password')
    full_url = f'{base_url}{query}'
    LOG.info('Running GET REST call towards the OpenStack Queuing Solution (%s)', full_url)
    logging.getLogger('requests').setLevel(logging.WARNING)
    headers = {"Content-Type": "application/json"}
    response = requests.get(full_url, auth=(user_id, password), headers=headers, verify=False)
    if response.status_code != 200:
        raise RequestException(response.json()['message'])
    return response.json()


@retry(retry_on_exception=is_connection_error, stop_max_attempt_number=MAX_RETRY, wait_fixed=10000)
def execute_oqs_post_rest_call(query, json_data):
    """
    Execute a POST REST call to OQS.

    Args:
        query (str): query to update or create
        json_data (obj): object data

    Returns:
        response (dict): REST request response

    Raises:
        RequestException: if REST request fails
    """
    base_url = AUTH.get('openstack_queuing_solution', 'base_url')
    user_id = AUTH.get('FUNCTIONAL_ID', 'user_id')
    password = AUTH.get('FUNCTIONAL_ID', 'password')
    full_url = f'{base_url}{query}'
    LOG.info('Running POST REST call towards the OpenStack Queuing Solution (%s) with payload %s',
             full_url, json_data)
    logging.getLogger('requests').setLevel(logging.WARNING)
    headers = {"Content-Type": "application/json"}
    response = requests.post(full_url, auth=(user_id, password),
                             data=json_data, headers=headers, verify=False)
    if response.status_code != 201:
        raise RequestException(response.json()['message'])
    return response.json()


@retry(retry_on_exception=is_connection_error, stop_max_attempt_number=MAX_RETRY, wait_fixed=10000)
def execute_oqs_put_rest_call(query, json_data):
    """
    Execute a PUT REST call to OQS.

    Args:
        query (str): query to modify
        json_data (obj): object data

    Returns:
        response (dict): REST request response
    """
    base_url = AUTH.get('openstack_queuing_solution', 'base_url')
    user_id = AUTH.get('FUNCTIONAL_ID', 'user_id')
    password = AUTH.get('FUNCTIONAL_ID', 'password')
    full_url = f'{base_url}{query}'
    logging.getLogger('requests').setLevel(logging.WARNING)
    headers = {"Content-Type": "application/json"}
    response = requests.put(full_url, auth=(user_id, password),
                            data=json_data, headers=headers, verify=False)
    if response.status_code != 200:
        raise RequestException(response.json()['message'])
    return response.json()


@retry(retry_on_exception=is_connection_error, stop_max_attempt_number=MAX_RETRY, wait_fixed=10000)
def execute_oqs_delete_rest_call(query):
    """
    Execute a DELETE REST call to OQS.

    Args:
        query (str): query to delete

    Returns:
        response (dict): REST request response

    Raises:
        RequestException: if REST request fails
    """
    base_url = AUTH.get('openstack_queuing_solution', 'base_url')
    user_id = AUTH.get('FUNCTIONAL_ID', 'user_id')
    password = AUTH.get('FUNCTIONAL_ID', 'password')
    full_url = f'{base_url}{query}'
    LOG.info('Running DELETE REST call towards the OpenStack Queuing Solution (%s)', full_url)
    logging.getLogger('requests').setLevel(logging.WARNING)
    headers = {"Content-Type": "application/json"}
    response = requests.delete(full_url, auth=(user_id, password), headers=headers, verify=False)
    if response.status_code != 200:
        raise RequestException(response.json()['message'])
    return response.json()
