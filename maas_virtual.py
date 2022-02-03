#!/usr/bin/python3

from maas_base import MaasBase
from ipaddress import IPv4Network, IPv4Address
import osias_variables
import random
import time


class MaasVirtual(MaasBase):
    def __init__(self, distro):
        MaasBase.__init__(self, distro)

    def _get_public_cidr(self, vm_ip_address):
        subnets = self._run_maas_command("subnets read")
        for subnet in subnets:
            if IPv4Address(vm_ip_address) in IPv4Network(subnet["cidr"]):
                return subnet["cidr"]
        return None

    def _create_bridge_interface(self, server_list: list, public_cidr, machines_info):
        self._waiting(server_list, "Ready")
        for server in server_list:
            machine_info = [
                info for info in machines_info if server in info["system_id"]
            ][0]
            for i, v in enumerate(machine_info["interface_set"]):
                if "eno2" in str(machine_info["interface_set"][i]):
                    interface_id = machine_info["interface_set"][i]["id"]
                    self._run_maas_command(
                        f"interfaces create-bridge {server} name=br0 parent={interface_id} bridge_stp=True"
                    )
                    self._set_interface(server, "br0", public_cidr)
                    self._set_interface(
                        server, "eno3", osias_variables.VM_Profile["Data_CIDR"]
                    )
            self._run_maas_command(f"interface disconnect {server} eno3")
            self._set_interface(server, "eno3", osias_variables.VM_Profile["Data_CIDR"])

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

    def _set_interface(self, system, interface, cidr):
        self._run_maas_command(
            f"interface link-subnet {system} {interface} subnet={cidr} mode=AUTO"
        )

    def create_virtual_machine(self, vm_profile, num_VMs):
        # public_cidr = self._get_public_cidr(vm_profile["Public_VM_IP"])
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
            interfaces = f"eno1:subnet_cidr={vm_profile['Internal_CIDR']};eno2:subnet_cidr={vm_profile['VM_DEPLOYMENT_CIDR']};eno3:subnet_cidr={vm_profile['Data_CIDR']}"
        else:
            interfaces = f"eno1:subnet_cidr={vm_profile['Internal_CIDR']};eno2:subnet_cidr={vm_profile['VM_DEPLOYMENT_CIDR']}"
        server_list = []
        for _ in range(num_VMs):
            server = self._run_maas_command(
                f"vm-host compose {pod_id} cores={vm_profile['vCPU']} memory={vm_profile['RAM_in_MB']} 'storage=mylabel:{vm_profile['HDD1']},mylabel:{vm_profile['HDD2']},mylabel:{vm_profile['HDD3']},mylabel:{vm_profile['HDD4']}' interfaces='{interfaces}'"
            )
            print(f"server: {server}")
            server_list.append(server["system_id"])
        machine_info = self._run_maas_command("machines read")
        self._create_bridge_interface(
            server_list, vm_profile["VM_DEPLOYMENT_CIDR"], machine_info
        )
        return server_list

    def find_virtual_machines_and_tag(
        self,
        vm_profile: int,
        pipeline_id: int,
    ):
        no_of_vms = vm_profile["Number_of_VM_Servers"]
        release = vm_profile["OPENSTACK_RELEASE"]
        distro = osias_variables.MAAS_VM_DISTRO[vm_profile["OPENSTACK_RELEASE"]]
        machines = self._run_maas_command(
            "machines read | jq '.[] | {system_id:.system_id,status_name:.status_name,pool_name:.pool.name,ip_addresses:.ip_addresses,distro_series:.distro_series,tag_names:.tag_names}' --compact-output"
        )
        print(f"machines: {machines}")
        ids = []
        machine_no = 0
        for machine in machines:
            if (
                machine["status_name"] == "Deployed"
                and machine["pool_name"] == "virtual_machine_pool"
                and machine["distro_series"] == distro
                and machine["tag_names"].__contains__("openstack_ready")
                and machine_no < no_of_vms
            ):
                ids.append(machine["system_id"])
                machine_no += 1
        if len(ids) < no_of_vms:
            create_n_vms = int(no_of_vms - len(ids))
            print(f"Creating {create_n_vms} virtual machine...")
            machine_list = self.create_virtual_machine(vm_profile, create_n_vms)
            self.deploy(machine_list)
            ids.extend(machine_list)
        pipeline_tag_name = f"{pipeline_id}_{release}"
        print(f"ids: {ids}\ntag: {pipeline_tag_name}")
        self._run_maas_command(
            f"tags create name={pipeline_tag_name} comment='Openstack {release} for {pipeline_id}'"
        )
        for vm in ids:
            self._run_maas_command(f"tag update-nodes {pipeline_tag_name} add={vm}")
            self._run_maas_command(f"tag update-nodes openstack_ready remove={vm}")
        return ids

    def find_virtual_machines_and_deploy(self, no_of_vms: int, pipeline_id: int):
        vm_profile = osias_variables.VM_Profile
        release = osias_variables["OPENSTACK_RELEASE"]
        distro = osias_variables.MAAS_VM_DISTRO[vm_profile["OPENSTACK_RELEASE"]]
        machines = self._run_maas_command(
            "machines read | jq '.[] | {system_id:.system_id,status_name:.status_name,pool_name:.pool.name,ip_addresses:.ip_addresses,distro_series:.distro_series,tag_names:.tag_names}' --compact-output"
        )
        print(f"machines: {machines}")
        ids = []
        machine_no = 0
        for machine in machines:
            if (
                machine["status_name"] == "Deployed"
                and machine["pool_name"] == "virtual_machine_pool"
                and machine["distro_series"] == distro
                and machine["tag_names"].__contains__("openstack_ready")
                and machine_no < no_of_vms
            ):
                ids.append(machine["system_id"])
                machine_no += 1
        if len(ids) < no_of_vms:
            create_n_vms = int(no_of_vms - len(ids))
            print(f"Creating {create_n_vms} virtual machine...")
            machine_list = self.create_virtual_machine(vm_profile, create_n_vms)
            self.deploy(machine_list)
            ids.extend(machine_list)
        pipeline_tag_name = f"{pipeline_id}_{release}"
        print(f"ids: {ids}\ntag: {tag_name}")
        self._run_maas_command(
            f"tags create name={pipeline_tag_name} comment='Openstack {release} for {pipeline_id}'"
        )
        for vm in ids:
            self._run_maas_command(f"tag update-nodes {pipeline_tag_name} add={vm}")
            self._run_maas_command(f"tag update-nodes openstack_ready remove={vm}")
        return final_ids

    def delete_virtual_machines(self):
        for server in self.machine_list:
            # self._run_maas_command(f"machine delete {server}")
            self._run_maas_command(f"machine release {server}")
            self._run_maas_command(
                f"machine deploy {server} distro_series={self.distro}"
            )
            self._run_maas_command(f"tag update-nodes openstack_ready add={server}")

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
