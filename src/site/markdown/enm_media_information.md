# **Media Handling Information**

Based on the product set version given, the Deployer will query the CI Portal to determine the versions, filenames and nexus urls for the following media.

##### **ENM Media details**

The ENM SED Media key pair values are populated with the Media artifact names as they will appear in Glance as follows**:

* ERICenm_CXP9027091<br/>
  <b>SED Schema Parameter (Variable Name):</b> enm_iso_image
* ERICrhel6baseimage_CXP9031559<br/>
   <b>SED Schema Parameter (Variable Name):</b> enm_rhel6_base_image_name
* ERICsles15image_CXP9041763<br/>
  <b>SED Schema Parameter (Variable Name):</b> enm_sles_image_name
* ERICrhel79lsbimage_CXP9041915<br/>
  <b>SED Schema Parameter (Variable Name):</b> enm_rhel79_base_image_name
* RHEL_OS_Patch_Set_CXP9034997<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel6_updates_iso_image
* RHEL79-MEDIA_CXP9041796<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel79_iso_image
* RHEL88-MEDIA_CXP9043481<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel88_iso_image
* RHEL_OS_Patch_Set_CXP9034997<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel79_updates_iso_image
* RHEL88_OS_Patch_Set_CXP9043482<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel88_updates_iso_image
* ERICrhelvnflafimage_CXP9032490<br/>
  <b>SED Schema Parameter (Variable Name):</b> servicesImage
* ERICrhelpostgresimage_CXP9032491<br/>
  <b>SED Schema Parameter (Variable Name):</b> dbImage
* EXTRvmwareguesttools_CXP9035510

**Note: EDP auto Deploy for vENM upgrades will populate the ENM SED Media key values above. For vENM upgrades the Deployer will populate the following ENM SED Media key values with the Media artifact file names.

* ERICenm_CXP9027091<br/>
  <b>SED Schema Parameter (Variable Name):</b> enm_iso_image
* RHEL_OS_Patch_Set_CXP9034997<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel6_updates_iso_image
* RHEL79-MEDIA_CXP9041796<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel79_iso_image
* RHEL_OS_Patch_Set_CXP9034997<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel79_updates_iso_image
* RHEL88-MEDIA_CXP9043481<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel88_iso_image
* RHEL88_OS_Patch_Set_CXP9043482<br/>
  <b>SED Schema Parameter (Variable Name):</b> rhel88_updates_iso_image
* ERICautodeploy_CXP9038326

**Note: VIO/SIENM SED will be populated with additional Media key values

* ERICvms_CXP9035350<br/>
  <b>SED Schema Parameter (Variable Name):</b> vms_media
* EXTRvmwareguesttools_CXP9035510<br/>
  <b>SED Schema Parameter (Variable Name):</b> vmwareguesttools_media
* ERICenm_CXP9027091<br/>
  <b>SED Schema Parameter (Variable Name):</b> enm_iso_image
* EXTRvmwareesxi_CXP9035974<br/>
  <b>SED Schema Parameter (Variable Name):</b> esxi_media
* EXTRvmwarevcenter_CXP9035456<br/>
  <b>SED Schema Parameter (Variable Name):</b> vcsa_media

#### **VIO/SIENM Platform Media Details**

 The following media will be downloaded\/transferred onto the DVMS and VMS based on information below.

| Media Name             | Description                                    | Product Number | Required on DVMS | Required on VMS |
|------------------------|------------------------------------------------|----------------|------------------|-----------------|
| EXTRvmwareesxi         | VMware HPE Custom Image for ESXi               | CXP 903 5974   | Yes              | No              |
| EXTRvmwarevcenter      | VMware vCenter Server Appliance ISO            | CXP 903 5456   | Yes              | No              |
| EXTRvmwarevio          | VMware Integrated OpenStack                    | CXP 903 5975   | Yes              | No              |
| ERICvmwarepatches      | VMware Patches                                 | CXP 903 5795   | Yes              | No              |
| ERICvms                | VM image of Virtual Management Server (VMS)    | CXP 903 5350   | Yes              | No              |
| ERICautodeploy         | EDP autodeploy package                         | CXP 903 8326   | Yes              | No              |
| ERICenm                | ENM Media                                      | CXP 902 7091   | Yes              | Yes             |
| EXTRvmwareguesttools   | Guest tools for VMware                         | CXP 903 5510   | Yes              | No              |
| ERICvnflcm             | VNF LCM Media                                  | CXP 903 4858   | Yes              | No              |
| RHEL_OS_Patch_Set      | Red Hat Linux Patch Set                        | CXP 903 4997   | Yes              | No              |
| RHEL88-MEDIA           | Red Hat Linux 8.8 Media                        | CXP 904 3481   | Yes              | No              |
| RHEL88_OS_Patch_Set    | Red Hat Linux 8.8 Patch Set                    | CXP 904 3482  | Yes              | No              |

#### **Media Handling**
Media images are checked if they are present in Glance based on the image name including any "image_posfix" identifier.

Note: The Current Media types that are handled by the Deployer when uploading to Glance are iso, qcow2, img and vmdk. The format of these artifacts when uploaded to Glance will be iso, qcow2 raw and vmdk respectively.

For each Media artifact/image

* Media artifact versions are determined from the product set, and downloaded directly from nexus.
* Check if Media image with the same name is available in Glance, if not it downloads those images locally and then uploads them to Glance**.
* Media image names on RHOS clouds will be given a postfix of '_CI' if one is not provided by using the --image-name-postfix argument.
* It will not be possible to specify a postfix identifier on a VMDK image for Small Integrated ENM/VIO deployments, the --image-name-postfix argument if given will be ignored.
* VMDK media type conversion required for Small Integrated ENM/VIO deployments will be performed on the deployments Virtual Management Server.
* Waits for the images to be fully uploaded to Glance.
* Downloads and extracts the cloud templates artifact.
* Downloads workflow artifacts**


Note: Small Integrated ENM/VIO artifacts/media artifacts must be updated using the SIENM/VIO specific platform functions.

** EDP vENM upgrade functionality will only download the ENM media as a prerequisites for EDP auto deploy if the media is not already
in Glance. Media key values in the ENM and VNF-LCM SED based on the keys containing "media" or "image" are used to identify the required Media.
The Media keys required to be populated should include the Media CXP number of the required Media in SED so that the required Media is download and the SED keys containing 'media' in the key name are populated with the Media filename.
Meda artifacts such as ENM cloud templates and worklows are not download independently. Media is downloaded to the /artifacts/ directory within the Deployer container which should be mounted to a docker volume.

##### **NWCI Media details**

When using the NWCI functionality the Media details be must be defined in a JSON file with the URL of the required Media.

Below is an example of media artifact json object file with expected media content for vENM product set,

Note: ERICenmcloudtemplates are required, although not defined in the ENM SED and VNF-LCM SED media key values, required to create ENM key pair stack if it does not already exist.

Note: SIENM/VIO has additional media requirements, user consult the relevant documentation including ENM SED for these media requirements.

The artifacts handled within the json file are:

* Media Details
    * ERICenm_CXP9027091
    * ERICsles15image_CXP9041763
    * ERICrhel79lsbimage_CXP9041915
    * RHEL79-MEDIA_CXP9041796
    * RHEL79_OS_Patch_Set_CXP9041797
    * RHEL88-MEDIA_CXP9043481
    * RHEL88_OS_Patch_Set_CXP9043482
    * ERICrhelvnflafimage_CXP9032490
    * ERICrhelpostgresimage_CXP9032491
    * ERICvnflafdevimage_CXP9032638


* Cloud Templates Details
    * ERICenmcloudtemplates_CXP9033639
* Deployment Workflows Details
    * ERICenmdeploymentworkflows_CXP9034151
* Cloud Management workflows
    * ERICenmcloudmgmtworkflows_CXP9036442
* VNF LCM Cloud Templates details
    * vnflcm-cloudtemplates

Note: The following Media types are handled by the Deployer when uploading to Glance are iso, qcow2, img and vmdk. The format of these artifacts when uploaded to Glance will be iso, qcow2 raw and vmdk respectively.

* VMDK media type conversion required for  SIENM/VIO projects will be performed on the projects Virtual Management Server.

Example of Json file Layout

```json
{
   "cloud_mgmt_workflows_details":{
      "CXP9036442":"https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICenmcloudmgmtworkflows_CXP9036442-1.14.1.rpm"
   },
   "vnflcm_cloudtemplates_details":{
      "vnflcm-cloudtemplates":"https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/vnflcm-cloudtemplates-5.21.1.tar.gz"
   },
   "edp_autodeploy_details":{
      "CXP9038326":"https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICautodeploy_CXP9038326-1.2.13.tar.gz"
   },
   "cloud_templates_details":{
      "CXP9033639":"https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICenmcloudtemplates_CXP9033639-1.91.7.rpm"
   },
   "cloud_performance_workflows_details":{
      "CXP9037118":"https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICenmcloudperformanceworkflows_CXP9037118-1.10.1.rpm"
   },
   "deployment_workflows_details":{
      "CXP9034151":"https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICenmdeploymentworkflows_CXP9034151-1.98.3.rpm"
   },
   "media_details":{
      "CXP9041797": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/RHEL79_OS_Patch_Set_CXP9041797-1.10.1.iso",
      "CXP9033639": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICenmcloudtemplates_CXP9033639-1.88.17.rpm",
      "CXP9041796": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/RHEL79-MEDIA_CXP9041796-1.0.1.iso",
      "CXP9043481": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/RHEL88-MEDIA_CXP9037123-1.0.1.iso",
      "CXP9041763": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICsles15image_CXP9041763-1.29.1.qcow2",
      "CXP9027091": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICenm_CXP9027091-2.10.93.iso",
      "CXP9041916": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICrhel79jbossimage_CXP9041916-1.5.2.qcow2",
      "CXP9041915": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICrhel79lsbimage_CXP9041915-1.5.4.qcow2",
      "CXP9034858": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICvnflcm_CXP9034858-5.20.6.tar.gz",
      "CXP9043482": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/RHEL88_OS_Patch_Set_CXP9037739-1.0.1.iso",
      "CXP9038326": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICautodeploy_CXP9038326-1.0.63.tar.gz",
      "CXP9032638": "https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICvnflafdevimage_CXP9032638-3.1.6.qcow2"
   },
   "vnflcm_details":{
      "CXP9034858":"https://arm901-eiffel004.athtem.eei.ericsson.se:8443/nexus/ERICvnflcm_CXP9034858-5.21.1.tar.gz"
   }
}
```

For each of the media artifacts, it will then

* Checks if they are in Glance.
* Waits for the images to be fully uploaded
* Sets up a temporary working directory of a random name, under /tmp/
* Downloads and installs the cloud templates artifact using the artifact url listed in the json file.

* SIENM/VIO projects will require additional artifact defined in the artifact.json in order to convert the product set media from .iso and .qcow2 to .vmdk media type.

```
    "vmware_guest_tools_details": {
        "CXP9035510": "https://150.132.35.218:8443/nexus/content/repositories/thirdparty/com/ericsson/oss/itpf/senm/EXTRvmwareguesttools_CXP9035510/1.0.1/EXTRvmwareguesttools_CXP9035510-1.0.1.iso"
    }
```

### **KGB+N adding artifacts**
Artifacts required to be installed in place of the artifacts that are part of a product set can be defined using the additional --rpm-versions argument. The --rpm-versions argument takes the artifact id and artifact version or artifact url separated by '::'. Additional artifacts must be separated by '@@'


If an artifact is contained within the ENM ISO, a new ENM ISO will be created with the required artifact(s). The new KGB+N ENM ISO image name will be suffixed with the following \_&ltdeployment_name&gt_KGB+N_CI


New packages that are not pre-existing on the ENM ISO, must have a media category defined (e.g. model, service) after the version or url or latest tag information separated by the '::' in a comma separated list.

EDP packages when defined in the --rpm-versions parameter are downloaded into a custom directory named '/artifacts/ci_edp_packages' that should be mounted to the prerequisite media docker volume. The EDP packages made available in the docker volume when mounted to EDP Auto Deploy container will enable the EDP packages to be installed within the EDP container.

```bash
--rpm-versions ERICpkgCXP1234567::1.2.3@@ERICpkgCXP7654321::https:/ERICrpmCXP7654321-1.2.3.
rpm@@ERICpkgCXP9876543::latest
```

To remove a package from the ENM ISO under a media category/categories after the media category/categories add the separator '::' followed by True.

```bash
--rpm-versions ERICpkgCXP1234567::<version | URL>::service::True
```

Small Integrated ENM/VIO artifacts/media artifacts must be updated using the SIENM/VIO specific platform functions within the Deployer.

The --media-versions parameter should be combined with --rpm-versions parameter for ERICvnflcm_CXP9034858 media on Small Integrated ENM/VIO deployments only, the new vnflcm-cloudtemplates version should be defined
in the --rpm-versions parameter when specifying new ERICvnflcm_CXP9034858 media.


## Example Usage


### **ENM**

#### Install

```bash
ci enm rollout: {
  docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm rollout
  --deployment-name ieatenmpdxxx --product-set 16.16::16.16.80 --debug --rpm-versions
  ERICenmcloudtemplates_CXP9033639::1.1.1@@ERICpmicmodel_CXP9030403::1.2.3@@ERICcli_CXP9030319::http//
  artifact_url
}
```

#### Upgrade

```bash
ci enm upgrade: {
  docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci enm upgrade
  --deployment-name ieatenmpdxxx --product-set 19.16::19.16.10 --debug --rpm-versions
  ERICenmcloudtemplates_CXP9033639::1.1.1@@ERICpmicmodel_CXP9030403::1.2.3@@ERICcli_CXP9030319::http//
  artifact_url
}
```


### **SIENM/VIO platform**

#### Install

```bash
ci vio platform install: {
  docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio platform install
  --deployment-name vio-xxxx --product-set 19.08::19.08.100 --vio-profile-list sienm_phase1,sienm_phase2
  --debug --media-versions RHEL6.10_Media_CXP9036772::1.1.1@@RHEL_OS_Patch_Set_CXP9034997::1.2.
  3@@ERICvnflcm_CXP9034858::http://artifact_url
}
```

#### Upgrade

```bash
ci vio platform upgrade: {
  docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio platform upgrade
  --deployment-name vio-xxxx --product-set 19.08::19.08.100 --debug --rpm-versions
  ERICenmcloudtemplates_CXP9033639::1.1.1@@ERICpmicmodel_CXP9030403::1.2.3@@ERICcli_CXP9030319::http://
  artifact_url,
  docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio platform upgrade
  --deployment-name vio-xxxx --product-set 19.08::19.08.100 --debug --media-versions RHEL6.
  10_Media_CXP9036772::1.1.1@@RHEL_OS_Patch_Set_CXP9034997::1.2.3@@ERICvnflcm_CXP9034858::http://
  artifact_url
}
```

#### DVMS deploy
```bash
ci vio dvms deploy: {
  docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> ci vio dvms deploy
  --deployment-name vio-xxxx --product-set 19.08::19.08.100  --media-versions ERICvms_CXP9035350::http://
  artifact_url --debug
}
```
