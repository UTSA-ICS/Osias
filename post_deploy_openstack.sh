#!/bin/bash

# shellcheck source=/dev/null
source "$HOME"/base_config.sh

PUBLICIP=$(/sbin/ip addr show br0 | grep 'inet ' | grep brd | awk '{print $2}')
PUBLIC_NETWORK="${PUBLICIP%.*}.0/24"

if [ $# -ge 1 ] && [ -n "$1" ]; then
  DNS_IP=$1
else
  echo "ERROR: No DNS Entry supplied!!!"
  exit 1
fi

if [ $# == 3 ]; then
  POOL_START=$2
  POOL_END=$3
fi

POOL_GATEWAY="${PUBLICIP%.*}.253"

sudo chown "$USER":"$USER" /etc/kolla/admin-openrc.sh
echo "export OS_CACERT=/etc/kolla/certificates/ca/root.crt" >> /etc/kolla/admin-openrc.sh
source /etc/kolla/admin-openrc.sh

openstack flavor create --id 1 --vcpus 1 --ram 2048 --disk 20 gp1.small
openstack flavor create --id 2 --vcpus 2 --ram 4096 --disk 20 gp1.medium
openstack flavor create --id 3 --vcpus 4 --ram 9216 --disk 20 gp1.large
openstack flavor create --id 4 --vcpus 1 --ram 1024 --disk 20 cb1.small
openstack flavor create --id 5 --vcpus 2 --ram 2048 --disk 20 cb1.medium
openstack flavor create --id 6 --vcpus 4 --ram 4096 --disk 20 cb1.large
openstack flavor create --id 7 --vcpus 1 --ram 3072 --disk 20 mb1.small
openstack flavor create --id 8 --vcpus 2 --ram 6144 --disk 20 mb1.medium
openstack flavor create --id 9 --vcpus 4 --ram 12288 --disk 20 mb1.large
openstack flavor create --id 11 --vcpus 1 --ram 2048 --disk 40 gp2.small
openstack flavor create --id 12 --vcpus 2 --ram 4096 --disk 40 gp2.medium
openstack flavor create --id 13 --vcpus 4 --ram 9216 --disk 40 gp2.large
openstack flavor create --id 14 --vcpus 1 --ram 1024 --disk 40 cb2.small
openstack flavor create --id 15 --vcpus 2 --ram 2048 --disk 40 cb2.medium
openstack flavor create --id 16 --vcpus 4 --ram 4096 --disk 40 cb2.large
openstack flavor create --id 17 --vcpus 1 --ram 3072 --disk 40 mb2.small
openstack flavor create --id 18 --vcpus 2 --ram 6144 --disk 40 mb2.medium
openstack flavor create --id 19 --vcpus 4 --ram 12288 --disk 40 mb2.large

TENANT=$(openstack project list -f value -c ID --user admin)
openstack network create --share --project "${TENANT}" --external --provider-network-type flat --provider-physical-network physnet1 public
if [ $# == 3 ]; then
  openstack subnet create --project "${TENANT}" --subnet-range "${PUBLIC_NETWORK}" --allocation-pool start="${POOL_START}",end="${POOL_END}" --dns-nameserver "${DNS_IP}" --gateway "${POOL_GATEWAY}" --network public public_subnet
else
  PUBLIC_NETWORK="192.168.1.0/24"
  openstack subnet create --project "${TENANT}" --subnet-range "${PUBLIC_NETWORK}" --dns-nameserver "${DNS_IP}" --network public public_subnet
fi
openstack network create --project "${TENANT}" private
openstack subnet create --project "${TENANT}" --subnet-range 192.168.100.0/24 --dns-nameserver "${DNS_IP}" --network private private_subnet
openstack router create --enable --project "${TENANT}" pub-router
openstack router set pub-router --external-gateway public
openstack router add subnet pub-router private_subnet
