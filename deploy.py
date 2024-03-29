#!/usr/bin/python3

import argparse
import ast
import os
import yaml
from time import sleep

import maas_base
import maas_virtual
import osias_variables
import setup_configs
import utils


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--sshkey",
        type=str,
        required=False,
        help="The path to the SSH key used to access the target node",
    )
    parser.add_argument(
        "-c",
        "--command",
        type=str,
        required=False,
        help="The command that will be run on the target node",
    )
    parser.add_argument(
        "-n",
        "--target_node",
        type=str,
        required=False,
        help="The target node IP address that the specified script will run on",
    )
    parser.add_argument(
        "--config",
        type=str,
        required=False,
        help="The config file in yaml format defining all servers and their IPs",
    )
    parser.add_argument(
        "--file_path",
        type=str,
        required=False,
        help="path of files to be copied from the deployment node",
    )
    parser.add_argument(
        "--MAAS_URL",
        type=str,
        required=False,
        help="The URL of the remote API, e.g. http://example.com/MAAS/ or "
        + "http://example.com/MAAS/api/2.0/ if you wish to specify the "
        + "API version.",
    )
    parser.add_argument(
        "--MAAS_API_KEY",
        type=str,
        required=False,
        help="The credentials, also known as the API key, for the remote "
        + "MAAS server. These can be found in the user preferences page "
        + "in the web UI; they take the form of a long random-looking "
        + "string composed of three parts, separated by colons.",
    )
    parser.add_argument(
        "--DOCKER_REGISTRY_PASSWORD",
        type=str,
        required=False,
        help="The password for the docker registry.",
    )
    parser.add_argument(
        "--VM_PUBLIC_CIDR",
        type=str,
        required=False,
        help="The smaller test subnet of public IP's that are reserved for the VM's and openstack deployment.",
    )
    parser.add_argument(
        "--VM_PROFILE",
        type=str,
        required=False,
        help="Dictionary of values containing the following which over-write the defaults listed in osias_variables.py",
    )
    parser.add_argument(
        "operation",
        type=str,
        choices=[
            "reboot_servers",
            "reprovision_servers",
            "tag_virtual_servers",
            "create_virtual_servers",
            "bootstrap_networking",
            "verify_connectivity",
            "bootstrap_openstack",
            "bootstrap_ceph",
            "pre_deploy_openstack",
            "deploy_ceph",
            "deploy_openstack",
            "post_deploy_openstack",
            "test_setup",
            "test_refstack",
            "test_functionality",
            "test_stress",
            "delete_virtual_machines",
            "delete_tags_and_ips",
            "complete_openstack_install",
            "copy_files",
            "run_command",
        ],
        help="Operation to perform",
    )

    args = parser.parse_args()
    print(args)

    return args


def bootstrap_networking(servers_public_ip):
    utils.run_script_on_server("bootstrap_networking.sh", servers_public_ip)


def bootstrap_openstack(
    servers_public_ip,
    servers_private_ip,
    controller_nodes,
    network_nodes,
    storage_nodes_private_ip,
    compute_nodes,
    monitoring_nodes,
    docker_registry_ip,
    docker_registry_username,
    docker_registry_password,
    openstack_release,
    ansible_version,
    ceph,
    enable_swift,
    vip_address,
    fqdn,
    osias_kolla_imports,
    kolla_base_distro,
):
    utils.copy_file_on_server("requirements.txt", servers_public_ip[0])

    utils.run_script_on_server(
        "bootstrap_kolla.sh",
        servers_public_ip[0],
        args=[openstack_release, ansible_version],
    )
    setup_configs.setup_kolla_configs(
        controller_nodes,
        network_nodes,
        storage_nodes_private_ip,
        compute_nodes,
        monitoring_nodes,
        servers_public_ip,
        docker_registry_ip,
        docker_registry_username,
        ceph,
        enable_swift,
        vip_address,
        fqdn,
        kolla_base_distro,
    )
    ssh_priv_key, ssh_public_key = utils.create_new_ssh_key()
    utils.run_script_on_server(
        "bootstrap_ssh_access.sh",
        servers_public_ip,
        args=[ssh_priv_key, ssh_public_key],
    )
    utils.run_script_on_server("configure_kolla.sh", servers_public_ip[0])
    if docker_registry_password:
        utils.run_script_on_server(
            "bootstrap_openstack.sh",
            servers_public_ip[0],
            args=[servers_private_ip[0], docker_registry_password],
        )
    else:
        utils.run_script_on_server(
            "bootstrap_openstack.sh", servers_public_ip[0], args=[servers_private_ip[0]]
        )

    str_servers_private_ip = " ".join(servers_private_ip)
    utils.run_script_on_server(
        "setup_certificates.sh", servers_public_ip[0], args=[str_servers_private_ip]
    )
    setup_configs.setup_nova_conf(compute_nodes)
    utils.run_script_on_server("setup_nova_conf.sh", servers_public_ip[0])
    if osias_kolla_imports:
        print("Creating & importing unique kolla configs.")
        utils.create_kolla_config_files(osias_kolla_imports)
        utils.run_script_on_server("write_kolla_configs.sh", servers_public_ip[0])


def bootstrap_ceph(servers_public_ip, ceph_release, DATA_CIDR):
    utils.run_script_on_server(
        "bootstrap_podman.sh",
        servers_public_ip,
    )
    if DATA_CIDR is None or DATA_CIDR == "None":
        DATA_CIDR = ""
    utils.run_script_on_server(
        "bootstrap_ceph.sh",
        servers_public_ip[0],
        args=[servers_public_ip[0], ceph_release, DATA_CIDR],
    )


def deploy_ceph(servers_public_ip, storage_nodes_data_ip, enable_swift):
    setup_configs.setup_ceph_node_permisions(storage_nodes_data_ip)
    utils.run_script_on_server(
        "configure_ceph_node_permissions.sh", servers_public_ip[0]
    )
    utils.run_script_on_server(
        "deploy_ceph.sh", servers_public_ip[0], args=[str(enable_swift)]
    )


def reprovision_servers(
    maas_url,
    maas_api_key,
    servers_public_ip,
    distro,
    wipe_physical_servers,
):
    utils.run_cmd("maas login admin {} {}".format(maas_url, maas_api_key))
    servers = maas_base.MaasBase(distro)
    servers.set_public_ip(servers_public_ip)
    if wipe_physical_servers:
        servers._release()
    servers.deploy()


def verify_network_connectivity(
    public_ips: list, private_ips: list, data_ips: list, vip_public: str
):
    # Test all IPs are active
    retry = dict()
    retry["public"] = []
    retry["internal"] = []
    functional_public_ip = ""
    active_private_ips = private_ips + data_ips
    count = 0
    while len(public_ips) > 0 and count <= 10:
        for ip in public_ips:
            result = utils.check_ip_active(ip)
            if result is True:
                functional_public_ip = ip
                public_ips.remove(ip)
            if result is False:
                count = count + 1
                print(
                    f"INFO: Attempt {count}/10 - Public IP, {ip}, did not respond, sleeping for 5 seconds."
                )
                sleep(5)

    count = 0
    while len(active_private_ips) > 0 and count <= 10:
        private_ip_results = utils.check_private_ip_active(
            functional_public_ip, active_private_ips
        )
        for ip in private_ip_results["active"]:
            active_private_ips.remove(ip)
        if len(private_ip_results["inactive"]) > 0:
            count = count + 1
            print(
                f"INFO: Attempt {count}/10 - Private IP, {private_ip_results['inactive']}, did not respond, sleeping for 5 seconds."
            )
            sleep(5)
    print("\nINFO: Completed verification that host IP's are online.")
    print(f"      There were {len(active_private_ips)} errors.\n")

    # Test all IPs are inactive.
    internal_subnet = ".".join((private_ips[0].split(".")[:3]))
    VIP_ADDRESS_SUFFIX = vip_public.split(".")[-1]
    vip_internal = ".".join((internal_subnet, VIP_ADDRESS_SUFFIX))

    inactive_results = list()
    inactive_results.append(utils.check_ip_active(vip_public))
    result = utils.check_private_ip_active(functional_public_ip, [vip_internal])
    if len(result["active"]) > 0:
        inactive_results.extend([True for _ in range(len(result["active"]))])
    print("\nINFO: Completed verification that VIP address are not being used.")
    print(f"      There were {inactive_results.count(True)} errors.\n")
    if len(active_private_ips) > 0 or True in inactive_results:
        raise Exception("ERROR: Please check the results above and correct any errors.")


def verify_vm_pool_availability(vm_profile, public_IP_pool):
    internal_subnet = ".".join(vm_profile["Internal_CIDR"].split(".")[:3])
    VIP_ADDRESS_SUFFIX = public_IP_pool[-1].split(".")[-1]
    vip_internal = ".".join((internal_subnet, VIP_ADDRESS_SUFFIX))
    active_ips = []
    for ip in public_IP_pool:
        active_ips.append(utils.check_ip_active(ip))
    active_ips.append(utils.check_ip_active(vip_internal))
    if True in active_ips:
        raise Exception(f"\nERROR: There were {active_ips.count(True)} errors.\n")


def tag_virtual_servers(maas_url, maas_api_key, vm_profile):
    """Find virtual machines and tag them with the pipeline ID and openstack branch.
    If VMs aren't available, they will be created.  Additionally, this will find an available
    IP range and create tags associated to them. An IP range will be used where the VIP is the last
    IP and the pool start IP is the beginning, the pool end IP will be calculated in the multinode
    file generation."""
    parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
    if not parent_project_pipeline_id:

        raise Exception("ERROR: <PARENT_PIPELINE_ID> is needed, please set it.")
    utils.run_cmd(f"maas login admin {maas_url} {maas_api_key}")
    servers = maas_virtual.MaasVirtual(None)
    osias_variables.VM_Profile.update(vm_profile.items())
    public_IP_pool = servers.get_ip_pool(
        osias_variables.VM_Profile["VM_DEPLOYMENT_CIDR"],
        osias_variables.VM_Profile["IPs_NEEDED"],
    )
    verify_vm_pool_availability(vm_profile, public_IP_pool)
    VIP_ADDRESS = str(public_IP_pool.pop())
    POOL_END_IP = str(public_IP_pool.pop())
    POOL_START_IP = str(public_IP_pool.pop(0))
    servers.find_virtual_machines_and_tag(
        vm_profile,
        parent_project_pipeline_id,
        VIP_ADDRESS,
        POOL_END_IP,
        POOL_START_IP,
    )


def create_virtual_servers(maas_url, maas_api_key, vm_profile, ceph_enabled):
    parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
    if not parent_project_pipeline_id:
        raise Exception("ERROR: <PARENT_PIPELINE_ID> is needed, please set it.")
    utils.run_cmd(f"maas login admin {maas_url} {maas_api_key}")
    servers = maas_virtual.MaasVirtual(
        osias_variables.MAAS_VM_DISTRO[vm_profile["OPENSTACK_RELEASE"]]
    )
    (
        server_dict,
        VIP_ADDRESS,
        POOL_END_IP,
        POOL_START_IP,
    ) = servers.find_virtual_machines_and_deploy(vm_profile, parent_project_pipeline_id)
    print(f"server_dict: {server_dict}")
    if ceph_enabled is None:
        ceph_enabled = False
    optional_vars = vm_profile
    optional_vars["CEPH"] = ceph_enabled
    optional_vars["POOL_START_IP"] = POOL_START_IP
    optional_vars["POOL_END_IP"] = POOL_END_IP
    optional_vars["VIP_ADDRESS"] = VIP_ADDRESS
    multinode = utils.create_multinode(server_dict, yaml.dump(optional_vars))
    print(f"Generated multinode is: {multinode}")
    f = open("MULTINODE.env", "w")
    f.write(f"{multinode}")
    f.close()


def delete_tags_and_ips(maas_url, maas_api_key, openstack_release=None):
    parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
    if not parent_project_pipeline_id:
        raise Exception("ERROR: PARENT_PIPELINE_ID is needed.")
    utils.run_cmd("maas login admin {} {}".format(maas_url, maas_api_key))
    servers = maas_virtual.MaasVirtual(None)
    return servers.delete_tags_and_ips(parent_project_pipeline_id, openstack_release)


def delete_virtual_machines(
    maas_url,
    maas_api_key,
    openstack_release,
):
    machine_ids, distro = delete_tags_and_ips(maas_url, maas_api_key, openstack_release)
    servers = maas_virtual.MaasVirtual(None)
    servers.delete_virtual_machines(machine_ids, distro)


def post_deploy_openstack(servers_public_ip, pool_start_ip, pool_end_ip, dns_ip):
    if not utils.is_vm_pool_enabled(pool_start_ip, pool_end_ip):
        utils.run_script_on_server(
            "post_deploy_openstack.sh",
            servers_public_ip[0],
            args=[dns_ip],
        )
    else:
        utils.run_script_on_server(
            "post_deploy_openstack.sh",
            servers_public_ip[0],
            args=[dns_ip, pool_start_ip, pool_end_ip],
        )


def main():
    args = parse_args()

    if args.config:
        config = utils.parser(args.config)
        controller_nodes = config.get_server_ips(node_type="control", ip_type="private")
        network_nodes = config.get_server_ips(node_type="network", ip_type="private")
        if config.bool_check_ips_exist(node_type="storage", ip_type="data"):
            storage_nodes_data_ip = config.get_server_ips(
                node_type="storage", ip_type="data"
            )
        else:
            storage_nodes_data_ip = config.get_server_ips(
                node_type="storage", ip_type="private"
            )
        storage_nodes_private_ip = config.get_server_ips(
            node_type="storage", ip_type="private"
        )
        compute_nodes = config.get_server_ips(node_type="compute", ip_type="private")
        monitoring_nodes = config.get_server_ips(node_type="monitor", ip_type="private")
        servers_public_ip = config.get_all_ips_type("public")
        servers_private_ip = config.get_all_ips_type("private")
        ceph_enabled = config.get_variables(variable="CEPH")
        ENABLE_SWIFT = config.get_variables(variable="ENABLE_SWIFT", optional=True)
        if isinstance(ceph_enabled, str):
            ceph_enabled = ast.literal_eval(ceph_enabled.title())
        if ENABLE_SWIFT:
            ENABLE_SWIFT = ast.literal_eval(ENABLE_SWIFT.title())
        docker_registry_ip = config.get_variables(
            variable="DOCKER_REGISTRY_IP", optional=True
        )
        docker_registry_username = config.get_variables(
            variable="DOCKER_REGISTRY_USERNAME", optional=True
        )
        OSIAS_KOLLA_IMPORTS = config.get_kolla_configs()
        VIP_ADDRESS = config.get_variables(variable="VIP_ADDRESS")
        DATA_CIDR = config.get_variables(variable="Data_CIDR", optional=True)
        POOL_START_IP = config.get_variables(variable="POOL_START_IP")
        POOL_END_IP = config.get_variables(variable="POOL_END_IP")
        DNS_IP = config.get_variables(variable="DNS_IP")
        FQDN = config.get_variables(variable="FQDN", optional=True)
        WIPE_PHYSICAL_SERVERS = config.get_variables(
            variable="WIPE_PHYSICAL_SERVERS", optional=True
        )
        if isinstance(WIPE_PHYSICAL_SERVERS, str):
            WIPE_PHYSICAL_SERVERS = ast.literal_eval(WIPE_PHYSICAL_SERVERS.title())

        if args.operation != "create_virtual_servers":
            if not VIP_ADDRESS or not POOL_START_IP or not POOL_END_IP or not DNS_IP:
                raise Exception(
                    "ERROR: Mandatory parms in the Multinode file are missing.\n"
                    + "Please ensure that the following parms are set to a valid value:\n"
                    + "[VIP_ADDRESS]: {VIP_ADDRESS},\n"
                    + "[POOL_START_IP]: {POOL_START_IP},\n"
                    + "[POOL_END_IP]: {POOL_END_IP}, and\n"
                    + "[DNS_IP]:{DNS_IP}."
                    + "VIP address is the horizon website,\n"
                    + "Pool start/end correlate to the floating IP's that VM's will use."
                )
        OPENSTACK_RELEASE = config.get_variables(variable="OPENSTACK_RELEASE").lower()
        if OPENSTACK_RELEASE not in osias_variables.NON_QUAY_RELEASE:
            if docker_registry_ip is not None:
                raise Exception(
                    f"Openstack version <{OPENSTACK_RELEASE}> is only on quay.io, please remove docker options from multinode variables."
                )
        PYTHON_VERSION = config.get_variables(
            variable="PYTHON_VERSION", openstack_release=OPENSTACK_RELEASE
        )
        TEMPEST_VERSION = config.get_variables(
            variable="TEMPEST_VERSION", openstack_release=OPENSTACK_RELEASE
        )
        REFSTACK_TEST_VERSION = config.get_variables(
            variable="REFSTACK_TEST_VERSION", openstack_release=OPENSTACK_RELEASE
        )
        ANSIBLE_MAX_VERSION = config.get_variables(
            variable="ANSIBLE_MAX_VERSION", openstack_release=OPENSTACK_RELEASE
        )
        MAAS_VM_DISTRO = config.get_variables(
            variable="MAAS_VM_DISTRO", openstack_release=OPENSTACK_RELEASE
        )
        CEPH_RELEASE = config.get_variables(
            variable="CEPH_RELEASE", openstack_release=OPENSTACK_RELEASE
        )
        IPs_NEEDED = osias_variables.VM_Profile["IPs_NEEDED"]
        KOLLA_BASE_DISTRO = osias_variables.KOLLA_BASE_DISTRO[OPENSTACK_RELEASE]

        cmd = "".join((args.operation, ".sh"))

        if args.operation == "reprovision_servers":
            if args.MAAS_URL and args.MAAS_API_KEY:
                reprovision_servers(
                    args.MAAS_URL,
                    args.MAAS_API_KEY,
                    servers_public_ip,
                    MAAS_VM_DISTRO,
                    WIPE_PHYSICAL_SERVERS,
                )
            else:
                raise Exception(
                    "ERROR: MAAS_API_KEY and/or MAAS_URL argument not specified.\n"
                    + "If operation is specified as [reprovision_servers] then "
                    + "the optional arguments [--MAAS_URL] and [--MAAS_API_KEY] have to be set."
                )
        elif args.operation == "bootstrap_networking":
            utils.copy_file_on_server("base_config.sh", servers_public_ip)
            bootstrap_networking(servers_public_ip)
        elif args.operation == "verify_connectivity":
            verify_network_connectivity(
                servers_public_ip,
                servers_private_ip,
                storage_nodes_data_ip,
                VIP_ADDRESS,
            )
        elif args.operation == "bootstrap_ceph":
            if not isinstance(ceph_enabled, bool):
                raise Exception(
                    "ERROR: Unable to determine if ceph should be enabled or not, OSIAS multinode value should be a boolean of 'true' or 'false' without quotes."
                )
            if ceph_enabled:
                if DATA_CIDR is None:
                    DATA_CIDR = ""
                bootstrap_ceph(
                    servers_public_ip,
                    CEPH_RELEASE,
                    DATA_CIDR,
                )
            else:
                print("'Bootstrap_Ceph' is skipped due to CEPH being DISABLED.")
        elif args.operation == "bootstrap_openstack":
            bootstrap_openstack(
                servers_public_ip,
                servers_private_ip,
                controller_nodes,
                network_nodes,
                storage_nodes_private_ip,
                compute_nodes,
                monitoring_nodes,
                docker_registry_ip,
                docker_registry_username,
                args.DOCKER_REGISTRY_PASSWORD,
                OPENSTACK_RELEASE,
                ANSIBLE_MAX_VERSION,
                ceph_enabled,
                ENABLE_SWIFT,
                VIP_ADDRESS,
                FQDN,
                OSIAS_KOLLA_IMPORTS,
                KOLLA_BASE_DISTRO,
            )
        elif args.operation == "deploy_ceph":
            if ceph_enabled:
                utils.copy_file_on_server("swift_settings.sh", servers_public_ip[0])
                deploy_ceph(servers_public_ip, storage_nodes_data_ip, ENABLE_SWIFT)
            else:
                print("'Deploy_Ceph' is skipped due to CEPH being DISABLED.")
        elif args.operation == "reboot_servers":
            utils.run_cmd_on_server("sudo -s shutdown -r 1", servers_public_ip)
            utils.run_cmd_on_server("echo Server is UP!", servers_public_ip)
        elif args.operation == "post_deploy_openstack":
            post_deploy_openstack(servers_public_ip, POOL_START_IP, POOL_END_IP, DNS_IP)
        elif args.operation == "test_refstack":
            if utils.is_vm_pool_enabled(POOL_START_IP, POOL_END_IP):
                utils.run_script_on_server(
                    "test_refstack.sh",
                    servers_public_ip[0],
                    args=[
                        DNS_IP,
                        "VM_POOL_ENABLED",
                        TEMPEST_VERSION,
                        REFSTACK_TEST_VERSION,
                        PYTHON_VERSION,
                    ],
                )
            else:
                utils.run_script_on_server(
                    "test_refstack.sh",
                    servers_public_ip[0],
                    args=[
                        DNS_IP,
                        "VM_POOL_DISABLED",
                        TEMPEST_VERSION,
                        REFSTACK_TEST_VERSION,
                        PYTHON_VERSION,
                    ],
                )
        elif args.operation == "test_functionality":
            client = utils.create_ssh_client(servers_public_ip[0])
            client.scp_from("/etc/kolla/admin-public-openrc.sh")
            client.scp_from("/etc/kolla/certificates/ca/root.crt")
            utils.run_cmd_locally("./test_basic_functionality.sh")
        elif args.operation == "test_setup":
            utils.run_script_on_server(
                "test_setup.sh",
                servers_public_ip[0],
                args=[
                    osias_variables.NOVA_MIN_MICROVERSION[OPENSTACK_RELEASE],
                    osias_variables.NOVA_MAX_MICROVERSION[OPENSTACK_RELEASE],
                    osias_variables.STORAGE_MIN_MICROVERSION[OPENSTACK_RELEASE],
                    osias_variables.STORAGE_MAX_MICROVERSION[OPENSTACK_RELEASE],
                    osias_variables.PLACEMENT_MIN_MICROVERSION[OPENSTACK_RELEASE],
                    osias_variables.PLACEMENT_MAX_MICROVERSION[OPENSTACK_RELEASE],
                    osias_variables.REFSTACK_TEST_IMAGE,
                    osias_variables.UBUNTU_NAMES[0],
                    osias_variables.UBUNTU_NAMES[1],
                    osias_variables.UBUNTU_VERSIONS[0],
                    osias_variables.UBUNTU_VERSIONS[1],
                ],
            )
        elif args.operation in [
            "pre_deploy_openstack",
            "test_stress",
        ]:
            utils.run_script_on_server(cmd, servers_public_ip[0])
        elif args.operation == "deploy_openstack":
            utils.run_script_on_server(
                "deploy_openstack.sh",
                servers_public_ip[0],
                args=[
                    OPENSTACK_RELEASE,
                ],
            )
        elif args.operation == "delete_virtual_machines":
            if args.MAAS_URL and args.MAAS_API_KEY:
                delete_virtual_machines(
                    args.MAAS_URL,
                    args.MAAS_API_KEY,
                    OPENSTACK_RELEASE,
                )
            else:
                raise Exception(
                    "ERROR: MAAS_API_KEY and/or MAAS_URL argument not specified.\n"
                    + "If operation is specified as [delete_virtual_machines] then "
                    + "the optional arguments [--MAAS_URL] and [--MAAS_API_KEY] have to be set."
                )
        elif args.operation == "copy_files":
            if args.file_path:
                client = utils.create_ssh_client(servers_public_ip[0])
                client.scp_from(args.file_path)
            else:
                raise Exception(
                    "ERROR: file_path argument not specified.\n"
                    + "If operation is specified as [copy_files] then the "
                    + "optional arguments [--file_path] has to be set."
                )
        elif args.operation == "complete_openstack_install":
            utils.run_script_on_server("bootstrap_networking.sh", servers_public_ip)
            bootstrap_openstack(
                servers_public_ip,
                servers_private_ip,
                controller_nodes,
                network_nodes,
                storage_nodes_private_ip,
                compute_nodes,
                monitoring_nodes,
                docker_registry_ip,
                docker_registry_username,
                args.DOCKER_REGISTRY_PASSWORD,
                OPENSTACK_RELEASE,
                ANSIBLE_MAX_VERSION,
                ceph_enabled,
                ENABLE_SWIFT,
                VIP_ADDRESS,
                FQDN,
                OSIAS_KOLLA_IMPORTS,
                KOLLA_BASE_DISTRO,
            )
            if ceph_enabled:
                bootstrap_ceph(
                    servers_public_ip,
                    CEPH_RELEASE,
                    DATA_CIDR,
                )
                deploy_ceph(servers_public_ip, storage_nodes_data_ip, ENABLE_SWIFT)
            utils.run_script_on_server("pre_deploy_openstack.sh", servers_public_ip[0])
            utils.run_script_on_server("deploy_openstack.sh", servers_public_ip[0])
            utils.run_script_on_server(
                "post_deploy_openstack.sh",
                servers_public_ip[0],
                args=[DNS_IP, POOL_START_IP, POOL_END_IP],
            )
            utils.run_script_on_server("test_setup.sh", servers_public_ip[0])
            utils.run_script_on_server("test_refstack.sh", servers_public_ip[0])
            utils.run_script_on_server(
                "test_basic_functionality.sh", servers_public_ip[0]
            )
    elif args.operation == "create_virtual_servers":
        if args.MAAS_URL and args.MAAS_API_KEY:
            VM_PROFILE = utils.merge_dictionaries(
                osias_variables.VM_Profile, ast.literal_eval(args.VM_PROFILE)
            )
            ceph_enabled = VM_PROFILE.get("CEPH")
            required_keys = ["VM_DEPLOYMENT_CIDR"]
            utils.check_required_keys_not_null(required_keys, VM_PROFILE)
            create_virtual_servers(
                args.MAAS_URL,
                args.MAAS_API_KEY,
                VM_PROFILE,
                ceph_enabled,
            )
        else:
            raise Exception(
                "ERROR: MAAS_API_KEY and/or MAAS_URL argument not specified.\n"
                + "If operation is specified as [create_virtual_servers] then "
                + "the optional arguments [--MAAS_URL] and [--MAAS_API_KEY] have to be set."
            )
    elif args.operation == "tag_virtual_servers":
        if args.MAAS_URL and args.MAAS_API_KEY:
            tag_virtual_servers(
                args.MAAS_URL, args.MAAS_API_KEY, ast.literal_eval(args.VM_PROFILE)
            )
        else:
            raise Exception(
                "ERROR: MAAS_API_KEY and/or MAAS_URL argument not specified.\n"
                + "If operation is specified as [reprovision_servers] then "
                + "the optional arguments [--MAAS_URL] and [--MAAS_API_KEY] have to be set."
            )
    elif args.operation == "delete_tags_and_ips":
        if args.MAAS_URL and args.MAAS_API_KEY:
            delete_tags_and_ips(
                args.MAAS_URL,
                args.MAAS_API_KEY,
            )
        else:
            raise Exception(
                "ERROR: MAAS_API_KEY and/or MAAS_URL argument not specified.\n"
                + "If operation is specified as [delete_virtual_machines] then "
                + "the optional arguments [--MAAS_URL] and [--MAAS_API_KEY] have to be set."
            )
    elif args.operation == "run_command":
        # If command is specified then only perform it
        if args.command and args.target_node:
            utils.run_cmd_on_server(args.command, args.target_node)
        else:
            raise Exception(
                "ERROR: command and target_node arguments not specified.\n"
                + "If operation is specified as [run_command] then the "
                + "optional arguments [--command] and [--target_node] have to be set."
            )


if __name__ == "__main__":
    main()
