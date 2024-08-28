# Description of 'ci enm rollout' command

## Intended Purpose
This command can be used to install an ENM environment using the software from the given product set. Its aim is to make this possible with as much of that process being automated as possible.
Deployment related information for the given deployment name, such as SED, project and pod details is retrieved from the Deployment Inventory Tool.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci enm rollout --help
```


## What it Does
Below are the main steps that this command will perform.

### Retrieval Of Deployment Information from DIT
The openstack credentials and SED are obtained from the Deployment Inventory Tool, for the given Deployment name.

### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information from DIT

### Checking if the openstack project is clean
A number of checks are run to make sure the openstack project is completely clean before starting the installation.
If any of these checks fail, the script will exit at this point.

VIO projects require a pre-existing internal network stack. The pre-existing internal network stack will be ignored
during this check on VIO projects.

These checks are as follows.

* Making sure no stacks remain in the project
* Making sure no vms remain in the project
* Making sure no volumes remain in the project
* Making sure no networks remain in the project


### Upgrade Schema Version of SED based on Cloud Templates
Checks the version of the cloud templates that is passed in either from the product set or from the --rpm-versions command. If this version is different from the version used in the SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
If this fails the script will throw an error.

At this point manual intervention is required as update is not possible.
This should be done through Documents page on the DIT UI.

### Upgrade Schema Version of VNF LCM SED based on VNF LCM Cloud Templates
Checks the version of the VNF LCM cloud templates that is passed in either from the product set or from the --rpm-versions command. If this version is different from the version used in the VNF LCM SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
If this fails the script will throw an error.

At this point manual intervention is required as update is not possible.
This should be done through Documents page on the DIT UI.

### Media Handling

* For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

### ENM SED
The Deployer generates a sed.json file to use during the installation process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a SED file.

* Downloads the SED that is associated with the given Deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on DIT and how to setup your Deployments, See DIT link below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Fills in the media related keys, using the image names that were handled earlier in the installation
* Reports any values in the final SED that have blank values (but doesn't fail the script).


### VNF LCM SED
The Deployer generates a vnflcm_sed.json file to use during the installation process.

When the Deployer is run in verbose mode, it will log details about each key that is being populated.

Below are the stages involved in generating a VNF LCM SED file.

* Downloads the VNF LCM SED that is associated with the given deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on the DIT tool and how to setup deployments, See DIT link below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
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

VNF-LCM HA configured deployments require a virtual IP port stack to be created based on VNF-LCM SED parameter 'ip_version' and an additional vnflcm_volume.
* vnflcm_dual_vip (created if VNF-LCM SED parameter ip_version is set to value 'dual')
* vnflcm_ipv4_vip (created if VNF-LCM SED parameter ip_version is set to value '4')
* vnflcm_ipv6_vip (created if VNF-LCM SED parameter ip_version is set to the value '6')
* vnflcm_volume_1


After stack creation, the script waits for the stack to go to the creation completed state. It has a timeout of 60 minutes before it gives up waiting for each creation to complete.

The deployment of IPv4 or Dual version internal_network and security_group stacks is determined by a key value of either 'v4' or 'dual' of the SED key 'ip_version'.

The actual stack names used will follow the convention [deployment\_name]\_[stack\_file\_name], where deployment\_name is given by the --deployment-name argument.

For example, if the deployment name was given as 'ieatenmxxx', the stack name for the VNFLCM stack would be 'ieatenmxxx_VNFLCM'.

### Upload Key Pair to DIT
After successful creation the public and private keys are retrieved from the stack by the Deployer and are pushed to the DIT tool under the deployment id that is currently being run against.


### ENM Deployment Workflow
The Deployer will run the necessary steps to execute the required to complete the deployment of ENM. Below are the steps the Deployer takes during this phase.

* Waits for the VNF LCM services VM to be available
* Resets the cloud-user password to 'N3wP@55w0rd'
* Installs the ENM deployment workflows
* sftp the sed.json to /vnflcm-ext/enm/ on the VNF LCM VM
* Executes the 'ENM Initial Install' workflow
* Waits for the workflow to reach the completed state
* Logs the results of each node in the workflow and fails the script if any nodes of type 'errorEndEvent' were found


### Cloud Management workflows
The Deployer installs the Cloud Management workflows.


### Cloud Performance workflows
The Deployer installs the Cloud Performance workflows.


### Enable VNF-LCM HTTPS
The following steps are executed post ENM Initial Install workflow on the VNF-LCM Services master VM to enable HTTPS:

* mount nfsdata:/ericsson/data/credm/ /ericsson/tor/data/credm/
* /opt/ericsson/ERICcredentialmanagercli/bin/credentialmanager.sh -i -x /ericsson/credm/data/xmlfiles/VNFLCM_CertRequest.xml


### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.


## What it Doesn't Do
Any steps mentioned in the official installation documentation, that are not covered in the section above could be assumed to be not handled by the Deployer, for example uploading of any other media not mentioned on this page.


## Example Usage
Below is an example command, used to install product set 16.16.80 on a Deployment called ieatenmxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm rollout --deployment-name ieatenmxxx --product-set 16.16::16.16.80 --debug
```

##### Optional: Alter the Number of Max Attempts for Workflows
Add the below parameter to the deployer command:

```bash
  --workflow-max-check-attempts <number>
```
This is used to set the specific amount of attempts for a workflow to complete, 1hr = 360 attempts.
The default is '1260' if none is specified.


#### Checking if the openstack project is clean
A number of checks are run to make sure the openstack project is completely clean after deleting the stacks.
If any of these checks fail, the script will exit at this point.

These checks are as follows.

* Making sure no stacks remain in the project
* Making sure no vms remain in the project
* Making sure no volumes remain in the project
* Making sure no networks remain in the project

VIO projects require a pre-existing internal network stack. The pre-existing internal network stack will be ignored
in such cases.



#### Exclude specific Servers, Volumes, Networks from Project clean check
To exclude specific Servers, Volumes, Networks from deletion, specify the following optional paramater(s) with comma separated string of the specfic resource name(s).

To exclude specific Servers from clean Project check, specify the following optional paramater with comma separated string of Server name(s).

##### Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --exclude-server exclude_server_1,exclude_server_2,exclude_server_3 --debug
```

To exclude specific Volumes from deletion, specify the following optional paramater with comma separated string of Volume name(s).

##### Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --exclude-volume exclude_volume_1,exclude_volume_2,exclude_volume_3 --debug
```

To exclude specific Networks from deletion, specify the following optional paramater with comma separated string of Network name(s).

##### Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --exclude-network exclude_network_1,exclude_network_2,exclude_network_3 --debug
```