#!/bin/bash

set -x

function_name=$1

function cleanup_master() {
    # Destroy openstack and delete images
    if [ -d "/opt/kolla" ]; then
        cd /opt/kolla || exi
        python3 -m venv venv
        source venv/bin/activate
        kolla-ansible -i multinode destroy --yes-i-really-really-mean-it --include-images
        deactivate
        sudo pip3 uninstall -qy python-openstackclient
    fi
    # Cleanup refstack
    cd ~ || exit
    sudo rm -fr refstack-client

    # Cleanup kolla and ansible directories
    sudo rm -fr /etc/kolla /etc/ansible /opt/kolla

    # disable automatic creation of OSD on available devices
    if [[ !  $(sudo ceph -s) ]]; then
        echo "Ceph not installed"
        exit 0
    fi

    sudo ceph orch apply osd --all-available-devices --unmanaged=true
    # Now remove all of the OSDs
    osds=$(sudo ceph osd ls)
    for osd in $osds
    do
        sudo ceph orch osd rm "$osd" --force
    done
    # Get all the available hosts
    hosts=$(sudo ceph orch host ls |awk '{print $1}' |grep -v HOST)
    # Cycle through the hosts, stop the osd service
    for host in $hosts
    do
        osd_services=()
        while IFS='' read -r line; do osd_services+=("$line"); done < <(ssh -o StrictHostKeyChecking=no "$host" systemctl |grep ceph |grep osd |awk '{print $1}')
        for osd_service in "${osd_services[@]}"
        do
            #osd_service=$(ssh -o StrictHostKeyChecking=no "$host" systemctl |grep ceph |grep osd |awk '{print $1}')
            ssh -o StrictHostKeyChecking=no "$host" sudo systemctl stop "$osd_service"
            sleep 1
            ssh -o StrictHostKeyChecking=no "$host" sudo systemctl disable "$osd_service"
            ssh -o StrictHostKeyChecking=no "$host" sudo systemctl daemon-reload
        done
    done
    # Sleep for 30 seconds to ensure that all osd's are removed.
    sleep 30
    # Cycle through the hosts, and zap the osd device
    for host in $hosts
    do
        host_device=$(ssh -o StrictHostKeyChecking=no "$host" lsblk |grep disk |tail -1 |awk '{print $1}')
        sudo ceph orch device zap --force "$host" /dev/"$host_device"
    done

    # Get all the fsids
    fsids=$(sudo cephadm ls |grep fsid |cut -d"\"" -f 4|uniq)

    # Remove ceph cluster & destroy ceph partition
    for id in $fsids;do sudo ./cephadm rm-cluster --force --fsid "$id";done
    sudo rm -fr /etc/ceph
}

function cleanup_nodes() {
    # This will remove: all stopped containers, all networks not used by at least one container,
    # all volumes not used by at least one container, all dangling images, all build cache
    sudo docker rm -f "$(sudo docker ps -aq)"
    sudo docker system prune --volumes --force -a

    # Cleanup up ssh know hosts
    rm -f ~/.ssh/known_hosts

    # Cleanup kolla dirs
    sudo rm -fr /etc/kolla /opt/kolla

    # Remove the docker package
    sudo rm -fr /etc/apt/sources.list.d/docker.list
}

function cleanup_storage_nodes() {
    # ceph services cleanup
    ceph_services=$(sudo systemctl |grep ceph |grep "\.service" |awk '{print $1}')
    for ceph_service in $ceph_services
    do
        sudo systemctl stop "$ceph_service"
        sleep 1
        sudo systemctl disable "$ceph_service"
    done

    sudo rm -fr /etc/systemd/system/ceph*
    sudo rm -fr /etc/systemd/system/*/ceph*
    sudo rm -fr /lib/systemd/system/ceph*

    sudo systemctl daemon-reload
    sudo systemctl reset-failed

    array=()
    while IFS='' read -r line; do array+=("$line"); done < <(lsblk -dp | grep -o '^/dev[^ ]*')
    new_array=()
    working_dir=$(df | grep '^/' | awk '{print $1}')
    for value in "${array[@]}"
    do
        [[ $working_dir =~ $value ]] || new_array+=("$value")
    done
    array=("${new_array[@]}")
    unset new_array

    for device in "${array[@]}"
    do
        echo "INFO: Working working on device [$device]"
        sudo umount "$device"
        sudo sgdisk --zap-all -- "$device"
        sudo partprobe || true
        sudo wipefs -af "$device"
    done

    # remove all logical devices that use the /dev/mapper driver
    sudo dmsetup remove_all

    # Remove the ceph package
    sudo rm -fr /etc/apt/sources.list.d/ceph.list
}

$function_name
