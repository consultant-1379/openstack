# Description of 'nwci enm rollback deployment' command

## Intended Purpose
This command can be used to rollback an ENM environment using the software from the given json file. Its aim is to make the process as automated as possible.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides or see Usage Paramater section below.

```bash
deployer nwci enm rollback deployment --help
```


## What it Does
Below are the main steps that this command will perform.


### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information input as paramaters into the Deployer.

### Media Handling

* For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

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


### ENM Rollback Deployment Workflow
The Deployer will run the necessary steps to execute the required workflow to complete the ENM rollback deployment. Below are the steps the Deployer takes during this phase.

* sftp the sed.json to /vnflcm-ext/enm/ on the VNF LCM VM
* Executes the 'Rollback Deployment' workflow
* Waits for the workflow to reach the completed state
* Logs the results of each node in the workflow and fails the script if any nodes of type 'errorEndEvent' were found


### VNF-LCM Rollback
The Deployer will rollback the VNF-LCM Stack if a delta exists between the installed media and the product set media versions.
Below are the steps the Deployer takes during this phase.

* Updates the VNF-LCM Server group Stack.
* Updates the VNF-LCM Security group Stack.
* Creates vnflcm_volume backup volumes from existing vnflcm_volume snapshot(s) created during the VNF-LCM upgrade process.
* Populates VNF-LCM SED values.
* Performs VNF-LCM Stack delete.
* Performs VNF-LCM Stack create.
* Deletes any existing vnflcm_volume snapshot(s).
* Deletes any obsolete vnflcm volume(s)
* Renames the vnflcm_volume backup volume(s) from &lt;deployment\_id&gt;\_vnflcm\_volume\&lt;volume\_count&gt;\_backup to &lt;deployment\_id&gt;\_vnflcm\_volume\&lt;volume\_count&gt;


### Cloud Management workflows
The Deployer installs the Cloud Management workflows version from the rollback product set.


### Cloud Performance workflows
The Deployer installs the Cloud Management workflows version from the rollback product set.


### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.


## What it Doesn't Do
Any steps mentioned in the official rollback deployment documentation, that are not covered in the section above could be assumed to be not handled by the Deployer, for example uploading of any other media not mentioned on this page.


## Example Usage
Below is an example command, used to rollback deployment to product set 17.14.100 on a Deployment called ieatenmpdxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> nwci enm rollback deployment --os-username nwciUser --os-password 'XXXXXXXXX' --os-auth-url https://nfvi.dc419.nbi2.ericsson.se:5000/v2.0/ --os-project-name NWCI --deployment-name nwci --sed-file-url http://141.137.173.80/ECEE_30k_Environemnt_17.5-17.5.106.json --artifact-json-file /var/tmp/30k_artifact_json_list.json --os-cacert /root/openstack/cert/ctrl-ca.crt --snapshot-tag snapshot_17.14.100 --debug
```

##### Optional: Alter the Number of Max Attempts for Workflows
Add the below parameter to the deployer command:

```bash
  --workflow-max-check-attempts <number>
```
This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
The default is '1260' if none is specified.
