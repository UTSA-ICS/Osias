#!/bin/bash

if [[ $DEPLOY_MULTIPLE_RELEASES == "true" ]];
then
    current_release=$(python3 -c "import json;import os;import toml; release=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE'))['OPENSTACK_RELEASE'] if isinstance(os.getenv('VM_PROFILE_CURRENT_RELEASE'), str) else toml.loads(os.getenv('MULTINODE_CURRENT_RELEASE'))['variables']['0']['OPENSTACK_RELEASE']; print(release)")
    previous_release=$(python3 -c "import json;import os;import toml; release=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'))['OPENSTACK_RELEASE'] if isinstance(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'), str) else toml.loads(os.getenv('MULTINODE_PREVIOUS_RELEASE'))['variables']['0']['OPENSTACK_RELEASE']; print(release)")


    sed -i "s/<RELEASE_NAME>/${current_release}/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_VM_PROFILE>/\$VM_PROFILE_CURRENT_RELEASE/g" trigger-pipeline.yml
    sed -i "s/<PREVIOUS_RELEASE_NAME>/${previous_release}/g" trigger-pipeline.yml

    cp deploy-pipeline.yml deploy-"${current_release}".yml
    sed -i "s/<RELEASE_NAME>/${current_release}/g" deploy-"${current_release}".yml

    cp deploy-pipeline.yml deploy-"${previous_release}".yml
    sed -i "s/<RELEASE_NAME>/${previous_release}/g" deploy-"${previous_release}".yml
else
    release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE'));print(release['OPENSTACK_RELEASE'])")

    sed -i "s/<RELEASE_NAME>/${release}/g" trigger-pipeline.yml
    sed -i "s/<RELEASE_VM_PROFILE>/\$VM_PROFILE/g" trigger-pipeline.yml

    cp deploy-pipeline.yml deploy-"${release}".yml
    sed -i "s/<RELEASE_NAME>/${release}/g" deploy-"${release}".yml
fi

cat trigger-pipeline.yml
