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

# https://support.huaweicloud.com/intl/en-us/tngg-kunpengsdss/kunpengsdss-tngg.pdf
# Set global settings
sudo ceph config set global osd_pool_default_min_size 1  # Allow writing one copy in a degraded state, Default: 0

# Optimizing Compression Algorithm
sudo ceph config set global bluestore_min_alloc_size_hdd 8192 # Change the value to 8KB to reduce the size of the compressed data and ensure the compression ratio, Default value: 32768


# Set OSD settings
OSD_WHO_IS="$(sudo ceph auth ls | grep 'osd.[0-9]')" || true
echo "OSD Clients: $OSD_WHO_IS"
for OSD in $OSD_WHO_IS; do
    sudo ceph config set "$OSD" osd_max_write_size 512  # Maximum size (in MB) of data that can be written by an OSD at a time, Default: 90
    sudo ceph config set "$OSD" osd_recovery_max_active 10  # Number of active restoration requests in the same period, Default: 3 for HDD, 10 for SSD
    sudo ceph config set "$OSD" osd_max_backfills 4  # Maximum number of backfills allowed by an OSD, Default: 1
    sudo ceph config set "$OSD" osd_map_cache_size 1024  # Size of the cache (in MB) that stores the OSD map, Default: 50
    sudo ceph config set "$OSD" osd_recovery_op_priority 2  # Restoration priority. The value ranges from 1 to 63. A larger value indicates higher resource usage, Default: 3
done

# Set client settings
sudo ceph config set global rbd_cache_writethrough_until_flush False
# Default: True
# This parameter is used for compatibility with the virtio driver earlier than linux-2.6.32. 
# It prevents the situation that data is written back when no flush request is sent. 
# After this parameter is set, librbd processes I/Os in writethrough mode. 
# The mode is switched to writeback only after the first flush request is received.

# Enable swift
source "$HOME"/swift_settings.sh 1

sudo ceph config set mgr mgr/cephadm/config_checks_enabled true # Enable additional configuration checks.

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
sudo ceph status

# Restart all services.
services="$(sudo ceph orch ls | grep ago | awk '{print $1}')"
for service in $services; do
  sudo ceph orch restart "$service"
done
sudo ceph crash archive-all  # Clear all health warnings.
