#!/bin/bash

set -euxo pipefail

NUM_OF_WHOS=$1
sudo ceph orch apply rgw osiasswift --port=7480 --placement="$NUM_OF_WHOS" # Default port results in port conflict and fails.
sudo ceph dashboard set-rgw-api-ssl-verify False
sudo ceph orch apply mgr "$HOSTNAME"
ceph_rgw_pass=$( grep ceph_rgw_keystone_password /etc/kolla/passwords.yml | cut -d':' -f2 | xargs ) # keystone_admin_password
internal_url=$( grep ^kolla_internal_vip_address: /etc/kolla/globals.yml | cut -d':' -f2 | xargs )

# https://docs.ceph.com/en/latest/radosgw/keystone/#integrating-with-openstack-keystone
# https://www.spinics.net/lists/ceph-users/msg64137.html
# The "WHO" field in the "ceph config set" needs to be "client.rgw.default" NOT
# "client.radosgw.gateway". This can be verified by issuing "ceph config dump"
# Additionally, the name of all of the gateways need to be present.

WHO_IS=""
NUM_WHO_IS=$(echo "$WHO_IS" | wc -w)
while [[ "$NUM_WHO_IS" -lt "$NUM_OF_WHOS" ]]
do
    WHO_IS="$(sudo ceph auth ls | grep client.rgw | grep client)" || true
    echo "Waiting..."
    sleep 10
    NUM_WHO_IS=$(echo "$WHO_IS" | wc -w)
done

WHO_IS="client.rgw.default $WHO_IS"
echo "RGW CLIENTS: $WHO_IS"
for WHO in $WHO_IS; do
    sudo ceph config set "$WHO" rgw_keystone_api_version 3
    sudo ceph config set "$WHO" rgw_keystone_url https://"$internal_url":35357
    sudo ceph config set "$WHO" rgw_keystone_accepted_admin_roles "admin, ResellerAdmin"
    sudo ceph config set "$WHO" rgw_keystone_accepted_roles "_member_, member, admin, ResellerAdmin"
    sudo ceph config set "$WHO" rgw_keystone_implicit_tenants true # Implicitly create new users in their own tenant with the same name when authenticating via Keystone. Can be limited to s3 or swift only.
    sudo ceph config set "$WHO" rgw_keystone_admin_user ceph_rgw # admin
    sudo ceph config set "$WHO" rgw_keystone_admin_password "$ceph_rgw_pass" # Got from the passwords.yml
    sudo ceph config set "$WHO" rgw_keystone_admin_project service
    sudo ceph config set "$WHO" rgw_keystone_admin_domain default
    sudo ceph config set "$WHO" rgw_keystone_verify_ssl false
    sudo ceph config set "$WHO" rgw_content_length_compat true
    sudo ceph config set "$WHO" rgw_enable_apis "s3, swift, swift_auth, admin"
    sudo ceph config set "$WHO" rgw_s3_auth_use_keystone true
    sudo ceph config set "$WHO" rgw_enforce_swift_acls true
    sudo ceph config set "$WHO" rgw_swift_account_in_url true
    sudo ceph config set "$WHO" rgw_swift_versioning_enabled true
    sudo ceph config set "$WHO" rgw_verify_ssl true
done


# Redeploy your rgw daemon
sudo ceph orch restart rgw.osiasswift
HOSTNAMES=$(sudo ceph orch host ls | grep -v HOST | awk '{print $1}' | tr '\n' ',')
sudo ceph orch apply mgr "$HOSTNAMES" # Add back-up mgr hosts

STANDBY_MGRS=$(sudo ceph -s | grep -i "standbys" | cut -d':' -f3 | wc -w)
NUM_HOSTNAMES=$(($(echo "$HOSTNAMES" | tr ',' ' ' | wc -w)-1))
while : ; do
    if [[ "$STANDBY_MGRS" -lt "$NUM_HOSTNAMES" ]]; then
        echo "Waiting for MGRS to join - $STANDBY_MGRS of $NUM_HOSTNAMES"
        STANDBY_MGRS=$(sudo ceph -s | grep -i "standbys" | cut -d':' -f3 | wc -w)
    else
        echo "ALL MGRS have joined"
        break
    fi
    sleep 5
done
