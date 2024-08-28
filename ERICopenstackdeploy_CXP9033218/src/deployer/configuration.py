"""
Handle loading of data from configuration files.

This module handles the importing of the default
and any custom configuration files
"""

from configparser import ConfigParser
from os.path import expanduser, join, dirname
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from io import StringIO

# pylint: disable=R0901


class DeployerConfig(ConfigParser):
    """
    A class to read the deployer.ini files to retrieve project settings.

    This class extends the SafeConfigParser
    and preruns the read function so that it
    first reads the packages deployer.ini, followed
    by a users deployer.ini in their home directory
    """

    def __init__(self):
        """Initialize a DeployerConfig object."""
        ConfigParser.__init__(self)
        self.read([
            join(dirname(__file__), 'etc/deployer.ini'),
            expanduser('~/.deployer.ini')
        ], encoding=None)


class VersionConfig(ConfigParser):
    """
    A class to read the version.ini files to retrieve the projects version.

    This class extends the SafeConfigParser
    and preruns the read function so that it
    first reads the packages version.ini, followed
    by a users version.ini in their home directory
    """

    def __init__(self):
        """Initialize a VersionConfig object."""
        ConfigParser.__init__(self)
        self.add_section('VERSION')
        self.set('VERSION', 'version', '0.0.0')
        self.read([
            join(dirname(__file__), 'etc/version.ini'),
            expanduser('~/.version.ini')
        ], encoding=None)


class FunctionalIdConfig(ConfigParser):
    """
    A class to read the functional ID and password to access REST API that require authentication.

    This class extends the SafeConfigParser
    and the read function reads the deployer
    functional id authentication config file.

    """

    def __init__(self):
        """Initialize a DeployerConfig object."""
        ConfigParser.__init__(self)
        try:
            auth_config_file = get_auth_config_file()
            self.read_file(auth_config_file)
        except (TypeError, AttributeError):
            pass


def get_auth_config_file():
    """Retrieve authentication configuration file."""
    nexus_url = 'https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories'
    try:
        auth_config_file = urlopen(
            f'{nexus_url}/releases/com/ericsson/de/ERICopenstackdeploy_CXP9033218/deployer_cfg.ini')
        config_file_content = auth_config_file.read().decode('utf-8')
        config_file = StringIO(config_file_content)
        config_file.seek(0)
        return config_file
    except (HTTPError, URLError):
        pass
