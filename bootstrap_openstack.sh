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

# This bootstrap is necessary to prep for openstack deployment.
kolla-ansible -i multinode bootstrap-servers

DockerServicePath=$(systemctl status docker | grep Loaded | tr ";" " " | awk '{print $3}' | cut -c2-)
IP_addr=$(hostname -I | tr " " " " | awk '{print $3}')
sudo sed -i "/^ExecStart=/ s/$/ -H tcp:\/\/$IP_addr:2375 -H unix:\/\/\/var\/run\/docker.sock --cluster-store=etcd:\/\/$IP_addr:2379 --cluster-advertise=$IP_addr:2375/" "$DockerServicePath"
sudo systemctl daemon-reload
sudo systemctl restart docker.service
grep ExecStart "$DockerServicePath"

# This bootstrap is necessary to prep for kuryr
kolla-ansible -i multinode bootstrap-servers
