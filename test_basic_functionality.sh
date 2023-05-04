#!/bin/bash

set -uo pipefail

# shellcheck source=/dev/null

if [ -f "/etc/kolla/admin-public-openrc.sh" ]; then
    source /etc/kolla/admin-public-openrc.sh
    echo "admin-public-openrc.sh found"
elif [ -f "admin-public-openrc.sh" ]; then
    source admin-public-openrc.sh
    echo "admin-public-openrc.sh found"
else
    echo "No openrc files found"
    exit 1
fi

if python3 -c 'import pkgutil; exit(not pkgutil.find_loader("openstackclient"))'; then
    echo 'Openstack client found'
else
    echo "Openstack client not found"
    pip3 install python-openstackclient
fi

pip3 install importlib-metadata==4.13.0 # Fix AttributeError: 'EntryPoints' object has no attribute 'items' from 5.0.0 upgrade.

FIRST_NAME="John"
LAST_NAME="Doe"
USER_EMAIL_ADDRESS="John.Doe@organization.com"
PASSWORD="$(
    echo $RANDOM | md5sum | head -c 16
    echo
)"
firstletter=${FIRST_NAME:0:1}
USER_NAME=$firstletter$LAST_NAME${PASSWORD:0:4}
NAME="$FIRST_NAME $LAST_NAME"

PROJECT_NAME=$USER_NAME
NETWORK_NAME="$PROJECT_NAME"_Network
SUBNET_NAME="$PROJECT_NAME"_Subnet
ROUTER_NAME="$PROJECT_NAME"_Router
KEYPAIR_NAME="$USER_NAME"_keypair
ADMIN_KEYPAIR_NAME="admin_keypair_${PASSWORD:0:4}"
FLAVOR="cb1.medium"
ERROR=0
SERVER_ERRORS=""

# Declare dictionaries
declare -A servers
declare -A vms
# servers['r2-610-1']="vm-test-1"
# vms["vm-test-1"]="openstack create server vm-test-1"

function lookup_key_from_value() {
    declare -n arr=$1
    search="$2"
    for key in "${!arr[@]}"; do
        if [[ "${arr[$key]}" == "$search" ]]; then
            echo "$key"
            break
        fi
    done
}

function retry {
    command="$*"
    retval=1
    attempt=1
    tries=10
    until [[ $retval -eq 0 ]] || [[ $attempt -gt $tries ]]; do
        # Execute inside of a subshell in case parent
        # script is running with "set -e"
        (
            set +e
            $command
        )
        retval=$?
        attempt=$((attempt + 1))
        if [[ $retval -ne 0 ]]; then
            echo "WARNING: Rare race condition, trying again in 5 seconds."
            sleep 5
        fi
    done
    if [[ $retval -ne 0 ]] && [[ $attempt -gt $tries ]]; then
        echo "ERROR: Critical error is happening, go ahead and exit"
        exit $retval
    fi
}

function create_project_and_user() {
    echo "INFO: Creating Group..."
    openstack project create --description "Project for $NAME" "$PROJECT_NAME"
    echo "INFO: Getting project/group ID..."
    PROJECT_ID=$(openstack project show -f shell -c id "$PROJECT_NAME" | cut -d"=" -f2 | tr -d '"')
    echo "INFO: Creating user..."
    openstack user create --project "$PROJECT_NAME" --description "$NAME" --password "$PASSWORD" --email "$USER_EMAIL_ADDRESS" --enable "$USER_NAME"
    echo "INFO: Adding user to project and set project as default project"
    openstack role add --user "$USER_NAME" --project "$PROJECT_ID" member
    openstack user set --project "$PROJECT_NAME" "$USER_NAME"

    echo "INFO: Getting External Network Information..."
    EXTERNAL_NETWORK_NAME=$(openstack network list --long | grep External | awk '{print $4}')
    EXTERNAL_NETWORK_ID=$(openstack network show -f shell "$EXTERNAL_NETWORK_NAME" -c id | cut -d "\"" -f 2)

    if [[ -z "$EXTERNAL_NETWORK_NAME" ]]; then
        echo "ERROR: EXTERNAL_NETWORK_NAME is not defined, cleaning up the project and quitting."
        delete_project_and_user
        exit 1
    fi
    if [[ -z "$EXTERNAL_NETWORK_ID" ]]; then
        echo "ERROR: EXTERNAL_NETWORK_ID is not defined, cleaning up the project and quitting."
        delete_project_and_user
        exit 1
    fi

    echo "INFO: Creating Network and subnet..."
    openstack network create --project "$PROJECT_ID" "$NETWORK_NAME"
    NETWORK_ID=$(openstack network show -f shell -c id "$NETWORK_NAME" | cut -d"=" -f2 | tr -d '"')
    openstack subnet create --project "$PROJECT_ID" --dns-nameserver "8.8.8.8" --subnet-range "192.168.0.0/24" --network "$NETWORK_ID" "$SUBNET_NAME"

    echo "INFO: Creating router and connections ..."
    openstack router create --project "$PROJECT_ID" "$ROUTER_NAME"
    ROUTER_ID=$(openstack router show -f shell "$ROUTER_NAME" -c id | cut -d"\"" -f 2)
    openstack router set --external-gateway "$EXTERNAL_NETWORK_ID" "$ROUTER_ID"
    openstack router add subnet "$ROUTER_ID" "$SUBNET_NAME"

    echo "INFO: UPDATING SECURITY GROUP RULES"

    SECURITY_GROUP_ID=$(openstack security group list | grep "$PROJECT_ID" | awk '{print $2}')
    ADMIN_SECURITY_GROUP_ID=$(openstack security group list --project admin -c ID -f value)
    openstack security group rule create --proto icmp --project "$PROJECT_NAME" "$SECURITY_GROUP_ID"
    openstack security group rule create --proto tcp --project "$PROJECT_NAME" --dst-port 22 "$SECURITY_GROUP_ID"
    openstack security group rule create --proto tcp --project admin --dst-port 22 "$ADMIN_SECURITY_GROUP_ID" || true
    openstack security group rule create --proto icmp --project admin "$ADMIN_SECURITY_GROUP_ID" || true

    echo "######################"
    echo "Username: $USER_NAME"
    echo "Password: $PASSWORD"
    echo "######################"
}

function check_status() {
    SOURCE=$1
    LIST_OF_BAD_STATUS="down failed error :-("
    LIST_OF_GOOD_STATUS="active running :-)"
    if echo "$LIST_OF_BAD_STATUS" | grep -i -q "$SOURCE"; then
        echo "1. ERROR: This is a BAD STATE: $SOURCE"
    elif echo "$LIST_OF_GOOD_STATUS" | grep -i -q "$SOURCE"; then
        echo "2. Operation is complete, now $SOURCE."
    else
        echo "3. Operation ($SOURCE) still proceeding. Please wait."
    fi
}

function ssh_into_vm() {
    i=0
    KEYPAIR_NAME=$1
    FLOATING_IP=$2
    INSTANCE_NAME=$3
    ssh_cmd="ssh -i $ADMIN_KEYPAIR_NAME -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5 ubuntu@$FLOATING_IP"
    echo "$ssh_cmd"
    while [[ i -le 15 ]]; do
        result=$($ssh_cmd "echo ok 2>&1")
        echo "$result"
        if [ "$result" == "ok" ]; then
            $ssh_cmd "ping -c 4 google.com &> /dev/null && echo pass || echo fail"
            break
        else
            echo "INFO: VM, $INSTANCE_NAME, not ready, waiting 10 seconds....."
            sleep 10
        fi
        i=$i+1
    done
}

function create_vms() {
    echo "INFO: Starting VM creation process."
    echo "INFO: Adjusting necessary quotas"
    flavor_vcpu=$(openstack flavor show $FLAVOR -f value -c vcpus)
    flavor_ram=$(openstack flavor show $FLAVOR -f value -c ram)
    original_vcpu_quota=$(openstack quota show -f value -c cores)
    original_ram_quota=$(openstack quota show -f value -c ram)
    original_instance_quota=$(openstack quota show -f value -c instances)
    node_count=$(openstack compute service list -f value -c Host --service nova-compute | wc -l)
    new_vcpu_quota=$((flavor_vcpu * node_count + 20))
    new_ram_quota=$((flavor_ram * node_count + 51200))
    new_instance_quota=$((node_count + 10))
    openstack quota set --cores $new_vcpu_quota --ram $new_ram_quota --instances $new_instance_quota admin

    echo "INFO: Getting list of compute nodes, creating keypairs, and creating floating IP..."
    mapfile -t compute_nodes < <(openstack compute service list -f value -c Host --service nova-compute)
    num_of_nodes=${#compute_nodes[@]}
    openstack keypair create --private-key "$ADMIN_KEYPAIR_NAME" "$ADMIN_KEYPAIR_NAME"
    chmod 600 "$ADMIN_KEYPAIR_NAME"
    mapfile -t IMAGE_LIST < <(openstack image list -c Name -f value | grep Ubuntu)
    ADMIN_NETWORK_ID=$(openstack network list --internal --project admin -c ID -f value)
    EXTERNAL_ID=$(openstack network list --external --long -f value -c ID)
    FLOATING_IP=$(openstack floating ip create "$EXTERNAL_ID" -f value -c floating_ip_address)
    echo "INFO: Created Floating IP of $FLOATING_IP"
    echo "INFO: Creating VM's now on each of the $num_of_nodes compute nodes."
    i=1

    for compute_node in "${compute_nodes[@]}"; do
        INSTANCE_NAME="TEST_INSTANCE_$(
            echo $RANDOM | md5sum | head -c 5
        )"
        echo "INFO: Deploying VM, $INSTANCE_NAME, on physical server ($i of $num_of_nodes): $compute_node"
        # shellcheck disable=SC2034
        servers["$compute_node"]="$INSTANCE_NAME"
        vms["$INSTANCE_NAME"]="openstack server create --key-name $ADMIN_KEYPAIR_NAME --network $ADMIN_NETWORK_ID --image ${IMAGE_LIST[-1]} --flavor $FLAVOR --availability-zone nova::$compute_node $INSTANCE_NAME"
        i=$((i + 1))
    done
    for VM_NAME in "${!vms[@]}"; do
        eval "${vms[${VM_NAME}]}"
    done
    i=1
    while true; do
        for VM_NAME in "${!vms[@]}"; do
            echo "INFO: Checking $VM_NAME status...."
            compute_node=$(lookup_key_from_value servers "$VM_NAME")
            STATUS_STATE=$(openstack server list -c Status --name "$VM_NAME" -f value)
            STATUS_VALUE=$(check_status "$STATUS_STATE")
            VALUE="${STATUS_VALUE::1}"
            echo "$STATUS_VALUE"
            echo "$VALUE"
            case $VALUE in
            1)
                echo "ERROR: VM, $VM_NAME is in a bad state $STATUS_VALUE, deleting..."
                openstack server delete "$VM_NAME"
                SERVER_ERRORS+="$compute_node "
                echo "INFO: Recreating $VM_NAME ..."
                eval "${vms[${VM_NAME}]}"
                ;;
            2)
                retry openstack server add floating ip "$VM_NAME" "$FLOATING_IP"
                TEST=$(ssh_into_vm "$KEYPAIR_NAME" "$FLOATING_IP" "$VM_NAME")
                echo "$TEST"
                ssh-keygen -f "/root/.ssh/known_hosts" -R "$FLOATING_IP"
                test_value="${TEST: -4}"
                if [ "$test_value" == "pass" ]; then
                    compute_node=$(lookup_key_from_value servers "$VM_NAME")
                    echo "INFO: SUCCESS: SSH PASSES ON $compute_node with $VM_NAME!"
                    echo "INFO: Deleting VM: $INSTANCE_NAME ON $compute_node ($i of $num_of_nodes)"
                    openstack server delete "$VM_NAME"
                    echo "INFO: Delete complete"
                    unset "vms[$VM_NAME]"
                    i=$((i + 1))
                else
                    echo "ERROR: SSH FAILED!!!!"
                    ERROR=$((ERROR + 1))
                fi
                break
                ;;
            3) sleep 2 ;;
            *)
                echo "ERROR: UNKNOWN ERROR"
                ERROR=$((ERROR + 1))
                break
                ;;
            esac
            sleep 1
        done
        if [[ ${#vms[@]} -eq 0 ]]; then
            echo "INFO: VM SSH test complete"
            break
        fi
    done
    echo "INFO: Deleting the floating IP: $FLOATING_IP"
    openstack floating ip delete "$FLOATING_IP"
    echo "INFO: Revert quota values"
    openstack quota set --cores "$original_vcpu_quota" --ram "$original_ram_quota" --instances "$original_instance_quota" admin
}

function delete_project_and_user() {
    echo "INFO: CLEANING UP PROJECT AND USER"
    openstack keypair delete "$ADMIN_KEYPAIR_NAME"
    echo "INFO: Keypair deleted"
    rm "$ADMIN_KEYPAIR_NAME" || true
    openstack user delete "$USER_NAME"
    echo "INFO: User deleted"
    openstack project delete "$USER_NAME"
    echo "INFO: Project deleted"
    mapfile -t port_list < <(openstack port list -c ID -f value --network "$USER_NAME"_Network)
    for port in "${port_list[@]}"; do
        echo "INFO: Deleting or Removing Port: $port"
        if openstack port delete "$port"; then
            echo "INFO: Port Deleted: $port"
        else
            openstack router remove port "$USER_NAME"_Router "$port"
            echo "INFO: Port Removed: $port."
        fi
    done
    echo "INFO: All Ports deleted"
    openstack subnet delete "$USER_NAME"_Subnet
    echo "INFO: Subnet deleted"
    openstack router delete "$USER_NAME"_Router
    echo "INFO: Router deleted"
    openstack network delete "$USER_NAME"_Network
    echo "INFO: Network deleted"
    echo "INFO: All project and user aspects have been deleted."
}

create_project_and_user
create_vms
delete_project_and_user
if [[ "$ERROR" -gt 0 ]]; then
    echo "####################################################################"
    echo "WARNING: THERE WERE $ERROR ERRORS FOUND! PLEASE SEARCH ABOVE FOR 'ERROR:'"
    echo "####################################################################"
    exit 1
else
    if [[ -n "$SERVER_ERRORS" ]]; then
        echo "#############################################"
        echo "VM's were re-created on the following servers"
        echo "$SERVER_ERRORS"
        echo "#############################################"
    fi
    echo "########################"
    echo "#   ALL TESTS PASSED   #"
    echo "########################"
fi
