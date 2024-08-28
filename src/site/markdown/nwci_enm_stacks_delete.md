# Description of 'nwci enm stacks delete' command

## Intended Purpose
This command can be used to delete all of the stacks for a particular ENM environment.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides or see Usage Paramater section below.

```bash
deployer nwci enm stacks delete --help
```


## What it Does
Below are the main steps that this command will perform.


### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the command line arguments given.


### Stack Deletion
The Deployer will delete all of the stacks in the given project in reverse order of creation.

If the delete command fails it will retry 3 times.

**WARNING: This will delete ALL stacks in your project, not just those created during the installation procedure. This is a temporary measure until an LCM workflow is created to delete only the appropriate stacks.**

After stack deletion has been started, the script waits for the stack to be completely deleted. It has a timeout of 60 minutes waiting for each deletion to complete.

VIO projects require a pre-existing internal network to be present, in such cases the internal network will not be deleted.


## Example Usage
Below is an example command, used to install delete all of the stacks in a project called 'Axis'.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> nwci enm stacks delete --os-username openstackuser --os-password 'openstackpassword123' --os-auth-url 'http://131.160.132.5:5000/v2.0' --os-project-name Axis --deployment-name enmcloud10 --debug
```

### Wait parameter
This is optional parameter in response to a known Redhat Openstack bug in cinder API when deleting multiple stacks, for more information see https://jira-oss.seli.wh.rnd.internal.ericsson.com/browse/CIP-20767


## Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmpdxxx --wait --debug
```
