#!/bin/bash

set -euo pipefail

if [ $# -ge 1 ] && [ -n "$1" ]; then
  DOCKER_REGISTRY_PASSWORD=$1
else
  echo "No Docker Password Supplied"
fi

cd /opt/kolla
source venv/bin/activate

kolla-genpwd

if [[ -v DOCKER_REGISTRY_PASSWORD ]]; then
  sudo sed -i "s|docker_registry_password: null|docker_registry_password: ${DOCKER_REGISTRY_PASSWORD}|g" /etc/kolla/passwords.yml
fi

kolla-ansible -i multinode certificates

# Necessary for Yoga onwards.
kolla-ansible install-deps || true 

# This bootstrap is necessary to prep for openstack deployment.
kolla-ansible -i multinode bootstrap-servers
