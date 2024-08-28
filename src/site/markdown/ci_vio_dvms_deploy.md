# Description of 'ci vio dvms deploy' command

## Intended Purpose
This command can be used to deploy a DVMS (Deployment Virtual Management Server) instance on a
RHOS (RedHat OpenStack) project required for the purposes of CI for Small Integrated ENM Platform
automation using the software from a given ENM product set.
The Deployment Inventory Tool (DIT) is used to retrieve information about a given Deployment,
such as its DVMS document, Project and Pod details.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
Deployer ci vio dvms deploy --help
```


## What it Does
Below are the main steps that this command will perform.

* The DVMS document is obtained from the Deployment Inventory Tool, associated with the given Deployment name.
* Sets the required OpenStack client environment variables, based on the project information in the DVMS document.
* Retrieves the required DVMS media artifact ERICvms_CXP9035350 from a given ENM product set version from the CI portal.
* The media artifact is extracted and media image is uploaded to Glance.
* The image name will be given a postfix of 'CI' if one is not provided by using the --image-name-postfix argument.
* Delete any pre-existing DVMS stack, called \<deployment_id>\_dvms
* Create the DVMS stack, called \<deployment_id>\_dvms using the media defined in ENM product set and the Flavor defined in the DVMS document.


## What it Doesn't Do
Any steps mentioned in the official installation documentation, that are not covered in the section above could be assumed to be not handled by the Deployer.


## Example Usage
Below is an example command, used to deploy DVMS instance on a RHOS project using product set 19.08.100 media assoicated with a Deployment called vio-xxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio dvms deploy --deployment-name vio-xxxx --product-set 19.08::19.08.100 --debug
```

