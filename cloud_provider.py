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


class CloudProvider:
    def __init__(self, vm_profile, credentials: dict):
        cloud = vm_profile["DEPLOYMENT_CLOUD"].lower()
        cloud_url = credentials["cloud_url"]
        cloud_pass = credentials["cloud_pass"]
        operating_system = osias_variables.MAAS_VM_DISTRO[vm_profile["OPENSTACK_RELEASE"]]
        parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
        if not parent_project_pipeline_id:
            raise Exception("ERROR: <PARENT_PIPELINE_ID> is needed, please set it.")
        if cloud == "maas":
            # deploy.py stuff
            cloud_user = "admin"
            utils.run_cmd(f"maas login {cloud_user} {cloud_url} {cloud_pass}")
            self.provider = maas.virtual.MaasVirtual(operating_system)

    def tag_virtual_servers(self):
        """Find virtual machines and tag them with the pipeline ID and openstack branch.
        If VMs aren't available, they will be created.  Additionally, this will find an available
        IP range and create tags associated to them. An IP range will be used where the VIP is the last
        IP and the pool start IP is the beginning, the pool end IP will be calculated in the multinode
        file generation."""
        # parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
        # if not parent_project_pipeline_id:

            # raise Exception("ERROR: <PARENT_PIPELINE_ID> is needed, please set it.")
        osias_variables.VM_Profile.update(vm_profile.items())
        
        if self.cloud == "maas":
            public_IP_pool = self.provider.get_ip_pool(
                osias_variables.VM_Profile["VM_DEPLOYMENT_CIDR"],
                osias_variables.VM_Profile["IPs_NEEDED"],
            )
            self._verify_vm_pool_availability(vm_profile, public_IP_pool)
            VIP_ADDRESS = str(public_IP_pool.pop())
            POOL_END_IP = str(public_IP_pool.pop())
            POOL_START_IP = str(public_IP_pool.pop(0))
        self.provider.find_virtual_machines_and_tag(
            vm_profile,
            parent_project_pipeline_id,
            VIP_ADDRESS,
            POOL_END_IP,
            POOL_START_IP,
        )


    def create_virtual_servers(maas_url, maas_api_key, vm_profile, ceph_enabled):
        # parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
        # if not parent_project_pipeline_id:
            # raise Exception("ERROR: <PARENT_PIPELINE_ID> is needed, please set it.")
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
        # parent_project_pipeline_id = os.getenv("PARENT_PIPELINE_ID", "")
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

    def _verify_vm_pool_availability(vm_profile, public_IP_pool):
        internal_subnet = ".".join(vm_profile["Internal_CIDR"].split(".")[:3])
        VIP_ADDRESS_SUFFIX = public_IP_pool[-1].split(".")[-1]
        vip_internal = ".".join((internal_subnet, VIP_ADDRESS_SUFFIX))
        active_ips = []
        for ip in public_IP_pool:
            active_ips.append(utils.check_ip_active(ip))
        active_ips.append(utils.check_ip_active(vip_internal))
        if True in active_ips:
            raise Exception(f"\nERROR: There were {active_ips.count(True)} errors.\n")