# Openstack Auto Deployer Tool #

The Openstack Auto Deployer is a tool created to automate the manual procedure for installation of ENM on OpenStack.

It is intended for continuous integration use where a fully automated deployment is required.

More information on OADT available: https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/sites/tor/openstack/latest/index.html

# Prerequisites #

* Python 3.6
* Pip
* Docker 18.6

## Setting up WSL2 on Windows ##

* If working from Windows Environment, WSL2 should be set up
* Steps can be found through this link: https://confluence-oss.seli.wh.rnd.internal.ericsson.com/display/TST/Docker+on+Windows+10

# Docker Build and Run #

* cd openstack/
* docker build . -t deployerenv
* docker run -it -v $PWD:/code/ deployerenv /bin/bash

# Install Deployer #

* pip install --upgrade -e /code/ERICopenstackdeploy_CXP9033218/src/

# Check Install has been successful and example command #

* deployer --help
* deployer ci enm rollout --deployment-name ieatenmpd201  --product-set 18.03::18.03.47 --debug


# How to manually build snapshot image #

To build an Openstack Auto Deployer snapshot Docker image, execute the "build_snapshot.py" script at the root level of the Openstack Auto Deployer source code with the Gerrit commit reference using the "--commit" parameter

* python build_snapshot.py --commit <commit_reference>
* e.g. python build_snapshot.py --commit refs/changes/44/012345/1

To build a Openstack Auto Deployer snapshot Docker image with a custom image name, the "--image-name" parameter must be used.

* python build_snapshot.py --commit <commit_reference> --image-name <image_name>
* e.g. python build_snapshot.py --commit refs/changes/44/012345/1  --image-name custom_deployer_image_name

The Gerrit commit reference is obtained from the Gerrit UI download options.

# Change Log #

Change Log link:
- Newer (six months worth using date range): https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/sites/tor/openstack/latest/changelog.html
- Version 21.0.6 and older: https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/sites/tor/openstack/latest/change_log.html

# Authors #

**DE Stratus** - PDLDESTRAT@pdl.internal.ericsson.com


# License #

ERICSSON 2021
