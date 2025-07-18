#!/bin/bash

set -eu

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <VM PROFILE>"
  exit 1
fi

# shellcheck source=/dev/null
source "${CI_PROJECT_DIR}"/"${1}"

export VM_IP_LIST=""  # Space-separated list of IPs for deletion
export VM_ID_LIST=""  # Space-separated list of VM IDs for deletion

# Prefill variables for cloud vendor
export CLOUD_VENDOR="proxmox"
export PROFILE_OUTPUT_FILE_NAME="profile.json"

cd cloud_provider
python3 generate_profile_command.py
cat $PROFILE_OUTPUT_FILE_NAME

mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "$SSH_PRIVATE_KEY" > ~/id_rsa
chmod 600 ~/id_rsa
ssh-keygen -y -f ~/id_rsa > ~/id_rsa.pub
chmod 644 ~/id_rsa.pub

python3 main.py --create_vms --output_file vm_info.json --profile_file $PROFILE_OUTPUT_FILE_NAME
cp vm_info.json "$CI_PROJECT_DIR"/.
cp log.txt "$CI_PROJECT_DIR"/.
