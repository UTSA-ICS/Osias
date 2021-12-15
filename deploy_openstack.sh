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
    kolla-ansible -i multinode bootstrap-servers
fi

kolla-ansible -i multinode deploy
kolla-ansible -i multinode post-deploy
echo "export OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt">> /etc/kolla/admin-openrc.sh
deactivate nondestructive

# Install the openstack client
python3 -m pip install -U pip wheel
python3 -m pip install python-openstackclient
