"""Command-line interface to install Ericsson Products on Openstack."""

import sys
import logging

from cliff.app import App
from cliff.commandmanager import CommandManager
from . import configuration
from . import image_utils
from . import oqs

CONFIG = configuration.VersionConfig()
LOG = logging.getLogger(__name__)


class Deployer(App):
    """ENM Openstack Deployer."""

    CONSOLE_MESSAGE_FORMAT = \
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    LOG_FILE_MESSAGE_FORMAT = \
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    logging.getLogger('deployer').addHandler(logging.NullHandler())

    def __init__(self):
        """Initialize the Deployer application."""
        super(Deployer, self).__init__(
            description=__doc__.strip(),
            version=CONFIG.get('VERSION', 'version'),
            command_manager=CommandManager('deployer.commands'),
            deferred_help=True,
        )

    def build_option_parser(self, description, version, argparse_kwargs=None):
        """Return the main parser object for the deployer."""
        parser = super(Deployer, self).build_option_parser(
            description,
            version)

        return parser


def main(argv=sys.argv[1:]):
    """
    The main function for the startup of the deployer.

    This creates the application and runs it
    It returns the value of the run method
    """
    try:
        myapp = Deployer()
        return myapp.run(argv)
    except KeyboardInterrupt:
        image_utils.Image.temporary_image_cleanup()
    finally:
        oqs.Deployment.update_deployment_queue_status()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
