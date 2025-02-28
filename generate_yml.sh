#!/bin/bash

# set -euxo pipefail

if [[ $DEPLOY_MULTIPLE_RELEASES == "true" ]]; then
    current_release=$(python3 -c "import json; import os; release=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE')); print(release['OPENSTACK_RELEASE'].replace('.', '_'))")
    previous_release=$(python3 -c "import json; import os; release=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE')); print(release['OPENSTACK_RELEASE'].replace('.', '_'))")

    ceph_current_bool=$(python3 -c "import os,json; multi=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE'));ceph=multi['CEPH'];print(ceph.lower())")
    ceph_previous_bool=$(python3 -c "import os,json; multi=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'));ceph=multi['CEPH'];print(ceph.lower())")

    cloud_provider_previous=$(python3 -c "import os,json; multi=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'));cloud_provider=multi['DEPLOYMENT_CLOUD'];print(cloud_provider.lower())")
    cloud_provider_current=$(python3 -c "import os,json; multi=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE'));cloud_provider=multi['DEPLOYMENT_CLOUD'];print(cloud_provider.lower())")

    sed -i "s/<CEPH_CURRENT_BOOL>/\"${ceph_current_bool}\"/g" trigger-pipeline.yml
    sed -i "s/<CEPH_PREVIOUS_BOOL>/\"${ceph_previous_bool}\"/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_NAME>/${current_release}/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_VM_PROFILE>/\$VM_PROFILE_CURRENT_RELEASE/g" trigger-pipeline.yml
    sed -i "s/<PREVIOUS_RELEASE_NAME>/${previous_release}/g" trigger-pipeline.yml


    cp deploy-pipeline.yml deploy-"${current_release}".yml
    sed -i "s/<RELEASE_NAME>/${current_release}/g" deploy-"${current_release}".yml

    cp deploy-pipeline.yml deploy-"${previous_release}".yml
    sed -i "s/<RELEASE_NAME>/${previous_release}/g" deploy-"${previous_release}".yml

    if [[ "$cloud_provider_previous" == "proxmox" ]]; then
      sed -i "s/<CLOUD_PROVIDER_IMAGE>/python:latest/g" deploy-"${previous_release}".yml
    else
      sed -i "s/<CLOUD_PROVIDER_IMAGE>/utsaics\/maas:2.8/g" deploy-"${previous_release}".yml
    fi

    if [[ "$cloud_provider_current" == "proxmox" ]]; then
      sed -i "s/<CLOUD_PROVIDER_IMAGE>/python:latest/g" deploy-"${current_release}".yml
    else
      sed -i "s/<CLOUD_PROVIDER_IMAGE>/utsaics\/maas:2.8/g" deploy-"${current_release}".yml
    fi

else

    if [[ -n "$MULTINODE" ]]; then
        release=$(python3 -c "import os; import yaml; release=yaml.safe_load(os.getenv('MULTINODE')); release=release['variables']['OPENSTACK_RELEASE']; print(release.lower())")
        ceph_current_bool=$(python3 -c "import os; import yaml; ceph_multi=yaml.safe_load(os.getenv('MULTINODE')); ceph=ceph_multi['variables']['CEPH']; print(str(ceph).lower())")
        sed -i "s/<RELEASE_VM_PROFILE>/''/g" trigger-pipeline.yml
    elif [[ -n "$VM_PROFILE" ]]; then
        release=$(python3 -c "import json; import os; release=json.loads(os.getenv('VM_PROFILE')); print(release['OPENSTACK_RELEASE'])")
        ceph_current_bool=$(python3 -c "import json; import os; vm_profile=json.loads(os.getenv('VM_PROFILE')); ceph=vm_profile['CEPH']; print(ceph.lower())")
        sed -i "s/<RELEASE_VM_PROFILE>/\$VM_PROFILE/g" trigger-pipeline.yml
    else
        echo "ERROR: VM_PROFILE or MULTINODE variable need to exist."
        exit 1
    fi

    sed -i "s/<CEPH_CURRENT_BOOL>/\"${ceph_current_bool}\"/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_NAME>/${release}/g" trigger-pipeline.yml

    cp deploy-pipeline.yml deploy-"${release}".yml
    sed -i "s/<RELEASE_NAME>/${release}/g" deploy-"${release}".yml
    sed -i "s/<CLOUD_PROVIDER_IMAGE>/python:latest/g" trigger-pipeline.yml
    sed -i "s/<CLOUD_PROVIDER_IMAGE>/python:latest/g" deploy-"${release}".yml
fi

cat trigger-pipeline.yml
python3 -c "import os; os.environ['CLOUD_PROVIDER_IMAGE'] = '${cloud_provider_image_current}'; print('CLOUD_PROVIDER_IMAGE set to', os.environ['CLOUD_PROVIDER_IMAGE'])"