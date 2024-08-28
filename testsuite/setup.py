"""This is the setuptools file for the deployer code style tests."""

from setuptools import setup

setup(
    install_requires=[
        'cliff==3.10.0',
        'netaddr==0.10.1',
        'openstacksdk==0.99.0',
        'python-openstackclient==5.8.0',
        'python-heatclient==1.17.0',
        'python-neutronclient==6.11.0',
        'requests[security]==2.25.1',
        'paramiko==2.7.2',
        'pylint==2.5.3',
        'pep8==1.7.0',
        'pycodestyle==2.5.0',
        'pep257==0.7.0',
        'retrying==1.3.3',
        'packaging==20.4',
        'patool==1.12',
        'pyunpack==0.1.2',
        'semantic_version==2.6.0',
        'timeout_decorator==0.4.1'
    ]
)
