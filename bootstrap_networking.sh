#!/bin/bash

set -euxo pipefail

# Add br0 bridge if it does not exist
br0_exists() { ip addr show br0 &>/dev/null; }
if ! br0_exists; then
    netplan_file="50-cloud-init.yaml" # "00-installer-config.yaml"
    # Get the public internet interface name
    interface_name=$(ip route | grep default | awk '{print $5}')
    gateway=$(ip route | grep default | awk '{print $3}')
    ip_addr=$(ip route | grep "${interface_name}" | grep link | awk '{print $NF}')
    subnet_size=$(ip route | grep "${interface_name} "| grep link | awk '{print $1}' | cut -d/ -f2)
    # Get existing MAC address
    mac_address=$(ip link show "${interface_name}" | grep link | awk '{print $2}')
    cat /etc/netplan/${netplan_file}
    cat /etc/hosts
    cat /etc/resolv.conf
    # Copy to work with a temp file
    cp /etc/netplan/${netplan_file} /tmp/${netplan_file}
    # Now modify the temp file to add the bridge information
    echo -ne "    bridges:
      br0:
          dhcp4: true
          interfaces:
              - $interface_name
          macaddress: $mac_address
          addresses:
            - $ip_addr/$subnet_size
          gateway4: $gateway
" >>/tmp/${netplan_file}

    # Delete gateway from original interface
    sed -i "0,/$gateway/{//d}" /tmp/${netplan_file}
    # Delete ip address and 'address:' line above from original interface
    line=$(grep -n -m 1 "$ip_addr" /tmp/50-cloud-init.yaml |sed  's/\([0-9]*\).*/\1/')
    n="$((line-1))"
    sed -i.bak -e "${n}d;${line}d" /tmp/50-cloud-init.yaml
    # Now copy over the modified file in the netplan directory
    sudo mv /tmp/${netplan_file} /etc/netplan/${netplan_file}
    # Activate the updated netplan configuration
    sudo netplan generate
    sleep 2
    sudo netplan apply
    sleep 5

    # Check the final result
    ip addr
    cat /etc/netplan/${netplan_file}
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
