# Description of 'nwci edp venm' command

## Intended Purpose
This command can be used to download ENM software from the artifacts urls defined in json object artifact file to an attached docker volume as prerequisite for EDP autodeploy.
The required media information is populated in given SED documents, the keystone project.rc file is generated from the CLI parameters provided.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer nwci edp venm --help
```

## Prerequisite
Two docker volumes must be available to be mounted to deployer container.

* The first docker volume should be mounted to /artifacts/ directory of the deployer container, this volume will store all the required  media artifacts.
* The second docker volume should be mounted to /config/ directory of the deployer container, this volume will store the generated ENM SED, VNF-LCM, keystone file, ca certificate and private SSH key associated with the given deployment.


## What it Does
Below are the main steps that this command will perform.


### Media Handling

For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

### Keystone.rc file creation
The keystone is created from the Deployment information retrieved from DIT.
The file is saved in the Deployer container as: /config/\<os_project_name>\_project.rc


### ENM Key Pair
The Deployer will create the ENM key pair using HEAT template from ERICenmcloudtemplates if it does not already exist, using the HEAT template listed below.

* /infrastructure_resources/key_pair.yaml

NOTE: On SIENM/VIO deployments the private key is retrieved from the IVMS.

The private SSH key is saved in the Deployer container as:  /config/\<os_project_name>\_project.rc


### ENM SED
The Deployer populates the sed.json file with the media file names for use by EDP autodeploy.

Media key values in the ENM SED are identified based on the keys containing "media" or "image" with the required CXP numbers, only required media should have CXP numbers defined to ensure the SED is populated with the required media file names.

Below are the stages involved in generating a SED file.

* Downloads/reads the SED
* Populates the media related keys with the media file name.
* The sed.json is saved under /config/ within deployer container which should be mounted to a docker volume.


### VNF LCM SED
The Deployer populates a lcm_sed.json file with the media file names for use by EDP autodeploy.

Media key values in the VNF-LCM SED are identified based on the keys containing "media" or "image" with the required CXP numbers, only required media should have CXP numbers defined to ensure the SED is populated with the required media file names.

Below are the stages involved in generating a VNF LCM SED file.

* Downloads/reads the VNF LCM SED.
* Populates the media related keys with the media file name.
* The lcm_sed.json is saved under /config/ within deployer container which should be mounted to a docker volume.


### Files created
The following files are created in the /config/ directory of the Deployer container.

* sed.json
* lcm_sed.json
* Key_pair_\<os_project_name>.pem
* \<os_project_name>\_project.rc

## Example Usage
Below is an example command, using product set 20.08.1 on a Deployment called ieatenmpdxxx, with two docker volumes called media-volume and config-volume.

```bash
 docker run -v media-volume:/artifacts -v conig-volume:/config --rm armdocker.rnd.ericsson.se/proj_nwci/enmdeployer:<version> nwci edp venm --os-username nwciUser --os-password 'XXXXXXXXX' --os-auth-url https://nfvi.dc419.nbi2.ericsson.se:5000/v2.0/ --os-project-name NWCI --deployment-name nwci --sed-file-url http://141.137.173.80/Athlone_ECEE_30k_Environemnt_17.5-17.5.106.yaml --vnf-lcm-sed-url http://141.137.173.80/Athlone_ECEE_VNF_LCM_17.5-17.5.106.json --artifact-json-file /var/tmp/30k_artifact_json_list.json --os-cacert /root/openstack/cert/ctrl-ca.crt --debug
```
