#!/bin/bash

set -euo pipefail

#
# Install Docker
#
sudo apt-get update
sudo apt-get -y install apt-transport-https ca-certificates curl gnupg lsb-release
#
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo   "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
#
sudo apt-get update
sudo apt-get -y install docker-ce docker-ce-cli containerd.io

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

# This bootstrap is necessary to prep for openstack deployment.
kolla-ansible -i multinode bootstrap-servers
