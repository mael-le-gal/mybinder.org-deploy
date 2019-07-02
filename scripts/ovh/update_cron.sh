#!/bin/bash

echo "Updating the python script configmap"

kubectl create -n ovh configmap script-clean-harbor-registry --from-file=scripts/ovh/clean_harbor_registry.py --dry-run -o yaml | kubectl apply -f -

echo "Updating the k8s cronjob"

kubectl apply -n ovh -f config/ovh/cron_clean_harbor_registry.yaml