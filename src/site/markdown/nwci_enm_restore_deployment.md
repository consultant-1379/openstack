# Description of 'nwci enm restore deployment' command

## Intended Purpose
This command can be used to restore an ENM environment using the software from the given product set. Its aim is to make the process as automated as possible.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer nwci enm restore deployment --help
```

## What it Does
Below are the main steps that this command will perform.

### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information input as paramaters into the deployer

### Media Handling

* For media handling information, refer this link [ENM Media Handling](enm_media_information.md)

### ENM SED
The Deployer generates a sed.json file to use during the rollback deployment process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a SED file.

* Downloads the given SED file
* Fills in the media related keys, using the image names that were handled earlier in the installation
* Reports any values in the final SED that have blank values (but doesn't fail the script).


### VNF LCM SED
The Deployer generates a vnflcm_sed.json file to use during the rollback deployment process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF LCM SED file.

* Downloads the given SED file
* Populates the media related key values, using the image names that were handled earlier in the process.
* Reports any values in the final VNF LCM SED that have blank values (but doesn't fail the script).
* The VNF-LCM SED is uploaded to the following directory /vnflcm-ext/vnf-lcm/\<VNF_LCM_MEDIA_VERSION> on the VNF-LCM services VM.


### ENM Restore Deployment Workflow
The Deployer will run the necessary steps to execute the required workflow to complete the ENM restore deployment. Below are the steps the deployer takes during this phase.

* sftp the sed.json to /vnflcm-ext/enm/ on the VNF LCM VM
* Executes the 'Rollback Deployment' workflow
* Completes the user task with the tag name provided
* Waits for the workflow to reach the completed state
* Logs the results of each node in the workflow and fails the script if any nodes of type 'errorEndEvent' were found


### Cleanup
If the deployer exits without exception, it will clean up the temporary directory it created.

## What it Doesn't Do
Any steps mentioned in the official restore deployment documentation, that are not covered in the section above could be assumed to be not handled by the deployer, for example uploading of any other media not mentioned on this page.

## Example Usage
Below is an example command, used to restore deployment to product set 19.01.1 on a deployment called ieatenmpdxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> nwci enm restore deployment --os-username nwciUser --os-password 'XXXXXXXXX' --os-auth-url https://nfvi.dc419.nbi2.ericsson.se:5000/v2.0/ --os-project-name NWCI --deployment-name nwci --sed-file-url http://141.137.173.80/ECEE_30k_Environemnt_17.5-17.5.106.json --vnf-lcm-sed-url http://141.137.173.80/Athlone_ECEE_VNF_LCM_17.5-17.5.106.json --artifact-json-file /var/tmp/30k_artifact_json_list.json --os-cacert /root/openstack/cert/ctrl-ca.crt --backup-tag backup_19.01.1 --debug
```

##### Optional: Alter the Number of Max Attempts for Workflows
Add the below parameter to the deployer command:

```bash
  --workflow-max-check-attempts <number>
```
This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
The default is '1260' if none is specified.
