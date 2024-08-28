# Description of 'ci vio platform post upgrade' command

## Intended Purpose
This command can be used to perform the Small Integrated ENM platform post-upgrade procedure.
The Deployment Inventory Tool (DIT) is used to retrieve information about a given Deployment,
such as its SED and the project and pod details.

SI-ENM document Rev: 3/153 72-CNA 403 3456 Uen AD

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci vio platform post upgrade --help
```

## Prerequisites

* ENM is successfully upgraded.
* Deployment is configured in DIT.

## What it Does
Below are the main steps that this command will perform.

### Retrieval Of Deployment Information from DIT
The DVMS document and ENM SED associated with the given Deployment name.

### Post-installation Steps
The following commands are ran on VMS:

```bash
/opt/ericsson/senm/bin/edp_autodeploy.sh -y -e /vol1/senm/etc/sed.json -m /vol1/senm/etc/lcm_sed.json -p sienm_post_upgrade_i
```

### Cleanup
If the Deployer exits without exception, it will clean up the contents of artifact directory on VMS.

To not clean up artifact directory on the VMS append the --skip-vio-cleanup CLI parameter to the 'ci vio platform post upgrade' command.


## What it Doesn't Do
Any steps mentioned in the official installation documentation, that are not covered in the section above could be assumed to be not handled by the Deployer.


### Post upgrade DVMS deletion
To automatically delete the RHOS hosted DVMS post upgrade append the --delete-dvms CLI parameter to the 'ci vio platform post upgrade' command.


## Example Usage
Below is an example command, used to perform post upgrade on a Deployment called vio-xxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio platform post upgrade --deployment-name vio-xxxx --product-set 19.08::19.08.100 --debug
```

Below is an example command using the --skip-vio-cleanup CLI parameter.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio platform post upgrade --deployment-name vio-xxxx --product-set 19.08::19.08.100 --skip-vio-cleanup --debug
```
