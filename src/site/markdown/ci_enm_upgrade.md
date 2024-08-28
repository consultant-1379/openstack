# Description of 'ci enm upgrade' command

## Intended Purpose
This command can be used to upgrade an ENM environment using the software from the given product set. Its aim is to make the process as automated as possible.
Deployment related information for the given deployment name, such as SED, project and pod details is retrieved from the Deployment Inventory Tool.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci enm upgrade --help
```


## What it Does
Below are the main steps that this command will perform.

### Retrieval Of Deployment Information from DIT
The openstack credentials and SED are obtained from the Deployment Inventory Tool, for the given Deployment name.

### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information from DIT.

### Upgrade Schema Version of SED based on Cloud Templates
Checks the version of the cloud templates in the product set. If this version is different from the version used in the SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
If this fails the script will throw an error.

At this point manual intervention is required as an update is not possible.
This should be done through Documents page on the DIT UI.

### Upgrade Schema Version of VNF-LCM SED based on VNF-LCM Cloud Templates
Checks the version of the VNF-LCM cloud templates that is passed in either from the product set or from the --rpm-versions command. If this version is different from the version used in the VNF-LCM SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
It this fails the script will throw an error.

At this point manual intervention is required as an update is not possible.
This should be done through Documents page on the DIT UI.

### Media Handling

* For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

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


### VNF-LCM SED
The Deployer generates a vnflcm_sed.json file to use during the upgrade process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF-LCM SED file.

* Downloads the VNF-LCM SED that is associated with the given deployment in DIT
  The given deployment must be defined in DIT.
  For more information on DIT and how to setup deployments, See DIT linked below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Populates the media related key values, using the image names that were handled earlier in the process.
* Reports any values in the final VNF-LCM SED that have blank values (but doesn't fail the script).
* Saves the final VNF-LCM SED object to disk in the temp directory [temp_directory]/vnflcm_sed.json


### VNF-LCM Upgrade
The Deployer performs a openstack stack update on the VNF-LCM security group, server group before the delete and recreate of the VNF-LCM stack, when there is a difference between the deployed VNF-LCM media and the VNF-LCM media defined in the product set used during the vENM upgrade process.

VNF-LCM upgrade on SI-ENM (VIO) VNF-LCM requires a server group workaround of marking the server group unhealthy to be performed prior to the server group stack update.

A volume snapshot is created for each vnflcm_volume e.g. &lt;deployment\_id&gt;\_vnflcm\_volume\_&lt;volume\_count&gt;\_snapshot prior to the VNF-LCM Stack delete.
The volume snapshot is required to create a vnflcm_volume backup in the event of VNF-LCM rollback.

If the vnflcm_volume backup(s) are required to be created prior to the VNF-LCM upgrade, the --create-lcm-backup-volume parameter must be specified. If the --create-lcm-backup-volume parameter is not specified the vnflcm_volume backup(s) will be created prior to a VNF-LCM rollback.



### VNF-LCM non-HA to HA upgrade
The Deployer performs a delete and recreate of the VNF-LCM Services stack if there is a difference between the deployed VNF-LCM configuration and the upgrade VNF-LCM SED configuration for VNF-LCM HA.

In addition and prior to the deleting and recreate of the VNF-LCM stack, the deployer will create a virtual IP ports stack or stacks based on the 'ip_version' parameter defined in the VNF-LCM SED and a additional vnflcm_volume named &lt;deployment\_id&gt;\_vnflcm\_volume_1.

The following virtual IP port stack is created based on the value of VNF-LCM SED ip_version parameter:
* vnflcm_dual_vip (created if VNF-LCM SED parameter ip_version is set to value 'dual')
* vnflcm_ipv4_vip (created if VNF-LCM SED parameter ip_version is set to value '4')
* vnflcm_ipv6_vip (created if VNF-LCM SED parameter ip_version is set to the value '6')


### ENM Upgrade Workflow
The Deployer will run the necessary steps to execute the required workflows to complete the ENM upgrade. Below are the steps the Deployer takes during this phase.

* sftp the sed.json to /vnflcm-ext/enm/ on the VNF-LCM VM
* Installs enm deployment workflows version from upgrade product set
* Executes the 'Prepare for upgrade' workflow
* Executes the 'Upgrade ENM' workflow
* Waits for the workflow to reach the completed state
* Logs the results of each node in the workflow and fails the script if any nodes of type 'errorEndEvent' were found


### Cloud Management workflows
The Deployer installs the latest Cloud Management workflows version from upgrade product set.


### Cloud Performance workflows
The Deployer installs the latest Cloud Performance workflows version from upgrade product set.


### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.
Cleans up the contents of artifacts directory on the VMS if the Deployment is VIO.


## What it Doesn't Do
Any steps mentioned in the official upgrade documentation, that are not covered in the section above could be assumed to be not handled by the Deployer, for example uploading of any other media not mentioned on this page.


## Example Usage
Below is an example command, used to upgrade product set 17.14.100 on a Deployment called ieatenmpdxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm upgrade --deployment-name ieatenmpdxxx --product-set 17.14::17.14.100 --debug
```

Below is an example command, used to upgrade product set 17.14.100 deployment called ieatenmpdxxx including the --vnf-lcm-backup parameter to create a VNF-LCM backup volume during a VNF-LCM upgrade.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm upgrade --deployment-name ieatenmpdxxx --product-set 17.14::17.14.100 --vnf-lcm-backup --debug
```

##### Optional: Increasing Number of Attempts
Below add this to the deployer command:

```bash
  --workflow-max-check-attempts <number>
```
This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
The default is '1260' if none is specified.

## Upgrade options
Separated VNF-LCM upgrade and vENM upgrade can be performed by using the --product-option CLI parameter and specifying either the ENM or VNF-LCM product option.

Separated ENM upgrade option example:

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm upgrade --deployment-name ieatenmpdxxx --product-set 19.16::19.16.10 --product-option ENM --debug
```

Separated VNF-LCM upgrade option example:

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm upgrade --deployment-name ieatenmpdxxx --product-set 19.16::19.16.10 --product-option VNF-LCM --debug
```
