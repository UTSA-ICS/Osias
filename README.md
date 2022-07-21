[![CodeFactor](https://www.codefactor.io/repository/github/utsa-ics/osias/badge/master)](https://www.codefactor.io/repository/github/utsa-ics/osias/overview/master)
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://gitlab.com/utsa-ics/osias)
[![Pipeline](https://gitlab.com/utsa-ics/deploy-openstack/badges/master/pipeline.svg?ignore_skipped=true)](https://gitlab.com/utsa-ics/deploy-openstack/-/commits/master)
[![Gitter chat](https://img.shields.io/badge/gitter-join%20chat%20%E2%86%92-brightgreen.svg)](https://gitter.im/utsa-ics-osias/community?utm_source=share-link&utm_medium=link&utm_campaign=share-link)

# Osias (OpenStack Infrastructure As a Service)

## Mission Statement

The name Osias (pronounced: oh-sigh-us) is a name of Hebrew origin meaning "salvation". (OpenStack
Infrastructure As a Service)

This projects inspiration came from the need to deploy and configure a clean operating system and
openstack, repeatably, at any moment.

Osias offers a from scratch deployment mechanism utilizing [MAAS](https://maas.io/) to provision
nodes with an OS, then setup and configure to install
[CEPH](https://docs.ceph.com/en/latest/cephadm/) (optional), deploy
[OpenStack](https://docs.openstack.org/kolla-ansible/latest/) private cloud, and the finally perform
OpenStack Certification Tests using [RefStack](https://refstack.openstack.org/#/) to validate the
deployment.

## Versions

- MAAS version: 2.8.2 - 3.1.0

|      | Kolla   | Python |    OS |      Ansible |    Ceph | Swift |
|----------|------|-----|--------------|---------|---------|-------|
| ussuri   | 10.x | 3.6 | Ubuntu 18.04 | \< 2.10 | Pacific | No    |
| victoria | 11.x | 3.8 | Ubuntu 20.04 | \< 2.10 | Pacific | No    |
| wallaby  | 12.x | 3.8 | Ubuntu 20.04 | \< 3.0  | Pacific | No    |
| xena     | 13.x | 3.8 | Ubuntu 20.04 | \< 5.0  | Pacific | Yes   |
| yoga     | 14.x | 3.8 | Ubuntu 20.04 | \< 6.0  | Quincy  | Yes   |

## MaaS

Please configure MaaS to:

- Have your SSH public key installed
- Have gitlabs SSH public key installed
- Ability to deploy your respective Ubuntu version

Each server in MaaS needs the following configuration:

- At least 2 NICs with IP's configured,
  1. (REQUIRED) One completely internal network, used for management network. This will be
     referenced as your private network in our multinode file.
  1. (REQUIRED) One network which is public facing and needs to be a bridge with an IP associated
     with it. This will be referenced as your public network in our multinode file.
  1. (OPTIONAL) If possible, a high speed network for use with storage/ceph, this should also be
     internal and separate from public access. This will be referenced as your data network in our
     multinode file. This network is optional, but highly recommended.
- The public network needs to be configured with a bridge, br0. We have STP enabled with a 15 ms
  forward delay.

### **Don't have MaaS?**

To bypass the use of MaaS, make sure you have

- Ubuntu installed,
- Passwordless sudo,
- `br0` configured on your public nic with an IP, and
- Your gitlab SSH public key installed.
- Also, set `REPROVISION_SERVERS=false` variable in GitLab, so it doesn't try to access the MaaS
  server.
- To deploy this code, we conduct our testing using python3.7. You can also use a python:3.7-buster
  docker image and manually issue the codes from the .gitlab-ci.yml, please see the `Dev Work`
  section below.

## Stages

### (OPTIONAL) Reprovision servers

This step will only occur if you have `REPROVISION_SERVERS=true` set in gitlab variables. This step
will release, wait for a ready state, then begin provisioning the servers from your multinode file.
It does this by querying maas for all of the machines, and captures the machine ID based off of the
IP's specified in your multinode file.

### Bootstrap Networking

This will take br0 and create 2 virtual interfaces (veno0 & veno1) used in kolla ansible's globals
file. neutron_external_interface will be use veno1 and kolla_external_vip_interface=br0.

### (OPTIONAL) Reboot

This stage will only happen if you are not using MaaS.

### Bootstrap OpenStack

- Kolla password and certificates will be generated here.
- SSH access will be granted for the ubuntu and root user. SSH access is necessary for the root due
  to cephadm.
- Globals file will be generated
- The nova.conf config file will be generated here.

### Deploy Ceph and OpenStack Pull

- Podman will be installed for cephadm
- Cephadm will be configured to use control\[0\] node as the head node and will be deployed.
  - All of your ceph volumes and keyrings will be generated in this stage.
  - 1 Radosgw will be installed for swift API services.
- Kolla pre-checks and kolla pull will both run.

### Deploy OpenStack

- Kolla deploy, and
- Kolla post-deploy to generate the admin-openrc.sh file
- Openstack client will be installed

### Post deploy OpenStack

- CirrOS will be downloaded and uploaded to OpenStack.
- Various flavors and networks will be created.

### Test Setup

- Refstack will be configured and run in the following stages.
  - `refstack-client test -c etc/tempest.conf -v --test-list "https://refstack.openstack.org/api/v1/guidelines/2020.11/tests?target=platform&type=required&alias=true&flag=false"`
- If tests are successful, radosgw will be installed HA, 3+ nodes.

## Physical Architecture

The conceptual layout of the hardware consists of the following 3 switches and N number of servers.
The public switch has internet access and is capable of being able to SSH into servers from
deployment node. The private switch and high speed switch is airgapped from the internet and is
completely internal. These two switches could be condensed into one switch, preferably a high speed
one. Your actual layout may differ if you choose to use, for example, fewer switches and instead
vlan's or more switches for binding ports together, etc.

```
┌──────────────────
│ PUBLIC SWITCH
├──────────────────
│ PRIVATE SWITCH
├──────────────────
│ HIGH SPEED SWITCH
├──────────────────
│ SERVER 1
├──────────────────
│ SERVER 2
├──────────────────
│ SERVER 3
├──────────────────
│ SERVER N
└──────────────────
```

## Configs

Tree structure of our config files:

```
/etc/kolla/config/
├── [drwxr-xr-x ubuntu   ubuntu  ]  cinder
│   ├── [drwxr-xr-x ubuntu   ubuntu  ]  cinder-backup
│   │   ├── [-rw-rw-r-- ubuntu   ubuntu  ]  ceph.client.cinder-backup.keyring
│   │   ├── [-rw-rw-r-- ubuntu   ubuntu  ]  ceph.client.cinder.keyring
│   │   └── [-rw-r--r-- ubuntu   ubuntu  ]  ceph.conf
│   └── [drwxr-xr-x ubuntu   ubuntu  ]  cinder-volume
│       ├── [-rw-rw-r-- ubuntu   ubuntu  ]  ceph.client.cinder.keyring
│       └── [-rw-r--r-- ubuntu   ubuntu  ]  ceph.conf
├── [drwxr-xr-x ubuntu   ubuntu  ]  glance
│   ├── [-rw-rw-r-- ubuntu   ubuntu  ]  ceph.client.glance.keyring
│   └── [-rw-r--r-- ubuntu   ubuntu  ]  ceph.conf
├── [drwxr-xr-x ubuntu   ubuntu  ]  nova
│   ├── [-rw-rw-r-- ubuntu   ubuntu  ]  ceph.client.cinder.keyring
│   └── [-rw-r--r-- ubuntu   ubuntu  ]  ceph.conf
└── [-rw-rw-r-- ubuntu   ubuntu  ]  nova.conf

5 directories, 10 files
```

## Variables

OSIAS' multinode file is configured similarly to kolla's multinode file, however, it's
implementation is different. The main sections: control, network, storage, compute and monitor, all
translate to kolla's multinode file where the private IP will be used.

In addition, the variables section in our multinode file can enable features:

- `DOCKER_REGISTRY = "<IP ADDRESS OR FQDN>"` will enable a local docker registry in the kolla
  globals section
- `DOCKER_REGISTRY_USERNAME = "kolla"` will allow you to change the docker registry username in the
  kolla globals section

### Multinode File

Our multinode file is formatted very similar to that of Kolla, where all of these sections will be
copied over to kolla's multinode file. However, `storage` will ALSO be used for our ceph deployment
and `variables` is our own.

- `POOL_START_IP = "{FLOATING_IP_POOL_START}"` This is the first IP used for your openstack
  deployment, the default value is an IP from the same subnet as your public IP's, i.e. 172.16.123.x
  or the CIDR indicated in osias_variables, VM_Profile: VM_DEPLOYMENT_CIDR.
- `POOL_END_IP = "{FLOATING_IP_POOL_END}"` This is the last IP used for your openstack deployment.
- `DNS_IP = "{DNS_IP}"` a single DNS entry can be entered, default value is `8.8.8.8`.
- `VIP_ADDRESS = "{VIP_ADDRESS}"` This will be used as horizon website and used in Kolla's global
  file.

The VIP, pool start/end are all calculated based off of the `IPs_NEEDED` variable in the
`osias_variables: VM_Profile` section. Osias will inspect your maas VM_DEPLOYMENT_CIDR subnet, find
a block of IP's necessary (IPs_NEEDED) that are free, and reserve the VIP_ADDRESS and the
pool_start_ip so the whole block is reserved.

```
#public = "Internet facing IP's"
#private = "Non-Internet facing IP's"
#data = "Non-Internet facing IP's, high speed IP's used for ceph, if not available leave "" "
[control]
    [control.0]
    public = "172.16.123.23"
    private = "192.168.3.23"
    data = "10.100.3.23"
[network]
    [network.0]
    public = "172.16.123.23"
    private = "192.168.3.23"
    data = "10.100.3.23"
[storage]
    [storage.0]
    public = "172.16.123.23"
    private = "192.168.3.23"
    data = "10.100.3.23"
[compute]
    [compute.0]
    public = "172.16.123.29"
    private = "192.168.3.29"
    data = "10.100.3.29"
    [compute.1]
    public = "172.16.123.25"
    private = "192.168.3.25"
    data = "10.100.3.25"
[monitor]
    [monitor.0]
    public = ""
    private = ""
    data = ""
[variables]
    [variables.0]
    CEPH = "{true|false}"
    DNS_IP = "{DNS_IP}"
    OPENSTACK_RELEASE = "{OPENSTACK_RELEASE}"
    POOL_START_IP = "{FLOATING_IP_POOL_START}"
    POOL_END_IP = "{FLOATING_IP_POOL_END}"
    VIP_ADDRESS = "{VIP_ADDRESS}"
    # Optional variables
    DOCKER_REGISTRY = "<DOCKER IP>"
    DOCKER_REGISTRY_USERNAME = "<DOCKER REGISTRY USERNAME>"
    FQDN = "<FULLY QUALIFIED DOMAIN NAME>"
```

### For development & MAAS created VM's

- `Data_CIDR = "{CIDR for high speed testing}"` a third nic will be created in the VM's which could
  be used for high speed cases. Currently, not used in CI/CD.

We use a variable called VM_PROFILE which helps create the multinode file above but for testing.
Below is the format needed:

```
{"Data_CIDR": "{DATA CIDR IF USED}", "DNS_IP": "{DNS IP}", "Number_of_VM_Servers": 3, "OPENSTACK_RELEASE": "{OPENSTACK_RELEASE}", "CEPH": "{True|False}", "DOCKER_REGISTRY_IP": "<DOCKER IP>", "DOCKER_REGISTRY_USERNAME": "<DOCKER REGISTRY USERNAME>", "VM_DEPLOYMENT_CIDR" = "<POOL OF IP's served as the cidr >"}
```

### Globals file

Our default options are as follows below. To modify these options and choose your own, they can be
found in the setup_configs.py file in the setup_kolla_configs definition with the variables: docker,
storage, or globals_file depending on the use-case.

```
kolla_base_distro: "centos"
kolla_install_type: "source"
kolla_internal_vip_address: "ENO1 network address.250" # this address is dynamic and may change
kolla_external_vip_address: "BR0 network address.250" # this address is dynamic and may change
network_interface: "eno1"
kolla_external_vip_interface: "br0"
neutron_external_interface: "veno1"
kolla_enable_tls_internal: "yes" #enabled if multinode deployment, disabled if AiO
kolla_enable_tls_external: "yes" #enabled if multinode deployment, disabled if AiO
kolla_copy_ca_into_containers: "yes"
kolla_verify_tls_backend: "no"
kolla_enable_tls_backend: "yes" #enabled if multinode deployment, disabled if AiO
openstack_cacert: /etc/pki/tls/certs/ca-bundle.crt
enable_cinder: "yes"
enable_cinder_backend_lvm: "no"
ceph_nova_user: "cinder"
glance_backend_ceph: "yes"
glance_backend_swift: "no"
cinder_backend_ceph: "yes"
cinder_backup_driver: "ceph"
nova_backend_ceph: "yes"
enable_mariabackup: "yes"
enable_neutron_agent_ha: "yes"
glance_enable_rolling_upgrade: "yes"
keepalived_virtual_router_id: "VIP host address i.e. 250 from above example"
```

## Dev Work

To do development work/bug fixes, first download/clone our repo and either run a docker container as
follows or have python3 installed:

`docker run -ti -v ~/deploy-openstack-master:/test python:3.7-buster bash`

Next, `cd /test` and install the python dependencies for the project

`pip3 install toml timeout_decorator`

Lastly, customize and source your variables as shown in the development_helper.sh file. Once
sourced, you can manually issue the commands from our gitlab-ci.yml file, for example:
`python3 -u deploy.py bootstrap_networking --config "$MULTINODE"`

Also, it has been tested you can deploy our code inside a
[LXD VM configured from MaaS](https://maas.io/docs/snap/2.9/ui/vm-host-networking#heading--lxd-setup).

### One Command, Complete Deployment

To issue all of our deployment in one command for an all-in-one dev environment:
All in one node may not fully test refstack components and will not install ceph.

./all_in_one_openstack_deployment.sh "$OPENSTACK_RELEASE" "$NODES_IP_ADDRESS"
