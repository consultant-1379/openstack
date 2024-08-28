FROM armdocker.seli.gic.ericsson.se/dockerhub-ericsson-remote/centos:8.4.2105
RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-Linux-* &&\
    sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-Linux-*

# Get git and any version of pip installed as a starting point for the rest
RUN echo $'[centosrepo]\n\
gpgcheck = 0\n\
enabled = 1\n\
baseurl = http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/\n\
name = CentOS Repository' > /etc/yum.repos.d/centos.repo

RUN dnf -y install git python3 \
 && alternatives --set python /usr/bin/python3 \
 && python -m pip install -U pip \
 && mkdir -p /artifacts/ && mkdir -p /config/ \
 && dnf -y install gcc python3-devel openssl-devel openssl libffi-devel genisoimage \
 && dnf -y install epel-release && yum -y install p7zip p7zip-plugins

# Install the packages that are required for testing. They in turn bring in their dependencies.
COPY testsuite/setup.py /setup/
RUN python -m pip install /setup/
