#!/bin/bash

cat deploy-pipeline.yml > deploy.yml

common_section="
default:
  # Official language image. Look for the different tagged releases at:
  # https://hub.docker.com/r/library/python/tags/
  image: python:3.7-buster
  interruptible: true

workflow:
  rules:
    - if: '\$CI_PIPELINE_SOURCE == \"parent_pipeline\"'
    - if: '\$CI_PIPELINE_SOURCE == \"merge_request_event\"'
    - if: '\$CI_PIPELINE_SOURCE == \"schedule\"'
    - if: '\$CI_PIPELINE_SOURCE == \"web\"'
"

if [[ $DEPLOY_MULTIPLE_RELEASES == "true" ]];
then
    current_release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE_CURRENT_RELEASE'));print(release['OPENSTACK_RELEASE'])")
    previous_release=$(python3 -c "import json;import os;release=json.loads(os.getenv('VM_PROFILE_PREVIOUS_RELEASE'));print(release['OPENSTACK_RELEASE'])")
    deploy_pipeline="
stages:
    - handle-yaml
    - deploy

handle-yaml:
    stage: handle-yaml
    needs:
        - pipeline: $PARENT_PIPELINE_ID
          job: generate_yaml_config
    script:
        - echo \"This job only exists to handle the YAML\"
    artifacts:
        paths:
            - deploy.yml

deploy:$current_release:
    stage: deploy
    variables:
        VM_PROFILE: \"\$VM_PROFILE_CURRENT_RELEASE\"
        REPROVISION_SERVERS: \"\$REPROVISION_SERVERS\"
        DOCKER_REGISTRY_PASSWORD: \"\$DOCKER_REGISTRY_PASSWORD\"
    trigger:
        include:
            - artifact: deploy.yml
              job: handle-yaml
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

echo "$common_section""$deploy_pipeline"
