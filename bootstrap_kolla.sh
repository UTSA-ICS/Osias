#!/bin/bash

set -euxo pipefail

OPENSTACK_RELEASE=$1
ANSIBLE_MAX_VERSION=$2

# Dependencies
sudo apt-get update
sudo apt-get -qqy install python3-dev libffi-dev gcc libssl-dev python3-pip python3-venv

# basedir and venv
sudo mkdir -p /opt/kolla
sudo chown "$USER":"$USER" /opt/kolla
cd /opt/kolla
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -U pip wheel
# Update requirements file
sed -i s/OPENSTACK_RELEASE/"${OPENSTACK_RELEASE}"/ "$HOME"/requirements.txt
sed -i s/ANSIBLE_MAX_VERSION/"${ANSIBLE_MAX_VERSION}"/ "$HOME"/requirements.txt
python3 -m pip install -r "$HOME"/requirements.txt

# General Ansible config
sudo mkdir -p /etc/ansible
sudo chown "$USER":"$USER" /etc/ansible
cat > /etc/ansible/ansible.cfg <<__EOF__
[defaults]
host_key_checking=False
pipelining=True
forks=100
interpreter_python=/usr/bin/python3
__EOF__

# Configure kolla
sudo mkdir -p /etc/kolla
sudo chown "$USER":"$USER" /etc/kolla
cp -r /opt/kolla/venv/share/kolla-ansible/etc_examples/kolla/* /etc/kolla || true
cp /opt/kolla/venv/share/kolla-ansible/ansible/inventory/* . || true

# Add nova config path
mkdir -p /etc/kolla/config/
cat > /etc/kolla/config/nova.conf <<__EOF__
[DEFAULT]
cpu_allocation_ratio = 16.0
ram_allocation_ratio = 1.5
reserved_host_memory_mb = 10240
allow_resize_to_same_host=True
scheduler_default_filters=AllHostsFilter
__EOF__
