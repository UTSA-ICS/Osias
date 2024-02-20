#!/usr/bin/python3

from maas_base import MaasBase
from ipaddress import IPv4Network, IPv4Address
import osias_variables


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
        print(f"Creating a bridge interface for {server_list}, please wait.")
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

    def _get_pod_id(self, storage, cores, memory, num_VMs):
        pods = self._run_maas_command("pods read")
        vms_needed = num_VMs
        pods_needed = []
        print(
            f"VM REQUIREMENTS NEED: \n\t\tSTORAGE: {storage}\t\tCORES: {cores}\tMEMORY: {memory}"
        )
        for pod in pods:
            pod_free_memory = (
                pod["memory_over_commit_ratio"] * pod["total"]["memory"]
                - pod["used"]["memory"]
            )
            pod_free_cores = (
                pod["cpu_over_commit_ratio"] * pod["total"]["cores"]
                - pod["used"]["cores"]
            )
            pod_free_storage = int(
                (pod["total"]["local_storage"] - pod["used"]["local_storage"]) / 1048576
            )
            print(
                f"POD {pod['id']} HAS:\n\t\tSTORAGE: {pod_free_storage}\tCORES: {pod_free_cores}\tMEMORY: {pod_free_memory}"
            )
            max_pod_memory_supported = int(pod_free_memory // (memory * num_VMs))
            max_pod_cores_supported = int(pod_free_cores // (cores * num_VMs))
            max_pod_storage_supported = int(pod_free_storage // (storage * num_VMs))
            print(
                f"Max VMs supported:\n\t\tSTORAGE: {max_pod_storage_supported}\t\tCORES: {max_pod_cores_supported}\tMEMORY: {max_pod_memory_supported}"
            )
            max_vm_supported_in_pod = min(
                min(
                    max_pod_memory_supported,
                    max_pod_cores_supported,
                    max_pod_storage_supported,
                ),
                vms_needed,
            )
            max_vm_supported_in_pod = (
                lambda max_vm_supported_in_pod: max_vm_supported_in_pod
                if (max_vm_supported_in_pod >= 0)
                else 0
            )(max_vm_supported_in_pod)
            print(f"Pod {pod['id']}, can support {max_vm_supported_in_pod} VM's.")
            pods_needed.extend([pod["id"]] * int(max_vm_supported_in_pod))
            if max_vm_supported_in_pod >= vms_needed:
                return pods_needed
            vms_needed -= max_vm_supported_in_pod
        raise Exception("KVM Host(s) do not have enough available resources.")

    def _set_interface(self, system, interface, cidr):
        self._run_maas_command(
            f"interface link-subnet {system} {interface} subnet={cidr} mode=AUTO"
        )

    def create_virtual_machine(self, vm_profile, num_VMs):
        # public_cidr = self._get_public_cidr(vm_profile["Public_VM_IP"])
        total_storage = (
            osias_variables.VM_Profile["HDD1"]
            + osias_variables.VM_Profile["HDD2"]
            + osias_variables.VM_Profile["HDD3"]
        )
        pod_id = self._get_pod_id(
            total_storage,
            osias_variables.VM_Profile["vCPU"],
            osias_variables.VM_Profile["RAM_in_MB"],
            num_VMs,
        )
        if vm_profile["Data_CIDR"]:
            osias_variables.VM_Profile.update(
                (k, vm_profile[k])
                for k in osias_variables.VM_Profile.keys() & vm_profile.keys()
            )
            interfaces = f"eno1:subnet_cidr={osias_variables.VM_Profile['Internal_CIDR']};eno2:subnet_cidr={osias_variables.VM_Profile['VM_DEPLOYMENT_CIDR']};eno3:subnet_cidr={osias_variables.VM_Profile['Data_CIDR']}"
        else:
            interfaces = f"eno1:subnet_cidr={osias_variables.VM_Profile['Internal_CIDR']};eno2:subnet_cidr={osias_variables.VM_Profile['VM_DEPLOYMENT_CIDR']}"
        server_list = []
        for _ in range(num_VMs):
            server = self._run_maas_command(
                f"vm-host compose {pod_id.pop()} cores={osias_variables.VM_Profile['vCPU']} memory={osias_variables.VM_Profile['RAM_in_MB']} 'storage=mylabel:{osias_variables.VM_Profile['HDD1']},mylabel:{osias_variables.VM_Profile['HDD2']},mylabel:{osias_variables.VM_Profile['HDD3']}' interfaces='{interfaces}'"
            )
            server_list.append(server["system_id"])

        machine_info = self._run_maas_command("machines read")
        self._waiting(server_list, "Ready")
        self._create_bridge_interface(
            server_list, osias_variables.VM_Profile["VM_DEPLOYMENT_CIDR"], machine_info
        )
        self._run_maas_command(
            f"tag update-nodes openstack_ready{''.join([' add=' + sub for sub in server_list])}"
        )

        return server_list

    def find_virtual_machines_and_tag(
        self, vm_profile, pipeline_id, vip, ip_end, ip_start
    ):
        no_of_vms = vm_profile["Number_of_VM_Servers"]
        release = vm_profile["OPENSTACK_RELEASE"].replace(".", "_")
        distro_hwe = osias_variables.MAAS_VM_DISTRO[vm_profile["OPENSTACK_RELEASE"]]
        distro = distro_hwe.split(" ")[0]
        machines = self._run_maas_command(
            "machines read | jq '.[] | {system_id:.system_id,status_name:.status_name,pool_name:.pool.name,ip_addresses:.ip_addresses,distro_series:.distro_series,tag_names:.tag_names}' --compact-output"
        )
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
            self.distro = distro_hwe
            self.deploy(server_list=machine_list)
            ids.extend(machine_list)
        tags = []
        tags.append(f"{pipeline_id}_{release}")
        tags.append(f"{pipeline_id}_{release}_vip-{vip.replace('.', '_')}")
        tags.append(f"{pipeline_id}_{release}_ip_end-{ip_end.replace('.', '_')}")
        tags.append(f"{pipeline_id}_{release}_ip_start-{ip_start.replace('.', '_')}")
        for tag in tags:
            self._run_maas_command(
                f"tags create name={tag} comment='Openstack {release} for {pipeline_id}'"
            )
        for vm in ids:
            for tag in tags:
                self._run_maas_command(f"tag update-nodes {tag} add={vm}")
            self._run_maas_command(f"tag update-nodes openstack_ready remove={vm}")
        return ids

    def find_virtual_machines_and_deploy(self, vm_profile, pipeline_id: int):
        release = vm_profile["OPENSTACK_RELEASE"].replace(".", "_")
        pipeline_tag_name = f"{pipeline_id}_{release}"
        machines = self._run_maas_command(
            "machines read | jq '.[] | {system_id:.system_id,status_name:.status_name,pool_name:.pool.name,ip_addresses:.ip_addresses,distro_series:.distro_series,tag_names:.tag_names}' --compact-output"
        )
        ids = []
        vip = ""
        ip_start = ""
        ip_end = ""
        for machine in machines:
            if (
                machine["tag_names"].__contains__(pipeline_tag_name)
                and machine["status_name"] == "Deployed"
            ):
                ids.append(machine["system_id"])
                for tag in machine["tag_names"]:
                    if "vip" in tag:
                        vip = tag.split("-")[1].replace("_", ".")
                    if "ip_start" in tag:
                        ip_start = tag.split("-")[1].replace("_", ".")
                    if "ip_end" in tag:
                        ip_end = tag.split("-")[1].replace("_", ".")
        dict_of_ids_and_ips = self._parse_ip_types(
            list(ids), list(machines), vm_profile
        )
        return dict_of_ids_and_ips, vip, ip_end, ip_start

    def delete_tags_and_ips(self, parent_project_pipeline_id, openstack_release=None):
        if openstack_release is None:
            filters = str(parent_project_pipeline_id)
        else:
            filters = f"{parent_project_pipeline_id}_{openstack_release.replace('.', '_')}"
        defs = self._run_maas_command(
            f"machines read |jq '.[] | {{system_id:.system_id,tag_names:.tag_names}} | select(.tag_names| contains([\"{filters}\"]))'"
        )
        vips = []
        starts = []
        machine_ids = []
        tags = []
        distro = osias_variables.MAAS_VM_DISTRO[openstack_release]
        if isinstance(defs, dict):
            defs = [defs]
        if defs:
            for i in defs:
                machine_ids.append(i["system_id"])
                vips.append([s for s in i["tag_names"] if "vip" in s][0])
                starts.append([s for s in i["tag_names"] if "start" in s][0])
                vips = list(dict.fromkeys(vips))
                starts = list(dict.fromkeys(starts))
                tags = tags + i["tag_names"]
            if len(vips) > 0:
                vips = [s.replace("_", ".").split("-")[1] for s in vips]
            if len(starts) > 0:
                starts = [s.replace("_", ".").split("-")[1] for s in starts]
            ips = vips + starts
            tags = [*set(tags)]
            for tag in tags:
                self._run_maas_command(f"tag delete {tag}")
            for ip in ips:
                self._run_maas_command(f"ipaddresses release ip={ip} force=true")
        return machine_ids, distro

    def delete_virtual_machines(self, machine_ids: list, distro: str):
        for machine_id in machine_ids:
            self._run_maas_command(f"machine release {machine_id}")
            self._run_maas_command(f"tag update-nodes openstack_ready add={machine_id}")
            self._waiting([f"{machine_id}"], "Ready")
            self._run_maas_command(
                f"machine deploy {machine_id} distro_series={distro}"
            )

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
