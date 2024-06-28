#!/bin/bash

TERRAFORM_PATH="../terraform"

ACR_NAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_name)
RESOURCE_GROUP=$(terraform -chdir=$TERRAFORM_PATH output -raw resource_group)
ACR_SERVER=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_login_server)
ACR_USERNAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_username)
ACR_PASSWORD=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_password)

while [[ "$#" -gt 0 ]]; do 
    case $1 in 
        --dir) CHART_DIR="$2"; shift;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

if [[ -z "$CHART_DIR" ]]; then
    echo "Error: Missing required arguments."
    usage
fi


az acr login --name $ACR_NAME

echo $ACR_PASSWORD | helm registry login $ACR_SERVER --username $ACR_USERNAME --password-stdin

TARRED_CHART=$(helm package $CHART_DIR | awk -F': ' '{print $2}')

echo "TARRED_CHART path: $TARRED_CHART"

# Push command does not contain version or the base name - just stores to helm directory 
# REgistry reference base is inferred from chart's name, tag is inferred from chart's version
helm push "$TARRED_CHART" oci://$ACR_SERVER/helm

echo "Helm Chart pushed to ACR."

rm -f "$TARRED_CHART"

echo "Cleaned up $TARRED_CHART"