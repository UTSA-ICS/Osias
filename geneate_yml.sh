#!/bin/bash


if [[ $DEPLOY_MULTIPLE_RELEASES == "true" ]];
then
    current_release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE'));print(release['OPENSTACK_RELEASE'])")
    previous_release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'));print(release['OPENSTACK_RELEASE'])")
    deploy_pipeline="
stages:
    - deploy

deploy:$current_release:
    stage: deploy
    variables:
        VM_PROFILE: \"\$VM_PROFILE_CURRENT_RELEASE\"
        REPROVISION_SERVERS: \"\$REPROVISION_SERVERS\"
        DOCKER_REGISTRY_PASSWORD: \"\$DOCKER_REGISTRY_PASSWORD\"
    trigger:
        include: deploy-pipeline.yml
        strategy: depend

deploy:$previous_release:
    stage: deploy
    variables:
        VM_PROFILE: \"\$VM_PROFILE_PREVIOUS_RELEASE\"
        REPROVISION_SERVERS: \"\$REPROVISION_SERVERS\"
        DOCKER_REGISTRY_PASSWORD: \"\$DOCKER_REGISTRY_PASSWORD\"
    trigger:
        include: deploy-pipeline.yml
        strategy: depend
"
else
    release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE'));print(release['OPENSTACK_RELEASE'])")
    deploy_pipeline="
stages:
    - deploy

deploy:$release:
    stage: deploy
    variables:
        VM_PROFILE: \"\$VM_PROFILE\"
        REPROVISION_SERVERS: \"\$REPROVISION_SERVERS\"
        DOCKER_REGISTRY_PASSWORD: \"\$DOCKER_REGISTRY_PASSWORD\"
    trigger:
        include: deploy-pipeline.yml
        strategy: depend
"
fi

echo "$deploy_pipeline"
