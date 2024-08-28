"""This file contains logic relating to the deployment inventory tool."""

import json
import logging
import requests
import urllib3
from retrying import retry
from deployer.utils import cached
from . import configuration
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AUTH = configuration.FunctionalIdConfig()
LOG = logging.getLogger(__name__)


class Deployment:
    """
    Represents a Deployment from the deployment inventory tool.

    Attributes:
        deployment_name (str): ENM deployment name
    """

    def __init__(self, **kwargs):
        """Initialize a Deployment object."""
        self.deployment_name = kwargs.pop('deployment_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def deployment_id(self):
        """str: Return the deployment id for this deployment."""
        return self.rest['_id']

    @property
    def project(self):
        """dict: Return the project id for this deployment."""
        return Project(
            database_id=self.rest['project_id']
        )

    @property
    def enm(self):
        """dict: Return the enm object for this deployment."""
        return self.rest['enm']

    @property
    def sed(self):
        """dict: Return the sed id for this deployment."""
        return Sed(
            database_id=self.rest['enm']['sed_id']
        )

    @property
    def vnf_lcm_sed(self):
        """dict: Return the VNF LCM sed object for this deployment."""
        attached_documents = self.rest['documents']
        try:
            vnf_lcm_document = [document for document in attached_documents
                                if 'vnflcm_sed_schema' in document['schema_name']][0]
        except IndexError:
            LOG.error('There is no VNF LCM SED document attached to the deployment.')

        return VNFLCMSed(
            database_id=vnf_lcm_document['document_id']
        )

    @property
    def vio_dvms_document(self):
        """dict: Return the VIO DVMS document object for this deployment."""
        attached_documents = self.rest['documents']
        try:
            vio_dvms = [document for document in attached_documents
                        if 'vio_dvms' in document['schema_name']][0]
        except IndexError:
            LOG.error('There is no VIO DVMS document attached to the deployment.')

        return VIODVMS(
            database_id=vio_dvms['document_id']
        )

    @property
    @cached
    def rest(self):
        """dict: Return the response from the DIT API for this deployment."""
        deployments = execute_dit_get_rest_call(
            '/api/deployments/', {'q': f'name={self.deployment_name}'}
        )
        deployment_count = len(deployments)
        if deployment_count == 0:
            raise RuntimeError(
                'Couldn\'t find a deployment called "%s" in the Deployment Inventory Tool' %
                self.deployment_name
            )

        return deployments[0]


class Project:
    """
    Represents a Project from the deployment inventory tool.

    Attributes:
        database_id (str, optional): database id, defaults to empty string
        project_name (str, optional): project name, defaults to empty string
    """

    def __init__(self, **kwargs):
        """Initialize a Project object."""
        self.database_id = kwargs.pop('database_id', '')
        self.project_name = kwargs.pop('project_name', '')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def pod(self):
        """dict: Return the pod id for this project."""
        return Pod(
            database_id=self.rest['pod_id']
        )

    @property
    def credentials(self):
        """dict: Return a dictionary containing the openstack credentials for the project."""
        return {
            'os_username': self.os_username,
            'os_password': self.os_password,
            'os_auth_url': self.pod.os_auth_url,
            'os_project_name': self.os_project_name,
            'os_cacert': ''
        }

    @property
    def os_username(self):
        """str: Return the username of the project."""
        if 'content' in self.rest:
            return self.rest['content']['username']

        return self.rest['username']

    @property
    def os_password(self):
        """str: Return the password of the project."""
        if 'content' in self.rest:
            return self.rest['content']['password']

        return self.rest['password']

    @property
    def os_project_name(self):
        """str: Return the project name project."""
        if 'content' in self.rest:
            return self.rest['content']['name']

        return self.rest['name']

    @property
    @cached
    def rest(self):
        """dict: the response from the DIT API for this project."""
        if self.project_name != '':
            projects = execute_dit_get_rest_call(
                '/api/projects/', {'q': 'name=' + self.project_name}
            )
            project_count = len(projects)
            if project_count == 0:
                raise RuntimeError(
                    'Couldn\'t find a project called "%s" in the Deployment Inventory Tool' %
                    self.project_name
                )

            return projects[0]

        return execute_dit_get_rest_call(
            f'/api/projects/{self.database_id}'
        )


class Pod:
    """
    Represents a Pod from the deployment inventory tool.

    Attributes:
        database_id (str): database id
    """

    def __init__(self, **kwargs):
        """Initialize a Pod object."""
        self.database_id = kwargs.pop('database_id')
        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def name(self):
        """str: Return the name of the pod."""
        if 'content' in self.rest:
            return self.rest['content']['name']

        return self.rest['name']

    @property
    def os_auth_url(self):
        """str: Return the auth url of the pod."""
        if 'content' in self.rest:
            return self.rest['content']['authUrl']

        return self.rest['authUrl']

    @property
    @cached
    def rest(self):
        """obj: Return the response from the DIT API for this pod."""
        return execute_dit_get_rest_call(
            f'/api/pods/{self.database_id}'
        )


class Sed:
    """
    Represents a Sed from the deployment inventory tool.

    Attributes:
        database_id (str): database id
    """

    def __init__(self, **kwargs):
        """Initialize a Sed object."""
        self.database_id = kwargs.pop('database_id')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def content(self):
        """dict: Return the content of the sed."""
        return self.rest['content']

    @property
    def schema(self):
        """str: Return the associated schema object."""
        return Schema(
            database_id=self.rest['schema_id']
        )

    @property
    def rest(self):
        """dict: Return the response from the DIT API for this sed."""
        return execute_dit_get_rest_call(
            f'/api/documents/{self.database_id}'
        )


class VNFLCMSed:
    """
    Represents a VNF LCM sed from the deployment inventory tool.

    Attributes:
        database_id (str): database id
    """

    def __init__(self, **kwargs):
        """Initialize a Sed object."""
        self.database_id = kwargs.pop('database_id')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def name(self):
        """str: Return the name of the sed."""
        return self.rest['name']

    @property
    def content(self):
        """dict: Return the content of the sed."""
        return self.rest['content']

    @property
    def schema(self):
        """dict: Return the associated schema object."""
        return Schema(
            database_id=self.rest['schema_id']
        )

    @property
    @cached
    def rest(self):
        """dict: Return the response from the DIT API for this sed."""
        return execute_dit_get_rest_call(
            f'/api/documents/{self.database_id}'
        )


class Schema:
    """
    Represents a Schema from the deployment inventory tool.

    Attributes:
        database_id (str): database id
    """

    def __init__(self, **kwargs):
        """Initialize a Schema object."""
        self.database_id = kwargs.pop('database_id')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def name(self):
        """str: Return the name of the schema."""
        return self.rest['name']

    @property
    def content(self):
        """dict: Return the scema content."""
        return self.rest['content']

    @property
    def version(self):
        """str: Return the version of the schema."""
        return self.rest['version']

    @property
    @cached
    def rest(self):
        """dict: Return the response from the DIT API for this schema."""
        return execute_dit_get_rest_call(
            f'/api/schemas/{self.database_id}',
            {'fields': 'name,version,content'}
        )


class VIODVMS:
    """
    Represents a VIO DVMS Document from the deployment inventory tool.

    Attributes:
        database_id (str): database id
    """

    def __init__(self, **kwargs):
        """Initialize a document object."""
        self.database_id = kwargs.pop('database_id')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def content(self):
        """dict: Return the content of the document."""
        return self.rest['content']

    @property
    def schema(self):
        """dict: Return the associated schema object."""
        return Schema(
            database_id=self.rest['schema_id']
        )

    @property
    @cached
    def rest(self):
        """dict: Return the response from the DIT API for this document."""
        return execute_dit_get_rest_call(
            f'/api/documents/{self.database_id}'
        )


def is_connection_error(exception):
    """
    Return True if ConnectionError exception.

    Returns:
        (bool): True | False
    """
    return isinstance(exception, requests.ConnectionError)


@retry(retry_on_exception=is_connection_error, stop_max_attempt_number=120, wait_fixed=10000)
def execute_dit_get_rest_call(url_string, payload=None):
    """
    Return response of GET REST call.

    Returns:
        (dict): result of a GET REST call towards the deployment inventory tool.
    """
    base_url = AUTH.get('deployment_inventory_tool', 'base_url')
    user_id = AUTH.get('FUNCTIONAL_ID', 'user_id')
    password = AUTH.get('FUNCTIONAL_ID', 'password')
    full_url = f'{base_url}{url_string}'
    LOG.info(
        'Running GET REST call towards the Deployment Inventory Tool (%s%s)',
        full_url,
        ' with payload ' + str(payload) if payload else ''
    )
    logging.getLogger('requests').setLevel(logging.WARNING)
    response = requests.get(full_url, auth=(user_id, password), params=payload, verify=False)
    response.raise_for_status()
    LOG.info('REST call completed')
    return response.json()


@retry(retry_on_exception=is_connection_error, stop_max_attempt_number=120, wait_fixed=10000)
def execute_dit_put_rest_call(url_string, json_data):
    """
    Return response of PUT REST call.

    Returns:
        (dict): result of a PUT REST call towards the deployment inventory tool.

    Raises:
        ConnectionError: if PUT request returns with status code  500, 502, 503 or 504
        HTTPError: if PUT request returns with any status code other than 200
    """
    base_url = AUTH.get('deployment_inventory_tool', 'base_url')
    user_id = AUTH.get('FUNCTIONAL_ID', 'user_id')
    password = AUTH.get('FUNCTIONAL_ID', 'password')
    full_url = f'{base_url}{url_string}'
    LOG.info(
        'Running PUT REST call towards the Deployment Inventory Tool (%s) with payload %s',
        url_string, json_data
    )
    logging.getLogger('requests').setLevel(logging.WARNING)
    headers = {'Content-Type': 'application/json'}
    response = requests.put(full_url, auth=(user_id, password),
                            data=json_data, headers=headers, verify=False)
    if response.status_code in [500, 502, 503, 504]:
        LOG.error('Rest Call failed with the following error: %s', response)
        raise requests.ConnectionError

    if response.status_code != 200:
        LOG.error('Rest Call failed with the following error: %s %s', response, response.json())
        raise requests.HTTPError

    LOG.info('REST call completed')
    return response.json()


def update_sed_schema_version(**kwargs):
    """
    Update the schema version for a given document if needs be.

    Args:
        document (str): sed document name
        new_version (str): new version to update

    Raises:
        RuntimeError: if schema version not available in DIT
    """
    document = kwargs.pop('document')
    new_version = kwargs.pop('new_version')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    if document.schema.version != new_version:
        payload = {'q': f'version={new_version}&name={document.schema.name}',
                   'fields': '_id'}
        new_schema = execute_dit_get_rest_call('/api/schemas', payload)
        if len(new_schema) != 1:
            raise RuntimeError('No Schema matching cloud templates version %s found in DIT' %
                               new_version)
        LOG.info('Attempting to update your schema version from %s to %s',
                 document.schema.version, new_version)
        execute_dit_put_rest_call(
            f'/api/documents/{document.database_id}/',
            json.dumps({'schema_id': new_schema[0]['_id']})
        )


def post_enm_key_pair_to_dit(**kwargs):
    """
    Post ENM key pair to DIT.

    Args:
        deployment_id (str): deployment id
        deployment_key_pair (str): deployment key pair
        public_key (str): public key
        private_key (str): private key
    """
    deployment_id = kwargs.pop('deployment_id')
    deployment_key_pair = kwargs.pop('deployment_key_pair')
    public_key = kwargs.pop('public_key')
    private_key = kwargs.pop('private_key')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    deployment_key_pair['public_key'] = public_key
    deployment_key_pair['private_key'] = private_key
    execute_dit_put_rest_call(
        f'/api/deployments/{deployment_id}/',
        json.dumps({'enm': deployment_key_pair})
    )
