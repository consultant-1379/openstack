# Description of 'nwci task' command

## Intended Purpose
This command can be used to run different NWCI related tasks.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer nwci task --help
```


## What it Does
Below are the main steps that this command will perform.


### Setting of OpenStack Environment Variables
Sets the required OpenStack client environment variables, based on the information from DIT.


### Running commands on the VNF-LCM services VM
Use the --run-lcm-cmd CLI parameter to execute commands on the VNF-LCM services VM.


## Example Usage
Below is an example command, run on a Deployment called ieatenmcxxx.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> nwci task --os-username nwciUser --os-password 'XXXXXXXXX' --os-auth-url https://nfvi.dc419.nbi2.ericsson.se:5000/v2.0/ --os-project-name NWCI --deployment-name nwci --sed-file-url http://141.137.173.80/Athlone_ECEE_30k_Environemnt_17.5-17.5.106.yaml -vnf-lcm-sed-url http://141.137.173.80/Athlone_ECEE_VNF_LCM_17.5-17.5.106.json --run-lcm-cmd <command> --os-cacert /root/openstack/cert/ctrl-ca.crt --debug
```

Example using VNF-LCM security vulnerability command.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> nwci task --os-username nwciUser --os-password 'XXXXXXXXX' --os-auth-url https://nfvi.dc419.nbi2.ericsson.se:5000/v2.0/ --os-project-name NWCI --deployment-name nwci --sed-file-url http://141.137.173.80/Athlone_ECEE_30k_Environemnt_17.5-17.5.106.yaml -vnf-lcm-sed-url http://141.137.173.80/Athlone_ECEE_VNF_LCM_17.5-17.5.106.json --run-lcm-cmd "sudo -i vnflcm security allowaccess --interface eth0 --file /vnflcm-ext/enm/enm_iptables_white_list.txt <<< $'y\n' " --os-cacert /root/openstack/cert/ctrl-ca.crt --debug
```

### Cleanup
If the Deployer exits without exception, it will clean up the temporary directory it created.


## What it Doesn't Do
Any steps mentioned in the official documentation, that are not covered in the section above could be assumed to be not handled by the Deployer.
