#!/bin/bash

cd /opt/kolla
source venv/bin/activate
kolla-ansible -i multinode deploy
kolla-ansible -i multinode post-deploy
