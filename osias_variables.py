"""
Dictionary of values containing the following:
    Number_of_VM_Servers,
    vCPU,
    RAM_in_MB,
    HDD1,
    HDD2,
    Internal_CIDR,
    Public_CIDR,
    Data_CIDR,
    VM_Deployment_CIDR,
    RAID

Number_of_VM_Servers: 3 to 7 VM's can be deployed in a test environment
HDD1 is the primary disk; HDD2-4 is used for Ceph/RAID,
Internal_CIDR is the internal CIDR from MaaS to assign an interface to VM,
Public_CIDR is the public CIDR from MaaS to assign an interface to the VM,
Data_CIDR is the private high speed CIDR from MaaS to assign an interface to the VM,
VM_Deployment_CIDR is a small /28 CIDR used for assigning a public IP to the VM,
    allocating IP's as floating IPs for OpenStack, and a VIP address for horizon
RAID: either true or absent, default is false.

example input:
{'vCPU': 8, 'RAM_in_MB': 16384, 'HDD1': 60, 'HDD2': 10, 'HDD3': 10, 'HDD4': 10, 'Internal_CIDR': '192.168.1.0/24',
'Number_of_VM_Servers': 3, 'Public_CIDR': '10.245.121.0/24', 'Data_CIDR': '10.100.0.0/16', 'DNS_IP': '10.250.53.202'}
"""

VM_Profile = {
    "Number_of_VM_Servers": 3,
    "vCPU": 8,
    "RAM_in_MB": 16384,
    "HDD1": 60,
    "HDD2": 10,
    "HDD3": 10,
    "HDD4": 10,
    "Internal_CIDR": "192.168.1.0/24",
    "Data_CIDR": "",
    "DNS_IP": "",
    "vm_deployment_cidr": "",
}

SUPPORTED_OPENSTACK_RELEASE = ["ussuri", "victoria", "wallaby"]
PYTHON_VERSION = {"ussuri": "3.6", "victoria": "3.8", "wallaby": "3.8"}
ANSIBLE_MAX_VERSION = {"ussuri": "2.10", "victoria": "2.10", "wallaby": "3.0"}
CEPH_VERSION = {"ussuri": "pacific", "victoria": "pacific", "wallaby": "pacific"}
MAAS_VM_DISTRO = {
    "ussuri": "bionic hwe_kernel=hwe-18.04",
    "victoria": "focal hwe_kernel=hwe-20.04",
    "wallaby": "focal hwe_kernel=hwe-20.04",
}

# REFSTACK VARIABLES
# https://docs.openstack.org/nova/latest/reference/api-microversion-history.html
# https://docs.openstack.org/cinder/latest/contributor/api_microversion_history.html
# https://docs.openstack.org/placement/latest/placement-api-microversion-history.html
# https://docs.openstack.org/releasenotes/tempest/unreleased.html
REFSTACK_TEST_IMAGE = (
    "https://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img"
)
REFSTACK_TEST_VERSION = {
    "ussuri": "2020.06",
    "victoria": "2020.11",
    "wallaby": "2020.11",
}
# Initial tempest version are: {"ussuri": "24.0.0", "victoria": "26.0.0", "wallaby": "27.0.0"}
TEMPEST_VERSION = {"ussuri": "26.0.0", "victoria": "29.0.0", "wallaby": "29.0.0"}
NOVA_MIN_MICROVERSION = {
    "ussuri": "2.1",
    "victoria": "2.80",
    "wallaby": "2.80",
}
NOVA_MAX_MICROVERSION = {
    "ussuri": "2.87",
    "victoria": "2.87",
    "wallaby": "2.88",
}
STORAGE_MIN_MICROVERSION = {
    "ussuri": "3.59",
    "victoria": "3.60",
    "wallaby": "3.62",
}
STORAGE_MAX_MICROVERSION = {
    "ussuri": "3.60",
    "victoria": "3.62",
    "wallaby": "3.64",
}
PLACEMENT_MIN_MICROVERSION = {
    "ussuri": "1.32",
    "victoria": "1.32",
    "wallaby": "1.32",
}
PLACEMENT_MAX_MICROVERSION = {
    "ussuri": "1.36",
    "victoria": "1.36",
    "wallaby": "1.36",
}
