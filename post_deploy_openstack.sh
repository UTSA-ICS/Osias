#!/bin/bash

# shellcheck source=/dev/null
source "$HOME"/base_config.sh

PUBLICIP=$(/sbin/ip addr show br0 | grep 'inet ' | grep brd | awk '{print $2}')
PUBLIC_NETWORK="${PUBLICIP%.*}.0/24"
PUBLIC_GATEWAY=$(/sbin/ip route | grep default | awk '{print $3}')

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

sudo chown "$USER":"$USER" /etc/kolla/admin-openrc.sh
echo "export OS_CACERT=/etc/kolla/certificates/ca/root.crt" >> /etc/kolla/admin-openrc.sh
source /etc/kolla/admin-openrc.sh

# Create public endpoint openrc file for access outside of server.
sudo touch /etc/kolla/admin-public-openrc.sh
sudo chown "$USER":"$USER" /etc/kolla/admin-public-openrc.sh
ENDPOINT=$(openstack endpoint list --service identity --interface public -c URL -f value)
grep -vwE "(OS_INTERFACE|OS_AUTH_URL|OS_ENDPOINT_TYPE|OS_CACERT)" /etc/kolla/admin-openrc.sh > /etc/kolla/admin-public-openrc.sh
{
echo "export OS_AUTH_URL=$ENDPOINT"
echo "export OS_INTERFACE=public"
echo "export OS_ENDPOINT_TYPE=publicURL"
echo "export OS_CACERT=root.crt"
} >> /etc/kolla/admin-public-openrc.sh

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
  openstack subnet create --project "${TENANT}" --subnet-range "${PUBLIC_NETWORK}" --allocation-pool start="${POOL_START}",end="${POOL_END}" --dns-nameserver "${DNS_IP}" --gateway "${PUBLIC_GATEWAY}" --network public public_subnet
else
  PUBLIC_NETWORK="192.168.1.0/24"
  openstack subnet create --project "${TENANT}" --subnet-range "${PUBLIC_NETWORK}" --dns-nameserver "${DNS_IP}" --network public public_subnet
fi
openstack network create --project "${TENANT}" private
openstack subnet create --project "${TENANT}" --subnet-range 192.168.100.0/24 --dns-nameserver "${DNS_IP}" --network private private_subnet
openstack router create --enable --project "${TENANT}" pub-router
openstack router set pub-router --external-gateway public
openstack router add subnet pub-router private_subnet

SERVICE_LIST="$(openstack service list)"

# check_service iterates through the services, finds the swift service url, checks if it is formatted correctly, if not, it will update it appropriately.
check_service() {
    service="$1"
    shift
    string="$*"
    if [ -z "${string##*"$service"*}" ] && [ "$service" == "swift" ] ;then
      openstack endpoint list -c URL -c ID -f value --service "$service" | while IFS=', ' read -r -a line
      do 
        if [[ ${line[1]} != */swift/v1/* ]] ;then    
          echo "Updating swift endpoints to include 'http.../swift/v1/...'' instead of 'http.../v1/...'"
          url="${line[1]//v1/swift\/v1}"
          openstack endpoint set --url "${url}" "${line[0]}"
        else
          echo "URL < ${line[1]} > is already correct"; 
        fi
      done
    else
      echo "Service not found."
    fi
}

check_service "swift" "$SERVICE_LIST"
