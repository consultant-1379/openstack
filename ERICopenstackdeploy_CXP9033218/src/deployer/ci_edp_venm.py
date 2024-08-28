"""This file contains logic relating to CI EDP VENM utility."""

import json
import logging
import os
import urllib.request

from cliff.command import Command
from deployer.utils import cached
from deployer.utils import CliNonZeroExitCodeException
from . import artifact
from . import ci
from . import configuration
from . import dit
from . import openstack
from . import utils
from . import cli_parameter


CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIEDPVENM(Command):
    """
    Downloads media and prepares configuration files for VENM using EDP.

    Attributes:
        cis_access (boolean, optional): cis access, defaults to True
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialise a CI EDP VENM Command object."""
        super().__init__(*args, **kwargs)
        self.cis_access = True

    def get_parser(self, prog_name):
        """
        Return the parser object for this command.

        Args:
            prog_name (str): ci edp venm

        Returns:
            parser (obj): command line parameters
        """
        self.cis_access = 'nwci' not in prog_name
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_skip_media_download_param(parser)
        if self.cis_access is True:
            parser = cli_parameter.add_product_set_params(parser)
            parser = cli_parameter.add_rpm_versions_param(parser)
            parser = cli_parameter.add_os_cacert_url_param(parser)
        else:
            parser = cli_parameter.add_openstack_credential_params(parser)
            parser = cli_parameter.add_sed_file_params(parser)
            parser = cli_parameter.add_lcm_sed_file_params(parser)
            parser = cli_parameter.add_artifact_json_file_param(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Args:
            deployment-name (str)
            product-set (str)
            rpm-versions(str)
            os-cacert-url(str)
        """
        # pylint: disable=R0912,R0914,R0915
        artifact_urls = []
        if self.cis_access is True:
            product_set_version = ci.get_product_set_version(args.product_set_string)
            deployment = dit.Deployment(deployment_name=args.deployment_name)
            os_project_details = deployment.project.credentials
            utils.setup_openstack_env_variables(os_project_details)

            os_cacert_filepath = ''
            if args.os_cacert_url:
                file_name = f'publicOS-{os_project_details["os_project_name"]}.cer'
                utils.write_data_file(
                    file_data=urllib.request.urlopen(args.os_cacert_url).read(),
                    file_path=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'), file_name)
                )
                os_cacert_filepath = os.path.join(CONFIG.get('EDP', 'ETC_DIR'), file_name)

            if args.rpm_versions:
                artifacts = artifact.Artifacts(
                    deployment_name=args.deployment_name,
                    product_set_version=product_set_version,
                    product_offering='enm',
                    rpm_versions=args.rpm_versions,
                    image_name_postfix=deployment.sed.content['parameters'].get('image_postfix', '')
                )
                artifact_urls = artifacts.get_kgb_plus_n_urls(
                    artifacts_dir=CONFIG.get('EDP', 'artifacts_dir')
                )

            enm_heat_templates_url = ci.get_artifact_url(
                cxp_number=CONFIG.get('CXPNUMBERS', 'ENM_HEAT_TEMPLATES'),
                product_set_version=product_set_version,
                artifact_urls=artifact_urls
            )
            enm_sed_schema = Schema(
                document=deployment.sed,
                version=utils.get_artifact_version_from_url(enm_heat_templates_url)
            )
            enm_sed_schema.update()
            enm_sed = Sed(
                document_id=deployment.sed.database_id,
                file_path=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'),
                                       CONFIG.get('enm', 'sed_file_name'))
            )
            vnflcm_media_url = ci.get_artifact_url(
                cxp_number=CONFIG.get('CXPNUMBERS', 'VNF_LCM'),
                product_set_version=product_set_version,
                artifact_urls=artifact_urls
            )
            vnflcm_sed_schema = Schema(
                document=deployment.vnf_lcm_sed,
                version=utils.get_artifact_version_from_url(vnflcm_media_url)
            )
            vnflcm_sed_schema.update()
            vnflcm_sed = Sed(
                document_id=deployment.vnf_lcm_sed.database_id,
                file_path=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'), 'lcm_sed.json')
            )
        else:
            product_set_version = None
            os_project_details = vars(args)
            utils.setup_openstack_env_variables(os_project_details)
            os_cacert_filepath = os_project_details['os_cacert']
            if os_cacert_filepath:
                file_name = 'publicOS-' + os_project_details['os_project_name'] + '.cer'
                utils.copy_file(
                    src=os_cacert_filepath,
                    dest=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'), file_name)
                )
                os_cacert_filepath = os.path.join(CONFIG.get('EDP', 'ETC_DIR'), file_name)

            if args.artifact_json_url:
                LOG.info('Reading file content of: %s', args.artifact_json_url)
                artifact_json_content = urllib.request.urlopen(args.artifact_json_url).read()
                try:
                    artifact_json = json.loads(artifact_json_content)
                except ValueError:
                    LOG.error('Unable to parse media artifact json document: %s Please ensure \
                              this file contains a valid json object.', args.artifact_json)
                    raise
            elif args.artifact_json_file:
                artifact_json = utils.load_json_file(
                    file_path=args.artifact_json_file
                )

            enm_heat_templates_url = artifact_json[CONFIG.get('CXPNUMBERS', 'ENM_HEAT_TEMPLATES')]
            artifact_urls += artifact_json.values()
            enm_sed = Sed(
                document_url=args.sed_file_url,
                document_path=args.sed_file_path,
                file_path=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'),
                                       CONFIG.get('enm', 'sed_file_name'))
            )
            vnflcm_sed = Sed(
                document_url=args.vnf_lcm_sed_file_url,
                document_path=args.vnf_lcm_sed_file_path,
                file_path=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'), 'lcm_sed.json')
            )

        if enm_sed.content['parameter_defaults'].get('image_postfix'):
            ci_image_postfix = enm_sed.content['parameter_defaults']['image_postfix']
        else:
            ci_image_postfix = ''
        enm_image_details = get_image_details(
            product_set_version=product_set_version,
            image_key_mapping=enm_sed.image_keys,
            media_cxp_numbers=enm_sed.media_keys.values(),
            postfix=ci_image_postfix,
            artifact_urls=artifact_urls
        )
        enm_media_details = get_media_details(
            product_set_version=product_set_version,
            media_key_mapping=enm_sed.media_keys,
            image_cxp_numbers=enm_sed.image_keys.values(),
            artifact_urls=artifact_urls
        )
        enm_sed_media_mapping = {media.key: media.name for media in enm_media_details}
        enm_sed.populate(sed_key_value_mapping=enm_sed_media_mapping)
        enm_sed.save()
        os_project_id = openstack.get_resource_attribute(
            identifier=os_project_details['os_project_name'],
            resource_type='project',
            attribute='id'
        )
        private_ssh_key = ''
        public_ssh_key = ''
        key_pair_name = enm_sed.content['parameter_defaults']['key_name']
        if 'SIENM' not in enm_sed.content['parameter_defaults']['enm_deployment_type']:
            heat_templates_dir = openstack.download_and_extract_templates(
                url=enm_heat_templates_url
            )
            key_pair_stack = openstack.Stack(
                name=key_pair_name,
                stack_file_path=heat_templates_dir + CONFIG.get('enm', 'key_pair_template'),
                param_file_path=enm_sed.file_path
            )
            if not key_pair_stack.already_exists():
                key_pair_stack.create()
                key_pair_stack.wait_until_created()
            private_ssh_key = openstack.get_private_ssh_key(
                key_pair_stack_name=key_pair_name
            )
            public_ssh_key = openstack.get_public_ssh_key(
                key_pair_stack_name=key_pair_name
            )
        else:
            LOG.info('SIENM deployment retrieving CA Cert.')
            vio_ca_cert = utils.get_vio_ca_cert(
                os_auth_url=os_project_details['os_auth_url']
            )
            os_cacert_filename = 'publicOS-' + os_project_details['os_project_name'] + '.cer'
            utils.write_data_file(
                file_data=vio_ca_cert,
                file_path=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'), os_cacert_filename)
            )
            os_cacert_filepath = os.path.join(CONFIG.get('EDP', 'ETC_DIR'), os_cacert_filename)
            attempts = 0
            while not private_ssh_key:
                if attempts >= 10:
                    LOG.warning('Unable to retrieve key pair from IVMS.')
                    break
                private_ssh_key = utils.run_ssh_command(
                    ip_address=enm_sed.content['parameter_defaults']['vms_ip_vio_mgt'],
                    username='root',
                    password=enm_sed.content['parameter_defaults']['vms_root_password'],
                    command='cat ' + os.path.join(CONFIG.get('vio', 'config_dir'),
                                                  key_pair_name + '.pem')
                )
                attempts += 1

            if self.cis_access:
                dit.execute_dit_put_rest_call(
                    f'/api/projects/{deployment.project.database_id}/',
                    json.dumps({"id": os_project_id})
                )

        if self.cis_access and private_ssh_key:
            dit.post_enm_key_pair_to_dit(
                deployment_id=deployment.deployment_id,
                deployment_key_pair=deployment.enm,
                public_key=public_ssh_key,
                private_key=private_ssh_key
            )
        utils.save_private_key(
            private_key=private_ssh_key,
            file_path=os.path.join(CONFIG.get('EDP', 'CONFIG_DIR'), key_pair_name + '.pem')
        )

        utils.create_keystone_file(
            os_auth_url=os_project_details['os_auth_url'],
            os_project_id=os_project_id,
            os_project_name=os_project_details['os_project_name'],
            os_username=os_project_details['os_username'],
            os_password=os_project_details['os_password'],
            os_volume_api_version=openstack.get_volume_api_version(),
            os_cacert_filepath=os_cacert_filepath,
            destination_directory=CONFIG.get('EDP', 'CONFIG_DIR')
        )
        vnflcm_media_details = get_media_details(
            product_set_version=product_set_version,
            media_key_mapping=vnflcm_sed.media_keys,
            image_cxp_numbers=vnflcm_sed.image_keys.values(),
            artifact_urls=artifact_urls
        )
        vnflcm_sed_media_mapping = {media.key: media.name for media in vnflcm_media_details}
        vnflcm_sed.populate(sed_key_value_mapping=vnflcm_sed_media_mapping)
        deployment_id = vnflcm_sed.content['parameter_defaults']['deployment_id']
        vnflcm_sed.populate(
            sed_key_value_mapping=get_vnflcm_resource_ids(stack_name=f'{deployment_id}_VNFLCM')
        )
        vnflcm_sed.save()
        if args.skip_media_download:
            LOG.info('--skip-media-download CLI parameter was specified, therefore no media \
was downloaded.')
            LOG.info('ENM and VNF-LCM SED, project.rc and private SSH key download complete.')
        else:
            download_artifacts(artifact_details=enm_image_details)
            download_artifacts(artifact_details=enm_media_details)
            download_artifacts(artifact_details=vnflcm_media_details)
            LOG.info('ENM and VNF-LCM media, SED, project.rc and private SSH key download \
complete.')


class Image:
    """
    This class represents an image artifact.

    It provides functions to read/manipulate an image.

    Attributes:
        product_set_version (str): product set version
        cxp_number (str): image cxp number
        is_media (boolean): image is_media
        is_required (boolean): image is_required
        postfix (str, optional): image postfix, defaults to empty string
        artifact_urls (list): image urls
    """

    def __init__(self, **kwargs):
        """Initialise a image object."""
        self.product_set_version = kwargs.pop('product_set_version')
        self.cxp_number = kwargs.pop('cxp_number')
        self.is_media = kwargs.pop('is_media')
        self.is_required = kwargs.pop('is_required')
        self.postfix = kwargs.pop('postfix', '')
        self.artifact_urls = kwargs.pop('artifact_urls')

    @property
    def name(self):
        """str: Return image name."""
        file_name = os.path.basename(self.url)
        return file_name.replace(file_name[file_name.rfind('.'):], self.postfix)

    @property
    def url(self):
        """str: Return image url."""
        return ci.get_artifact_url(
            product_set_version=self.product_set_version,
            cxp_number=self.cxp_number,
            artifact_urls=self.artifact_urls
        )

    @property
    @cached
    def exists(self):
        """bool: Return true if image exists in glance or on the file system."""
        file_name = os.path.join(CONFIG.get('EDP', 'artifacts_dir'), os.path.basename(self.url))
        if os.path.isfile(file_name):
            return True
        if self.is_required:
            return False

        image_list = openstack.openstack_client_command(
            command_type='openstack',
            object_type='image',
            action='list',
            arguments='--insecure --limit 1000000'
        )
        return any(image['Name'] == self.name for image in image_list)

    def download(self):
        """Download image."""
        if self.is_media and not self.exists:
            utils.download_file(
                url=self.url,
                destination_directory=CONFIG.get('EDP', 'artifacts_dir')
            )


class Media:
    """
    This class represents a media artifact.

    It provides functions to read/manipulate media.

    Attributes:
        product_set_version (str): product set version
        cxp_number (str): cxp number
        key (str): SED key
        is_image (boolean): media is_image
        artifact_urls (list): media urls
    """

    def __init__(self, **kwargs):
        """Initialise a media object."""
        self.product_set_version = kwargs.pop('product_set_version')
        self.cxp_number = kwargs.pop('cxp_number')
        self.key = kwargs.pop('key')
        self.is_image = kwargs.pop('is_image')
        self.artifact_urls = kwargs.pop('artifact_urls')

    @property
    def name(self):
        """str: Return media filename."""
        return os.path.basename(self.url)

    @property
    def url(self):
        """str: Return the media download url."""
        return ci.get_artifact_url(
            cxp_number=self.cxp_number,
            product_set_version=self.product_set_version,
            artifact_urls=self.artifact_urls
        )

    @property
    def exists(self):
        """boolean: Return true if media file already exists."""
        return os.path.isfile(os.path.join(CONFIG.get('EDP', 'artifacts_dir'), self.name))

    def download(self):
        """Download media file."""
        if not self.is_image and not self.exists:
            utils.download_file(
                url=self.url,
                destination_directory=CONFIG.get('EDP', 'artifacts_dir')
            )


class Schema:
    """
    This class represents a site engineering document schema json.

    It provides functions to update SED schema version.

    Attributes:
        document (obj): schema document
        version (str): schema version
    """

    def __init__(self, **kwargs):
        """Initialise a SED schema object."""
        self.document = kwargs.pop('document')
        self.version = kwargs.pop('version')

    @property
    def name(self):
        """str: Return SED schema name."""
        return self.document.schema.name

    def update(self):
        """Update SED schema version."""
        LOG.info('Updating %s SED schema.', self.name)
        dit.update_sed_schema_version(
            document=self.document,
            new_version=self.version
        )


class Sed:
    """
    This class represents a site engineering document.

    It provides functions to read/manipulate and save a SED file.

    Attributes:
        document_id (str, optional): document_id, defaults to  None
        document_url (str, optional): document_url, defaults to  None
        document_path (str, optional): document path, defaults to  None
        file_path (str): file path
    """

    def __init__(self, **kwargs):
        """Initialise a SED object."""
        self.document_id = kwargs.pop('document_id', None)
        self.document_url = kwargs.pop('document_url', None)
        self.document_path = kwargs.pop('document_path', None)
        self.file_path = kwargs.pop('file_path')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        if self.document_id:
            document_object = dit.execute_dit_get_rest_call(
                url_string=f'/api/documents/{self.document_id}'
            )
            self.document = document_object['content']
        elif self.document_url:
            self.document = json.loads(urllib.request.urlopen(self.document_url).read())
        elif self.document_path:
            self.document = self.load_document()

    @property
    @cached
    def content(self):
        """obj: Return contents of the SED."""
        if 'parameters' in self.document:
            content = {'parameter_defaults': {}}
            content['parameter_defaults'].update(self.document['parameters'])
            return content
        return self.document

    @property
    def image_keys(self):
        """dict: Return SED image keys."""
        image_keys = {}
        for sed_key, key_value in self.content['parameter_defaults'].items():
            if 'image' in sed_key and key_value.upper().startswith('CXP'):
                image_keys.update({sed_key: key_value.upper()})
            elif 'dvms_image_name' in sed_key:
                continue
            elif 'image' in sed_key and not sed_key.startswith('image') and key_value != '':
                LOG.error('The SED key: "%s" has an invalid value: %s', sed_key, key_value)
                raise RuntimeError(
                    """
                    Missing SED key media mappings in SED, each required image and media key
                    must have a corresponding CXP number value only in order to populate the SED.
                    """
                )
        return image_keys

    @property
    def media_keys(self):
        """dict: Return SED media keys."""
        media_keys = {}
        for sed_key, key_value in self.content['parameter_defaults'].items():
            if sed_key.endswith('_media') and key_value.upper().startswith('CXP'):
                media_keys.update({sed_key: key_value.upper()})
            elif sed_key.endswith('_media') and key_value != '':
                LOG.error('The SED key: "%s" has an invalid value: %s', sed_key, key_value)
                raise RuntimeError(
                    """
                    Missing SED key media mappings in SED, each required image and media key
                    must have a corresponding CXP number value only in order to populate the SED.
                    """
                )
        return media_keys

    def populate(self, **kwargs):
        """
        Populate SED key values.

        Args:
            sed_key_value_mapping (str): SED key value mapping
        """
        sed_key_value_mapping = kwargs.pop('sed_key_value_mapping')

        if kwargs:
            raise TypeError('Unexpected **kwargs: %r' % kwargs)

        for sed_key, key_value in sed_key_value_mapping.items():
            LOG.info('Populate SED key: %s with the value: %s', sed_key, key_value)
            self.content['parameter_defaults'][sed_key] = key_value

    def save(self):
        """
        Save the current SED details as json.

        The SED details will be saved from memory
        into the given file path on disk in json format.
        """
        # Convert values to strings to workaround issue with lcm
        # not being able to parse non string values
        sed_content = {
            'parameter_defaults': {}
        }
        for key, value in self.content['parameter_defaults'].items():
            sed_content['parameter_defaults'][key] = str(value)
        utils.save_json_string_to_disk(
            file_path=self.file_path,
            json_string={'parameter_defaults': sed_content['parameter_defaults']}
        )
        LOG.info('Saving SED contents to: %s', self.file_path)

    def load_document(self):
        """
        Load document from file on the file system.

        Returns:
            (obj): document content

        Raises:
            ValueError: if SED document is not found
        """
        with open(self.document_path, 'r') as file_object:
            file_contents = file_object.read()

        try:
            document = json.loads(file_contents)
        except ValueError:
            LOG.error('Unable to parse SED document: %s this document must contain \
                      a valid json object.', self.document_path)
            raise

        if not isinstance(document, dict):
            raise RuntimeError(
                'The SED document could not be parsed properly, please make sure its valid.'
            )
        return document


def get_image_details(**kwargs):
    """
    Return image details.

    Args:
        product_set_version (str): image product set version
        image_key_mapping (dict): image key mapping
        media_cxp_numbers (list): list of image media cxp numbers
        postfix (str): ci image postfix
        artifact_urls (list): list of artifact urls

    Returns:
        image details (list): list of Image object instances
    """
    product_set_version = kwargs.pop('product_set_version')
    image_key_mapping = kwargs.pop('image_key_mapping')
    media_cxp_numbers = kwargs.pop('media_cxp_numbers')
    postfix = kwargs.pop('postfix')
    artifact_urls = kwargs.pop('artifact_urls')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    image_details = []
    for key, cxp_number in image_key_mapping.items():
        is_media = cxp_number in media_cxp_numbers
        is_required = cxp_number in CONFIG.get('CXPNUMBERS', 'ENM_ISO')
        image = Image(
            product_set_version=product_set_version,
            cxp_number=cxp_number,
            key=key,
            is_media=is_media,
            is_required=is_required,
            postfix=postfix,
            artifact_urls=artifact_urls
        )
        image_details.append(image)
    return image_details


def get_media_details(**kwargs):
    """
    Return media details.

    Args:
        product_set_version (str): media product set version
        media_key_mapping (dict): media key mapping
        image_cxp_numbers (str): image cxp numbers
        artifact_urls (str): artifact urls

    Returns:
        (list): list of Media object instances
    """
    product_set_version = kwargs.pop('product_set_version')
    media_key_mapping = kwargs.pop('media_key_mapping')
    image_cxp_numbers = kwargs.pop('image_cxp_numbers')
    artifact_urls = kwargs.pop('artifact_urls')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    media_details = []
    for key, cxp_number in media_key_mapping.items():
        is_image = cxp_number in image_cxp_numbers
        media = Media(
            product_set_version=product_set_version,
            cxp_number=cxp_number,
            key=key,
            is_image=is_image,
            artifact_urls=artifact_urls
        )
        media_details.append(media)
    return media_details


def download_artifacts(**kwargs):
    """
    Download artifacts.

    Args:
        artifact_details (obj): artifact details
    """
    artifact_details = kwargs.pop('artifact_details')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    for artifact_item in artifact_details:
        artifact_item.download()


def get_vnflcm_resource_ids(**kwargs):
    """
    Return VNF-LCM stack resource ids.

    Args:
        stack_name (str): VNF-LCM stack name

    Returns:
        (dict): VNF-LCM stack resource ids

    Raises:
        CliNonZeroExitCodeException: if the command failed with exit code
    """
    stack_name = kwargs.pop('stack_name')

    if kwargs:
        raise TypeError('Unexpected **kwargs: %r' % kwargs)

    vnflcm_resource_ids = {}
    try:
        stack_params = openstack.openstack_client_command(
            command_type='openstack',
            object_type='stack',
            action='environment show',
            arguments=stack_name
        )
    except CliNonZeroExitCodeException:
        return vnflcm_resource_ids

    vnflcm_resource_ids = {
        'server_group_for_db_vm': stack_params['parameter_defaults']['server_group_for_db_vm'],
        'security_group_id': stack_params['parameter_defaults']['security_group_id'],
        'cinder_volume_id': stack_params['parameter_defaults']['cinder_volume_id'],
        'server_group_for_svc_vm': stack_params['parameter_defaults']['server_group_for_svc_vm'],
        'internal_net_id': stack_params['parameter_defaults']['internal_net_id'],
        'external_mtu': stack_params['parameter_defaults']['external_mtu'],
        'internal_mtu': stack_params['parameter_defaults']['internal_mtu'],
        'external_net_id': stack_params['parameter_defaults']['external_net_id']
    }
    return vnflcm_resource_ids
