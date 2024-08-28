# Description of 'nwci enm snapshot deployment' command

## Intended Purpose
This command can be used to snapshot an ENM environment using the software from the given json file. Its aim is to make the process automated as possible.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides or see Usage Paramater section below.

```bash
deployer nwci enm snapshot deployment --help
```


## What it Does
Below are the main steps that this command will perform.


### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the command line arguments given.

### Media Handling
* For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

### VNF LCM SED
The Deployer generates a vnflcm_sed.json file to use during the snapshot deployment process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF LCM SED file.

* Downloads the given SED file
* Populates the media related key values, using the image names that were handled earlier in the process.
* Reports any values in the final VNF LCM SED that have blank values (but doesn't fail the script).
* The VNF-LCM SED is uploaded to the following directory /vnflcm-ext/vnf-lcm/\<VNF_LCM_MEDIA_VERSION> on the VNF-LCM services VM.


### ENM Snapshot Deployment Workflow
The Deployer will run the necessary steps to execute the required workflow to complete the ENM snapshot deployment. Below are the steps the Deployer takes during this phase.

* Executes the 'Snapshot Deployment' workflow
* Waits for the workflow to reach the completed state
* Logs the results of each node in the workflow and fails the script if any nodes of type 'errorEndEvent' were found


### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.

## What it Doesn't Do
Any steps mentioned in the official snapshot deployment documentation, that are not covered in the section above could be assumed to be not handled by the Deployer, for example uploading of any other media not mentioned on this page.


## Example Usage
Below is an example command, used to create a snapshot deployment of product set 17.14.100 on a Deployment called ieatenmpdxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> nwci enm snapshot deployment --os-username bucinwci --os-password buc1NWc1-2017 --os-auth-url https://ctrl3.serodc419.cloud.k2.ericsson.se:5000/v2.0 --os-project-name NWCI --os-cacert /var/tmp/mount/os_cert.crt --deployment-name nwci --sed-file-url http://141.137.173.80/ECEE_30k_Environemnt_17.5-17.5.106.json --vnf-lcm-sed-url http://141.137.173.80/Athlone_ECEE_VNF_LCM_17.5-17.5.106.json --snapshot-tag snapshot_17.14.100 --debug
```

##### Optional: Alter the Number of Max Attempts for Workflows
Add the below parameter to the deployer command:

```bash
  --workflow-max-check-attempts <number>
```
This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
The default is '1260' if none is specified.
