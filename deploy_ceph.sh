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

# Enable swift
source "$HOME"/swift_settings.sh 1

# Enable hyper-converged ceph settings:
# https://docs.ceph.com/en/quincy/cephadm/install/#enabling-osd-memory-autotuning
sudo ceph config set mgr mgr/cephadm/autotune_memory_target_ratio 0.2
sudo ceph config set osd osd_memory_target_autotune true
sudo ceph orch restart osd.all-available-devices
sudo ceph orch restart mgr

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
