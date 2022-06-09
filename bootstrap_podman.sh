#!/bin/bash

set -euxo pipefail

# Update to fetch the latest package index
sudo apt-get update

source /etc/os-release
# Install podman
echo "deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
curl -L https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_"${VERSION_ID}"/Release.key | sudo apt-key add -

# Update to fetch the package index for ceph added above
sudo apt-get update
sudo apt-get -qqy install podman
podman --version
