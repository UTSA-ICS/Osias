#!/bin/bash

set -euxo pipefail

# Add br0 bridge if it does not exist
br0_exists() { ip addr show br0 &>/dev/null; }
if ! br0_exists; then
    sudo apt install -y bridge-utils
    netplan_file="50-cloud-init.yaml" # "00-installer-config.yaml"
    # Get existing MAC address
    mac_address=$(sudo grep macaddress /etc/netplan/${netplan_file} | awk '{print $2}' | head -n 1)
    # Get the interface name (remove the ":" from the name)
    interface_name=$(sudo grep -A 1 ethernets /etc/netplan/${netplan_file} | grep -v ethernets | awk '{print $1}')
    interface_name=${interface_name%:}
    eth0_ip=$(ip address show dev eth0 | grep 'inet ' | awk '{print $2}')
    eth0_ip0=$(ip route | grep "eth0 proto kernel scope link src" | awk '{print $1}')
    temp=$(echo "$eth0_ip"  | awk -F'/' '{print $1}')
    eth0_router=$(ip route | grep "$temp" | grep default | awk '{print $3}')
    sudo cat /etc/netplan/${netplan_file}
    cat /etc/hosts
    cat /etc/resolv.conf
    # Copy to work with a temp file
    sudo cp /etc/netplan/${netplan_file} /tmp/${netplan_file}
        # Now modify the temp file to add the bridge information
    sudo brctl addbr br0
    sudo ip link set dev br0 up
    sudo chmod 666 /tmp/${netplan_file}
    echo -ne "  bridges:
      br0:
          addresses:
              - $eth0_ip
          routes:
            -   metric: 0
                to: $eth0_ip0
                via: $eth0_router
          interfaces:
              - $interface_name
          macaddress: $mac_address
" >>/tmp/${netplan_file}
    # remove dhcp4: true line if present in eth0
    sudo sed -i '/^\s*eth0:/,/^\s*eth1:/ {/dhcp4: true/d}' /tmp/${netplan_file}

    # Now copy over the modified file in the netplan directory
    sudo mv /tmp/${netplan_file} /etc/netplan/${netplan_file}
    sudo chmod 600 /etc/netplan/${netplan_file}
    sudo chown root:root /etc/netplan/${netplan_file}
    # Activate the updated netplan configuration
    sudo netplan generate
    sleep 2
    sudo chmod 600 /etc/netplan/${netplan_file}
    sudo netplan apply
    sleep 5

    # Check the final result
    ip addr
    sudo cat /etc/netplan/${netplan_file}
fi

sudo sh -c "cat > /etc/rc.local <<__EOF__
#!/bin/sh -e

ip a | grep -Eq ': veno1.*state UP' || sudo ip link add veno0 type veth peer name veno1
ip link set veno0 up
ip link set veno1 up
ip link set veno0 master br0
exit 0
__EOF__"

sudo chmod +x /etc/rc.local
sudo chmod 755 /etc/rc.local
sudo chown root:root /etc/rc.local
sudo /etc/rc.local

sudo netplan apply
sleep 5
