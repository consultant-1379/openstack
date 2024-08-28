"""This is the setuptools file for the deployer package."""

from setuptools import setup, find_packages
from deployer import configuration

CONFIG = configuration.VersionConfig()

setup(
    name='ERICopenstackdeploy_CXP9033218',
    include_package_data=True,
    version=CONFIG.get('VERSION', 'version'),
    package_data={'deployer': ['etc/*', 'heat_templates/*']},
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'deployer = deployer.shell:main'
        ],
        'deployer.commands': [
            'ci enm backup deployment = deployer.ci_enm_backup_deployment:CIENMBackupDeployment',
            'ci enm restore deployment = deployer.ci_enm_restore_deployment:CIENMRestoreDeployment',
            'ci enm rollout = deployer.ci_enm_rollout:CIENMRollout',
            'ci enm snapshot deployment = deployer.ci_enm_snapshot:CIENMSnapshotDeployment',
            'ci enm upgrade = deployer.ci_enm_upgrade:CIENMUpgrade',
            'ci enm rollback deployment = ' +
            'deployer.ci_enm_rollback_deployment:CIENMRollbackDeployment',
            'ci enm stacks delete = deployer.enm_stacks_delete:CIENMStacksDelete',
            'ci vio dvms deploy = deployer.ci_vio_dvms_deploy:CIVIODvmsDeploy',
            'ci vio platform install = deployer.ci_vio_platform_install:CIVIOPlatformInstall',
            'ci vio platform upgrade = deployer.ci_vio_platform_upgrade:CIVIOPlatformUpgrade',
            'ci vio platform post install = ' +
            'deployer.ci_vio_platform_post_install:CIVIOPlatformPostInstall',
            'ci vio platform post upgrade = ' +
            'deployer.ci_vio_platform_post_upgrade:CIVIOPlatformPostUpgrade',
            'glance clean = deployer.glance_clean:GlanceClean',
            'ci enm schema upgrade = deployer.ci_enm_schema_upgrade:CIENMSchemaUpgrade',
            'ci task = deployer.ci_tasks:CITask',
            'nwci task = deployer.ci_tasks:CITask',
            'nwci enm backup deployment = ' +
            'deployer.ci_enm_backup_deployment:CIENMBackupDeployment',
            'nwci enm restore deployment = ' +
            'deployer.ci_enm_restore_deployment:CIENMRestoreDeployment',
            'nwci enm rollout = deployer.ci_enm_rollout:CIENMRollout',
            'nwci enm snapshot deployment = deployer.ci_enm_snapshot:CIENMSnapshotDeployment',
            'nwci enm upgrade = deployer.ci_enm_upgrade:CIENMUpgrade',
            'nwci enm rollback deployment = ' +
            'deployer.ci_enm_rollback_deployment:CIENMRollbackDeployment',
            'nwci enm stacks delete = deployer.enm_stacks_delete:CIENMStacksDelete',
            'ci edp venm = deployer.ci_edp_venm:CIEDPVENM',
            'nwci edp venm = deployer.ci_edp_venm:CIEDPVENM'
        ]
    },
    install_requires=[
        'cliff==3.10.0',
        'netaddr==0.10.1',
        'openstacksdk==0.99.0',
        'python-openstackclient==5.8.0',
        'python-heatclient==1.17.0',
        'python-neutronclient==6.11.0',
        'python-cinderclient==7.4.0',
        'requests[security]==2.25.1',
        'paramiko==2.7.2',
        'retrying==1.3.3',
        'packaging==20.4',
        'patool==1.12',
        'pyunpack==0.1.2',
        'semantic_version==2.6.0',
        'timeout_decorator==0.4.1'
    ]
)
