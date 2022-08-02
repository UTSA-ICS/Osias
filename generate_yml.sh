#!/bin/bash

if [[ $DEPLOY_MULTIPLE_RELEASES == "true" ]];
then
    current_release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE'));print(release['OPENSTACK_RELEASE'])")
    previous_release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'));print(release['OPENSTACK_RELEASE'])")

    ceph_current_bool=$(python3 -c "import os,json; multi=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE'));ceph=multi['CEPH'];print(ceph.lower())")
    ceph_previous_bool=$(python3 -c "import os,json; multi=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'));ceph=multi['CEPH'];print(ceph.lower())")
    
    sed -i "s/<CEPH_CURRENT_BOOL>/${ceph_current_bool}/g" trigger-pipeline.yml
    sed -i "s/<CEPH_PREVIOUS_BOOL>/${ceph_previous_bool}/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_NAME>/${current_release}/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_VM_PROFILE>/\$VM_PROFILE_CURRENT_RELEASE/g" trigger-pipeline.yml
    sed -i "s/<PREVIOUS_RELEASE_NAME>/${previous_release}/g" trigger-pipeline.yml

    cp deploy-pipeline.yml deploy-"${current_release}".yml
    sed -i "s/<RELEASE_NAME>/${current_release}/g" deploy-"${current_release}".yml

    cp deploy-pipeline.yml deploy-"${previous_release}".yml
    sed -i "s/<RELEASE_NAME>/${previous_release}/g" deploy-"${previous_release}".yml
else
    release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE'));print(release['OPENSTACK_RELEASE'])")

    ceph_current_bool=$(python3 -c "import os,json; multi=json.loads(os.getenv('VM_PROFILE'));ceph=multi['CEPH'];print(ceph.lower())")
    
    sed -i "s/<CEPH_CURRENT_BOOL>/${ceph_current_bool}/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_NAME>/${release}/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_VM_PROFILE>/\$VM_PROFILE/g" trigger-pipeline.yml

    cp deploy-pipeline.yml deploy-"${release}".yml
    sed -i "s/<RELEASE_NAME>/${release}/g" deploy-"${release}".yml
fi

cat trigger-pipeline.yml
