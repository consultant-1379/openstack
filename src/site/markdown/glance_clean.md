# Description of 'glance clean' command

## Intended Purpose
This command can be used to delete all or selected images from glance.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides or see Usage Paramater section below.

```bash
deployer glance clean --help
```


## What it Does
Below are the main steps that this command will perform.


### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the command line arguments given.


### Glance image deletion
The Deployer will delete all or specific images in glance. Specifying the image name or CXP number after the  --delete-images parameter. Multiple different images types can be deleted by specifying the image or CXP numbers in a comma separated list. Wildcard * characters can be used in a delete param to delete specific images e.g. CXP9026826*\_CI.

NOTE: VMDK images on VIO clouds will not have a postfix identifier or file extension in the image name.

The --retain-latest parameter allows a specific number of images to be retained in glance, this parameter is specified as a integer value, By default unless otherwise specified the three latest images will be retained. Setting the --retain-latest parameter to the value 0 will delete all versions of the image/images specified.

## Example Usage
Below is an example command, used to delete images in a pod called 'http://podd2.athtem.eei.ericsson.se:5000/v2.0'.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> glance clean  --os-username USERNAME --os-password 'PASSWORD' --os-auth-url 'http://podd2.athtem.eei.ericsson.se:5000/v2.0' --os-project-name 'Stratus' --delete-images CXP9027091,CXP9026759,CXP9031559,CXP9032719,CXP9026826 --retain-latest 0 --debug
```
