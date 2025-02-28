#!/bin/bash

set -euo pipefail

network_interface_ip=$1

if [ $# -ge 2 ] && [ -n "$2" ]; then
    DOCKER_REGISTRY_PASSWORD=$2
else
    echo "No Docker Password Supplied"
fi

cd /opt/kolla
source venv/bin/activate

kolla-genpwd

if [[ -v DOCKER_REGISTRY_PASSWORD ]]; then
    sudo sed -i "s|docker_registry_password: null|docker_registry_password: ${DOCKER_REGISTRY_PASSWORD}|g" /etc/kolla/passwords.yml
fi

base_ip=$(echo "$network_interface_ip" | cut -d"." -f1-3)
network_interface=$(ip a | grep "$base_ip" |  awk '{print $NF}')
sudo sed -i "s|NETWORK_INTERFACE|${network_interface}|g" /etc/kolla/globals.yml

kolla-ansible certificates -i multinode -vvv

# Necessary for Yoga onwards.
kolla-ansible install-deps || true

# This bootstrap is necessary to prep for openstack deployment.
kolla-ansible bootstrap-servers -i multinode -vvv