#!/usr/bin/python3

import os
import subprocess
from itertools import islice
from pathlib import Path

import yaml

import osias_variables
from ssh_tool import ssh_tool


class parser:
    def __init__(self, config):
        self.data = yaml.safe_load(config)
        self.kolla_configs = {}

    def get_server_ips(self, node_type, ip_type):
        data = self.data[node_type]
        ips = []
        for myips in data:
            ips.append(myips[ip_type])
        return ips

    def get_variables(self, variable, openstack_release=None):
        if "variables" in self.data and variable in self.data["variables"]:
            data = self.data["variables"]
            if variable in data:
                return str(data[variable])
        elif getattr(osias_variables, variable):
            x = getattr(osias_variables, variable)
            return x[openstack_release]
        return None

    def get_kolla_configs(self):
        if "etc" in self.data:
            data = self.data["etc"]
            results = {}
            results = self.find_strings(data, data)
            return results
        return None

    def find_paths(self, nested_dict, value, prepath=()):
        def yielder(nested_dict, value, prepath=()):
            for k, v in nested_dict.items():
                path = prepath + (k,)
                if v == value:  # found value
                    path = ("/etc", *path)
                    dest = "/".join(path)
                    yield dest
                elif hasattr(v, "items"):  # v is a dict
                    yield from yielder(v, value, path)

        return list(yielder(nested_dict, value, prepath=()))

    def find_strings(self, nested_dict, orig_dict):
        for key, value in nested_dict.items():
            if isinstance(value, dict):
                self.find_strings(value, orig_dict)
            if isinstance(value, str):
                x = *self.find_paths(orig_dict, value), value
                for i in range(len(x)):
                    if i != len(x) - 1:
                        self.kolla_configs[x[i]] = x[len(x) - 1]
        return self.kolla_configs

    def get_all_ips_type(self, iptype):
        data = ["control", "network", "storage", "compute", "monitor"]
        ALL_IPS = []
        for my_node_type in data:
            ips = parser.get_server_ips(self, node_type=my_node_type, ip_type=iptype)
            ALL_IPS.extend(ips)
        ALL_IPS = list((dict.fromkeys(ALL_IPS)))  # remove duplicates from list
        ALL_IPS = list(filter(None, ALL_IPS))  # remove null values from list

        if not ALL_IPS and iptype != "data":
            raise Exception(f"{iptype} IPs are not set, empty list.")
        return ALL_IPS

    def get_each_servers_ips(self):
        data = self.data.keys()
        SERVERS = []
        for my_node_type in data:
            data = self.data.get(my_node_type)
            for key, value in data.items():
                if value["public"]:  # Remove any empty servers
                    SERVERS.extend([value])
                    # Remove duplicate servers from the list
        SERVERS = [i for n, i in enumerate(SERVERS) if i not in SERVERS[:n]]
        return SERVERS

    def bool_check_ips_exist(self, node_type, ip_type):
        data = self.data[node_type]
        for item in data:
            return bool(item[ip_type])


def convert_to_list(parm):
    if isinstance(parm, str):
        tmpList = []
        tmpList.append(parm)
        return tmpList
    return parm


def merge_dictionaries(default_dictionary, user_input_dictionary):
    """Merges user_input_dictionary into default dictionary;
    default values will be overwritten by users input."""
    return {**default_dictionary, **user_input_dictionary}


def create_ssh_client(target_node):
    client = ssh_tool("ubuntu", target_node)
    if not client.check_access():
        raise Exception(
            f"ERROR: Failed to connect to target node with IP {target_node} using SSH"
        )
    return client


def copy_file_on_server(script, servers):
    servers = convert_to_list(servers)
    for server in servers:
        client = create_ssh_client(server)
        client.scp_to(script)


def run_script_on_server(script, servers, args=None):
    servers = convert_to_list(servers)
    for server in servers:
        client = create_ssh_client(server)
        client.scp_to(script)
        if args:
            arguments = ""
            for arg in args:
                arguments += "".join((' "', arg, '"'))
            cmd = "".join((script, arguments))
        else:
            cmd = script

        print(cmd)
        client.ssh("".join(("source ", cmd)))


def run_cmd_on_server(cmd, servers):
    servers = convert_to_list(servers)
    for server in servers:
        client = create_ssh_client(server)
        client.ssh(cmd)


def run_cmd(command, test=True, output=True):
    print(f"\nCommand Issued: \n\t{command}\n")
    stdout = None
    try:
        stdout = subprocess.check_output(
            command, stderr=subprocess.STDOUT, shell=True, executable="/bin/bash"
        )
    except subprocess.CalledProcessError as e:
        if test:
            raise Exception(e.output.decode()) from e
        print(e.output.decode())
    if output:
        print(f"\nCommand Output: \n{stdout.decode()}\n")
    return stdout


def check_ip_active(IP):
    response = os.system("ping -c 1 " + IP + " > /dev/null 2>&1")
    if response == 0:
        print(f"Ping shows {IP} is in use (packets received)!")
        return True
    else:
        print(f"Ping shows {IP} is NOT in use (packets lost)!")
        return False


def check_private_ip_active(public_ip: str, private_ips: list):
    result = {}
    result["active"] = []
    result["inactive"] = []
    for private_ip in private_ips:
        try:
            run_cmd_on_server(
                "ping -c 1 " + private_ip + " > /dev/null 2>&1", public_ip
            )
            print(f"INFO: Ping shows {private_ip} is in use (packets received)!")
            result["active"].append(private_ip)
        except:
            print(f"INFO: Ping shows {private_ip} is NOT in use (packets lost)!")
            result["inactive"].append(private_ip)
    return result


def create_kolla_config_files(data: dict):
    with open("write_kolla_configs.sh", "w") as f:
        f.write("#!/bin/bash")
        f.write("\n\n")
        f.write("set -euxo pipefail")
        f.write("\n\n")
        for file_location, file_contents in data.items():
            directory = Path(file_location).parent
            f.write(f"mkdir -p {directory}/ && touch {file_location}\n")
            f.write(f"cat >> {file_location} << __EOF__\n")
            f.write(f"{file_contents}\n")
            f.write("__EOF__\n")


def create_multinode(input_dictionary, optional_variables):
    control_items = list(islice(input_dictionary.items(), 3))
    monitor_item = list(islice(input_dictionary.items(), 1))
    control_labels = ["control", "network"]
    secondary_labels = ["storage", "compute"]
    monitor_label = ["monitor"]
    multinode = {}
    for label in control_labels:
        multinode[label] = []
        for i, value in enumerate(control_items):
            multinode[label].append(i)
            multinode[label][i] = {}
            multinode[label][i]["public"] = value[1]["public"]
            multinode[label][i]["private"] = value[1]["internal"]
            multinode[label][i]["data"] = value[1]["data"]
    for label in secondary_labels:
        multinode[label] = []
        for i, (k, v) in enumerate(input_dictionary.items()):
            multinode[label].append(i)
            multinode[label][i] = {}
            multinode[label][i]["public"] = v["public"]
            multinode[label][i]["private"] = v["internal"]
            multinode[label][i]["data"] = v["data"]
    for label in monitor_label:
        multinode[label] = []
        for i, (k, v) in enumerate(monitor_item):
            multinode[label].append(i)
            multinode[label][i] = {}
            multinode[label][i]["public"] = v["public"]
            multinode[label][i]["private"] = v["internal"]
            multinode[label][i]["data"] = v["data"]
    multinode["variables"] = {}
    optional_variables = dict(
        [
            (x.split(":")[0].strip(), x.split(":")[1].strip("' "))
            for x in optional_variables.strip("{}").split(",")
        ]
    )
    multinode["variables"].update(optional_variables)
    return multinode


def create_new_ssh_key():
    cleanup_cmd = "rm -f deploy_id_rsa"
    run_cmd(cleanup_cmd)
    cleanup_cmd = "rm -f deploy_id_rsa.pub"
    run_cmd(cleanup_cmd)

    create_key_cmd = "ssh-keygen -q -t rsa -N '' -f ./deploy_id_rsa"
    run_cmd(create_key_cmd)

    with open("deploy_id_rsa", "r") as f:
        ssh_priv_key = f.read()
    with open("deploy_id_rsa.pub", "r") as f:
        ssh_public_key = f.read()

    cleanup_cmd = "rm -f deploy_id_rsa"
    run_cmd(cleanup_cmd)
    cleanup_cmd = "rm -f deploy_id_rsa.pub"
    run_cmd(cleanup_cmd)

    return ssh_priv_key, ssh_public_key


def check_required_keys_not_null(required_keys, input_dictionary):
    for key in required_keys:
        if (key in input_dictionary) and (input_dictionary[key] != ""):
            return True
        raise Value_Required_to_Proceed(key)


def is_vm_pool_enabled(pool_start, pool_end):
    return bool(pool_start != pool_end)


class Value_Required_to_Proceed(ValueError):
    pass
