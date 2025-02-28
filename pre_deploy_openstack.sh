#!/bin/bash

set -euxo pipefail

cd /opt/kolla
source venv/bin/activate

kolla-ansible prechecks -i multinode
kolla-ansible pull -i multinode
