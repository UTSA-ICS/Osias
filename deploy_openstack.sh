#!/bin/bash

set -euxo pipefail

cd /opt/kolla
source venv/bin/activate

echo "Entered globals.yml options:"
echo "############################"
grep "^[^#-]" /etc/kolla/globals.yml
echo "############################"

kolla-ansible deploy -i multinode -vvv
kolla-ansible post-deploy -i multinode -vvv
deactivate nondestructive

# Install the openstack client
python3 -m pip install -U pip wheel
python3 -m pip install python-openstackclient
