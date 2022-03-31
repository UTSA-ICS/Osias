#!/bin/bash

servers="$1"

echo "$servers"

if [ -d /etc/kolla/certificates/private/ ]; then
  mkdir -p /tmp/certificates
  cp /etc/kolla/certificates/private/*/*.crt /tmp/certificates
fi

for server in $servers; do
  echo "copying to: $server"
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$server" mkdir -p "$HOME"/certificates
  scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 /tmp/certificates/* "$server":$HOME/certificates
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$server" sudo cp "$HOME"/certificates/*.crt /usr/local/share/ca-certificates/
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$server" sudo update-ca-certificates
done
