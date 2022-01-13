#!/usr/bin/python3

import json
import timeout_decorator
import time
import utils
import random
import ast


class maas_base:
    def __init__(self, distro):
        self.fs_type = "ext4"
        self.distro = distro

    def _run_maas_command(self, command):
        return json.loads(utils.run_cmd(f"maas admin {command}", output=False))

    def _check_for_raid(self, server_list):
        no_raid = []
        raid = []
        for server in server_list[:]:
            result = self._run_maas_command(f"raids read {server}")
            if result:
                raid.append(server)
            else:
                no_raid.append(server)
        return no_raid, raid

    def _create_boot_partitions(self, server):
        RAID_BOOT_IDS = []
        ALL_HDDS_IDS = []
        ALL_BLOCKDEVICES = self._run_maas_command(f"block-devices read {server}")
        for block in ALL_BLOCKDEVICES:
            ALL_HDDS_IDS.append(block["id"])
        for hdd in ALL_HDDS_IDS:
            BOOT_PART_ID = self._run_maas_command(
                f"partitions create {server} {hdd} size=2G bootable=yes"
            )
            RAID_BOOT_IDS.append(BOOT_PART_ID["id"])
        RAID_BOOT_IDS = ",".join([str(elem) for elem in RAID_BOOT_IDS])
        return RAID_BOOT_IDS

    def _create_root_partitions(self, server):
        RAID_ROOT_IDS = []
        ALL_HDDS_IDS = []
        ALL_BLOCKDEVICES = self._run_maas_command(f"block-devices read {server}")
        for block in ALL_BLOCKDEVICES:
            ALL_HDDS_IDS.append(block["id"])
        for hdd in ALL_HDDS_IDS:
            ROOT_PART_ID = self._run_maas_command(
                f"partitions create {server} {hdd} bootable=yes"
            )
            RAID_ROOT_IDS.append(ROOT_PART_ID["id"])
        RAID_ROOT_IDS = ",".join([str(elem) for elem in RAID_ROOT_IDS])
        return RAID_ROOT_IDS

    def _create_single_bootable_partition(self, server_list):
        for server in server_list[:]:
            ALL_BLOCKDEVICES = self._run_maas_command(f"block-devices read {server}")
            for block in ALL_BLOCKDEVICES:
                if "sda" in block["name"]:
                    device_id = block["id"]
            partition_id = self._run_maas_command(
                f"partitions create {server} {device_id} bootable=yes"
            )
            partition_id = partition_id["id"]
            self._run_maas_command(
                f"partition format {server} {device_id} {partition_id} fstype={self.fs_type} label='boot'"
            )
            self._run_maas_command(
                f"partition mount {server} {device_id} {partition_id} mount_point='/'"
            )

    def _create_software_raid_for_boot(self, server_list):
        for server in server_list[:]:
            RAID_BOOT_IDS = "{" + RAID_BOOT_IDS + "}"
            self._run_maas_command(
                f"raids create {server} name=md/boot level={self.raid_level} partitions={RAID_BOOT_IDS}"
            )
            self._run_maas_command(
                f"raids create {server} name=md/boot level={self.raid_level} partitions={RAID_BOOT_IDS}"
            )
            RAID_BOOT_ID = self._run_maas_command(f"block-devices read {server}")
            for section in RAID_BOOT_ID:
                if "md/boot" in section["name"]:
                    RAID_BOOT_ID = section["id"]
            self._run_maas_command(
                f"block-device format {server} {RAID_BOOT_ID} fstype={self.fs_type} label='boot'"
            )
            self._run_maas_command(
                f"block-device mount {server} {RAID_BOOT_ID} mount_point='/boot'"
            )

    def _create_software_raid_for_root(self, server_list):
        for server in server_list[:]:
            print(f"INFO: Creating RAID on {server}")
            RAID_ROOT_IDS = self._create_root_partitions(server)
            RAID_ROOT_IDS = "{" + RAID_ROOT_IDS + "}"
            RAID_ROOT_ID = self._run_maas_command(
                f"raids create {server} name='md/root' level={self.raid_level} partitions={RAID_ROOT_IDS}"
            )
            RAID_ROOT_ID = self._run_maas_command(f"block-devices read {server}")
            for section in RAID_ROOT_ID:
                if "md/root" in section["name"]:
                    RAID_ROOT_ID = section["id"]
            self._run_maas_command(
                f"block-device format {server} {RAID_ROOT_ID} fstype={self.fs_type} label='root'"
            )
            self._run_maas_command(
                f"block-device mount {server} {RAID_ROOT_ID} mount_point='/'"
            )

    def _delete_all_bcache(self, server_list):
        for server in server_list[:]:
            BCACHE_DEVICE_IDS = self._run_maas_command(f"bcaches read {server}")
            for ID in BCACHE_DEVICE_IDS:
                bcache_id = ID["id"]
                utils.run_cmd(
                    f"maas admin bcache delete {server} {bcache_id}", output=False
                )
            BCACHE_CACHE_SETS = self._run_maas_command(
                f"bcache-cache-sets read {server}"
            )
            for ID in BCACHE_CACHE_SETS:
                BCACHE_CACHE_SETS_ID = ID["id"]
                utils.run_cmd(
                    f"maas admin bcache-cache-set delete {server} {BCACHE_CACHE_SETS_ID}",
                    output=False,
                )

    def _delete_all_partitions(self, server_list):
        for server in server_list[:]:
            PARTITIONS = self._run_maas_command(f"block-devices read {server}")
            for block in PARTITIONS:
                if block["partitions"]:
                    partition_id = block["partitions"][0]["id"]
                    device_id = block["partitions"][0]["device_id"]
                    utils.run_cmd(
                        f"maas admin partition delete {server} {device_id} {partition_id}",
                        output=False,
                    )

    def _delete_all_raids(self, server_list=None):
        if server_list:
            server_list = server_list
        else:
            server_list = self.machine_list
        for server in server_list[:]:
            machine_list = self._run_maas_command(f"raids read {server}")
            MD_DEVICES = []
            for raid in machine_list:
                MD_DEVICES.append(raid["id"])
            for device in MD_DEVICES:
                utils.run_cmd(f"maas admin raid delete {server} {device}", output=False)

    def _find_machine_ids(self):
        machine_list = self._run_maas_command(f"machines read")
        deployment_list = []
        for machine in machine_list:
            check = any(item in self.public_ips for item in machine["ip_addresses"])
            if check:
                deployment_list.append(machine["system_id"])
        self.machine_list = deployment_list
        return deployment_list

    def _release(self, server_list):
        for machine in server_list[:]:
            self._run_maas_command(f"machine release {machine}")
        self._waiting(server_list, "Ready")

    def _wipe_drives_create_software_raid(self, server_list):
        no_raid, raided_servers = self._check_for_raid(server_list)
        if no_raid:
            print("INFO: Step 1/3 - Delete All Partitions")
            self._delete_all_partitions(no_raid)
            print("INFO: Step 2/3 - Delete All BCache")
            self._delete_all_bcache(no_raid)
            print("INFO: Step 3/3 - Create Software RAID for Root")
            self._create_software_raid_for_root(no_raid)

    def _wipe_drives_create_osds(self, server_list):
        no_raid, raided_servers = self._check_for_raid(server_list)
        if raided_servers:
            print("INFO: Step 1/4 - Delete All RAIDs")
            self._delete_all_raids(raided_servers)
            print("INFO: Step 2/4 - Delete All Partitions")
            self._delete_all_partitions(raided_servers)
            print("INFO: Step 3/4 - Delete All BCache")
            self._delete_all_bcache(raided_servers)
            print("INFO: Step 4/4 - Creating Single Bootable Partition")
            self._create_single_bootable_partition(raided_servers)

    @timeout_decorator.timeout(2500, timeout_exception=StopIteration)
    def _waiting(self, server_list, desired_status):
        while len(server_list) > 0:
            machine_info_list = self._run_maas_command(f"machines read")
            for server in server_list[:]:
                for machine in machine_info_list:
                    if server in machine["system_id"]:
                        current_status = machine["status_name"]
                        status_message = machine["status_message"]
                        print(
                            f"SERVER: {server} - CURRENT STATUS: {current_status} - {status_message} - DESIRED STATUS: {desired_status}\n"
                        )
                        if current_status == desired_status:
                            print("STATE: COMPLETE.")
                            server_list.remove(server)
                            break
                        elif current_status == "Failed deployment":
                            print("STATE: Re-deploying.")
                            self.deploy([server])
                        elif current_status == "Failed commissioning":
                            print("STATE: Commissioning Failed, exiting.")
                            break
                        else:
                            print("STATE: Waiting")
                    else:
                        continue
            if len(server_list) > 0:
                print("Sleeping 30 seconds.")
                time.sleep(30)
            else:
                continue
        print("All servers have reached the desired state.")

    def deploy(self, server_list=None):
        if server_list:
            server_list = server_list
        else:
            server_list = self.machine_list
        self._release(server_list[:])
        print("Info: Removing RAIDs and creating OSD's")
        self._wipe_drives_create_osds(server_list)
        for machine in server_list[:]:
            self._run_maas_command(
                f"machine deploy {machine} distro_series={self.distro}"
            )
        self._waiting(server_list[:], "Deployed")

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

    def get_machines_info(self):
        return self._run_maas_command(f"machines read")

    def get_ip_pool(self, cidr: str, gap: int):
        time.sleep(int(random.uniform(0, 60)))
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
                self._run_maas_command(f"ipaddresses reserve ip={first_ip}")
                self._run_maas_command(f"ipaddresses reserve ip={last_ip}")
                ip_pool = [
                    prefix + "." + str(i)
                    for i in range(first_ip_last_octet + 1, last_ip_last_octet + 1)
                ]
                return ip_pool
        else:
            print("No more valid IPs available")
            return 1

    def release_ip_pool(self, vip: str, ips_needed: int):
        self._run_maas_command(f"ipaddresses release {vip}")
        prefix = vip[: vip.rfind(".")]
        first_ip = f"{prefix}.{int(vip.split('.')[-1]) - ips_needed}"
        self._run_maas_command(f"ipaddresses release {first_ip}")

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
