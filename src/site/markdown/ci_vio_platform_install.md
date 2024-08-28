# Description of 'ci vio platform install' command

## Intended Purpose
This command can be used to install the Small Integrated ENM Platform using the software from a given ENM product set.
The Deployment Inventory Tool (DIT) is used to retrieve information about a given Deployment,
such as its SED and the project and pod details.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
Deployer ci vio platform install --help
```


## What it Does
Below are the main steps that this command will perform.

### Retrieval Of Deployment Information from DIT
The following is retrieved for the given Deployment name:

* DVMS document
* ENM SED
* VNF-LCM SED

### Update /etc/resolv.config on DVMS
Update the /etc/resolv.config file with the ntp ip addresses from the associated Deployment Virtual Management Server (DVMS) document.

### Create directories on DVMS
The following directories will be created on DVMS and IVMS, if they do not already exist:

* /vol1/ENM/artifacts
* /vol1/senm/etc

### Media Handling

* For media handling information, refer this link [ENM Media Handling](enm_media_information.md)

### ENM SED
The Deployer generates a sed.json file to use during the install process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a SED file.

* Downloads the SED that is associated with the given Deployment in DIT.
  The given Deployment must be defined in DIT.
  For more information on DIT and how to setup your Deployments, See DIT linked below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Fills in the media related keys, using the image names that were handled earlier in the installation
* Reports any values in the final SED that have blank values (but doesn't fail the script).
* Saves the final ENM SED object to disk in the temp directory [temp_directory]/sed.json
* Transfers ENM SED located in [temp_directory]\/sed.json to DVMS directory /vol1/senm/etc/sed.json


### VNF-LCM SED
The Deployer generates a lcm_sed.json file to use during the install process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF-LCM SED file.

* Downloads the VNF-LCM SED that is associated with the given deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on the DIT tool and how to setup deployments, See the DIT tool linked below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Populates the media related key values, using the image names that were handled earlier in the process.
* Reports any values in the final VNF-LCM SED that have blank values (but doesn't fail the script).
* Saves the final VNF-LCM SED object to disk in the temp directory [temp_directory]/lcm_sed.json
* Transfers VNF-LCM SED located in [temp_directory]/lcm_sed.json to DVMS directory /vol1/senm/etc/lcm_sed.json


### Install EDP autodeploy packages
The EDP packages contained within the ERICautodeploy_CXP9038326 tar.gz archive will installed using yum.

### Configure DVMS
The following command is ran on the DVMS to configure the DVMS:

```bash
/opt/ericsson/senm/bin/edp_autodeploy.sh -y -e /vol1/senm/etc/sed.json -m /vol1/senm/etc/lcm_sed.json -p sienm_init_dvms_upgrade
```


### Install of VIO Platform
Based on the profile list the following command is ran:

```bash
/opt/ericsson/senm/bin/edp_autodeploy.sh -y -e /vol1/senm/etc/sed.json -m /vol1/senm/etc/lcm_sed.json -p <vio-profile-list>
```

### SIENM media preparation
The ENM media software is converted to VMDK format and uploaded. This done by executing EDP core profile on the DVMS: core_openstack_software_preparation

```bash
/opt/ericsson/senm/bin/edp_autodeploy.sh -y -e /vol1/senm/etc/sed.json -m /vol1/senm/etc/lcm_sed.json -k /vol1/senm/etc/Key_pair_<os_project_name>.pem -O /vol1/senm/etc/<os_project_name>_project.rc -p core_openstack_software_preparation
```

### Cleanup
If the Deployer exits without exception, it will clean up the contents of artifacts directory on the DVMS.


## What it Doesn't Do
Any steps mentioned in the official installation documentation, that are not covered in the section above could be assumed to be not handled by the Deployer.


## Example Usage
Below is an example command, used to deploy product set 19.08.100 on a Deployment called vio-xxxx and passing in a profile list.
Profiles information can found in Small Integrated ENM Installation Instructions Documentation.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio platform install --deployment-name vio-xxxx --product-set 19.08::19.08.100 --vio-profile-list sienm_phase1,sienm_phase2 --debug
```
