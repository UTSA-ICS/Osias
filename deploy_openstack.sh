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
    kolla-ansible -i -vvvv multinode bootstrap-servers
fi

echo "Entered globals.yml options:"
echo "############################"
grep "^[^#-]" /etc/kolla/globals.yml
echo "############################"

kolla-ansible -i multinode -vvvv deploy
kolla-ansible -i multinode -vvvv post-deploy
deactivate nondestructive

# Install the openstack client
python3 -m pip install -U pip wheel
python3 -m pip install python-openstackclient
