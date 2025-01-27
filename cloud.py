#!/usr/bin/python3
import json

import ast
import os
import yaml

import maas_virtual
import osias_variables
import utils
from cloud_provider.cloud_provider import CloudProvider as PythonAPI
from cloud_provider.cloud_proxmox import ProxMox
from cloud_provider.vm_profile import generate_vm_specs
import variables



class Cloud:
    def __init__(self, vm_profile, credentials: dict):
        self.vm_profile = vm_profile or {}
        self.cloud = credentials.get("cloud_provider").lower()
        self.openstack_release = self.vm_profile.get(
            "OPENSTACK_RELEASE", "default_release"
        )
        cloud_url = credentials["cloud_url"]
        cloud_pass = credentials["cloud_pass"]
        operating_system = osias_variables.MAAS_VM_DISTRO.get(
            self.openstack_release, "default_os"
        )
        self.parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
        if not self.parent_project_pipeline_id:
            raise Exception("ERROR: <PARENT_PIPELINE_ID> is needed, please set it.")
        if self.cloud == "maas":
            cloud_user = "admin"
            utils.run_cmd(f"maas login {cloud_user} {cloud_url} {cloud_pass}")
            self.provider = maas_virtual.MaasVirtual(operating_system)

        elif self.cloud == "proxmox":
            cloud_url = os.getenv("PROXMOX_CLOUD_URL")
            cloud_user = os.getenv("PROXMOX_CLOUD_USER")
            cloud_pass = os.getenv("PROXMOX_CLOUD_PASS")
            self.provider = PythonAPI(
                provider = ProxMox,
                url = cloud_url,
                username= cloud_user,
                password = cloud_pass,
            )

    def tag_virtual_servers(self):
        """Find virtual machines and tag them with the pipeline ID and openstack branch.
        If VMs aren't available, they will be created.  Additionally, this will find an available
        IP range and create tags associated to them. An IP range will be used where the VIP is the last
        IP and the pool start IP is the beginning, the pool end IP will be calculated in the multinode
        file generation."""
        osias_variables.VM_Profile.update(self.vm_profile.items())

        if self.cloud == "maas":
            public_IP_pool = self.provider.get_ip_pool(
                osias_variables.VM_Profile["VM_DEPLOYMENT_CIDR"],
                osias_variables.VM_Profile["IPs_NEEDED"],
            )
            self.verify_vm_pool_availability(public_IP_pool)
            VIP_ADDRESS = str(public_IP_pool.pop())
            POOL_END_IP = str(public_IP_pool.pop())
            POOL_START_IP = str(public_IP_pool.pop(0))
            self.provider.find_virtual_machines_and_tag(
                self.vm_profile,
                self.parent_project_pipeline_id,
                VIP_ADDRESS,
                POOL_END_IP,
                POOL_START_IP,
            )

    def create_virtual_servers(self, ceph_enabled):
        if self.cloud == "maas":
            print(f"Working in a {self.cloud} environment.")
            (
                server_dict,
                VIP_ADDRESS,
                POOL_END_IP,
                POOL_START_IP,
            ) = self.provider.find_virtual_machines_and_deploy(
                self.vm_profile, self.parent_project_pipeline_id
            )
        elif self.cloud == "proxmox":
            print(f"Working in a {self.cloud} environment.")
            POOL_START_IP = "10.245.124.237"
            POOL_END_IP = "10.245.124.248"
            VIP_ADDRESS = "10.245.124.249"
            DNS_IP = "10.250.53.202"

            # Debug: Ensure VM profile creation is correct
            self.vm_profile = self.create_vm_profile()
            print(f"[DEBUG] VM Profile: {self.vm_profile}")

            # Debug: Ensure VM creation returns a valid server_dict
            server_dict = self.provider.create_vms(self.vm_profile)
            print(f"[DEBUG] Server Dict: {json.dumps(server_dict, indent=4)}")

            # Debug: Save server_dict to file for additional inspection
            with open("vm_info.json", "w") as f:
                json.dump(server_dict, f, indent=4)
            print("[DEBUG] VM information written to vm_info.json")

        # Debug: Check initial value of ceph_enabled
        print(f"[DEBUG] Original ceph_enabled: {ceph_enabled}")
        if ceph_enabled is None:
            ceph_enabled = False
        elif isinstance(ceph_enabled, str):
            try:
                ceph_enabled = ast.literal_eval(ceph_enabled.title())
                print(f"[DEBUG] Evaluated ceph_enabled: {ceph_enabled}")
            except Exception as e:
                print(f"[ERROR] Failed to evaluate ceph_enabled: {e}")

        # Debug: Validate optional_vars before dumping to YAML
        optional_vars = self.vm_profile
        optional_vars["CEPH"] = ceph_enabled
        optional_vars["POOL_START_IP"] = POOL_START_IP
        optional_vars["POOL_END_IP"] = POOL_END_IP
        optional_vars["VIP_ADDRESS"] = VIP_ADDRESS
        if self.cloud == "proxmox":
            optional_vars["DNS_IP"] = DNS_IP
        print(f"[DEBUG] Optional Vars Before Dump: {optional_vars}")

        # Debug: Check the YAML dump of optional_vars
        dumped_vars = yaml.dump(optional_vars)
        print(f"[DEBUG] YAML Dump of Optional Vars:\n{dumped_vars}")

        # Debug: Ensure create_multinode is receiving valid inputs
        multinode = utils.create_multinode(server_dict, dumped_vars)
        print(f"[DEBUG] Generated Multinode: {json.dumps(multinode, indent=4)}")

        # Debug: Write the multinode output to a file
        with open("MULTINODE.env", "w") as f:
            f.write(f"{multinode}")
        print("[DEBUG] MULTINODE.env file written successfully.")

    def delete_tags_and_ips(self, openstack_release=None):
        if not self.parent_project_pipeline_id:
            raise Exception("ERROR: PARENT_PIPELINE_ID is needed.")

        return self.provider.delete_tags_and_ips(
            self.parent_project_pipeline_id, openstack_release
        )

    def delete_virtual_machines(self, openstack_release, vm_info):
        if self.cloud == "maas":
            machine_ids, distro = self.delete_tags_and_ips(openstack_release)
            self.provider.delete_virtual_machines(machine_ids, distro)
        elif self.cloud == "proxmox":
            ip_list = [vm["public_ip"] for vm in vm_info.values()]
            ids_to_delete = self._get_vm_ids_by_ips(ip_list)
            self.provider.delete_vms(ids_to_delete)

    def verify_vm_pool_availability(self, public_IP_pool):
        internal_subnet = ".".join(self.vm_profile["Internal_CIDR"].split(".")[:3])
        VIP_ADDRESS_SUFFIX = public_IP_pool[-1].split(".")[-1]
        vip_internal = ".".join((internal_subnet, VIP_ADDRESS_SUFFIX))
        active_ips = []
        for ip in public_IP_pool:
            active_ips.append(utils.check_ip_active(ip))
        active_ips.append(utils.check_ip_active(vip_internal))
        if True in active_ips:
            raise Exception(f"\nERROR: There were {active_ips.count(True)} errors.\n")

    def create_vm_profile(self):
        """
        Generate VM profiles for the given number of VMs using the provided specifications
        and create the VM specs using generate_vm_specs.
        """
        profiles = []

        # Get the number of VMs to generate
        number_of_vms = int(self.vm_profile.get("Number_of_VM_Servers", 1))

        # Generate VM profiles
        for i in range(number_of_vms):
            vm_name = f"{variables.PROXMOX_NAME}-{i + 1}-{self.parent_project_pipeline_id}"
            profiles.append(
                {
                    "name": vm_name,
                    "count": 1,
                    "hd": variables.PROXMOX_HD,
                    "os": variables.PROXMOX_TEMPLATE_NAME,
                    "ram": variables.PROXMOX_RAM,
                    "vCPU": variables.PROXMOX_VCPU,
                    "network": {"bridge_name": variables.PROXMOX_NETWORK_BRIDGE},
                }
            )

        # Create args with the cloud provider
        class Args:
            cloud_vendor = self.cloud

        args = Args()
        # Generate VM specs using the generated profiles
        print(f"VM Profiles: {profiles}")
        result = generate_vm_specs(args, profiles=profiles)
        print(f"THIS IS THE PROFILE: {result}")
        return result

    def _get_vm_ids_by_ips(self, ip_list):
        """
        Helper method to get VM IDs based on a list of IP addresses.
        :param ip_list: List of IP addresses.
        :return: List of corresponding VM IDs.
        :raises ValueError: If any IP address does not map to a VM ID.
        """
        vm_ids = []

        for ip in ip_list[:]:
            vm_id = self.provider.get_vm_id_by_ip(ip)
            if vm_id:
                vm_ids.append(vm_id)
                ip_list.remove(ip)

        # If there are any remaining IPs, raise an exception
        if ip_list:
            raise ValueError(
                f"No VM ID found for the following IP addresses: {ip_list}"
            )

        return vm_ids
