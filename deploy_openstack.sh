#!/bin/bash

set -euxo pipefail

cd /opt/kolla
source venv/bin/activate

OPENSTACK_RELEASE="$1"
if [[ "$OPENSTACK_RELEASE" == "ussuri" ]]; then
    # Bootstrap server is necessary to fix some docker links,
    # otherwise certain refstack tests will fail.
    # This seems like a bug in ussuri as it is not needed
    # in the subsequent victoria release.
    kolla-ansible bootstrap-servers -i multinode -vvv
fi

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
