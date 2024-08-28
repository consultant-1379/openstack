# Description of 'ci edp venm' command

## Intended Purpose
This command can be used to download ENM software from the given product set on an attached docker volume as prerequisite for EDP autodeploy.
Deployment related information for the given deployment name, such as SED, project and pod details is retrieved from the Deployment Inventory Tool.


## Command Line Arguments
Please refer to the help provided by the command itself, for details on each command line argument it provides.

```bash
deployer ci edp venm --help
```

## Prerequisite
Two docker volumes must be available to be mounted to deployer container.

* The first docker volume should be mounted to /artifacts/ directory of the deployer container, this volume will store all the required  media artifacts.
* The second docker volume should be mounted to /config/ directory of the deployer container, this volume will store the generated ENM SED, VNF-LCM, keystone file, ca certificate and private SSH key associated with the given deployment.


## What it Does
Below are the main steps that this command will perform.


### Retrieval Of Deployment Information from DIT
The openstack credentials and SED are obtained from the Deployment Inventory Tool, for the given Deployment name.


### Upgrade Schema Version of SED based on Cloud Templates
Checks the version of the cloud templates from the product set. If this version is different from the version used in the SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
If this fails the script will throw an error.

At this point manual intervention is required as update is not possible.
This should be done through the Documents page on the DIT UI.


### Upgrade Schema Version of VNF LCM SED based on VNF LCM media
Checks the version of the VNF LCM media from the product set. If this version is different from the version used in the VNF LCM SED in DIT it will attempt to update it.

This includes removing and adding fields based on the new Schema and also filling in any defaults.
If this fails the script will throw an error.

At this point manual intervention is required as update is not possible.
This should be done through the Documents page on the DIT UI.

### Media Handling

* For media handling information, refer to this link [ENM Media Handling](enm_media_information.md)

### Keystone.rc file creation
The keystone is created from the Deployment information retrieved from DIT.
The file is saved in the Deployer container as: /config/\<os_project_name>\_project.rc


### ENM Key Pair
The Deployer will create the ENM key pair using HEAT template from ERICenmcloudtemplates if it does not already exist, using the HEAT template listed below.

* /infrastructure_resources/key_pair.yaml

NOTE: On SIENM/VIO deployments the private key is retrieved from the IVMS.

After successful creation the public and private keys are retrieved from the stack by the Deployer and are posted to the DIT tool under the deployment id that is currently being run against.

The private SSH key is saved in the Deployer container as:  /config/\<os_project_name>\_project.rc


### ENM SED
The Deployer generates a sed.json file for use by EDP autodeploy.

Below are the stages involved in generating a SED file.

* Downloads the SED that is associated with the given Deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on DIT and how to setup your Deployments, See DIT link below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
* Populates the media related keys with the media file name.
* The sed.json is saved under /config/ within deployer container which should be mounted to a docker volume.


### VNF LCM SED
The Deployer generates a lcm_sed.json file for use by EDP autodeploy.

Below are the stages involved in generating a VNF LCM SED file.

* Downloads the VNF LCM SED that is associated with the given deployment in DIT.
  The given deployment must be defined in DIT.
  For more information on the DIT tool and how to setup deployments, See DIT link below.
  [DIT documentation](https://atvdit.athtem.eei.ericsson.se/helpdocs/#help/app/helpdocs)
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
 docker run -v media-volume:/artifacts -v config-volume:/config --rm armdocker.rnd.ericsson.se/proj_nwci/enmdeployer:<version> ci edp venm --deployment-name ieatenmpdxxx --product-set 20.08::20.08.1 --debug
```

### Skip media download
Media download can be skipped if not required, where only the ENM, VNF-LCM SED, keypair and keystone files are made available in the attached docker volume.

```bash
docker run -v config-volume:/config --rm armdocker.rnd.ericsson.se/proj_nwci/enmdeployer:<version> ci edp venm --deployment-name ieatenmpdxxx --product-set 20.10::20.10.1 --skip-media-download --debug
```
