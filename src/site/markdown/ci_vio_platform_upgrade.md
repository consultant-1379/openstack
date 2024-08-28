# Description of 'ci vio platform upgrade' command

## Intended Purpose
This command can be used to perform a upgrade of a Small Integrated ENM Platform.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci vio platform upgrade --help
```


## What it Does
Below are the main steps that this command will perform.

### Retrieval Of Deployment Information from DIT
The following are retrieved for a given Deployment:

* DVMS document
* ENM SED
* VNF-LCM SED

### Update /etc/resolv.config on DVMS
The file /etc/resolv.config file is updated with the ntp ip addresses from the DVMS document associated with the Deployment.

### Create directories on DVMS
If the following directories do not exist, they will be created:

* /vol1/ENM/artifacts
* /vol1/senm/etc

### Media Handling
* For media handling information, refere this link [ENM Media Handling](enm_media_information.md)

### ENM SED
The Deployer generates a sed.json file to use during the upgrade process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a SED file.

* Downloads the SED that is associated with the given Deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on DIT and how to setup your Deployments, See DIT linked below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Fills in the media related keys, using the image names that were handled earlier in the installation
* Reports any values in the final SED that have blank values (but doesn't fail the script).
* Saves the final ENM SED object to disk in the temp directory [temp_directory]/sed.json
* Transfers ENM SED located in [temp_directory]/sed.json to DVMS directory /vol1/senm/etc/sed.json


### VNF-LCM SED
The Deployer generates a lcm_sed.json file to use during the upgrade process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF-LCM SED file.

* Downloads the VNF-LCM SED that is associated with the given Deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on the DIT tool and how to setup deployments, See DIT linked below.
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
/opt/ericsson/senm/bin/edp_autodeploy.sh -y -e /vol1/senm/etc/sed.json -m /vol1/senm/etc/lcm_sed.json -p sienm_init_dvms
```


### Determine VIO Platform Components to Upgrade
Audit script is ran on DVMS:

```bash
/opt/ericsson/senm/bin/audit_senm.sh -y -e /vol1/senm/etc/sed.json -r
```

This will create the recipe file: /vol1/senm/etc/recipe.\<number>

### Perform Online VIO Platform Upgrade
Based on the content of the recipe file it is determined if an upgrade is required. If required following command is ran:

```bash
/opt/ericsson/senm/bin/edp_autodeploy.sh -y -e /vol1/senm/etc/sed.json -r <recipe file>
```

### Verify Platform Components Versions
Audit script is ran on DVMS:

```bash
/opt/ericsson/senm/bin/audit_senm.sh -y -e /vol1/senm/etc/sed.json -r
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
Below is an example command, used to upgrade product set 19.08.100 on a Deployment called vio-xxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio platform upgrade --deployment-name vio-xxxx --product-set 19.08::19.08.100 --debug
```
