# Description of 'ci enm schema upgrade' command

## Intended Purpose
This command can be used to upgrade the ENM and VNF-LCM SED Schema versions in the Deployment Inventory Tool.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci enm schema upgrade --help
```


## What it Does
Below are the main steps that this command will perform.



### Upgrade Schema Version of ENM SED based on ENM Cloud Templates
Checks the version of the ENM cloud templates from the product set. If this version is different from the version used in the SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
If this fails the script will throw an error.

At this point manual intervention is required as update is not possible.
This should be done through the Documents page on the DIT UI.


### Upgrade Schema Version of VNF-LCM SED based on VNF-LCM Cloud Templates
Checks the version of the VNF-LCM cloud templates from the product set. If this version is different from the version used in the SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
If this fails the script will throw an error.

At this point manual intervention is required as update is not possible.
This should be done through the Documents page on the DIT UI.



## Example Usage
Below is an example command, using product set 20.08.1 on a Deployment called ieatenmpdxxx, with two docker volumes called media-volume and config-volume.

```bash
 docker run --rm armdocker.rnd.ericsson.se/proj_nwci/enmdeployer:<version> ci enm schema upgrade --deployment-name ieatenmpdxxx --product-set 20.08::20.08.1 --debug
```

