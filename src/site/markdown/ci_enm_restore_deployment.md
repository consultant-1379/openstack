# Description of 'ci enm restore deployment' command

## Intended Purpose
This command can be used to restore an ENM environment using the software from the given product set. Its aim is to make the process as automated as possible.
Deployment related information for the given deployment name, such as SED, project and pod details is retrieved from the Deployment Inventory Tool.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci enm restore deployment --help
```


## What it Does
Below are the main steps that this command will perform.

### Retrieval Of Deployment Information from DIT
The openstack credentials and SED are obtained from the Deployment Inventory Tool, for the given Deployment name.

### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information from DIT

### Media Handling

* For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

### ENM SED
The Deployer generates a sed.json file to use during the restore deployment process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a SED file.

* Downloads the SED that is associated with the given Deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on DIT and how to setup your Deployments, See DIT linked below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Fills in the media related keys, using the image names that were handled earlier in the installation
* Reports any values in the final SED that have blank values (but doesn't fail the script).


### VNF LCM SED
The Deployer generates a vnflcm_sed.json file to use during the restore deployment process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF LCM SED file.

* Downloads the VNF LCM SED that is associated with the given deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on the DIT tool and how to setup deployments, See DIT linked below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Populates the media related key values, using the image names that were handled earlier in the process.
* Reports any values in the final VNF LCM SED that have blank values (but doesn't fail the script).
* The VNF-LCM SED is uploaded to the following directory /vnflcm-ext/vnf-lcm/\<VNF_LCM_MEDIA_VERSION> on the VNF-LCM services VM.


### ENM Restore Deployment Workflow
The Deployer will run the necessary steps to execute the required workflow to complete the ENM restore deployment. Below are the steps the Deployer takes during this phase.

* sftp the sed.json to /vnflcm-ext/enm/ on the VNF LCM VM
* Executes the 'Rollback Deployment' workflow
* Completes the user task with the tag name provided
* Waits for the workflow to reach the completed state
* Logs the results of each node in the workflow and fails the script if any nodes of type 'errorEndEvent' were found


### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.

## What it Doesn't Do
Any steps mentioned in the official restore deployment documentation, that are not covered in the section above could be assumed to be not handled by the Deployer, for example uploading of any other media not mentioned on this page.

## Example Usage
Below is an example command, used to restore deployment to product set 17.14.100 on a Deployment called ieatenmpdxxx.

```bash
deployer ci enm restore deployment --deployment-name ieatenmpdxxx --product-set 17.14::17.14.100 --backup-tag backup_17.14.100 --debug
```

##### Optional: Alter the Number of Max Attempts for Workflows
Add the below parameter to the deployer command:

```bash
  --workflow-max-check-attempts <number>
```
This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
The default is '1260' if none is specified.
