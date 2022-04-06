#!/bin/bash

set -euxo pipefail

sudo ceph orch host ls
sudo ceph orch device ls --refresh
sudo ceph orch apply osd --all-available-devices

# Create pool for Cinder
sudo ceph osd pool create volumes
sudo rbd pool init volumes

# Create pool for Cinder Backup
sudo ceph osd pool create backups
sudo rbd pool init backups

# Create pool for Glance
sudo ceph osd pool create images
sudo rbd pool init images

# Create pool for Nova
sudo ceph osd pool create vms
sudo rbd pool init vms

# Create pool for Gnocchi
#sudo ceph osd pool create metrics
#sudo rbd pool init metrics

# Get Swift ready
sudo ceph orch apply rgw osiasswift # --port=6780 # Default port results in port conflict and fails.
sudo ceph dashboard set-rgw-api-ssl-verify False 
ceph_rgw_pass=$( grep ceph_rgw_keystone_password /etc/kolla/passwords.yml | cut -d':' -f2 | xargs ) # keystone_admin_password
internal_url=$( grep ^kolla_internal_vip_address: /etc/kolla/globals.yml | cut -d':' -f2 | xargs )

# https://docs.ceph.com/en/latest/radosgw/keystone/#integrating-with-openstack-keystone
sudo ceph config set client.radosgw.gateway rgw_keystone_api_version 3
sudo ceph config set client.radosgw.gateway rgw_keystone_url https://"$internal_url":35357
# sudo ceph config set client.radosgw.gateway rgw_keystone_admin_token {keystone_admin_token}
# sudo ceph config set client.radosgw.gateway rgw_keystone_admin_token_path {path_to_keystone_admin_token}_#preferred
# sudo ceph config set client.radosgw.gateway rgw_keystone_token_cache_size {number_of_tokens_to_cache}
sudo ceph config set client.radosgw.gateway rgw_keystone_admin_tenant service # {keystone service tenant name}
sudo ceph config set client.radosgw.gateway rgw_keystone_accepted_roles admin,_member_,member
sudo ceph config set client.radosgw.gateway rgw_keystone_implicit_tenants true # Implicitly create new users in their own tenant with the same name when authenticating via Keystone. Can be limited to s3 or swift only.
sudo ceph config set client.radosgw.gateway rgw_keystone_admin_user ceph_rgw # admin
sudo ceph config set client.radosgw.gateway rgw_keystone_admin_password "$ceph_rgw_pass" # Got from the passwords.yml
sudo ceph config set client.radosgw.gateway rgw_keystone_admin_project service
sudo ceph config set client.radosgw.gateway rgw_keystone_admin_domain default
sudo ceph config set client.radosgw.gateway rgw_swift_account_in_url true
sudo ceph config set client.radosgw.gateway rgw_keystone_verify_ssl false
sudo ceph config set client.radosgw.gateway rgw_content_length_compat true
sudo ceph config set client.radosgw.gateway rgw_enable_apis "swift, s3, admin"
sudo ceph config set client.radosgw.gateway rgw_keystone_accepted_admin_roles admin
sudo ceph config set client.radosgw.gateway rgw_s3_auth_use_keystone true
sudo ceph config set client.radosgw.gateway rgw_swift_versioning_enabled true

# Redeploy your rgw daemon
sudo ceph orch apply rgw osiasswift # --port=6780
sudo ceph orch apply mgr "$HOSTNAME" # Sometimes active manager is removed, this resets it.

# Get cinder and cinder-backup ready
sudo mkdir -p /etc/kolla/config/cinder/cinder-backup
sudo chown -R ubuntu:ubuntu /etc/kolla/config/
sudo cp /etc/ceph/ceph.conf /etc/kolla/config/cinder/cinder-backup/ceph.conf
sudo ceph auth get-or-create client.cinder-backup mon 'profile rbd' osd 'profile rbd pool=backups' mgr 'profile rbd pool=backups' > /etc/kolla/config/cinder/cinder-backup/ceph.client.cinder-backup.keyring
sudo ceph auth get-or-create client.cinder mon 'profile rbd' osd 'profile rbd pool=volumes, profile rbd pool=vms, profile rbd pool=images' mgr 'profile rbd pool=volumes, profile rbd pool=vms, profile rbd pool=images' > /etc/kolla/config/cinder/cinder-backup/ceph.client.cinder.keyring
sudo sed -i $'s/\t//g' /etc/kolla/config/cinder/cinder-backup/ceph.conf
sudo sed -i $'s/\t//g' /etc/kolla/config/cinder/cinder-backup/ceph.client.cinder.keyring
sudo sed -i $'s/\t//g' /etc/kolla/config/cinder/cinder-backup/ceph.client.cinder-backup.keyring

# Get cinder-volume ready
sudo mkdir -p /etc/kolla/config/cinder/cinder-volume
sudo chown -R ubuntu:ubuntu /etc/kolla/config/
sudo cp /etc/ceph/ceph.conf /etc/kolla/config/cinder/cinder-volume/ceph.conf
sudo ceph auth get-or-create client.cinder > /etc/kolla/config/cinder/cinder-volume/ceph.client.cinder.keyring
sudo sed -i $'s/\t//g' /etc/kolla/config/cinder/cinder-volume/ceph.conf
sudo sed -i $'s/\t//g' /etc/kolla/config/cinder/cinder-volume/ceph.client.cinder.keyring

# Get glance ready
sudo mkdir -p /etc/kolla/config/glance
sudo chown -R ubuntu:ubuntu /etc/kolla/config/
sudo cp /etc/ceph/ceph.conf /etc/kolla/config/glance/ceph.conf
sudo ceph auth get-or-create client.glance mon 'profile rbd' osd 'profile rbd pool=volumes, profile rbd pool=images' mgr 'profile rbd pool=volumes, profile rbd pool=images' > /etc/kolla/config/glance/ceph.client.glance.keyring
sudo sed -i $'s/\t//g' /etc/kolla/config/glance/ceph.conf
sudo sed -i $'s/\t//g' /etc/kolla/config/glance/ceph.client.glance.keyring

# Get nova ready
sudo mkdir -p /etc/kolla/config/nova
sudo chown -R ubuntu:ubuntu /etc/kolla/config/
sudo cp /etc/ceph/ceph.conf /etc/kolla/config/nova/ceph.conf
sudo ceph auth get-or-create client.cinder > /etc/kolla/config/nova/ceph.client.cinder.keyring
sudo sed -i $'s/\t//g' /etc/kolla/config/nova/ceph.conf
sudo sed -i $'s/\t//g' /etc/kolla/config/nova/ceph.client.cinder.keyring

# Get Gnocchi ready
#sudo mkdir -p  /etc/kolla/config/gnocchi
#sudo chown -R ubuntu:ubuntu /etc/kolla/config/
#sudo cp /etc/ceph/ceph.conf /etc/kolla/config/gnocchi/ceph.conf
#sudo ceph auth get-or-create client.gnocchi mon 'profile rbd' osd 'profile rbd pool=metrics' mgr 'profile rbd pool=metrics' > /etc/kolla/config/gnocchi/ceph.client.gnocchi.keyring
#sudo sed -i $'s/\t//g' /etc/kolla/config/gnocchi/ceph.conf
#sudo sed -i $'s/\t//g' /etc/kolla/config/gnocchi/ceph.client.gnocchi.keyring

# Verify all permissions are correct.
sudo chown -R ubuntu:ubuntu /etc/kolla/config/
