# Download and Installation
The Deployer is a python based project and is delivered as a python wheel package.

## Installation Prerequisites

### Python 2.7
Python 2.7 is required to run the Deployer. You can check if python 2.7 is installed using the following command.

```bash
python --version
```

Please refer to the python web site for further information on installing python 2.7 https://www.python.org/


### pip
The pip package is required to do the installation of the package. You can check if pip installed using the following command.

```bash
pip --version
```

Please refer to the pip installation documentation for further information on installing pip https://pip.pypa.io/en/stable/installing/

Example steps to install pip below via cli

```bash
curl -O https://bootstrap.pypa.io/get-pip.py
python get-pip.py
```


### Access to Python Package Index
During installation of the Deployer, the whl file will download its dependencies from the python package index, so it needs network connectivity to this url. https://pypi.python.org


### Operating System Libraries
During installation of the Deployers dependencies, some of those dependencies require various libraries / compilers. On a CentOS 7 server, it is found that the required libraries were as follows. These may be named slightly differently depending on your operating system.

- gcc
- python-devel
- openssl-devel
- libffi-devel

Example below of installation on CentOS 7 server using yum.

```bash
yum -y install gcc python-devel openssl-devel libffi-devel
```

To use commands relating to conversion of tar.gz to iso format, the following dependency is also required.

- genisoimage

Example below of installation on CentOS 7 server using yum.

```bash
yum -y install genisoimage
```


## Download Deployer Package
All of the versions of this package are delivered to the CI Portal at the link below where you can find their corresponding download links.
https://cifwk-oss.lmera.ericsson.se/prototype/packages/ERICopenstackdeploy_CXP9033218/

Download the whl file to the server you wish to install it on.

eg

```bash
curl -O https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/releases/com/ericsson/de/ERICopenstackdeploy_CXP9033218/1.0.15/ERICopenstackdeploy_CXP9033218-1.0.15.-py2.py3-none-any.whl
```


## Install Deployer Package
To install the package just run the pip install command below on the downloaded file.

```bash
pip install <downloaded_file>
```

eg

```bash
pip install ERICopenstackdeploy_CXP9033218-1.0.15.-py2.py3-none-any.whl
```


## Verify Deployer Package Installation
Now the package should be installed and accessible from anywhere on the system. Example given below to verify the version of the package that’s installed.

```bash
deployer --version
```


# Using Docker Image as an Alternative
An alternative to installing the OpenStack Deployer package and related prerequisites, is to make use of a docker image with all of these prerequisites already performed. This image is made available on artifactory. The versions of the image will match the version of the Deployer artifact.

The list of available versions can be found at the link below.

https://arm.epk.ericsson.se/artifactory/webapp/#/artifacts/browse/tree/General/docker-v2-global-local/proj_nwci/enmdeployer


## Prerequisites

### Docker
To make use of this docker image, the server must have docker installed.


## Verify Docker Container Works
To make use of the docker image, simply run the docker command below, followed by the arguments you would normally give to the script.

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:<version> <arguments>
```

eg

```bash
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer --version
```

This will pull down and make use of the latest available version of the Deployer image. Just as with any docker run command, you can specify a specific version of the Deployer image to use. The example below specifically requests use of version 1.0.6 of the image

```
docker run --rm armdocker.seli.gic.ericsson.se/proj_nwci/enmdeployer:1.0.6 --version
```
