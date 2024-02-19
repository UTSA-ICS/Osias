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
6GB Ceph drives is minimum required.
HDD1 is the primary disk; HDD2+ is used for Ceph/RAID,
Internal_CIDR is the internal CIDR from MaaS to assign an interface to VM,
Public_CIDR is the public CIDR from MaaS to assign an interface to the VM,
Data_CIDR is the private high speed CIDR from MaaS to assign an interface to the VM,
VM_Deployment_CIDR is a small /28 CIDR used for assigning a public IP to the VM,
    allocating IP's as floating IPs for OpenStack, and a VIP address for horizon
RAID: either true or absent, default is false.

example input:
{'vCPU': 8, 'RAM_in_MB': 16384, 'HDD1': 60, 'HDD2': 10, 'Internal_CIDR': '192.168.1.0/24',
'Number_of_VM_Servers': 3, 'Public_CIDR': '10.245.121.0/24', 'Data_CIDR': '10.100.0.0/16', 'DNS_IP': '10.250.53.202'}
"""

VM_Profile = {
    "Number_of_VM_Servers": 3,
    "vCPU": 6,
    "RAM_in_MB": 16384,
    "HDD1": 60,
    "HDD2": 6,
    "HDD3": 6,
    "Internal_CIDR": "192.168.1.0/24",
    "Data_CIDR": "10.100.0.0/16",
    "DNS_IP": "",
    "VM_DEPLOYMENT_CIDR": "10.245.121.0/24",
    "IPs_NEEDED": 12,
}

SUPPORTED_OPENSTACK_RELEASE = [
    "ussuri",
    "victoria",
    "wallaby",
    "xena",
    "yoga",
    "zed",
    "2023.1",
    "2023.2",
]
NON_QUAY_RELEASE = ["ussuri", "victoria", "wallaby", "xena", "yoga"]
PYTHON_VERSION = {
    "ussuri": "3.6",
    "victoria": "3.8",
    "wallaby": "3.8",
    "xena": "3.8",
    "yoga": "3.8",
    "zed": "3.8",
    "2023.1": "3.10",
    "2023.2": "3.10",
}
ANSIBLE_MAX_VERSION = {
    "ussuri": "2.10",
    "victoria": "2.10",
    "wallaby": "3.0",
    "xena": "5.0",
    "yoga": "6",
    "zed": "6",
    "2023.1": "8",
    "2023.2": "8",
}
CEPH_RELEASE = {
    "ussuri": "pacific",
    "victoria": "pacific",
    "wallaby": "pacific",
    "xena": "pacific",
    "yoga": "quincy",
    "zed": "quincy",
    "2023.1": "quincy",
    "2023.2": "quincy",
}
MAAS_VM_DISTRO = {
    "ussuri": "bionic hwe_kernel=hwe-18.04",
    "victoria": "focal hwe_kernel=hwe-20.04-edge",
    "wallaby": "focal hwe_kernel=hwe-20.04-edge",
    "xena": "focal hwe_kernel=hwe-20.04-edge",
    "yoga": "focal hwe_kernel=hwe-20.04-edge",
    "zed": "jammy hwe_kernel=hwe-22.04-edge",
    "2023.1": "jammy hwe_kernel=hwe-22.04-edge",
    "2023.2": "jammy hwe_kernel=hwe-22.04-edge",
}

KOLLA_BASE_DISTRO = {
    "ussuri": "centos",
    "victoria": "centos",
    "wallaby": "centos",
    "xena": "centos",
    "yoga": "centos",
    "zed": "rocky",
    "2023.1": "rocky",
    "2023.2": "rocky",
}

# REFSTACK VARIABLES
# https://docs.openstack.org/nova/latest/reference/api-microversion-history.html
# https://docs.openstack.org/cinder/latest/contributor/api_microversion_history.html
# https://docs.openstack.org/placement/latest/placement-api-microversion-history.html
# https://docs.openstack.org/releasenotes/tempest/unreleased.html
# https://refstack.openstack.org/#/guidelines
UBUNTU_NAMES = ["focal", "jammy"]
UBUNTU_VERSIONS = ["20.04.4", "22.04"]
REFSTACK_TEST_IMAGE = (
    "https://download.cirros-cloud.net/0.6.1/cirros-0.6.1-x86_64-disk.img"
)
REFSTACK_TEST_VERSION = {
    "ussuri": "2020.11",
    "victoria": "2021.11",
    "wallaby": "2021.11",
    "xena": "2021.11",
    "yoga": "2021.11",
    "zed": "2022.06",
    "2023.1": "2022.11",
    "2023.2": "2022.11",
}
TEMPEST_VERSION = {
    "ussuri": "29.2.0",
    "victoria": "29.2.0",
    "wallaby": "29.1.0",
    "xena": "31.1.0",
    "yoga": "31.1.0",
    "zed": "33.0.0",
    "2023.1": "34.2.0",
    "2023.2": "36.0.0",
}
NOVA_MIN_MICROVERSION = {
    "ussuri": "2.1",
    "victoria": "2.1",
    "wallaby": "2.1",
    "xena": "2.1",
    "yoga": "2.1",
    "zed": "2.1",
    "2023.1": "2.1",
    "2023.2": "2.1",
}
NOVA_MAX_MICROVERSION = {
    "ussuri": "2.87",
    "victoria": "2.87",
    "wallaby": "2.88",
    "xena": "2.90",
    "yoga": "2.92",
    "zed": "2.93",
    "2023.1": "2.95",
    "2023.2": "2.95",
}
STORAGE_MIN_MICROVERSION = {
    "ussuri": "3.0",
    "victoria": "3.0",
    "wallaby": "3.0",
    "xena": "3.0",
    "yoga": "3.0",
    "zed": "3.0",
    "2023.1": "3.0",
    "2023.2": "3.0",
}
STORAGE_MAX_MICROVERSION = {
    "ussuri": "3.60",
    "victoria": "3.62",
    "wallaby": "3.64",
    "xena": "3.66",
    "yoga": "3.69",
    "zed": "3.70",
    "2023.1": "3.70",
    "2023.2": "3.70",
}
PLACEMENT_MIN_MICROVERSION = {
    "ussuri": "1.0",
    "victoria": "1.0",
    "wallaby": "1.0",
    "xena": "1.0",
    "yoga": "1.0",
    "zed": "1.0",
    "2023.1": "1.0",
    "2023.2": "1.0",
}
PLACEMENT_MAX_MICROVERSION = {
    "ussuri": "1.36",
    "victoria": "1.36",
    "wallaby": "1.36",
    "xena": "1.39",
    "yoga": "1.39",
    "zed": "1.39",
    "2023.1": "1.39",
    "2023.2": "1.39",
}
