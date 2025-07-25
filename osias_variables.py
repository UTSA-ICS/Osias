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
    "2023.1",
    "2023.2",
    "2024.2",
    "2025.1",
]

# https://governance.openstack.org/tc/reference/runtimes/
PYTHON_VERSION = {
    "2023.1": "3.10",
    "2023.2": "3.10",
    "2024.2": "3.11",
    "2025.1": "3.12",
}
ANSIBLE_MAX_VERSION = {
    "2023.1": "8",
    "2023.2": "8",
    "2024.2": "10",
    "2025.1": "12",
}
CEPH_RELEASE = {
    "2023.1": "quincy",
    "2023.2": "quincy",
    "2024.2": "reef",
    "2025.1": "reef",
}
MAAS_VM_DISTRO = {
    "2023.1": "jammy hwe_kernel=hwe-22.04-edge",
    "2023.2": "jammy hwe_kernel=hwe-22.04-edge",
    "2024.2": "jammy hwe_kernel=hwe-22.04-edge",
    "2025.1": "noble hwe_kernel=hwe-24.04-edge",
}

KOLLA_BASE_DISTRO = {
    "2023.1": "rocky",
    "2023.2": "rocky",
    "2024.2": "rocky",
    "2025.1": "rocky",
}

# REFSTACK VARIABLES
# https://docs.openstack.org/nova/latest/reference/api-microversion-history.html
# https://docs.openstack.org/cinder/latest/contributor/api_microversion_history.html
# https://docs.openstack.org/placement/latest/placement-api-microversion-history.html
# https://docs.openstack.org/releasenotes/tempest/unreleased.html
# https://refstack.openstack.org/#/guidelines
UBUNTU_NAMES = ["jammy", "noble"]
UBUNTU_VERSIONS = ["22.04", "24.04"]
REFSTACK_TEST_IMAGE = (
    "https://download.cirros-cloud.net/0.6.3/cirros-0.6.3-x86_64-disk.img"
)
REFSTACK_TEST_VERSION = {
    "2023.1": "2022.11",
    "2023.2": "2022.11",
    "2024.2": "2022.11",
    "2025.1": "2022.11",
}
TEMPEST_VERSION = {
    "2023.1": "34.2.0",
    "2023.2": "36.0.0",
    "2024.2": "41.0.0",
    "2025.1": "43.0.0",
}
NOVA_MIN_MICROVERSION = {
    "2023.1": "2.1",
    "2023.2": "2.1",
    "2024.2": "2.1",
    "2025.1": "2.1",
}
NOVA_MAX_MICROVERSION = {
    "2023.1": "2.95",
    "2023.2": "2.95",
    "2024.2": "2.96",
    "2025.1": "2.100",
}
STORAGE_MIN_MICROVERSION = {
    "2023.1": "3.0",
    "2023.2": "3.0",
    "2024.2": "3.0",
    "2025.1": "3.0",
}
STORAGE_MAX_MICROVERSION = {
    "2023.1": "3.70",
    "2023.2": "3.70",
    "2024.2": "3.71",
    "2025.1": "3.71",
}
PLACEMENT_MIN_MICROVERSION = {
    "2023.1": "1.0",
    "2023.2": "1.0",
    "2024.2": "1.0",
    "2025.1": "1.0",
}
PLACEMENT_MAX_MICROVERSION = {
    "2023.1": "1.39",
    "2023.2": "1.39",
    "2024.2": "1.39",
    "2025.1": "1.39",
}
