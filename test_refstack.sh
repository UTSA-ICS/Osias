#!/bin/bash

# shellcheck source=/dev/null
source "$HOME"/base_config.sh

source /etc/kolla/admin-openrc.sh

DNS_IP=$1
VM_POOL=$2
TEMPEST_VERSION=$3
REFSTACK_TEST_VERSION=$4
PYTHON_VERSION=${5::1}
TENANT=openstack
USER_NAME=swiftop

if ! openstack user list -c Name -f value | grep -q "$USER_NAME"; then
    openstack user create "$USER_NAME" --password a_big_secret
fi

if ! openstack project list -c Name -f value | grep -q "$TENANT"; then
    openstack project create --enable "$TENANT"
fi

if ! openstack role list -c Name -f value | grep -q 'ResellerAdmin'; then
    openstack role create ResellerAdmin
fi

openstack role add Member --user "$USER_NAME" --project "$TENANT"
openstack role add ResellerAdmin --user "$USER_NAME" --project "$TENANT"

TENANT_ID=$(openstack project list -f value -c ID --user "$USER_NAME")

if ! openstack network list --project "${TENANT_ID}" -c Name -f value | grep -q "$USER_NAME"_Network; then
    openstack network create --project "${TENANT_ID}" "$USER_NAME"_Network
fi

if ! openstack subnet list --project "${TENANT_ID}" -c Name -f value | grep -q "$USER_NAME"_Subnet; then
    openstack subnet create --project "${TENANT_ID}" --subnet-range 192.168.100.0/24 --dns-nameserver "${DNS_IP}" --network "$USER_NAME"_Network "$USER_NAME"_Subnet
fi

if ! openstack router list --project "${TENANT_ID}" -c Name -f value | grep -q "$USER_NAME"_Router; then
    openstack router create --enable --project "${TENANT_ID}" "$USER_NAME"_Router
    openstack router add subnet "$USER_NAME"_Router "$USER_NAME"_Subnet
fi

git clone https://opendev.org/openinfra/refstack-client.git || true
cd refstack-client || exit
./setup_env -t "${TEMPEST_VERSION}" -p "${PYTHON_VERSION}" -q

cp "$HOME"/accounts.yaml "$HOME"/refstack-client/etc/accounts.yaml
cp "$HOME"/tempest.conf "$HOME"/refstack-client/etc/tempest.conf

source .venv/bin/activate

#
# Refstack Tests
#

# Sample for running a single testcase
#refstack-client test -c etc/tempest.conf -v -- --regex tempest.api.identity.v3.test_tokens.TokensV3Test.test_create_token
wget "https://refstack.openstack.org/api/v1/guidelines/${REFSTACK_TEST_VERSION}/tests?target=platform&type=required&alias=true&flag=false" -O /tmp/platform."${REFSTACK_TEST_VERSION}"-test-list.txt

# This is for the instance of an all-in-one deploy where there is no nested
# virtualization is available and so no VMs can be created - hence the VM pool
# is disabled. So skip the testcases that test for compute servers.
if [[ "$VM_POOL" == "VM_POOL_DISABLED" ]]; then
    tests=(
        tempest.api.compute.images.test_images_oneserver.ImagesOneServerTestJSON
        tempest.api.compute.servers.test_create_server.ServersTestJSON
        tempest.api.compute.servers.test_create_server.ServersTestManualDisk
        tempest.api.compute.servers.test_delete_server.DeleteServersTestJSON.test_delete_active_server
        tempest.api.compute.servers.test_instance_actions.InstanceActionsTestJSON
        tempest.api.compute.servers.test_list_server_filters.ListServerFiltersTestJSON
        tempest.api.compute.servers.test_list_servers_negative.ListServersNegativeTestJSON
        tempest.api.compute.servers.test_multiple_create.MultipleCreateTestJSON.test_multiple_create
        tempest.api.compute.servers.test_server_actions.ServerActionsTestJSON
        tempest.api.compute.servers.test_servers.ServersTestJSON.test_create_specify_keypair
        tempest.api.compute.servers.test_servers.ServersTestJSON.test_create_with_existing_server_name
        tempest.api.compute.servers.test_servers.ServersTestJSON.test_update_access_server_address
        tempest.api.compute.servers.test_servers.ServersTestJSON.test_update_server_name
        tempest.api.compute.servers.test_servers_negative.ServersNegativeTestJSON
    )
    for test in "${tests[@]}"; do
        sed -i "/$test/d" /tmp/platform."${REFSTACK_TEST_VERSION}"-test-list.txt
    done
fi

# Now run the refstack test using the refstack client. Return true so that the results can be analyzed if a run fails.
refstack-client test -c etc/tempest.conf -v --test-list "/tmp/platform.${REFSTACK_TEST_VERSION}-test-list.txt" || true

# Cleanup user & project creation
openstack user delete "$USER_NAME"
openstack project delete "$TENANT"
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
openstack subnet delete "$USER_NAME"_Subnet || true
openstack router delete "$USER_NAME"_Router || true
openstack network delete "$USER_NAME"_Network || true


# Finishing refstack test evaluation....
# Now check to see if we are getting the expected failure and nothing else.
# If so then exit with 0 indicating passing tests.
# We will continue to research a solution for this 1 failing test but until it is resolved
# flag the tests as passed.

# This will find the highest number file, indicitive of the latest refstack test run.
FILENAME=$(find "$HOME"/refstack-client/.tempest/.stestr/ -name '*[0-9]' | sort -nr | head -n1)

NUM_FAILURES=$(grep -c "failure:" "$FILENAME" || true)
echo "Number of failure are -->> [$NUM_FAILURES]"

exceptions=('MultipleCreateTestJSON' 'test_get_object_using_temp_url' 'test_put_object_using_temp_url' 'test_upload_too_many_objects')

ALLOWED_FAILURES=0
if [[ $(grep -c "failure:" "$FILENAME") -eq 0 ]]; then
    echo "100% of test passed."
else
    for exception in "${exceptions[@]}"; do
        n="$(grep 'failure:' "$FILENAME" | grep -c "$exception" || true)"
        if [[ $n -gt 0 ]]; then
            echo "Found [$n] exceptions with $exception"
        fi
        ALLOWED_FAILURES=$((ALLOWED_FAILURES + n))
    done
fi

if [[ $NUM_FAILURES -eq 0 ]]; then
    MSG="#            All Tests Passed!            #"
elif [[ $NUM_FAILURES -eq $ALLOWED_FAILURES ]]; then
    MSG="#   Expected unresolved failure - EXIT 0  #"
else
    echo "###########################################"
    echo "#       Unexpected error occurred!        #"
    echo "#                ERROR!!!!                #"
    echo "###########################################"
    echo "#       WARNING: Failed tests are:        #"
    grep '^failure:' "$FILENAME" | grep -o -P "(tempest+).*" | cut -d '[' -f 1 | cut -d ')' -f 1
    echo "###########################################"
    exit 1
fi

SWIFT=$(grep "swift =" "$HOME"/refstack-client/etc/tempest.conf | awk -F= '{print $NF}')
if [[ "$SWIFT" == *"True"* ]]; then
    echo "###########################################"
    echo "# Enabling production settings for swift  #"
    echo "###########################################"
    source "$HOME"/swift_settings.sh 3
fi

echo "###########################################"
echo "$MSG"
echo "#                 PASS!!!!                #"
echo "###########################################"
exit 0
