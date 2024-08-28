# Description of 'ci enm stacks delete' command

## Intended Purpose
This command can be used to delete all of the stacks for a particular ENM environment.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci enm stacks delete --help
```


## What it Does
Below are the main steps that this command will perform.


### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information from DIT.


### Stack Deletion
The Deployer will delete all of the stacks in the associated project in reverse order of creation.

If the delete command fails it will retry 3 times.

**WARNING: This will delete ALL stacks in your project, not just those created during the installation procedure. This is a temporary measure until an LCM workflow is created to delete only the appropriate stacks.**

After stack deletion has been started, the script waits for the stack to be completely deleted. It has a timeout of 60 minutes waiting for each deletion to complete.

VIO projects require a pre-existing internal network to be present, in such cases the internal network will not be deleted.

### Checking if the openstack project is clean
A number of checks are run to make sure the openstack project is completely clean after deleting the stacks.
If any of these checks fail, the script will exit at this point.

These checks are as follows.

* Making sure no stacks remain in the project
* Making sure no vms remain in the project
* Making sure no volumes remain in the project
* Making sure no networks remain in the project

VIO projects require a pre-existing internal network stack. The pre-existing internal network stack will be ignored
in such cases.



## Example Usage
Below is an example command, used to install delete all of the stacks in a project associated with the deployment 'ieatenmxxx'.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --debug
```


### Wait parameter
This is an optional parameter in response to a known Redhat Openstack bug in cinder API when deleting multiple stacks, for more information see https://jira-oss.seli.wh.rnd.internal.ericsson.com/browse/CIP-20767


## Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --wait --debug
```

## Exclude specific Servers, Volumes, Networks from deletion
To exclude specific Servers, Volumes, Networks from deletion, specify the following optional paramater(s) with comma separated string of the specfic resource name(s).

To exclude specific Servers from deletion, specify the following optional paramater with comma separated string of Server name(s).

## Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --exclude-server exclude_server_1,exclude_server_2,exclude_server_3 --debug
```

To exclude specific Volumes from deletion, specify the following optional paramater with comma separated string of Volume name(s).

## Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --exclude-volume exclude_volume_1,exclude_volume_2,exclude_volume_3 --debug
```

To exclude specific Networks from deletion, specify the following optional paramater with comma separated string of Network name(s).

## Example Usage
```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm stacks delete --deployment-name ieatenmxxx --exclude-network exclude_network_1,exclude_network_2,exclude_network_3 --debug
```

