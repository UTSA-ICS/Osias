#!/bin/bash

set -euo pipefail

# shellcheck source=/dev/null
source "$HOME"/base_config.sh

if [ -f "/etc/kolla/admin-public-openrc.sh" ]; then source /etc/kolla/admin-public-openrc.sh
    echo "admin-public-openrc.sh found"
elif [ -f "admin-public-openrc.sh" ]; then source admin-public-openrc.sh
    echo "admin-public-openrc.sh found"
else echo "No openrc files found"
    exit 1
fi

if python3 -c 'import pkgutil; exit(not pkgutil.find_loader("openstackclient"))'; then
    echo 'Openstack client found'
else
    echo "Openstack client not found"
    pip3 install python-openstackclient
fi

FIRST_NAME="John"
LAST_NAME="Doe"
USER_EMAIL_ADDRESS="John.Doe@organization.com"
PASSWORD="$(openssl rand -base64 12)"
firstletter=${FIRST_NAME:0:1}
USER_NAME=$firstletter$LAST_NAME
NAME="$FIRST_NAME $LAST_NAME"

PROJECT_NAME=$USER_NAME
NETWORK_NAME="$PROJECT_NAME"_Network
SUBNET_NAME="$PROJECT_NAME"_Subnet
ROUTER_NAME="$PROJECT_NAME"_Router
KEYPAIR_NAME="$USER_NAME"_keypair
ADMIN_KEYPAIR_NAME="admin_keypair"
FLAVOR="cb1.medium"
INSTANCE_NAME="TEST_INSTANCE"

function create_project_and_user () {
    echo "INFO: CREATING GROUP"
    openstack project create --description "Project for $NAME" "$PROJECT_NAME"
    echo "INFO: Creating user..."
    openstack user create --project "$PROJECT_NAME" --description "$NAME" --password "$PASSWORD" --email "$USER_EMAIL_ADDRESS" --enable "$USER_NAME"
    echo "INFO: Getting project ID..."
    PROJECT_ID=$(openstack project show -f shell -c id "$PROJECT_NAME" |cut -d"=" -f2 | tr -d '"')
    echo "INFO: Adding user to project and set project as default project"
    openstack role add --user "$USER_NAME"  --project "$PROJECT_ID" member
    openstack user set --project "$PROJECT_NAME" "$USER_NAME"

    echo "INFO: CREATING NETWORKING"
    EXTERNAL_NETWORK_NAME=$(openstack network list --long | grep External | awk '{print $4}')
    EXTERNAL_NETWORK_ID=$(openstack network show -f shell "$EXTERNAL_NETWORK_NAME" -c id | cut -d "\"" -f 2)

    if [[ -z "$EXTERNAL_NETWORK_NAME" ]]; then
        echo "EXTERNAL_NETWORK_NAME is not defined, quitting."
        exit 1
    fi
    if [[ -z "$EXTERNAL_NETWORK_ID" ]]; then
        echo "EXTERNAL_NETWORK_ID is not defined, quitting."
        exit 1
    fi

    openstack network create --project "$PROJECT_ID" "$NETWORK_NAME"
    NETWORK_ID=$(openstack network show -f shell -c id "$NETWORK_NAME" |cut -d"=" -f2 | tr -d '"')

    echo "INFO: Creating Subnetworking..."
    openstack subnet create --project "$PROJECT_ID" --dns-nameserver "8.8.8.8" --subnet-range "192.168.0.0/24" --network "$NETWORK_ID" "$SUBNET_NAME"

    echo "INFO: Creating router..."
    openstack router create --project "$PROJECT_ID" "$ROUTER_NAME"

    echo "INFO: Acquiring router id..."
    ROUTER_ID=$(openstack router show -f shell "$ROUTER_NAME" -c id |cut -d"\"" -f 2)

    echo "INFO: Setting external gateway on router..."
    openstack router set --external-gateway "$EXTERNAL_NETWORK_ID" "$ROUTER_ID"

    echo "INFO: Adding subnet to router..."
    openstack router add subnet "$ROUTER_ID" "$SUBNET_NAME"

    echo "INFO: UPDATING SECURITY GROUP RULES"

    SECURITY_GROUP_ID=$(openstack security group list | grep "$PROJECT_ID" | awk '{print $2}')
    ADMIN_SECURITY_GROUP_ID=$(openstack security group list --project admin -c ID -f value)
    openstack security group rule create --proto icmp --project "$PROJECT_NAME" "$SECURITY_GROUP_ID"
    openstack security group rule create --proto tcp --project "$PROJECT_NAME" --dst-port 22 "$SECURITY_GROUP_ID"
    openstack security group rule create --proto tcp --project admin --dst-port 22 "$ADMIN_SECURITY_GROUP_ID" || true

    echo "######################"
    echo "Username: $USER_NAME"
    echo "Password: $PASSWORD"
    echo "######################"
}


function check_status () {
    SOURCE=$1
    LIST_OF_BAD_STATUS="down failed error :-("
    LIST_OF_GOOD_STATUS="active running :-)"
    if echo "$LIST_OF_BAD_STATUS" | grep -i -q "$SOURCE"; then
        echo "1. This is a bad state: $SOURCE";
    elif echo "$LIST_OF_GOOD_STATUS" | grep -i -q "$SOURCE"; then
        echo "2. Operation is complete, now $SOURCE."
    else
        echo "3. Operation ($SOURCE) still proceeding. Please wait.";
    fi
}

function create_vms () {
    mapfile -t compute_nodes < <(openstack compute service list -f value -c Host --service nova-compute)
    openstack keypair create  --private-key "$ADMIN_KEYPAIR_NAME" "$ADMIN_KEYPAIR_NAME"
    chmod 600 ~/"$ADMIN_KEYPAIR_NAME"
    mapfile -t IMAGE_LIST < <(openstack image list -c Name -f value | grep Ubuntu)
    EXTERNAL_ID=$(openstack network list --external --long -f value -c ID)

    for compute_node in "${compute_nodes[@]}"; do
        echo "Deploying server on $compute_node"
        openstack server create --key-name "$ADMIN_KEYPAIR_NAME" --network "$NETWORK_NAME" --image "${IMAGE_LIST[-1]}" --flavor "$FLAVOR" --availability-zone nova::"$compute_node" "$INSTANCE_NAME"
        FLOATING_IP=$(openstack floating ip create "$EXTERNAL_ID" -f value -c floating_ip_address)
        echo "Assigning public IP to server: $FLOATING_IP"
        openstack server add floating ip "$INSTANCE_NAME" "$FLOATING_IP"
        while true ; do
            echo "Checking status...."
            STATUS_STATE=$(openstack server list -c Status --name $INSTANCE_NAME -f value)
            STATUS_VALUE=$( check_status "$STATUS_STATE" )
            VALUE="${STATUS_VALUE: :1}"
            echo "$STATUS_VALUE"
	    echo "$VALUE"
            case $VALUE in
                1 ) exit 1;;
		        2 ) TEST=$( ssh_into_vm $KEYPAIR_NAME "$FLOATING_IP")
		            echo "$TEST"
		            test_value="${TEST: -4}"
		            if [ "$test_value" == "pass" ]; then
        			    echo "PASS: SSH PASSES ON $compute_node!"
                 	    echo "Deleting server $INSTANCE_NAME"
                        openstack server delete $INSTANCE_NAME
                  	    openstack floating ip delete "$FLOATING_IP"
                        echo "Delete complete"
	                else
			            echo "ERROR: SSH FAILED!!!!"
			            exit 1
		            fi
                    break;;
                3 ) sleep 1;;
                * ) echo "Unkown Error"
		            exit 1;;
            esac
            sleep 1
        done
    done

}

function ssh_into_vm () {
    i=0
    KEYPAIR_NAME=$1
    FLOATING_IP=$2
    ssh_cmd="ssh -i $ADMIN_KEYPAIR_NAME -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=5 ubuntu@$FLOATING_IP"
    echo "$ssh_cmd"
    while [[ i -le 10 ]]; do
	    result=$($ssh_cmd "echo ok 2>&1")
	    echo "$result"
            if [ "$result" == "ok" ];  then
                $ssh_cmd "ping -c 4 google.com &> /dev/null && echo pass || echo fail"
                 break
            else
                echo "VM not ready, waiting 10 seconds....."
                sleep 10
            fi
        i=$i+1
    done
}
function delete_project_and_user () {
    openstack keypair delete "$ADMIN_KEYPAIR_NAME"
    rm "$KEYPAIR_NAME" || true
    rm "$ADMIN_KEYPAIR_NAME" || true
    openstack user delete "$USER_NAME"
    openstack project delete "$USER_NAME"
    mapfile -t port_list < <(openstack port list -c ID -f value --network "$USER_NAME"_Network)
    for port in "${port_list[@]}"; do
        echo "Deleting port: $port"
        openstack port delete "$port" || true
        openstack router remove port "$USER_NAME"_Router "$port" || true
    done
    openstack subnet delete "$USER_NAME"_Subnet
    openstack router delete "$USER_NAME"_Router
    openstack network delete "$USER_NAME"_Network
}

create_project_and_user
create_vms
delete_project_and_user
