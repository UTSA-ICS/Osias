#!/usr/bin/python3

from ipaddress import IPv4Network
import osias_variables
import ast


def setup_kolla_configs(
    controller_nodes,
    network_nodes,
    storage_nodes,
    compute_nodes,
    monitoring_nodes,
    servers_public_ip,
    docker_registry,
    docker_registry_username,
    vm_cidr,
    ceph,
    vip_address,
):
    internal_subnet = ".".join((controller_nodes[0].split(".")[:3]))
    if vm_cidr:
        kolla_external_vip_address = str(list(IPv4Network(vm_cidr))[-1])
        VIP_SUFFIX = kolla_external_vip_address.split(".")[-1]
        if VIP_SUFFIX == "255":
            print(
                "\n\nWARNING: You are setting the VIP address to the network address, VIP is being reassigned to 254\n\n"
            )
            VIP_SUFFIX = "254"
            kolla_external_vip_address = str(list(IPv4Network(vm_cidr))[-2])
        kolla_internal_vip_address = ".".join((internal_subnet, VIP_SUFFIX))
        SUFFIX = VIP_SUFFIX
    else:
        external_subnet = ".".join((servers_public_ip[0].split(".")[:3]))
        VIP_ADDRESS_SUFFIX = vip_address.split(".")[-1]
        kolla_external_vip_address = ".".join((external_subnet, VIP_ADDRESS_SUFFIX))
        kolla_internal_vip_address = ".".join((internal_subnet, VIP_ADDRESS_SUFFIX))
        SUFFIX = VIP_ADDRESS_SUFFIX

    if len(controller_nodes) == 1:
        # HA not available
        ha_options = """
enable_neutron_agent_ha: "no"
"""
    else:
        ha_options = """
enable_neutron_agent_ha: "yes"
"""
    if docker_registry:
        docker = f"""
# Docker Options
docker_registry: "{docker_registry}"
docker_registry_insecure: "yes"
docker_registry_username: "{docker_registry_username}"
"""
    else:
        docker = "# Docker Set To Docker Hub"
    if isinstance(ceph, str):
        if ast.literal_eval(ceph):
            ceph = True
        else:
            ceph = False
    if ceph:
        print("Implementing STORAGE with CEPH")
        storage = """
glance_backend_ceph: "yes"
glance_backend_file: "no"
#glance_backend_swift: "no"

enable_cinder: "yes"
#enable_cinder_backend_lvm: "no"

ceph_nova_user: "cinder"
cinder_backend_ceph: "yes"
cinder_backup_driver: "ceph"

nova_backend_ceph: "yes"
#gnocchi_backend_storage: "ceph"
"""
    else:
        print("Implementing STORAGE without CEPH")
        storage = """
glance_backend_ceph: "no"
glance_backend_file: "yes"
#glance_backend_swift: "no"

enable_cinder: "no"
#enable_cinder_backend_lvm: "no"

#ceph_nova_user: "cinder"
#cinder_backend_ceph: "no"
#cinder_backup_driver: "ceph"

nova_backend_ceph: "no"
#gnocchi_backend_storage: "ceph"
"""

    # Default value of the network interface
    network_interface = "eno1"
    # Default value of tls backend
    tls_enabled = "yes"
    # Check if its a all in one deployment on a single
    # node; if so then use br0 as the network interface
    # and disable tls backend
    if (
        len(controller_nodes) == 1
        and len(network_nodes) == 1
        and len(storage_nodes) == 1
        and len(compute_nodes) == 1
    ):
        if (
            controller_nodes == network_nodes
            and controller_nodes == storage_nodes
            and controller_nodes == compute_nodes
            and kolla_internal_vip_address == kolla_external_vip_address
        ):
            network_interface = "br0"
            tls_enabled = "no"
            ha_options += """
enable_haproxy: "no"
    """

    globals_file = f"""
# Globals file is completely commented out besides these variables.
cat >>/etc/kolla/globals.yml <<__EOF__
# Basic Options
kolla_base_distro: "centos"
kolla_install_type: "source"
kolla_internal_vip_address: "{kolla_internal_vip_address}"
kolla_external_vip_address: "{kolla_external_vip_address}"
network_interface: "{network_interface}"
kolla_external_vip_interface: "br0"
neutron_external_interface: "veno1"
kolla_enable_tls_internal: "{tls_enabled}"
kolla_enable_tls_external: "{tls_enabled}"
kolla_copy_ca_into_containers: "yes"
kolla_verify_tls_backend: "no"
kolla_enable_tls_backend: "{tls_enabled}"
openstack_cacert: /etc/pki/tls/certs/ca-bundle.crt
keepalived_virtual_router_id: "{SUFFIX}"

{storage}

{docker}

# Recommended Global Options:
enable_mariabackup: "yes"
{ha_options}
glance_enable_rolling_upgrade: "yes"

# Desired Global Options:
#enable_aodh: "yes"
#enable_prometheus: "yes"
#enable_ceilometer: "yes"
#enable_panko: "yes"
#enable_neutron_metering: "yes"
#enable_neutron_dvr: "yes"
#enable_neutron_qos: "yes"

#enable_telegraf: "yes"
#enable_watcher: "yes"

#enable_gnocchi: "yes
#ceph_gnocchi_pool_name: "metrics"
#gnocchi_incoming_storage: "{{{{ 'redis' if enable_redis | bool else '' }}}}"

#enable_central_logging: "yes"
#enable_grafana: "yes"

#enable_skydive: "yes"
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

    with open("configure_kolla.sh", "w") as f:
        f.write("#!/bin/bash")
        f.write("\n\n")
        f.write("set -euxo pipefail")
        f.write("\n\n")
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
