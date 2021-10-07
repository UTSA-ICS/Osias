#!/usr/bin/python3

import toml
import subprocess
from ssh_tool import ssh_tool
from itertools import islice
import osias_variables


class parser:
    def __init__(self, config):
        self.data = toml.loads(config)

    def get_server_ips(self, node_type, ip_type):
        data = self.data.get(node_type)
        ips = []
        for myips in data.values():
            ips.append(myips[ip_type])
        return ips

    def get_variables(self, variable):
        if "variables" in self.data:
            data = self.data.get("variables")
            if variable in data["0"]:
                return data["0"][variable]
        return None

    def get_all_public_ips(self):
        data = ["control", "network", "storage", "compute", "monitor"]
        ALL_PUBLIC_IPS = []
        for my_node_type in data:
            ips = parser.get_server_ips(self, node_type=my_node_type, ip_type="public")
            ALL_PUBLIC_IPS.extend(ips)
        ALL_PUBLIC_IPS = list(
            (dict.fromkeys(ALL_PUBLIC_IPS))
        )  # remove duplicates from list
        ALL_PUBLIC_IPS = list(
            filter(None, ALL_PUBLIC_IPS)
        )  # remove null values from list
        return ALL_PUBLIC_IPS

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
        data = self.data.get(node_type)
        for key, value in data.items():
            return bool(value[ip_type])


def convert_to_list(parm):
    if isinstance(parm, str):
        tmpList = []
        tmpList.append(parm)
        return tmpList
    return parm


def merge_dictionaries(default_dictionary, user_input_dictionary, path=None):
    """Merges user_input_dictionary into default dictionary;
    default values will be overwritten by users input."""
    return {**default_dictionary, **user_input_dictionary}


def merge_nested_dictionaries(a, b, path=None):
    """Merge nested dictionaries where the value is also a dictionary"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_nested_dictionaries(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass
            else:
                raise Exception("Conflict at %s" % ".".join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


def create_ssh_client(target_node):
    client = ssh_tool("ubuntu", target_node)
    if not client.check_access():
        print(f"Failed to connect to target node with IP {target_node} using SSH")
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


def create_multinode(input_dictionary, optional_variables):
    control_items = list(islice(input_dictionary.items(), 3))
    monitor_item = list(islice(input_dictionary.items(), 1))
    control_labels = ["control", "network"]
    secondary_labels = ["storage", "compute"]
    monitor_label = ["monitor"]
    multinode = ""
    for label in control_labels:
        multinode += f"\n[{label}]"
        for i, value in enumerate(control_items):
            internal = value[1]["internal"]
            public = value[1]["public"]
            data = value[1]["data"]
            multinode += f"""
    [{label}.{i}]
        public = \"{public}\"
        private = \"{internal}\"
        data = \"{data}\""""
    for label in secondary_labels:
        multinode += f"\n[{label}]"
        for i, (k, v) in enumerate(input_dictionary.items()):
            internal = v["internal"]
            public = v["public"]
            data = v["data"]
            multinode += f"""
    [{label}.{i}]
        public = \"{public}\"
        private = \"{internal}\"
        data = \"{data}\""""
    for label in monitor_label:
        multinode += f"\n[{label}]"
        for i, (k, v) in enumerate(monitor_item):
            internal = v["internal"]
            public = v["public"]
            data = v["data"]
            multinode += f"""
    [{label}.{i}]
        public = \"{public}\"
        private = \"{internal}\"
        data = \"{data}\""""

    multinode += f"\n[variables]\n\t[variables.0]\n"
    multinode += f"\t\t{optional_variables}"
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
