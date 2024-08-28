"""This file contains cli parameters used by other modules."""

import logging

LOG = logging.getLogger(__name__)


def add_openstack_credential_params(parser):
    """
    Append openstack credential parameters to the parser.

    This function appends the openstack credential
    parameters which are required to run openstack cli commands
    """
    parser.add_argument(
        '--os-username',
        help="""
        This is the username used for openstack cli commands.
        """,
        required=True
    )

    parser.add_argument(
        '--os-password',
        help="""
        This is the password used for openstack cli commands.
        """,
        required=True
    )

    parser.add_argument(
        '--os-auth-url',
        help="""
        This is the url to connect to for openstack cli commands.
        """,
        required=True
    )

    parser.add_argument(
        '--os-project-name',
        help="""
        This is the project to use for openstack cli commands.
        """,
        required=True
    )

    parser.add_argument(
        '--os-cacert',
        help="""
        This is the certificate to use for openstack cli commands.
        """,
        default=''
    )
    return parser


def add_deployment_name_param(parser):
    """Append the deployment name parameter to the parser."""
    parser.add_argument(
        '--deployment-name',
        nargs='?',
        help="""
        The name of the deployment, used as a prefix on the stack names.
        """,
        required=True
    )
    return parser


def add_os_cacert_url_param(parser):
    """Append the openstack cacert file parameter to the parser."""
    parser.add_argument(
        '--os-cacert-url',
        help="""
        This is the certificate to use for openstack cli commands.
        """,
        default=''
    )
    return parser


def add_artifact_json_file_param(parser):
    """Append the artifact json list parameter to the parser."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--artifact-json-file',
        dest='artifact_json_file',
        help="""
        The Full path to the json file with all the artifacts for the deployment defined.
        """,
        default=None
    )
    group.add_argument(
        '--artifact-json-url',
        dest='artifact_json_url',
        help="""
        The url to the json file with all the artifacts for the deployment defined.
        """,
        default=None
    )
    return parser


def add_cloud_templates_dir_param(parser):
    """
    Append cloud templates extracted directory parameter to the parser.

    This function appends the cloud templates extracted directory
    parameter to the parser
    """
    parser.add_argument(
        '--cloud-templates-extracted-dir',
        nargs='?',
        help="""
        The full path to where the cloud templates have already been extracted.
        """,
        required=True
    )
    return parser


def add_rpm_versions_param(parser):
    """
    Append rpm versions parameter to the parser.

    This function appends the rpm version related parameters
    which are required if overriding rpm versions in a ENM ISO
    """
    parser.add_argument(
        '--rpm-versions',
        help="""
        This is used to override the rpm versions within a ENM ISO.
        If this parameter is not provided, the version is taken from the ENM ISO.
        """,
        required=False
    )
    return parser


def add_media_versions_param(parser):
    """
    Append media versions parameter to the parser.

    This function appends the media version related parameters
    which are required if overriding media versions in a product set version
    """
    parser.add_argument(
        '--media-versions',
        help="""
        This is used to override the media versions within a product set version.
        """,
        required=False
    )
    return parser


def add_sed_file_params(parser):
    """
    Append SED file parameters to the parser.

    This function appends the SED file related parameters
    which are used to specify the SED file location
    """
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--sed-file-path',
        nargs='?',
        help="""
        The path to a SED file to be used in stack creations.
        """
    )
    group.add_argument(
        '--sed-file-url',
        nargs='?',
        help="""
        The url path to a SED file to be used in stack creations.
        """
    )
    return parser


def add_product_set_params(parser):
    """
    Append product set parameter to the parser.

    This function appends the product set parameter
    which is required to retrieve the media artifacts
    """
    parser.add_argument(
        '--product-set',
        dest='product_set_string',
        nargs='?',
        help="""
        The information for the ISO and Images to be uploaded to
        Glance will be taken from the referenced product Set.
        To get the latest specify productDrop::Latest (e.g. 15.8::Latest).
        To get passed images specify productDrop::passed (e.g. 15.8::Passed).
        To specify a specific product drop version specify
        productDrop::version (e.g. 15.8::8.0.2).
        """,
        required=True
    )
    return parser


def add_lcm_sed_file_params(parser):
    """
    Append VNF LCM SED file parameters to the parser.

    This function appends the SED file related parameters
    which are required to specify where the SED file for a deployment
    """
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--vnf-lcm-sed-file-path',
        nargs='?',
        help="""
        The path to a VNF LCM SED file to be used in VNF LCM stack creation.
        """
    )
    group.add_argument(
        '--vnf-lcm-sed-file-url',
        nargs='?',
        help="""
        The url path to a VNF LCM SED file to be used in VNF LCM stack creation.
        """
    )
    return parser


def add_create_lcm_backup_volume(parser):
    """Append wait on stack delete parameter to the parser."""
    parser.add_argument(
        '--create-lcm-backup-volume',
        help="""
        This parameter should only be defined if a VNF-LCM backup volume before VNF-LCM upgrade.
        NOTE: The VNF-LCM backup volume will be created by default during rollback if this parameter
        is not defined.
        """,
        required=False,
        action='store_true'
    )
    return parser


def add_delete_image_param(parser):
    """Append the delete image name parameter to the parser."""
    parser.add_argument(
        '--delete-images',
        nargs='?',
        help="""
        The image name or CXP number of the images to be deleted.
        """,
        default=''
    )
    return parser


def add_retain_images_param(parser):
    """Append the number of images to be retained parameter to the parser."""
    parser.add_argument(
        '--retain-latest',
        nargs='?',
        help="""
        Integer value specifies the number of latest version images to be retain in glance.
        """,
        default=3
    )
    return parser


def add_wait(parser):
    """Append wait on stack delete parameter to the parser."""
    parser.add_argument(
        '--wait',
        help="""
        This parameter should only be defined if the wait on delete functionality is required between deleting stacks.
        """,
        required=False,
        action='store_true'
    )
    return parser


def add_exclude_server(parser):
    """Append exclude server delete parameter to the parser."""
    parser.add_argument(
        '--exclude-server',
        help="""
        This parameter should only be defined to exclude a Server(s) from project teardown/deletion and or from
        blocking pre-existing resource checks on vENM initial install/rollout.

        Multiple Server names should be comma separated e.g. exclude_server_1,exclude_server_2,exclude_server_3
        """,
        required=False,
        default=list(),
        type=lambda exclude_server_arg: exclude_server_arg.split(',')
    )
    return parser


def add_exclude_volume(parser):
    """Append exclude volume delete parameter to the parser."""
    parser.add_argument(
        '--exclude-volume',
        help="""
        This parameter should only be defined to exclude a volume(s) from project teardown/deletion and or from
        blocking pre-existing resource checks on vENM initial install/rollout.

        Multiple Volume names should be comma separated e.g. exclude_volume_1,exclude_volume_2,exclude_volume_3
        """,
        required=False,
        default=list(),
        type=lambda exclude_volume_arg: exclude_volume_arg.split(',')
    )
    return parser


def add_exclude_network(parser):
    """Append exclude network delete parameter to the parser."""
    parser.add_argument(
        '--exclude-network',
        help="""
        This parameter should only be defined to exclude a Network(s) from project teardown/deletion and or from
        blocking pre-existing resource checks on vENM initial install/rollout.

        Multiple Network names should be comma separated e.g. exclude_network_1,exclude_network_2,exclude_network_3
        """,
        required=False,
        default=list(),
        type=lambda exclude_network_arg: exclude_network_arg.split(',')
    )
    return parser


def add_snapshot_tag_param(parser):
    """Add snapshot tag to the deployer."""
    parser.add_argument(
        '--snapshot-tag',
        help="""
        This is a snapshot tracking tag.
        """,
        required=True
    )
    return parser


def add_backup_tag_param(parser):
    """Add backup tag to the deployer."""
    parser.add_argument(
        '--backup-tag',
        help="""
        This is a backup tracking tag.
        """,
        required=True
    )
    return parser


def add_external_script_param(parser):
    """Add and execute an external script to the LCM node after deployment."""
    parser.add_argument(
        '--upload-script-path',
        help="""
        This is used to execute a script after the deployment of the LCM Node (default is None)
        """,
        default=None,
        required=False
    )
    return parser


def add_workflow_max_check_attempts(parser):
    """Used to set the specific amount of attempts for a workflow to complete, 1hr=360 attempts."""
    parser.add_argument(
        '--workflow-max-check-attempts',
        type=int,
        dest='workflow_max_check_attempts',
        help="""
        This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
        The default is '1260' if none is specified.
        """,
        default='1260',
        required=False
    )
    return parser


def add_image_name_postfix_param(parser):
    """Append image name postfix parameter to the parser."""
    parser.add_argument(
        '--image-name-postfix',
        help="""
        This is used to define a string that will be appended to the image names during upload on RHOS clouds, eg 'CI' or 'RV. The default for RHOS clouds is '_CI' if none is specified.
        If no image name postfix identifier is required specify the following: 'no-postfix'.
        This parameter will be ignored for image uploads on VIO clouds and no default image name postfix will used.
        """,
        default='_CI',
        required=False
    )
    return parser


def add_run_lcm_cmd_param(parser):
    """Append run lcm cmd parameter to the parser."""
    parser.add_argument(
        '--run-lcm-cmd',
        help="""
        This is used to define a command to be run on the VNF-LCM services VM.
        """,
        required=False
    )
    return parser


def add_workflows_cleanup_param(parser):
    """Append workflows cleanup parameter to the parser."""
    parser.add_argument(
        '--workflows-cleanup',
        nargs='?',
        help="""
        This is used to uninstall obsolete workflows from the VNF-LCM services VM.

        By default the following number of workflows are retained:
        enmdeploymentworkflows retain latest 5 (n-4)
        enmcloudmgmtworkflows retain latest 2 (n-1)
        enmcloudperformanceworkflows retain latest 2 (n-1)

        To override the default workflow rentention values, a comma separated list can be specified as shown below:

        --workflow-cleanup enmdeploymentworkflows=3,enmcloudmgmtworkflows=2,enmcloudperformanceworkflows=2
        """,
        const='enmdeploymentworkflows=5,enmcloudmgmtworkflows=2,enmcloudperformanceworkflows=2',
        required=False
    )
    return parser


def add_product_option_param(parser):
    """Append product option to the parser."""
    parser.add_argument(
        '--product-option',
        help="""
        This is used to define a separate upgrade or rollback option for either VNF-LCM or vENM products.
        """,
        choices=['ENM', 'VNF-LCM'],
        required=False
    )
    return parser


def add_vio_profile_list_param(parser):
    """Append VIO profile list parameter to the parser."""
    parser.add_argument(
        '--vio-profile-list',
        dest='vio_profile_list',
        help="""
        This parameter for setting the profile list for execute different stages for the VIO platform install and configuration.
        Input can be one or more profiles in a comma separated list.
        Refer to offical Small Integrated ENM Installation Instructions for profiles.
        """,
        required=True
    )
    return parser


def add_delete_dvms_param(parser):
    """Append delete dvms parameter to the parser."""
    parser.add_argument(
        '--delete-dvms',
        help="""
        This parameter should only be defined if it is required to delete a RHOS hosted DVMS post SIENM/VIO platform install or upgrade.
        """,
        required=False,
        action='store_true'
    )
    return parser


def add_skip_vio_cleanup_param(parser):
    """Append skip vio cleanup parameter to the parser."""
    parser.add_argument(
        '--skip-vio-cleanup',
        help="""
        This parameter should only be defined if it is required to skip artifact cleanup on SIENM/VIO platform post install or upgrade.
        """,
        required=False,
        action='store_true'
    )
    return parser


def add_skip_media_download_param(parser):
    """Append skip EDP media download parameter to the parser."""
    parser.add_argument(
        '--skip-media-download',
        help="""
        This parameter should only be defined if it is required to skip media download.
        """,
        required=False,
        action='store_true'
    )
    return parser
