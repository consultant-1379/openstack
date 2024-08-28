# Description of 'nwci enm rollout' command

## Intended Purpose
This command can be used to install an ENM environment using the software from the given json file. Its main aim is to make the installation process as automated as possible. The "nwci" command allows the script to be executed without the need to have access to the PDU NAM CIFWK Portal.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides or see Usage Paramater section below.

```bash
deployer nwci enm rollout --help
```


## What it Does
Below are the main steps that this command will perform.


### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the command line arguments given.

### Media Handling

* For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

### ENM SED
The Deployer generates a sed.json file to use during the installation process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a SED file.

* Downloads the given SED file
* Fills in the media related keys, using the image names that were handled earlier in the installation
* Reports any values in the final SED that have blank values (but doesn't fail the script).


### VNF LCM SED
The Deployer generates a vnflcm_sed.json file to use during the installation process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF LCM SED file.

* Downloads the given SED file
* Populates the media related key values, using the image names that were handled earlier in the process.
* Reports any values in the final VNF LCM SED that have blank values (but doesn't fail the script).
* The VNF-LCM SED is uploaded to the following directory /vnflcm-ext/vnf-lcm/\<VNF_LCM_MEDIA_VERSION> on the VNF-LCM services VM.


### Stack and Volume Creation
The Deployer will create all of the lcm stacks in the documented order.

The stacks below are created.

* internal_network
* security_group
* enm_keypair
* VNF LCM security group
* VNF LCM server group
* VNFLCM

The volume below is created.

* vnflcm_volume

VNF-LCM HA configured deployments require a virtual IP port stack to be created based on VNF-LCM SED parameter 'ip_version' and a additional vnflcm_volume.
* vnflcm_dual_vip (created if VNF-LCM SED parameter ip_version is set to value 'dual')
* vnflcm_ipv4_vip (created if VNF-LCM SED parameter ip_version is set to value '4')
* vnflcm_ipv6_vip (created if VNF-LCM SED parameter ip_version is set to the value '6')
* vnflcm_volume_1

After stack creation, the script waits for the stack to go to the creation completed state. It has a timeout of 60 minutes before it gives up waiting for each creation to complete.

The deployment of IPv4 or Dual version internal_network and security_group stacks is determined by a key value of either 'v4' or 'dual' of the SED key 'ip_version'.

The actual stack names used will follow the convention [deployment\_name]\_[stack\_file\_name], where deployment_name is given by the --deployment-name argument.

For example, if the deployment name was given as 'ieatenmpdxxx', the stack name for the VNFLCM stack would be 'ieatenmpdxxx_VNFLCM'.


### ENM Deployment Workflows
The Deployer will run the necessary steps to execute the required workflow to complete the deployment of ENM. Below are the steps the Deployer takes during this phase.

* First it waits for the VNF LCM services VM to be available
* Resets the cloud-user password to 'N3wP@55w0rd'
* If the optional parameter, "--upload_script_path" is given with a script path this script is uploaded to the VNF LCM VM and executed
* Installs ENM deploment workflows
* sftp the sed.json to /vnflcm-ext/enm/ on the VNF LCM VM
* Executes the 'ENM Initial Install' workflow
* Waits for the workflow to reach the completed state
* Logs the results of each node in the workflow and fails the script if any nodes of type 'errorEndEvent' were found


### Cloud Management workflows
The Deployer installs the Cloud Management workflows.


### Cloud Performance workflows
The Deployer installs the Cloud Performance workflows.


### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.


## What it Doesn't Do
Any steps mentioned in the official installation documentation, that are not covered in the section above could be assumed to be not handled by the Deployer, for example uploading of any other media not mentioned on this page.


## Example Usage
Below is an example command, used to install using a json file into a project called 'NWCI'. This example uses a SED file stored on a simple web server.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> nwci enm rollout --os-username nwciUser --os-password 'XXXXXXXXX' --os-auth-url https://nfvi.dc419.nbi2.ericsson.se:5000/v2.0/ --os-project-name NWCI --deployment-name nwci --sed-file-url http://141.137.173.80/ECEE_Environment/ECEE_30k_Environemnt_17.5-17.5.106.json --vnf-lcm-sed-url http://141.137.173.80/ECEE_Environment/Athlone_ECEE_VNF_LCM_17.5-17.5.106.json --artifact-json-file /var/tmp/30k_artifact_json_list.json --os-cacert /root/openstack/cert/ctrl-ca.crt
```

##### Optional: Alter the Number of Max Attempts for Workflows
Add the below parameter to the deployer command:

```bash
  --workflow-max-check-attempts <number>
```
This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
The default is '1260' if none is specified.
