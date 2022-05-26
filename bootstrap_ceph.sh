#!/bin/bash

set -euxo pipefail

MONITOR_IP=$1
CEPH_RELEASE=$2

# Update to fetch the latest package index
sudo apt-get update

# Fetch most recent version of cephadm
curl --silent --remote-name --location https://github.com/ceph/ceph/raw/"$CEPH_RELEASE"/src/cephadm/cephadm
chmod +x cephadm

if [[ $(lsb_release -c | awk '{print $2}') != "jammy" ]]; then
    sudo ./cephadm add-repo --release "$CEPH_RELEASE"
fi

# Update to fetch the package index for ceph added above
sudo apt-get update

# Install ceph-common and cephadm packages
sudo ./cephadm install ceph-common
sudo ./cephadm install

sudo mkdir -p /etc/ceph
sudo ./cephadm bootstrap --mon-ip "$MONITOR_IP"

# Turn on telemetry and accept Community Data License Agreement - Sharing
sudo ceph telemetry on --license sharing-1-0

sudo ceph -v
sudo ceph status
