#!/bin/bash

set -euxo pipefail

MONITOR_IP=$1
CEPH_RELEASE=$2
CLUSTER_NETWORK="${3:-''}"
echo "$CLUSTER_NETWORK"
# Update to fetch the latest package index
sudo apt-get update

# Fetch most recent version of cephadm
curl --silent --remote-name --location https://github.com/ceph/ceph/raw/"$CEPH_RELEASE"/src/cephadm/cephadm
chmod +x cephadm

sudo ./cephadm add-repo --release "$CEPH_RELEASE"

# Update to fetch the package index for ceph added above
sudo apt-get update

# Install ceph-common and cephadm packages
sudo ./cephadm install ceph-common
sudo ./cephadm install

sudo mkdir -p /etc/ceph

if [ $# == 3 ]; then
  sudo ./cephadm bootstrap --mon-ip "$MONITOR_IP" # --cluster-network "$CLUSTER_NETWORK"
else
  sudo ./cephadm bootstrap --mon-ip "$MONITOR_IP"
fi

# Turn on telemetry and accept Community Data License Agreement - Sharing
sudo ceph telemetry on --license sharing-1-0
sudo ceph telemetry enable channel perf

sudo ceph -v
sudo ceph status
