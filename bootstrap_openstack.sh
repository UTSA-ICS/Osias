#!/bin/bash

set -euo pipefail

cd /opt/kolla
source venv/bin/activate

kolla-genpwd

if [[ -v DOCKER_REGISTRY_PASSWORD ]]; then
  sudo sed -i "s|docker_registry_password: null|docker_registry_password: ${DOCKER_REGISTRY_PASSWORD}|g" /etc/kolla/passwords.yml
fi

kolla-ansible -i multinode certificates

# This bootstrap is necessary to prep for openstack deployment.
kolla-ansible -i multinode bootstrap-servers
