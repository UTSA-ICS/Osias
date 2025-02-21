#!/bin/bash

set -euxo pipefail

echo "=== Starting Bridge Setup ==="
DNS_IP="$1"

# Function to check if br0 exists
br0_exists() { ip addr show br0 &>/dev/null; }

if ! br0_exists; then
    echo "br0 does not exist, proceeding with setup..."

    # Install bridge-utils if not installed
    echo "Installing bridge-utils..."
    sudo apt install -y bridge-utils

    netplan_file="/etc/netplan/50-cloud-init.yaml"

    echo "Using netplan file: $netplan_file"
    echo "Contents of netplan file before modification:"
    sudo cat "$netplan_file"

    # Get existing MAC address
    mac_address=$(sudo grep macaddress "$netplan_file" | awk '{print $2}' | head -n 1)
    echo "MAC Address: $mac_address"

    # Get the interface name
    interface_name=$(sudo grep -A 1 ethernets "$netplan_file" | grep -v ethernets | awk '{print $1}')
    interface_name=${interface_name%:}
    echo "Interface Name: $interface_name"

    # Get eth0 IP and routing details
    eth0_ip=$(ip address show dev eth0 | grep 'inet ' | awk '{print $2}')
    eth0_ip0=$(ip route | grep "eth0 proto kernel scope link src" | awk '{print $1}')
    temp=$(echo "$eth0_ip" | awk -F'/' '{print $1}')
    eth0_router=$(ip route | grep "$temp" | grep default | awk '{print $3}')

    echo "eth0 IP: $eth0_ip"
    echo "eth0 Subnet: $eth0_ip0"
    echo "eth0 Router: $eth0_router"

    echo "Checking /etc/hosts:"
    cat /etc/hosts

    echo "Checking /etc/resolv.conf:"
    cat /etc/resolv.conf

    # Backup netplan file
    sudo cp "$netplan_file" /tmp/50-cloud-init.yaml
    echo "Netplan file backed up at /tmp/50-cloud-init.yaml"

    # Create bridge
    echo "Creating bridge br0..."
    sudo brctl addbr br0
    sudo ip link set dev br0 up
    echo "Bridge br0 created and set up."

    # Modify netplan configuration
    sudo chmod 666 /tmp/50-cloud-init.yaml
    echo "Adding bridge configuration to netplan..."

    cat <<EOF | sudo tee -a /tmp/50-cloud-init.yaml
    bridges:
        br0:
            addresses:
                - $eth0_ip
            routes:
                - to: 0.0.0.0/0
                  via: $eth0_router
            interfaces:
                - $interface_name
            macaddress: $mac_address
            mtu: 1500
            parameters:
                forward-delay: 15
                stp: true
            nameservers:
                addresses:
                    - $DNS_IP
                search:
                    - maas
EOF

    # Remove dhcp4: true if present in eth0
    echo "Removing dhcp4: true from netplan..."
    sudo sed -i '/^\s*eth0:/,/^\s*eth1:/ {/dhcp4: true/d}' /tmp/50-cloud-init.yaml

    echo "Pre-netplan generate - netplan file:"
    sudo cat /tmp/50-cloud-init.yaml

    # Apply netplan changes
    echo "Moving netplan configuration..."
    sudo mv /tmp/50-cloud-init.yaml "$netplan_file"
    sudo chmod 600 "$netplan_file"
    sudo chown root:root "$netplan_file"

    sudo netplan generate
    echo "Final netplan file:"
    sudo cat "$netplan_file"
    echo "================================="
    sleep 2
    echo "Applying netplan configuration..."
    sudo netplan apply
    sleep 5

    echo "Applied IP address configuration:"
    ip addr show
fi

echo "=== Setting up rc.local ==="

# Ensure rc.local exists and is configured
sudo tee /etc/rc.local > /dev/null <<EOF
#!/bin/bash

ip a | grep -Eq ': veno1.*state UP' || sudo ip link add veno0 type veth peer name veno1
ip link set veno0 up
ip link set veno1 up
ip link set veno0 master br0

exit 0
EOF

sudo chmod +x /etc/rc.local
sudo chmod 755 /etc/rc.local
sudo chown root:root /etc/rc.local

echo "Running rc.local..."
sudo /etc/rc.local

echo "Reapplying netplan..."
sudo netplan apply
sleep 5

echo "=== Script Completed ==="
