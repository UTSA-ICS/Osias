#!/bin/bash

servers="$1"

echo "$servers"

if [ -d /etc/kolla/certificates/private/ ]; then
  mkdir -p /tmp/certificates
  cp /etc/kolla/certificates/private/*/*.crt /tmp/certificates
fi

for server in $servers; do
  echo "copying to: $server"
  scp -pr -o StrictHostKeyChecking=no -o ConnectTimeout=30 /tmp/certificates "$server":"$HOME"/certificates
  ssh -t -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$server" sudo -- "sh -c 'cp $HOME/certificates/*.crt /usr/local/share/ca-certificates/ && update-ca-certificates'"
done
