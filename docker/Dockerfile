FROM armdocker.seli.gic.ericsson.se/dockerhub-ericsson-remote/centos:8
RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-Linux-* &&\
    sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-Linux-*

ARG VERSION

RUN echo $'[centosrepo]\n\
gpgcheck = 0\n\
enabled = 1\n\
baseurl = http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/\n\
name = CentOS Repository' > /etc/yum.repos.d/centos.repo

RUN dnf -y install git python3 \
 && alternatives --set python /usr/bin/python3 \
 && python -m pip install -U pip \
 && dnf -y install gcc python3-devel openssl-devel openssl libffi-devel genisoimage \
 # Install 7zip and depedencies
 && dnf -y install epel-release && yum -y install p7zip p7zip-plugins \
 # Install the deployer
 && python -m pip install --no-cache-dir --upgrade \
https://arm1s11-eiffel004.eiffel.gic.ericsson.se:8443/nexus/content/repositories/releases/com/ericsson/de/ERICopenstackdeploy_CXP9033218/\
$VERSION/ERICopenstackdeploy_CXP9033218-\
$VERSION.-py2.py3-none-any.whl \
 # Cleanup to reduce image size
 && yum remove -y gcc python3-devel openssl-devel \
 && dnf clean all \
 && mkdir -p /config/ \
 && mkdir -p /artifacts/

ENTRYPOINT ["deployer"]
