#!/usr/bin/python3

import utils
from maas_base import maas_base
from ipaddress import ip_network, ip_address


class maas_virtual(maas_base):
    def __init__(self, distro):
        maas_base.__init__(self, distro)

    def _get_public_cidr(self, vm_ip_address):
        subnets = self._run_maas_command("subnets read")
        for subnet in subnets:
            if ip_address(vm_ip_address) in ip_network(subnet["cidr"]):
                return subnet["cidr"]
        return None

    def _create_bridge_interface(self, server, public_cidr, vm_ip, machine_info):
        self._waiting([server], "Ready")
        for i, v in enumerate(machine_info["interface_set"]):
            if "eno2" in str(machine_info["interface_set"][i]):
                interface_id = machine_info["interface_set"][i]["id"]
                self._run_maas_command(
                    f"interfaces create-bridge {server} name=br0 parent={interface_id} bridge_stp=True"
                )
                self._set_interface(server, "br0", public_cidr, vm_ip)

    def _get_pod_id(self, storage, cores, memory):
        pods = self._run_maas_command(f"pods read")
        print(
            f"VM REQUIREMENTS: \n\tNEED STORAGE: {storage}\tCORES: {cores}\tMEMORY: {memory}"
        )
        for pod in pods:
            free_memory = (
                pod["memory_over_commit_ratio"] * pod["total"]["memory"]
                - pod["used"]["memory"]
            )
            free_cores = (
                pod["cpu_over_commit_ratio"] * pod["total"]["cores"]
                - pod["used"]["cores"]
            )
            free_storage = int(
                (pod["total"]["local_storage"] - pod["used"]["local_storage"]) / 1048576
            )
            print(
                f"POD {pod['id']} HAS: STORAGE: {free_storage}\tCORES: {free_cores}\tMEMORY: {free_memory}"
            )
            if free_memory >= memory:
                print(f"There is sufficient memory")
                if free_cores >= cores:
                    print(f"There is sufficient cores")
                    if free_storage >= storage:
                        print(f"There is sufficient storage")
                        print(pod["id"])
                        return pod["id"]
        return False

    def _set_interface(self, system, interface, cidr, vm_ip):
        self._run_maas_command(
            f"interface link-subnet {system} {interface} subnet={cidr} mode=STATIC ip_address={vm_ip}"
        )

    def create_virtual_machine(self, vm_profile):
        public_cidr = self._get_public_cidr(vm_profile["Public_VM_IP"])
        total_storage = (
            vm_profile["HDD1"]
            + vm_profile["HDD2"]
            + vm_profile["HDD3"]
            + vm_profile["HDD4"]
        )
        pod_id = self._get_pod_id(
            total_storage, vm_profile["vCPU"], vm_profile["RAM_in_MB"]
        )
        if vm_profile["Data_CIDR"]:
            interfaces = f"eno1:subnet_cidr={vm_profile['Internal_CIDR']};eno2:subnet_cidr={public_cidr};eno3:subnet_cidr={vm_profile['Data_CIDR']}"
        else:
            interfaces = f"eno1:subnet_cidr={vm_profile['Internal_CIDR']};eno2:subnet_cidr={public_cidr}"
        server = self._run_maas_command(
            f"vm-host compose {pod_id} cores={vm_profile['vCPU']} memory={vm_profile['RAM_in_MB']} 'storage=mylabel:{vm_profile['HDD1']},mylabel:{vm_profile['HDD2']},mylabel:{vm_profile['HDD3']},mylabel:{vm_profile['HDD4']}' interfaces='{interfaces}'"
        )
        server = server["system_id"]
        machine_info = self._run_maas_command(f"machine read {server}")
        self._create_bridge_interface(
            server, public_cidr, vm_profile["Public_VM_IP"], machine_info
        )
        return server

    def find_virtual_machines(no_of_vms: int, vm_profile):
        machines = run_maas_command_with_filter(
            "machines read", "system_id", "status_name", "pool.name"
        )
        ids = []
        for machine in machines:
            if (
                machine["statusname"] == "Ready"
                and machine["poolname"] == "virtual_machine_pool"
            ):
                ids.append(machine["systemid"])
        if len(ids) >= no_of_vms:
            return ids[:no_of_vms]
        else:
            while len(ids) < no_of_vms:
                print("Creating virtual machine...")
                system_id = create_virtual_machine(vm_profile)
                ids.append(system_id)
            return ids[:no_of_vms]

    def delete_virtual_machines(self):
        for server in self.machine_list:
            # self._run_maas_command(f"machine delete {server}")
            self._run_maas_command(f"machine release {server}")

    def get_machines_interface_ip(
        self, server_list, machines_info, interface, interface_common_name
    ):
        results = {}
        for server in server_list:
            for i in machines_info:
                if server in str(i):
                    for j, v in enumerate(i["interface_set"]):
                        if interface in str(i["interface_set"][j]):
                            discovered_ip = i["interface_set"][j]["links"][0][
                                "ip_address"
                            ]
                            results[server] = {interface_common_name: discovered_ip}
        return results
