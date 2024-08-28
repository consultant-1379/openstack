"""This file contains logic relating to CI VIO Platform Install."""

import json
import logging
import os
from cliff.command import Command
from . import artifact
from . import ci
from . import configuration
from . import dit
from . import openstack
from . import sed
from . import utils
from . import vio
from . import cli_parameter

CONFIG = configuration.DeployerConfig()
LOG = logging.getLogger(__name__)

# pylint: disable=W0221


class CIVIOPlatformInstall(Command):
    """
    Installs VIO Platform with the help of CI tools including DIT.

    Attributes:
        product_offering (str): ENM product offering
    """

    LOG = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        """Initialize a CIVIOPlatformInstall Command object."""
        super().__init__(*args, **kwargs)
        self.product_offering = 'vio_platform'

    def get_parser(self, prog_name):
        """
        Return the parser object for this command.

        Arguments:
            prog_name (str): deployer ci vio platform install

        Returns:
            parser (object): list parameters for 'deployer ci vio platform install --help'
            usage: deployer ci vio platform install [-h] --deployment-name [DEPLOYMENT_NAME]
                                        --product-set [PRODUCT_SET_STRING]
                                        [--rpm-versions RPM_VERSIONS]
                                        [--media-versions MEDIA_VERSIONS]
                                        --vio-profile-list VIO_PROFILE_LIST

        """
        parser = super().get_parser(prog_name)
        parser = cli_parameter.add_deployment_name_param(parser)
        parser = cli_parameter.add_product_set_params(parser)
        parser = cli_parameter.add_rpm_versions_param(parser)
        parser = cli_parameter.add_media_versions_param(parser)
        parser = cli_parameter.add_vio_profile_list_param(parser)
        return parser

    def take_action(self, args):
        """
        Execute the relevant steps for this command.

        Arguments:
            Passing values for following arguments from this command:
                deployment_name (str)
                product_set_string (str)
                rpm_versions (str)
                media_versions (str)
                vio_profile_list (str)

        """
        # pylint: disable=R0914,R0915
        deployment = dit.Deployment(deployment_name=args.deployment_name)
        vio_dvms_object = deployment.vio_dvms_document.content
        dvms_ip_address = vio_dvms_object['dvms_ip_vio_mgt']
        dvms_username = vio_dvms_object['dvms_username']
        dvms_password = vio_dvms_object['dvms_password']
        is_vio_deployment = True

        artifacts = artifact.Artifacts(
            deployment_name=args.deployment_name,
            product_set_version=ci.get_product_set_version(args.product_set_string),
            product_offering=self.product_offering,
            image_name_postfix=deployment.sed.content.get('parameters').get('image_postfix', ''),
            rpm_versions=args.rpm_versions,
            media_versions=args.media_versions,
            is_vio_deployment=is_vio_deployment
        )
        dvms = vio.DeploymentVirtualManagementServer(
            ip_address=dvms_ip_address,
            username=dvms_username,
            password=dvms_password,
            os_project_details=deployment.project.credentials,
            artifact_json=artifacts.artifact_json
        )
        dvms.update_resolv_config(
            vio_dvms_object=vio_dvms_object
        )
        dvms.create_directories()
        dvms.download_vio_media()
        enm_sed_file_path = os.path.join(utils.get_temporary_directory_path(), 'sed.json')
        enm_sed_object = sed.Sed(
            product_offering=self.product_offering,
            media_details=artifacts.media_details.sed_key_values(),
            sed_document=deployment.sed,
            sed_document_path=enm_sed_file_path,
            schema_version=artifacts.get_artifact_version(artifact_name='cloud_templates_details')
        )
        vio.upload_file(
            name='ENM SED',
            file_name='sed.json',
            ip_address=dvms_ip_address,
            username=dvms_username,
            password=dvms_password,
            document_file_path=enm_sed_file_path
        )
        vnf_lcm_sed_file_path = os.path.join(utils.get_temporary_directory_path(), 'lcm_sed.json')
        sed.Sed(
            product_offering=self.product_offering,
            media_details=artifacts.media_details.sed_key_values(),
            sed_document=deployment.vnf_lcm_sed,
            sed_document_path=vnf_lcm_sed_file_path,
            schema_version=artifacts.get_artifact_version(
                artifact_name='vnflcm_cloudtemplates_details'
            )
        )
        vio.upload_file(
            name='VNF-LCM SED',
            file_name='lcm_sed.json',
            ip_address=dvms_ip_address,
            username=dvms_username,
            password=dvms_password,
            document_file_path=vnf_lcm_sed_file_path
        )
        extracted_edp_filename = utils.extract_gunzipfile_contents(
            ip_address=dvms_ip_address,
            username=dvms_username,
            password=dvms_password,
            file_path=CONFIG.get('vio', 'artifacts_dir'),
            package_name=os.path.basename(
                artifacts.get_artifact_url(artifact_name='edp_autodeploy_details')
            )
        )
        edp_tarfile_contents = utils.get_remote_tarfile_contents(
            ip_address=dvms_ip_address,
            username=dvms_username,
            password=dvms_password,
            file_path=CONFIG.get('vio', 'artifacts_dir'),
            package_name=extracted_edp_filename
        )
        edp_packages = [item for item in edp_tarfile_contents if '.rpm' in item]
        utils.extract_remote_tarfile(
            ip_address=dvms_ip_address,
            username=dvms_username,
            password=dvms_password,
            file_path=CONFIG.get('vio', 'artifacts_dir'),
            package_name=extracted_edp_filename
        )
        for package_name in edp_packages:
            utils.install_rpm_package(
                ip_address=dvms_ip_address,
                username=dvms_username,
                password=dvms_password,
                file_path=CONFIG.get('vio', 'artifacts_dir'),
                package_name=package_name
            )
        dvms.configure_dvms_for_platform(profile=CONFIG.get('vio', 'install_init_dvms'))
        dvms.install_vio_platform(
            vio_profile_list=args.vio_profile_list
        )
        vio.post_vio_key_pair_to_dit(
            deployment_id=deployment.deployment_id,
            deployment_key_pair=deployment.enm,
            vms_ip_address=enm_sed_object.sed_data['parameter_defaults']['vms_ip_vio_mgt'],
            vms_username='root',
            vms_password=enm_sed_object.sed_data['parameter_defaults']['vms_root_password'],
            vio_key_pair_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
        )
        deployment = dit.Deployment(deployment_name=args.deployment_name)
        utils.setup_openstack_env_variables(deployment.project.credentials)
        ivms = vio.InternalVirtualManagementServer(
            ip_address=enm_sed_object.sed_data['parameter_defaults']['vms_ip_vio_mgt'],
            username='root',
            password=enm_sed_object.sed_data['parameter_defaults']['vms_root_password'],
            artifact_json=artifacts.artifact_json
        )
        private_ssh_key = ivms.get_private_ssh_key(
            key_pair_name=enm_sed_object.sed_data['parameter_defaults']['key_name']
        )
        private_key_file_path = utils.save_private_key(
            private_key=private_ssh_key,
            file_path=os.path.join(utils.get_temporary_directory_path(),
                                   enm_sed_object.sed_data['parameter_defaults']['key_name'] +
                                   '.pem')
        )
        ivms.create_artifact_directory()
        ivms.download_media()
        dvms.upload_keystone_file()
        dvms.upload_private_key(private_key_file_path=private_key_file_path)
        dvms.upload_cacert_file()
        dvms.download_enm_media(
            media_artifact_mappings=artifacts.get_media_artifact_mappings(),
            image_name_postfix=deployment.sed.content.get('parameters').get('image_postfix', '')
        )
        dvms.run_profile(
            profile=CONFIG.get('vio', 'software_prep')
        )
        openstack_project_id = openstack.get_resource_attribute(
            identifier=deployment.project.os_project_name,
            resource_type='project',
            attribute='id'
        )
        dit.execute_dit_put_rest_call(
            f'/api/projects/{deployment.project.database_id}/',
            json.dumps({"id": openstack_project_id})
        )
        utils.remove_contents_of_directory(
            ip_address=dvms_ip_address,
            username=dvms_username,
            password=dvms_password,
            location=CONFIG.get('vio', 'artifacts_dir')
        )
        LOG.info(
            'The Small Integrated ENM platform install has successfully completed. \
Now follow the relevant documentation to determine when the platform is fully ready.'
        )
