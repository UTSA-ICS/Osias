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
# Copy certificates so Kolla will copy them over and trust them.
sudo cp /etc/kolla/certificates/ca/root.crt /usr/local/share/ca-certificates/kolla-root.crt
sudo update-ca-certificates

# This bootstrap is necessary to prep for openstack deployment.
kolla-ansible -i multinode bootstrap-servers
