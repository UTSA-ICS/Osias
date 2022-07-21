#!/bin/bash

set -x

OPENSTACK_RELEASE="$1"
MY_IP="$2"

! read -r -d '' MULTINODE << EOM
[control]
    [control.0]
    public = "$MY_IP"
    private = "$MY_IP"
    data = ""
[network]
    [network.0]
    public = "$MY_IP"
    private = "$MY_IP"
    data = ""
[storage]
    [storage.0]
    public = "$MY_IP"
    private = "$MY_IP"
    data = ""
[compute]
    [compute.0]
    public = "$MY_IP"
    private = "$MY_IP"
    data = ""
[monitor]
    [monitor.0]
    public = ""
    private = ""
    data = ""
[variables]
    [variables.0]
    CEPH = "False"
    VM_DEPLOYMENT_CIDR = "${MY_IP}/32"
    VIP_ADDRESS = "${MY_IP}"
    VIP_IP = "${MY_IP}"
    POOL_START_IP = "${MY_IP}"
    POOL_END_IP = "${MY_IP}"
    DNS_IP = "8.8.8.8"
    OPENSTACK_RELEASE = "$OPENSTACK_RELEASE"
EOM

#
# Create and configure ubuntu user if it does not exist
#
user_exists(){ id "$1" &>/dev/null; }
if ! user_exists "ubuntu"; then
  # Create ssh keys
  ssh-keygen -t rsa -f "$HOME"/.ssh/id_rsa -C "All in one key" -N ""
  cat "$HOME"/.ssh/id_rsa.pub > "$HOME"/.ssh/authorized_keys
  # Add the ubuntu user which will be used by the deployment scripts
  sudo useradd -m -U -c "Ubuntu User" -s "/bin/bash" ubuntu
  # Create ssh keys to allow login
  sudo cp -Rp "$HOME"/.ssh /home/ubuntu/
  sudo chown -R ubuntu.ubuntu /home/ubuntu/.ssh
  # Now enable passwordless sudo for ubuntu
  echo "ubuntu ALL=(ALL) NOPASSWD: ALL" > ubuntu
  sudo cp ubuntu /etc/sudoers.d/.
fi

#
# Deploy openstack using kolla
#
pip3 install toml timeout_decorator
python3 -u deploy.py bootstrap_networking --config "$MULTINODE"
python3 -u deploy.py bootstrap_openstack --config "$MULTINODE"
python3 -u deploy.py pre_deploy_openstack --config "$MULTINODE"
python3 -u deploy.py deploy_openstack --config "$MULTINODE"
python3 -u deploy.py post_deploy_openstack --config "$MULTINODE"
python3 -u deploy.py test_setup --config "$MULTINODE"
python3 -u deploy.py test_refstack --config "$MULTINODE"
