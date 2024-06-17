#!/bin/bash

TERRAFORM_PATH="../terraform"

ACR_NAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_name)
RESOURCE_GROUP=$(terraform -chdir=$TERRAFORM_PATH output -raw resource_group)
ACR_SERVER=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_login_server)
ACR_USERNAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_username)
ACR_PASSWORD=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_password)

while [[ "$#" -gt 0 ]]; do 
    case $1 in 
        --image) IMAGE_NAME="$2"; shift;;
        --tag) IMAGE_TAG="$2"; shift;;
        --dir) DOCKER_DIR="$2"; shift;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

if [[ -z "$IMAGE_TAG" ]]; then
    IMAGE_TAG="default"
fi
if [[ -z "$IMAGE_NAME" || -z "$DOCKER_DIR" ]]; then
    echo "Error: Missing required arguments."
    usage
fi


az acr login --name $ACR_NAME

docker build -t $ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG $DOCKER_DIR

docker push $ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG

echo "Docker image pushed to ACR: $ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG"