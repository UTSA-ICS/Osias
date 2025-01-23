#!/usr/bin/python3

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
        self.cloud = credentials.get("cloud_provider")
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
            (
                server_dict,
                VIP_ADDRESS,
                POOL_END_IP,
                POOL_START_IP,
            ) = self.provider.find_virtual_machines_and_deploy(
                self.vm_profile, self.parent_project_pipeline_id
            )

        if self.cloud == "proxmox":
            POOL_START_IP = "10.245.124.237"
            POOL_END_IP = "10.245.124.248"
            VIP_ADDRESS = "10.245.124.249"
            self.vm_profile = self.create_vm_profile()
            server_dict = self.provider.create_vms(self.vm_profile)
        print(f"server_dict: {server_dict}")
        if ceph_enabled is None:
            ceph_enabled = False
        optional_vars = self.vm_profile
        optional_vars["CEPH"] = ceph_enabled
        optional_vars["POOL_START_IP"] = POOL_START_IP
        optional_vars["POOL_END_IP"] = POOL_END_IP
        optional_vars["VIP_ADDRESS"] = VIP_ADDRESS
        multinode = utils.create_multinode(server_dict, yaml.dump(optional_vars))
        print(f"Generated multinode is: {multinode}")
        f = open("MULTINODE.env", "w")
        f.write(f"{multinode}")
        f.close()

    def delete_tags_and_ips(self, openstack_release=None):
        if not self.parent_project_pipeline_id:
            raise Exception("ERROR: PARENT_PIPELINE_ID is needed.")

        return self.provider.delete_tags_and_ips(
            self.parent_project_pipeline_id, openstack_release
        )

    def delete_virtual_machines(self, openstack_release):
        machine_ids, distro = self.delete_tags_and_ips(openstack_release)
        self.provider.delete_virtual_machines(machine_ids, distro)

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
            vm_name = f"{variables.PROXMOX_NAME}_{i + 1}_{self.parent_pipeline_id}"
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
        result = generate_vm_specs(args, profiles=profiles)

        return result
