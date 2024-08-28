"""This file contains logic relating to managing artifacts."""

import json
import logging
import os
import re
import requests
import semantic_version

from pyunpack import Archive
from deployer.utils import cached
from deployer.ci import MediaCategoryNotDefinedException, ArtifactNotFoundException
from . import ci
from . import configuration
from . import image_utils
from . import openstack
from . import utils


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)


class Artifacts:
    """
    Represents an artifacts instance.

    This class represents an artifacts instance and provides
    functions to manage artifact related tasks.

    Attributes:
        deployment_name (str): deployment_name
        product_set_version (str, optional): product_set_version, defaults to None
        product_offering (str, optional): product_offering, defaults to None
        artifact_json_file (str, optional): artifact_json_file, defaults to None
        artifact_json_url (str, optional): artifact_json_url, defaults to None
        image_name_postfix (str, optional): image_name_postfix, defaults to empty string
        rpm_versions (str, optional): rpm_versions, defaults to None
        media_versions (str, optional): media_versions, defaults to None
        is_vio_deployment (boolean): is_vio_deployment, defaults to False
    """

    # pylint: disable=R0902

    LOG = logging.getLogger(__name__)

    def __init__(self, **kwargs):
        """Initialize an artifacts object."""
        self.deployment_name = kwargs.pop('deployment_name')
        self.product_set_version = kwargs.pop('product_set_version', None)
        self.product_offering = kwargs.pop('product_offering')
        self.artifact_json_file = kwargs.pop('artifact_json_file', None)
        self.artifact_json_url = kwargs.pop('artifact_json_url', None)
        self.image_name_postfix = kwargs.pop('image_name_postfix', '')
        self.rpm_versions = kwargs.pop('rpm_versions', None)
        self.media_versions = kwargs.pop('media_versions', None)
        self.is_vio_deployment = kwargs.pop('is_vio_deployment', False)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.temp_directory = utils.get_temporary_directory_path()
        self.product_offering_details = utils.get_product_offering_details(
            product_offering=self.product_offering
        )

    @property
    @cached
    def artifact_json(self):
        """obj: Return a populated artifact json object."""
        if self.artifact_json_url is not None:
            self.artifact_json_file = utils.download_file(
                url=self.artifact_json_url,
                destination_directory=self.temp_directory
            )
        if self.artifact_json_file is not None:
            return utils.load_json_file(
                file_path=self.artifact_json_file
            )

        return self.generate_artifact_json()

    @property
    def media_details(self):
        """list: Return media artifact details list."""
        return image_utils.ImageListFromConfig(
            product_offering=self.product_offering,
            artifact_json=self.artifact_json,
            image_name_postfix=self.image_name_postfix
        )

    def __check_parameter_format(self):
        """Check media and RPM versions parameter format."""
        ignored_colons = [':/', '.se:', '.com:']
        if self.rpm_versions:
            ignored_colons_count = sum([self.rpm_versions.count(item) for item in ignored_colons])
            if self.rpm_versions.count('@') % 2 != 0:
                raise ValueError('Packages and media should be separated by "@@", check the \
following parameters: %s' % self.rpm_versions)
            artifact_version_separator_count = self.rpm_versions.count(':') - ignored_colons_count
            if artifact_version_separator_count % 2 != 0 or artifact_version_separator_count < 2:
                raise ValueError('Artifact ids, versions, urls and or category information should \
be separated by "::", check the following parameters: %s' % self.rpm_versions)

        if self.media_versions:
            ignored_colons_count = sum([self.media_versions.count(item) for item in ignored_colons])
            vnflcm_artifact_id = self.product_offering_details['vnflcm_cloudtemplates_details'][
                'artifact_id']
            media_version_separator_count = self.media_versions.count(':') - ignored_colons_count
            if media_version_separator_count % 2 != 0 or media_version_separator_count < 2:
                raise RuntimeError('Media artifact ids and version information should be separated \
"::", check the following parameters: %s' % self.media_versions)
            if self.media_versions.count('@') % 2 != 0:
                raise RuntimeError('Media artifacts should be separated by "@@", check the \
following parameters: %s' % self.media_versions)
            if (CONFIG.get('CXPNUMBERS', 'VNF_LCM') in self.media_versions and
                    self.rpm_versions is None):
                raise RuntimeError('Missing artifact: %s should be defined in the --rpm-versions \
parameter.' % vnflcm_artifact_id)
            if (CONFIG.get('CXPNUMBERS', 'VNF_LCM') in self.media_versions and self.rpm_versions is
                    not None and vnflcm_artifact_id not in self.rpm_versions):
                raise RuntimeError('Missing artifact: %s should be defined in the --rpm-versions \
parameter.' % vnflcm_artifact_id)

    def generate_artifact_json(self):
        """
        Generate a populated artifact json.

        Returns:
            artifact_json (obj): generated artifact json data.
                eg: {"media_details": {<cxp_number>:<url>,...}}
        """
        artifact_urls = self.get_kgb_plus_n_urls()
        artifacts = {}
        for product_set_item, item_details in self.product_offering_details.items():
            if '_details' not in product_set_item:
                continue
            if isinstance(item_details, list):
                artifacts.update({product_set_item: {}})
                cxp_number = ''
                for details in item_details:
                    try:
                        cxp_number = details.get('cxp_number')
                        url = ci.get_artifact_url(
                            cxp_number=cxp_number,
                            product_set_version=self.product_set_version,
                            artifact_urls=artifact_urls
                        )
                        artifacts[product_set_item].update({cxp_number: url})
                    except ArtifactNotFoundException:
                        LOG.warning(
                            'Media artifact with CXP number: %s was not found in Product Set: %s',
                            cxp_number, self.product_set_version
                        )
                        continue
            else:
                try:
                    url = ci.get_artifact_url(
                        cxp_number=item_details['cxp_number'],
                        product_set_version=self.product_set_version,
                        artifact_urls=artifact_urls
                    )
                    artifacts[product_set_item] = {item_details['cxp_number']: url}
                except ArtifactNotFoundException:
                    LOG.warning(
                        'Media artifact with CXP number: %s was not found in Product Set: %s',
                        cxp_number, self.product_set_version
                    )
                    continue
        artifact_json = json.dumps(artifacts)
        return json.loads(artifact_json)

    def get_kgb_plus_n_urls(self, **kwargs):
        """
        Return the additional artifact urls from CI portal.

        Args:
            artifacts_dir (str, optional): artifact's directory path, defaults to temp directory

        Returns:
            artifact_urls (list): artifact urls
        """
        artifacts_dir = kwargs.pop('artifacts_dir', self.temp_directory)

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.__check_parameter_format()
        artifact_urls = []

        if self.rpm_versions:
            artifacts = process_artifacts_parameter(media_artifacts=self.rpm_versions)
            artifact_urls.extend(self.get_test_artifact_sources(
                artifacts=artifacts,
                artifacts_dir=artifacts_dir
            ))

        if self.media_versions:
            artifact_list = process_artifacts_parameter(media_artifacts=self.media_versions)
            for artifact_id, artifact_details in artifact_list.items():
                if 'http' in artifact_details['version']:
                    artifact_urls.append(artifact_details['version'])
                else:
                    query = f'/api/getMediaArtifactVersionData/mediaArtifact/{artifact_id}\
/version/{artifact_details["version"]}/'
                    ci_portal_response = ci.execute_ci_portal_get_rest_call(query, 'json')
                    artifact_url = ci_portal_response['athlone_url']
                    if not str(artifact_url).strip():
                        artifact_url = ci_portal_response['hub_url']
                    artifact_urls.append(artifact_url)
        return artifact_urls

    def get_artifact_url(self, **kwargs):
        """
        Return artifact URL from the artifact json.

        Args:
            artifact_name (str): artifact name

        Returns:
            artifact URL (str): artifact URL from the artifact json

        Raises:
            ValueError: if an artifact with the given name is not defined in the artifact json.
        """
        artifact_name = kwargs.pop('artifact_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        details = self.product_offering_details[artifact_name]
        cxp_number = details['cxp_number']
        if cxp_number in self.artifact_json[artifact_name]:
            return str(self.artifact_json[artifact_name][cxp_number])
        raise ValueError('Missing Artifact with CXP No: %s' % cxp_number)

    def get_artifact_version(self, **kwargs):
        """
        Return artifact version from the url in the artifact json.

        Args:
            artifact_name (str): artifact name

        Returns:
            artifact version (str): artifact version

        Raises:
            ValueError: if an artifact with the given name is not defined in the artifact json.
        """
        artifact_name = kwargs.pop('artifact_name')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        details = self.product_offering_details[artifact_name]
        cxp_number = details['cxp_number']
        if cxp_number in self.artifact_json[artifact_name]:
            artifact_url = str(self.artifact_json[artifact_name][cxp_number])
        else:
            raise ValueError('Missing Artifact with CXP No: %s' % cxp_number)
        return utils.get_artifact_version_from_url(artifact_url)

    def get_artifact_id(self, **kwargs):
        """
        Return the artifact id for the given artifact.

        Args:
            artifact_type (str): artifact type

        Returns:
            artifact id (str): artifact id for the given artifact
        """
        artifact_type = kwargs.pop('artifact_type')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        artifact_details = self.product_offering_details[artifact_type]
        return artifact_details['artifact_id']

    def upload_media_artifacts(self):
        """Upload media artifacts to Glance."""
        self.media_details.upload_images_to_glance()
        self.media_details.wait_for_images_in_glance()

    def get_media_artifact_mappings(self):
        """
        Return media parent artifact mappings.

        Returns:
            media_artifact_mappings (dict): media parent artifact mappings
                eg: {<cxp_number>: <parent artifact name>}
        """
        media_details = self.product_offering_details['media_details']
        media_artifact_mappings = dict()
        for media in media_details:
            artifact_mapping = dict()
            if media.get('parent_artifact'):
                artifact_mapping[media['cxp_number']] = media['parent_artifact']
                media_artifact_mappings.update(artifact_mapping)
        return media_artifact_mappings

    def get_test_artifact_sources(self, **kwargs):
        """
        Return additional non-product set test artifact urls.

        Args:
            artifacts (dict): list of artifacts
            artifacts_dir (str): artifacts directory path

        Returns:
            artifact_sources (list): non-product set test artifact urls
                eg: [<url>,..]
        """
        artifacts = kwargs.pop('artifacts')
        artifacts_dir = kwargs.pop('artifacts_dir')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        artifact_sources = []
        edp_packages = {}
        packages = {}

        for artifact_id, artifact_details in artifacts.items():
            if is_edp_package(artifact_id=artifact_id) or artifact_details['add_category'] == 'edp':
                edp_packages.update({artifact_id: artifact_details})
            elif (is_vnflcm_media(artifact_id=artifact_id) and
                  'http' not in artifact_details['version']):
                response = ci.execute_ci_portal_get_rest_call(
                    f'/api/artifact/{artifact_id}/version/{artifact_details["version"]}/nexusUrl/\
?local=true',
                    'json'
                )
                artifact_sources.append(response[0]['url'])
            elif is_vnflcm_media(artifact_id=artifact_id):
                artifact_sources.append(artifact_details['version'])
            elif any(media for media in ci.get_ps_version_contents_cached(self.product_set_version)
                     if artifact_id in media['artifactName']):
                if 'http' not in artifact_details['version']:
                    response = ci.execute_ci_portal_get_rest_call(
                        f'/api/getMediaArtifactVersionData/mediaArtifact/{artifact_id}\
/version/{artifact_details["version"]}/',
                        'json'
                    )
                    artifact_sources.append(ci.get_local_artifact_url(artifact_object=response))
                else:
                    artifact_sources.append(artifact_details['version'])
            else:
                packages.update({artifact_id: artifact_details})

        if edp_packages:
            download_edp_packages(packages=edp_packages)

        package_instances = get_package_instances(packages=packages)
        if package_instances:
            package_urls = [package.url for package in package_instances]
            artifact_sources.extend(package_urls)
            enm_iso_name = build_enm_iso(
                product_set_version=self.product_set_version,
                image_name_postfix=self.image_name_postfix,
                package_instances=package_instances,
                deployment_name=self.deployment_name,
                build_dir=artifacts_dir
            )
            artifact_sources.append(enm_iso_name)
        return artifact_sources


class Package:
    """
    This class represents a iso package.

    It provides functions to read/manipulate iso package information.

    Attributes:
        artifact_id (str): iso package artifact id
        src_version (str): iso package source version
        add_category (str): iso package add category
        remove_category (list): iso package remove category
    """

    def __init__(self, **kwargs):
        """Initialise a Package object."""
        self.artifact_id = kwargs.pop('artifact_id')
        self.src_version = kwargs.pop('src_version')
        self.add_category = kwargs.pop('add_category')
        self.remove_category = kwargs.pop('remove_category')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        self.version = self.src_version

    @property
    def version(self):
        """str: Return package version."""
        return self._version

    @version.setter
    def version(self, version):
        if 'http' in version:
            self._version = utils.get_artifact_version_from_url(version)
        elif 'latest' in version:
            self._version = self.latest_version
        elif semantic_version.validate(version):
            self._version = version
        else:
            raise ValueError(
                'Invalid version information specified for: %s A valid url, GAV version or latest \
 tag must be specified.' % self.artifact_id)

    @property
    @cached
    def latest_version(self):
        """str: Return the package latest version."""
        try:
            response = ci.execute_ci_portal_get_rest_call(
                f'/api/deployment/getlatestartifactversion/?artifacts={self.artifact_id}::latest',
                'json'
            )
            return response.split('::')[1]
        except requests.HTTPError:
            LOG.info('Artifact: %s is not registered in the CI portal', self.artifact_id)
            return None

    @property
    def category_names(self):
        """set: Return a list of category names assiocated with package."""
        category_names = []
        if self.latest_version is not None:
            try:
                response = ci.execute_ci_portal_get_rest_call(
                    f'/api/getartifactversiondata/artifact/{self.artifact_id}/version/\
{self.latest_version}',
                    'json'
                )
                category_names = response['category__name'].split(',')
            except requests.HTTPError:
                LOG.info('This package: %s is not on the ENM ISO.', self.artifact_id)

        if not category_names and not self.add_category:
            raise MediaCategoryNotDefinedException(
                'Media category not defined for this package: %s , any new package not already \
existing/delivered to the media must have the media category defined in command line argument for \
the package e.g. <artifact_id>::<url>::<media_category_1>,<media_category_2>' % self.artifact_id
            )

        if self.add_category:
            category_names.extend(self.add_category)
        elif self.remove_category:
            category_names = [category for category in category_names
                              if category not in self.remove_category]
        return set(category_names)

    @property
    def is_package(self):
        """bool: Return True if category name is not image."""
        return 'image' not in self.category_names

    @property
    def url(self):
        """str: Return package download url."""
        if 'http' in self.src_version.lower():
            return self.src_version

        response = ci.execute_ci_portal_get_rest_call(
            f'/api/artifact/{self.artifact_id}/version/{self.version}/nexusUrl/?local=true',
            'json'
        )
        return response[0]['url']

    @property
    def directory(self):
        """str: Return package download directory."""
        return self._directory

    @directory.setter
    def directory(self, directory):
        self._directory = directory

    def download(self):
        """Download package file."""
        utils.download_file(
            url=self.url,
            destination_directory=self.directory
        )


class ISO:
    """
    This class represents a ISO image.

    It provides functions to read/manipulate and build ISO image.

    Attributes:
        product_set_version (str): product set version
        cxp_number (str): image cxp number
        postfix (str): image postfix
        build_dir (str): image build directory
    """

    def __init__(self, **kwargs):
        """Initialise a ISO object."""
        self.product_set_version = kwargs.pop('product_set_version')
        self.cxp_number = kwargs.pop('cxp_number')
        self.postfix = kwargs.pop('postfix')
        self.build_dir = kwargs.pop('build_dir')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

    @property
    def name(self):
        """str: Return iso name."""
        return os.path.basename(self.url)

    @property
    def modified_name(self):
        """str: Return modified iso file name."""
        return self.name.replace('.iso', f'{self.postfix}.iso')

    @property
    def url(self):
        """str: Return product set iso url."""
        return ci.get_nexus_url_from_ps_and_media(
            self.cxp_number,
            self.product_set_version
        )

    @property
    def extracted_filepath(self):
        """str: Return extracted iso path."""
        extracted_filepath = os.path.join(self.build_dir, self.modified_name.replace('.iso', ''))
        os.system(f'mkdir -p {extracted_filepath}')
        return extracted_filepath

    def download(self):
        """Downloaded ISO."""
        utils.download_file(
            url=self.url,
            destination_directory=self.build_dir
        )

    def extract(self):
        """Extract ISO image."""
        LOG.info('Extract %s to: %s', self.name, self.extracted_filepath)
        iso_filepath = os.path.join(self.build_dir, self.name)
        Archive(iso_filepath).extractall(self.extracted_filepath)
        LOG.info('%s extracted to: %s', self.name, self.extracted_filepath)
        os.system(f'rm -f {iso_filepath}')

    @classmethod
    def add_package(cls, **kwargs):
        """
        Add/replace packages on the extracted iso.

        Args:
            package_url (str): iso package url
            package_filepath (str): iso package filepath
        """
        package_url = kwargs.pop('package_url')
        package_filepath = kwargs.pop('package_filepath')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        LOG.info('Add %s to: %s', os.path.basename(package_url), package_filepath)
        utils.download_file(
            url=package_url,
            destination_directory=package_filepath
        )

    def get_category_path(self, **kwargs):
        """
        Return filepath of a given media category.

        Args:
            category (str): media category file path

        Returns:
            category_path (str): filepath of a given media category
        """
        category = kwargs.pop('category')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        if category in dict(CONFIG.items('ENM_ISO')):
            return os.path.join(self.extracted_filepath, CONFIG.get('ENM_ISO', category))

        for root, dirs, _ in os.walk(self.extracted_filepath):
            category_dir = [dir_name for dir_name in dirs if category in dir_name]
            if category_dir:
                category_path = os.path.join(root, category_dir[0])

        return category_path

    def get_package_path(self, **kwargs):
        """
        Return filepath of a given package.

        Args:
            artifact_id (str): Package id

        Returns:
            package_paths (list): filepaths of a given package
        """
        artifact_id = kwargs.pop('artifact_id')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        package_paths = []
        search_pattern = re.compile(f'{artifact_id}-[0-9]+.[0-9]+')
        for root, _, package in os.walk(self.extracted_filepath):
            for package_path in filter(search_pattern.match, package):
                package_paths.append(os.path.join(root, package_path))
        return package_paths

    @classmethod
    def delete_package(cls, **kwargs):
        """
        Delete package from the extracted iso.

        Args:
            package_filepath (str): package filepath

        Raises:
            FileNotFoundError: if the file not found
        """
        package_filepath = kwargs.pop('package_filepath')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        try:
            os.remove(package_filepath)
        except FileNotFoundError:
            LOG.info('File: %s not found or already deleted', package_filepath)

    def build(self):
        """Build ISO image."""
        LOG.info('Building new ISO image')
        os.system(
            f'genisoimage -J -joliet-long -allow-lowercase -allow-multidot -o \
"{self.extracted_filepath}.iso" "{self.extracted_filepath}"'
        )
        LOG.info('Deleting extracted iso: %s', self.extracted_filepath)
        os.system(f'rm -rf {self.extracted_filepath}')
        LOG.info('ISO build successfully complete.')


def process_artifacts_parameter(**kwargs):
    """
    Return a dict of dicts of media artifacts including id, version and media category.

    Args:
        media_artifacts (str): list of media artifacts

    Returns:
        processed_artifacts (dict): dict of dicts of media including id, version and media category
            eg: {<artifact_id>: {version:<version>, add_category: <[media_category]>,
                remove_category: [<media_category>]}}
    """
    media_artifacts = kwargs.pop('media_artifacts')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    processed_artifacts = {}
    for item in media_artifacts.split('@@'):
        artifact_id = item.split('::')[0]
        version = item.split('::')[1]
        if ''.join(item.split('::')[3:]).upper() == 'TRUE':
            remove_category = filter(bool, ''.join(item.split('::')[2:3]).split(','))
            if processed_artifacts.get(artifact_id):
                processed_artifacts[artifact_id]['remove_category'] = remove_category
            else:
                processed_artifacts.update(
                    {artifact_id: {
                        'version': version,
                        'add_category': list(),
                        'remove_category': remove_category}}
                )
        else:
            add_category = filter(bool, ''.join(item.split('::')[2:3]).split(','))
            if processed_artifacts.get(artifact_id):
                processed_artifacts[artifact_id]['add_category'] = add_category
            else:
                processed_artifacts.update(
                    {artifact_id: {
                        'version': version,
                        'add_category': add_category,
                        'remove_category': list()}}
                )
    return processed_artifacts


def get_package_instances(**kwargs):
    """
    Return package object instances.

    Args:
        packages (dict): list of packages

    Returns:
        package_details (obj): package object instances
    """
    packages = kwargs.pop('packages')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    package_details = []
    for artifact_id, details in packages.items():
        package = Package(
            artifact_id=artifact_id,
            src_version=details['version'],
            add_category=details['add_category'],
            remove_category=details['remove_category']
        )
        package_details.append(package)

    return package_details


def download_edp_packages(**kwargs):
    """
    Download list of EDP packages.

    Args:
        packages (dict): list of EDP packages
    """
    packages = kwargs.pop('packages')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    edp_package_details = get_package_instances(packages=packages)
    os.makedirs(CONFIG.get('EDP', 'CI_PKG_DIR'), exist_ok=True)
    for package in edp_package_details:
        package.directory = CONFIG.get('EDP', 'CI_PKG_DIR')
        package.download()


def build_enm_iso(**kwargs):
    """
    Return the modified image name of the rebuilt ENM ISO.

    Args:
        product_set_version (str): product set version
        package_instances (list): package instance
        deployment_name (str): deployment name
        build_dir (str): ISO build directory

    Returns:
        modified ENM ISO name (str): modified image name of the rebuilt ENM ISO
    """
    product_set_version = kwargs.pop('product_set_version')
    image_name_postfix = kwargs.pop('image_name_postfix', '_CI')
    package_instances = kwargs.pop('package_instances')
    deployment_name = kwargs.pop('deployment_name')
    build_dir = kwargs.pop('build_dir')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    if not image_name_postfix:
        image_name_postfix = '_CI'

    enm_iso = ISO(
        product_set_version=product_set_version,
        cxp_number=CONFIG.get('CXPNUMBERS', 'ENM_ISO'),
        postfix=f'_{deployment_name}_KGB+N',
        build_dir=build_dir
    )
    enm_iso.download()
    enm_iso.extract()
    for package in package_instances:
        package_filepaths = enm_iso.get_package_path(artifact_id=package.artifact_id)
        for package_filepath in package_filepaths:
            enm_iso.delete_package(package_filepath=package_filepath)

        for category in package.category_names:
            package_filepath = enm_iso.get_category_path(category=category)
            enm_iso.add_package(
                package_filepath=package_filepath,
                package_url=package.url
            )
    enm_iso.build()
    openstack.delete_image_in_glance(enm_iso.modified_name.replace('.iso', image_name_postfix))
    return enm_iso.modified_name


def is_vnflcm_media(**kwargs):
    """
    Return true if artifact id is part of the latest VNF-LCM media drop.

    Args:
        artifact_id (str): artifact id

    Returns:
        (bool): True | False
    """
    artifact_id = kwargs.pop('artifact_id')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    product_name = CONFIG.get('vnflcm', 'PRODUCT_NAME')
    product_drop = ci.get_latest_product_drop(product_name=product_name)
    vnflcm_media = ci.get_product_drop_contents(
        product_name=product_name,
        product_drop=product_drop
    )
    if any(media for media in vnflcm_media if artifact_id in media['name']):
        return True
    return False


def is_edp_package(**kwargs):
    """
    Return true if artifact id is part of the latest EDP autodeploy drop.

    Args:
        artifact_id (str): artifact id

    Returns:
        (bool): True | False
    """
    artifact_id = kwargs.pop('artifact_id')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    product_name = CONFIG.get('EDP', 'PRODUCT_NAME')
    product_drop = ci.get_latest_product_drop(product_name=product_name)
    edp_packages = ci.get_product_drop_contents(
        product_name=product_name,
        product_drop=product_drop
    )
    if any(package for package in edp_packages if artifact_id in package['name']):
        return True
    return False
