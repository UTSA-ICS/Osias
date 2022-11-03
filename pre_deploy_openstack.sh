#!/bin/bash

set -euxo pipefail

cd /opt/kolla
source venv/bin/activate

kolla-ansible -i multinode prechecks
kolla-ansible -i multinode pull
