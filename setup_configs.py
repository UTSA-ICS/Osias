#!/usr/bin/python3

import ast
import os


def setup_kolla_configs(
    controller_nodes,
    network_nodes,
    storage_nodes,
    compute_nodes,
    monitoring_nodes,
    servers_public_ip,
    docker_registry,
    docker_registry_username,
    vm_deployment_cidr,
    ceph,
    vip_address,
    fqdn,
    kolla_base_distro,
):
    internal_subnet = ".".join((controller_nodes[0].split(".")[:3]))
    VIP_SUFFIX = vip_address.split(".")[-1]
    if VIP_SUFFIX == "255":
        print(
            "\n\nWARNING: You are setting the VIP address to the network address, VIP is being reassigned to 254\n\n"
        )
        VIP_SUFFIX = "254"
    external_subnet = ".".join((servers_public_ip[0].split(".")[:3]))
    VIP_ADDRESS_SUFFIX = vip_address.split(".")[-1]
    kolla_external_vip_address = ".".join((external_subnet, VIP_ADDRESS_SUFFIX))
    kolla_internal_vip_address = ".".join((internal_subnet, VIP_ADDRESS_SUFFIX))
    SUFFIX = VIP_ADDRESS_SUFFIX

    if docker_registry:
        print("Docker Set To Pull From Local Registry")
        docker = f"""
# Docker Options
docker_registry: "{docker_registry}"
docker_registry_insecure: "yes"
docker_registry_username: "{docker_registry_username}"
"""
    else:
        print("Docker Set To Pull From The Cloud")
        docker = "# Docker Set To Pull From The Cloud "
    if ceph:
        print("Implementing STORAGE with CEPH")
        storage = f"""
glance_backend_ceph: "yes"
glance_backend_file: "no"
#glance_backend_swift: "no"
glance_enable_rolling_upgrade: "yes"

enable_cinder: "yes"
#enable_cinder_backend_lvm: "no"

ceph_nova_user: "cinder"
cinder_backend_ceph: "yes"
cinder_backup_driver: "ceph"

nova_backend_ceph: "yes"
#gnocchi_backend_storage: "ceph"

# Swift options:
enable_ceph_rgw: true # Feature from Xena onwards
# This sets up the endpoints, etc.

enable_swift: "no" # Feature for swift on disk, not through ceph.
enable_swift_s3api: "yes"
#ceph_rgw_port: 7480 # Leave commented, else HAProxy fails on deploy
enable_ceph_rgw_keystone: true

ceph_rgw_swift_compatibility: true
# enable/disable complete RadosGW compatibility with Swift API.
# This should match the configuration used by Ceph RadosGW.

ceph_rgw_swift_account_in_url: true
# By default, the RadosGW endpoint URL does not include the project (account) ID.
# This prevents cross-project and public object access.
# This can be resolved by setting ceph_rgw_swift_account_in_url to true

enable_ceph_rgw_loadbalancer: true
ceph_rgw_hosts:
  - host: $HOST0
    ip: {controller_nodes[0]}
    port: 7480
  - host: $HOST1
    ip: {controller_nodes[1]}
    port: 7480
  - host: $HOST2
    ip: {controller_nodes[2]}
    port: 7480
"""
    else:
        print("Implementing STORAGE without CEPH")
        storage = """
glance_backend_ceph: "no"
glance_backend_file: "yes"
#glance_backend_swift: "no"
enable_glance_image_cache: "yes"
glance_cache_max_size: "10737418240" # 10GB by default
glance_enable_rolling_upgrade: "yes"

enable_cinder: "no"
#enable_cinder_backend_lvm: "no"

#ceph_nova_user: "cinder"
#cinder_backend_ceph: "no"
#cinder_backup_driver: "ceph"

nova_backend_ceph: "no"
#gnocchi_backend_storage: "ceph"
"""

    # Default value of the network interface
    network_interface = "NETWORK_INTERFACE"
    # Default value of tls backend
    tls_enabled = "yes"
    # Default value of High Availability options:
    ha_options = """
enable_haproxy: "yes"
"""
    if isinstance(fqdn, str):
        try:
            if ast.literal_eval(fqdn) is None:
                fqdn = "{{ kolla_external_vip_address }}"
        except (ValueError, SyntaxError):
            print(f"fqdn is {fqdn}")
    else:
        if fqdn is None:
            fqdn = "{{ kolla_external_vip_address }}"
    # Check if its a all in one deployment on a single
    # node; if so then use br0 as the network interface
    # and disable tls backend
    if (
        len(controller_nodes) == 1
        and len(network_nodes) == 1
        and len(storage_nodes) == 1
        and len(compute_nodes) == 1
    ):
        tls_enabled = "no"
        if (
            controller_nodes == network_nodes
            and controller_nodes == storage_nodes
            and controller_nodes == compute_nodes
            and kolla_internal_vip_address == kolla_external_vip_address
        ):
            # This is a gitlab deployment, only 1 nic, 1 IP.
            # Due to 1 IP, internal and external VIP's match.
            network_interface = "br0"
            ha_options = """
# If vip's don't match, disabling haproxy will fail deployment
enable_haproxy: "no"
    """

    globals_file = f"""
# Globals file is completely commented out besides these variables.
cat >>/etc/kolla/globals.yml <<__EOF__
# Basic Options
kolla_base_distro: "{kolla_base_distro}"
network_interface: "{network_interface}"
kolla_external_vip_interface: "br0"
neutron_external_interface: "veno1"

# Enable direct access to the internet from compute nodes & reduce latency.
enable_neutron_provider_networks: "yes"
neutron_bridge_name: "br0"
enable_neutron_dvr: "yes"

keepalived_virtual_router_id: "{SUFFIX}"
kolla_internal_vip_address: "{kolla_internal_vip_address}"
kolla_external_vip_address: "{kolla_external_vip_address}"

kolla_enable_tls_internal: "{tls_enabled}"
kolla_enable_tls_external: "{tls_enabled}"
kolla_enable_tls_backend: "{tls_enabled}"
rabbitmq_enable_tls: "{tls_enabled}"
kolla_copy_ca_into_containers: "{tls_enabled}"
openstack_cacert: "{{{{ '/etc/pki/tls/certs/ca-bundle.crt' if kolla_enable_tls_external == 'yes' else '' }}}}"

{storage}

{docker}

# Recommended Global Options:
enable_mariabackup: "no"
{ha_options}

# Desired Global Options:
#enable_neutron_metering: "yes"
#enable_neutron_qos: "yes"
#enable_neutron_agent_ha: "no"
# Masakari provides Instances High Availability Service for OpenStack clouds by automatically recovering failed Instances.
#enable_masakari: "yes"
#enable_central_logging: "yes"
kolla_external_fqdn: "{fqdn}"
__EOF__
"""

    CONTROLLER_NODES = "\\n".join(controller_nodes)
    NETWORK_NODES = "\\n".join(network_nodes)
    COMPUTE_NODES = "\\n".join(compute_nodes)
    MONITORING_NODES = "\\n".join(monitoring_nodes)
    STORAGE_NODES = "\\n".join(storage_nodes)

    multinode_file = f"""
cd /opt/kolla

# Update multinode file
# Update control nodes
sed -i 's/^control01/{CONTROLLER_NODES}/g' multinode
sed -i '/^control02/d' multinode
sed -i '/^control03/d' multinode

# Update Network nodes
sed -i 's/^network01/{NETWORK_NODES}/g' multinode
sed -i '/^network02/d' multinode

# Update compute nodes
sed -i 's/^compute01/{COMPUTE_NODES}/g' multinode

# Update monitor nodes
sed -i 's/^monitoring01/{MONITORING_NODES}/' multinode

# Update storage nodes
sed -i 's/^storage01/{STORAGE_NODES}/g' multinode

"""

    get_remote_hosts_names = ""
    if ceph:
        CONTROLLER_SSH_NODES = " ".join(controller_nodes)
        second_line = "arraylength=${#array[@]}"
        get_remote_hosts_names = f"""
declare -a array=({CONTROLLER_SSH_NODES})
{second_line}


for (( i=0; i<arraylength; i++ ));
do
  declare HOST"$i"="$(ssh  -o StrictHostKeyChecking=no "${{array[$i]}}" cat /proc/sys/kernel/hostname)"
done
        """

    with open("configure_kolla.sh", "w") as f:
        f.write("#!/bin/bash")
        f.write("\n\n")
        f.write("set -euxo pipefail")
        f.write("\n\n")
        f.write(get_remote_hosts_names)
        f.write(globals_file)
        f.write("\n\n")
        f.write(multinode_file)


def setup_ceph_node_permisions(storage_nodes):
    copy_keys = ""
    copy_ssh_id = ""
    add_ceph_hosts = ""
    for node in storage_nodes:
        copy_keys += "".join(
            (
                "ssh -o StrictHostKeyChecking=no ",
                node,
                " sudo cp /home/ubuntu/.ssh/authorized_keys /root/.ssh/authorized_keys",
                "\n",
            )
        )
        copy_ssh_id += "".join(
            (
                "ssh-copy-id -f -i /etc/ceph/ceph.pub -o StrictHostKeyChecking=no root@$(ssh -o StrictHostKeyChecking=no ",
                node,
                " hostname)",
                "\n",
            )
        )
        add_ceph_hosts += "".join(
            (
                "sudo ceph orch host add $(ssh -o StrictHostKeyChecking=no ",
                node,
                " hostname) ",
                node,
                "\n",
            )
        )

    with open("configure_ceph_node_permissions.sh", "w") as f:
        f.write("#!/bin/bash")
        f.write("\n\n")
        f.write("set -euxo pipefail")
        f.write("\n\n")
        f.write(copy_keys)
        f.write("\n\n")
        f.write(copy_ssh_id)
        f.write("\n\n")
        f.write(add_ceph_hosts)


def setup_nova_conf(compute_nodes):
    # Ref: https://www.openstack.org/videos/summits/berlin-2018/effective-virtual-cpu-configuration-in-nova
    # Identical host CPU's: host-passthrough
    # Mixed host CPU's: host-model or custom
    # NOTE: - PCID Flag is only necessary on custom mode and required to address the guest performance degradation as a result of vuln patches
    # - Intel VMX to expose the virtualization extensions to the guest,
    # - pdpe1gb to configure 1GB huge pages for CPU models that do not provide it.
    CPU_MODELS = ""
    for node in compute_nodes:
        CPU_MODELS += "".join(
            (
                'models+="$(ssh -o StrictHostKeyChecking=no ',
                node,
                ' cat /sys/devices/cpu/caps/pmu_name || true) "',
                "\n",
            )
        )
    MULTILINE_CMD = """

# Remove duplicates and trailing spaces
models="$(echo "$models" | xargs -n1 | sort -u | xargs)"
COUNT=$(wc -w <<< "$models")
echo "THERE ARE $COUNT CPU ARCHITECTURES"
if [ "$COUNT" -le 1 ]
then
   MODE="host-passthrough"
elif [ "$COUNT" -ge 2 ]
then
   MODE="host-model"
fi
echo "MODE IS SET TO: $MODE"

# Replace spaces with commas
models="${models// /,}"

cat >> /etc/kolla/config/nova.conf <<__EOF__
[libvirt]
cpu_mode = $MODE
# cpu_models = $models
# cpu_model_extra_flags = pcid, vmx, pdpe1gb
__EOF__

"""
    with open("setup_nova_conf.sh", "w") as f:
        f.write("#!/bin/bash")
        f.write("\n\n")
        f.write("set -euxo pipefail")
        f.write("\n\n")
        f.write("models=''")
        f.write("\n\n")
        f.write(CPU_MODELS)
        f.write("\n\n")
        f.write(MULTILINE_CMD)
