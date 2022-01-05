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

SUPPORTED_OPENSTACK_RELEASE = ["ussuri", "victoria", "wallaby", "xena"]
PYTHON_VERSION = {
    "ussuri": "3.6",
    "victoria": "3.8",
    "wallaby": "3.8",
    "xena": "3.8",
}
ANSIBLE_MAX_VERSION = {
    "ussuri": "2.10",
    "victoria": "2.10",
    "wallaby": "3.0",
    "xena": "5.0",
}
CEPH_VERSION = {
    "ussuri": "pacific",
    "victoria": "pacific",
    "wallaby": "pacific",
    "xena": "pacific",
}
MAAS_VM_DISTRO = {
    "ussuri": "bionic hwe_kernel=hwe-18.04",
    "victoria": "focal hwe_kernel=hwe-20.04",
    "wallaby": "focal hwe_kernel=hwe-20.04",
    "xena": "focal hwe_kernel=hwe-20.04",
}

# REFSTACK VARIABLES
# https://docs.openstack.org/nova/latest/reference/api-microversion-history.html
# https://docs.openstack.org/cinder/latest/contributor/api_microversion_history.html
# https://docs.openstack.org/placement/latest/placement-api-microversion-history.html
# https://docs.openstack.org/releasenotes/tempest/unreleased.html
# https://refstack.openstack.org/#/guidelines
REFSTACK_TEST_IMAGE = (
    "https://download.cirros-cloud.net/0.5.2/cirros-0.5.2-x86_64-disk.img"
)
REFSTACK_TEST_VERSION = {
    "ussuri": "2020.11",
    "victoria": "2021.11",
    "wallaby": "2021.11",
    "xena": "2021.11",
}
TEMPEST_VERSION = {
    "ussuri": "29.2.0",
    "victoria": "a32c763c82a100ec0f8a9776420649b4568f8202",
    "wallaby": "29.1.0",
    "xena": "29.2.0",
}
NOVA_MIN_MICROVERSION = {
    "ussuri": "2.1",
    "victoria": "2.1",
    "wallaby": "2.1",
    "xena": "2.1",
}
NOVA_MAX_MICROVERSION = {
    "ussuri": "2.87",
    "victoria": "2.87",
    "wallaby": "2.88",
    "xena": "2.90",
}
STORAGE_MIN_MICROVERSION = {
    "ussuri": "3.0",
    "victoria": "3.0",
    "wallaby": "3.0",
    "xena": "3.0",
}
STORAGE_MAX_MICROVERSION = {
    "ussuri": "3.60",
    "victoria": "3.62",
    "wallaby": "3.64",
    "xena": "3.66",
}
PLACEMENT_MIN_MICROVERSION = {
    "ussuri": "1.0",
    "victoria": "1.0",
    "wallaby": "1.0",
    "xena": "1.0",
}
PLACEMENT_MAX_MICROVERSION = {
    "ussuri": "1.36",
    "victoria": "1.36",
    "wallaby": "1.36",
    "xena": "1.38",
}
