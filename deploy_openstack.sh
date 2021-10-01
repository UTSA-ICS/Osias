#!/bin/bash

set -euxo pipefail

cd /opt/kolla
source venv/bin/activate
# Bootstrap server is necessary to fix some docker links, otherwise certain refstack tests will fail.
kolla-ansible -i multinode bootstrap-servers
kolla-ansible -i multinode deploy
kolla-ansible -i multinode post-deploy
deactivate nondestructive

# Install the openstack client
python3 -m pip install -U pip wheel
python3 -m pip install python-openstackclient
