# Description of 'ci task' command

## Intended Purpose
This command can be used to run different CI related tasks. Its aim is to make the process as automated as possible.
Deployment related information for the given deployment name, such as SED, project and pod details is retrieved from the Deployment Inventory Tool.

## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci task --help
```


## What it Does
Below are the main steps that this command will perform.

### Retrieval Of Deployment Information from DIT
The openstack credentials and SED are obtained from the Deployment Inventory Tool, for the given Deployment name.

### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information from DIT.


### Running commands on the VNF-LCM services VM
Use the --run-lcm-cmd CLI parameter to execute commands on the VNF-LCM services VM.


## Example Usage
Below is an example command, run on a Deployment called ieatenmcxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci task --deployment-name ieatenmcxxx --run-lcm-cmd <command> --debug
```

Example using VNF-LCM security vulnerability command.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci task --deployment-name ieatenmcxxx --run-lcm-cmd "sudo -i vnflcm security allowaccess --interface eth0 --file /vnflcm-ext/enm/enm_iptables_white_list.txt <<< $'y\n' " --debug
```


### Cleanup/Uninstall of obsolete workflows on the VNF-LCM services VM
Use the --workflows-cleanup CLI parameter to execute commands on the VNF-LCM services VM.

By default the following number of workflows are retained:
enmdeploymentworkflows retain latest 5 (n-4)
enmcloudmgmtworkflows retain latest 2 (n-1)
enmcloudperformanceworkflows retain latest 2 (n-1)

## Example Usage
Below is an example command, run on a Deployment called ieatenmcxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci task --deployment-name ieatenmcxxx --workflows-cleanup --debug
```

To override the default workflow rentention values, a comma separated list can be specified as shown below:

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci task --deployment-name ieatenmcxxx --workflow-cleanup enmdeploymentworkflows=3,enmcloudmgmtworkflows=2,enmcloudperformanceworkflows=2 --debug
```


### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.


## What it Doesn't Do
Any steps mentioned in the official documentation, that are not covered in the section above could be assumed to be not handled by the Deployer.
