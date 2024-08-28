"""This module contains any logic specific to ci and the ci portal."""

import logging
import os
import re
from urllib.parse import urlparse
import requests
import urllib3
from deployer.utils import cached, CliNonZeroExitCodeException
from . import configuration
from . import utils

AUTH = configuration.FunctionalIdConfig()
CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ArtifactNotFoundException(Exception):
    """Custom exception for expressing an artifact not being found."""


class MediaCategoryNotDefinedException(Exception):
    """Custom exception for expressing an media category not defined for new artifact."""


@cached
def get_product_set_version(product_set_string):
    """
    Return the product set version according to the product set version string.

    Args:
        product_set_string (str): product set in string

    Returns:
        (str): product set version
    """
    product = get_product_name()
    product_set_string = product_set_string.upper()
    query = ''
    qualifier = '::'
    if qualifier in product_set_string:
        drop = product_set_string.split(qualifier, 1)[0]
        product_set_version = product_set_string.split(qualifier, 1)[1]
    else:
        drop = product_set_string
        product_set_version = 'LATEST'

    if product_set_version == 'LATEST':
        query = f'/api/productSet/{product}/drop/{drop}/versions/latest/'
    elif product_set_version == 'GREEN':
        query = f'/getLastGoodProductSetVersion/?drop={drop}&productSet={product}'

    if query != '':
        product_set_version = execute_ci_portal_get_rest_call(query, 'string')

    return product_set_version


def get_version_from_package_url(**kwargs):
    """
    Return the version of a package according to the URL given.

    Args:
        url (str): Package url

    Returns:
        version (str): package version
    """
    url = kwargs.pop('package_url')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    package_name = url[url.rindex('/') + 1:]
    pattern = "(\\-)(\\d+).(\\d+).(\\d+)"
    version_pattern = re.compile(pattern)
    version = version_pattern.search(package_name).group()
    version = version.replace('-', '')
    if 'SNAPSHOT' in package_name:
        version = f'{version}-SNAPSHOT'
    return version


@cached
def get_artifact_details_from_media(**kwargs):
    """
    Return details from the CI portal about a given artifact.

    It finds the artifact on the given media, given the product set version

    Args:
        media_cxp_number (str): media cxp number
        cxp_number (str): cxp number
        product_set_version (str): Product set version

    Returns:
        iso_version_artifact (dict): iso version artifact details

    Raises:
        ArtifactNotFoundException: if Artifact not found on the given media
    """
    media_cxp_number = kwargs.pop('media_cxp_number')
    cxp_number = kwargs.pop('cxp_number')
    product_set_version = kwargs.pop('product_set_version')
    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    product_set_version_contents = get_ps_version_contents_cached(
        product_set_version
    )
    # Figure out the contents of the media
    # associated with the given product set
    for product_set_artifact in product_set_version_contents:
        if product_set_artifact['artifactNumber'] == media_cxp_number:
            iso_version_contents = get_media_contents_cached(
                product_set_artifact['artifactName'],
                product_set_artifact['version']
            )
            break

    # Try to find the artifact on the media
    for iso_version_artifact in iso_version_contents:
        if iso_version_artifact['number'] == cxp_number:
            return iso_version_artifact

    raise ArtifactNotFoundException(
        'Couldn\'t find this cxp on the given media: %s' % cxp_number
    )


def get_local_artifact_url(**kwargs):
    """
    Return local url based on host response time.

    Args:
        artifact_object (obj): artifact object

    Returns:
        local artifact url (str): artifact url

    Raises:
        CliNonZeroExitCodeException: if the commands fails with a non-zero exit code
    """
    artifact_object = kwargs.pop('artifact_object')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    hub_key = 'hubUrl' if artifact_object.get('hubUrl') else 'hub_url'
    hub_netloc = urlparse(artifact_object.get(hub_key)).netloc
    hub_hostname = hub_netloc.split(':')[0]

    if not (artifact_object.get('athloneUrl') or artifact_object.get('athlone_url')):
        LOG.info('%s will be downloaded from: %s as no alternative source is available.',
                 os.path.basename(artifact_object[hub_key]), hub_hostname)
        return artifact_object[hub_key]

    athlone_key = 'athloneUrl' if artifact_object.get('athloneUrl') else 'athlone_url'
    if artifact_object.get(athlone_key) == '':
        LOG.info('%s will be downloaded from: %s as no alternative source is available.',
                 os.path.basename(artifact_object[hub_key]), hub_hostname)
        return artifact_object[hub_key]

    athlone_netloc = urlparse(artifact_object[athlone_key]).netloc
    athlone_hostname = athlone_netloc.split(':')[0]

    try:
        athlone_response_time = utils.get_host_response_time(hostname=athlone_hostname)
    except CliNonZeroExitCodeException:
        LOG.info('%s will be downloaded from: %s as %s was unreachable.',
                 os.path.basename(artifact_object[hub_key]), hub_hostname, athlone_hostname)
        return artifact_object[hub_key]

    try:
        hub_response_time = utils.get_host_response_time(hostname=hub_hostname)
    except CliNonZeroExitCodeException:
        LOG.info('%s will be downloaded from: %s as %s was unreachable.',
                 os.path.basename(artifact_object[athlone_key]), athlone_hostname, hub_hostname)
        return artifact_object[athlone_key]

    if athlone_response_time > hub_response_time:
        LOG.info('%s will be downloaded from: %s as it was determined to have the least latency.',
                 os.path.basename(artifact_object[hub_key]), hub_hostname)
        return artifact_object[hub_key]
    return artifact_object[athlone_key]


@cached
def get_nexus_url_from_ps_and_media(cxp_number, product_set_version):
    """
    Return the nexus url for a given cxp number from the product set and media details.

    Args:
        cxp_number (str): artifact cxp number
        product_set_version (str): product set version

    Returns:
        nexus url from media (str): artifact url

    Raises:
        ArtifactNotFoundException: if Artifact not found on the given media
    """
    product_set_version_contents = get_ps_version_contents_cached(
        product_set_version
    )
    # Try to find the media on the product set
    for artifact_object in product_set_version_contents:
        if artifact_object['artifactNumber'] == cxp_number:
            return get_local_artifact_url(artifact_object=artifact_object)

    media_cxp_numbers = [
        CONFIG.get('CXPNUMBERS', 'ENM_ISO'),
        CONFIG.get('CXPNUMBERS', 'VNF_LCM')
    ]
    exception_caught = ''
    for media_cxp_number in media_cxp_numbers:
        try:
            artifact_details = get_artifact_details_from_media(
                media_cxp_number=media_cxp_number,
                cxp_number=cxp_number,
                product_set_version=product_set_version
            )
            artifact_url = artifact_details['url']
            return artifact_url
        except ArtifactNotFoundException as exception:
            exception_caught = exception
    raise exception_caught


@cached
def get_ps_version_contents_cached(product_set_version):
    """
    Return the contents of the product set version given.

    Args:
        product_set_version (str): product set version

    Returns:
        (obj): REST request reponse
    """
    product_set_name = get_product_name()
    query = f'/getProductSetVersionContents/?productSet={product_set_name}\
&version={product_set_version}'
    ps_version_contents_json_obj = execute_ci_portal_get_rest_call(
        query,
        "json"
    )
    return ps_version_contents_json_obj[0]['contents']


@cached
def get_media_contents_cached(iso_name, iso_version):
    """
    Return the contents of the media version given.

    Args:
        iso_name (str): media iso_name
        iso_version (str): media iso_version

    Returns:
        (obj): REST request response
    """
    query = f'/getPackagesInISO/?isoName={iso_name}&isoVersion={iso_version}&useLocalNexus=true'
    iso_version_contents_json_obj = execute_ci_portal_get_rest_call(
        query,
        'json'
    )
    return iso_version_contents_json_obj['PackagesInISO']


def execute_ci_portal_get_rest_call(query, url_return_type):
    """
    Function used to run a get rest call towards the ci portal.

    Input:
        The url to call and the url return type (json or text)
    Output:
        The response from the rest call
    """
    base_url = AUTH.get('ci_portal', 'base_url')
    full_url = f'{base_url}{query}'
    LOG.info('Running REST call towards the CI Portal (%s)', full_url)
    logging.getLogger('requests').setLevel(logging.WARNING)
    response = requests.get(full_url, verify=False)
    response.raise_for_status()
    if url_return_type == 'json':
        data = response.json()
    else:
        data = response.text
    LOG.info('REST call completed')
    return data


def get_artifact_url(**kwargs):
    """
    Get the required artifact urls.

    Args:
        cxp_number (str): cxp_number
        product_set_version (str): product set version
        artifact_urls (list, optional): artifact urls, defaults to None

    Returns:
        (str): artifact url

    Raises:
        ValueError: if product set version is None
    """
    cxp_number = kwargs.pop('cxp_number')
    product_set_version = kwargs.pop('product_set_version')
    artifact_urls = kwargs.pop('artifact_urls', None)

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    if artifact_urls is not None:
        override_artifact = [url for url in artifact_urls if cxp_number in url]
        if override_artifact:
            return override_artifact[0]

    if product_set_version is None:
        raise ValueError('Undefined artifact url for: %s check that the artifact is present \
in artifact file supplied.' % cxp_number)

    return get_nexus_url_from_ps_and_media(
        cxp_number,
        product_set_version
    )


def get_product_name():
    """
    Return the product name to use during calls to the CI Portal.

    Returns:
        (str): product name
    """
    return 'ENM'


def get_latest_product_drop(**kwargs):
    """
    Get latest drop for a given product.

    Args:
        product_name (str): latest drop product name

    Returns:
        (str): product latest drop
    """
    product_name = kwargs.pop('product_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    response = execute_ci_portal_get_rest_call(
        f'/api/product/{product_name}/latestdrop/',
        'json'
    )
    return response['drop']


def get_product_drop_contents(**kwargs):
    """
    Get product drop contents.

    Args:
        product_name (str): product name
        product_drop (str): product drop

    Returns:
        (obj): REST request response
    """
    product_name = kwargs.pop('product_name')
    product_drop = kwargs.pop('product_drop')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    return execute_ci_portal_get_rest_call(
        f'/getDropContents/?drop={product_drop}&product={product_name}&pretty=true',
        'json'
    )
