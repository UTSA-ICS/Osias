#!/bin/bash

set -euxo pipefail

SSH_PRIVATE_KEY="$1"
SSH_PUBLIC_KEY="$2"

echo -n "$SSH_PRIVATE_KEY" >"$HOME"/.ssh/id_rsa
chmod 600 "$HOME"/.ssh/id_rsa

echo -n "$SSH_PUBLIC_KEY" >"$HOME"/.ssh/id_rsa.pub
echo -n "$SSH_PUBLIC_KEY" >>"$HOME"/.ssh/authorized_keys
