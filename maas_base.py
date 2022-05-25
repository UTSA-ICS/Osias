#!/usr/bin/python3

import copy
import json
import timeout_decorator
import time
import utils
import random
import osias_variables
import ast
from ipaddress import IPv4Network, IPv4Address


class MaasBase:
    def __init__(self, distro):
        self.fs_type = "ext4"
        self.distro = distro

    def _run_maas_command(self, command):
        result = utils.run_cmd(f"maas admin {command}", output=False)
        if result == b"":
            return result
        try:
            return json.loads(result)
        except ValueError:
            result = result.decode("utf-8")
            result = result.rstrip()
            result = result.replace("null", "'Null'")
            result = [ast.literal_eval(i) for i in result.split("\n")]
            return result

    def _find_machine_ids(self):
        machine_list = self._run_maas_command("machines read")
        deployment_list = []
        for machine in machine_list:
            check = any(item in self.public_ips for item in machine["ip_addresses"])
            if check:
                deployment_list.append(machine["system_id"])
        self.machine_list = deployment_list
        return deployment_list

    def _get_all_used_ips(self, cidr: str):
        reserved_ips = self._run_maas_command(f"subnet reserved-ip-ranges {cidr}")
        used_ips = []
        for item in reserved_ips:
            start = item["start"]
            ip0 = int(start.split(".")[-1])
            num_ips = item["num_addresses"]
            prefix = start[: start.rfind(".")]  # first 3 octets of cidr
            ip_list = range(ip0, ip0 + num_ips)
            for ip in ip_list:
                used_ips.append(f"{prefix}.{ip}")
        return used_ips

    def _parse_ip_types(self, machine_ids: list, machine_info: list, vm_profile=None):
        """Given a list of servers and machine info, return a parsed list of info."""
        results = {}
        for machine in machine_ids:
            for info in machine_info:
                if machine == info["system_id"]:
                    ips = info["ip_addresses"]
                    temp = {}
                    for cidr in ["Internal_CIDR", "Data_CIDR", "VM_DEPLOYMENT_CIDR"]:
                        if vm_profile:
                            fixed_cidr = osias_variables.VM_Profile.update(
                                (k, vm_profile[k])
                                for k in osias_variables.VM_Profile.keys()
                                & vm_profile.keys()
                            )
                        else:
                            fixed_cidr = osias_variables.VM_Profile[cidr]

                        for ip in ips:
                            if (
                                IPv4Address(ip) in IPv4Network(fixed_cidr)
                                and cidr == "Internal_CIDR"
                            ):
                                label = "internal"
                            if (
                                IPv4Address(ip) in IPv4Network(fixed_cidr)
                                and cidr == "Data_CIDR"
                            ):
                                label = "data"
                            if (
                                IPv4Address(ip) in IPv4Network(fixed_cidr)
                                and cidr == "VM_DEPLOYMENT_CIDR"
                            ):
                                label = "public"
                            temp[label] = ip
                    results[machine] = temp
        print(results)
        return results

    def _release(self, server_list):
        for machine in server_list[:]:
            self._run_maas_command(f"machine release {machine}")
        self._waiting(server_list, "Ready")

    @timeout_decorator.timeout(2500, timeout_exception=StopIteration)
    def _waiting(self, server_list: list, desired_status: str):
        timer_loop_counter = 1
        servers = copy.deepcopy(server_list)
        print(f"Waiting for {servers} to reach desired state, {desired_status}.")
        while len(servers) > 0:
            if len(servers) == 1:
                read_cmd = f"machine read {servers[0]} | jq '"
            else:
                read_cmd = "machines read | jq '.[] | "
            fields = "{system_id:.system_id,status_name:.status_name,status_message:.status_message,pool_name:.pool.name,ip_addresses:.ip_addresses}' --compact-output"
            machine_info_list = self._run_maas_command(f"{read_cmd}{fields}")
            if isinstance(machine_info_list, dict):
                # `machine read` returns dict, `machines read` returns a list
                machine_info_list = [machine_info_list]
            for server in servers[:]:
                for machine in machine_info_list:
                    if server in machine["system_id"]:
                        current_status = machine["status_name"]
                        status_message = machine["status_message"]
                        print(
                            f"SERVER: {server} - CURRENT STATUS: {current_status} - {status_message} - DESIRED STATUS: {desired_status}\n"
                        )
                        if current_status == desired_status:
                            print("STATE: COMPLETE.")
                            servers.remove(server)
                            break
                        elif current_status == "Failed deployment":
                            self._run_maas_command(f"machine release {server}")
                            self._waiting([server], "Ready")
                            print("STATE: Re-deploying.")
                            self.deploy([server])
                        elif current_status == "Failed commissioning":
                            print("STATE: Commissioning Failed, exiting.")
                            break
                        else:
                            print("STATE: Waiting")
                    else:
                        continue
            if len(servers) > 0:
                # This will slowly speed up the timer, reducing time as follows: [30, 23, 20, 18, 17, 16, 15, 15, 14, ...]
                ttime = int((30 / timer_loop_counter ** (1 / 3)))
                print(f"Sleeping {ttime} seconds.")
                time.sleep(ttime)
                timer_loop_counter = timer_loop_counter + 1
            else:
                continue
        print("All servers have reached the desired state.")
        return machine_info_list

    def deploy(self, server_list=None):
        if server_list:
            server_list = server_list
        else:
            server_list = self.machine_list
        for machine in server_list[:]:
            self._run_maas_command(
                f"machine deploy {machine} distro_series={self.distro}"
            )
        machine_info = self._waiting(server_list[:], "Deployed")
        return self._parse_ip_types(list(server_list), list(machine_info))

    def get_machines_info(self):
        return self._run_maas_command("machines read")

    def get_ip_pool(self, cidr: str, gap: int):
        used_ips = self._get_all_used_ips(cidr)

        sorted_list_of_ips = []
        for ip in sorted(used_ips, key=lambda ip: [int(ip) for ip in ip.split(".")]):
            sorted_list_of_ips.append(ip)
        ips_available = [
            abs(int(x[1].split(".")[-1]) - int(x[0].split(".")[-1]))
            for x in zip(sorted_list_of_ips[1:], sorted_list_of_ips)
        ]

        for index, diff in enumerate(ips_available):
            if diff > gap:
                prefix = sorted_list_of_ips[index][
                    : sorted_list_of_ips[index].rfind(".")
                ]  # first 3 octets of cidr
                if diff > gap:
                    first_ip_last_octet = random.randint(
                        int(sorted_list_of_ips[index].split(".")[-1]) + 1,
                        int(sorted_list_of_ips[index].split(".")[-1])
                        + ips_available[index]
                        - gap,
                    )
                last_ip_last_octet = first_ip_last_octet + gap - 1
                first_ip = f"{prefix}.{first_ip_last_octet}"
                last_ip = f"{prefix}.{last_ip_last_octet}"
                self._run_maas_command(f"ipaddresses reserve ip={last_ip}")
                self._run_maas_command(f"ipaddresses reserve ip={first_ip}")
                ip_pool = [
                    prefix + "." + str(i)
                    for i in range(first_ip_last_octet, last_ip_last_octet + 1)
                ]
                return ip_pool
        else:
            print("No more valid IPs available")
            return 1

    def release_ip_pool(self, *ips):
        for ip in ips:
            self._run_maas_command(f"ipaddresses release ip={ip}")

    def set_machine_list(self):
        self.machine_list = self._find_machine_ids()

    def set_public_ip(self, public_ips):
        self.public_ips = public_ips
        self.machine_list = self._find_machine_ids()

    def set_raid(self, raid):
        if raid:
            self.raid = True
        else:
            self.raid = False
