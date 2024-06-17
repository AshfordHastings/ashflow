#!/bin/bash

TERRAFORM_PATH="../terraform"

ACR_NAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_name)
RESOURCE_GROUP=$(terraform -chdir=$TERRAFORM_PATH output -raw resource_group)
ACR_SERVER=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_login_server)
ACR_USERNAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_username)
ACR_PASSWORD=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_password)
EMAIL="ashfordh1@gmail.com"
NAMESPACE="default"
SECRET_NAME="acr-secret"

az login

kubectl create secret docker-registry $SECRET_NAME \
    --docker-server=$ACR_SERVER \
    --docker-username=$ACR_USERNAME \
    --docker-password=$ACR_PASSWORD \
    --docker-email=$EMAIL \
    --namespace=$NAMESPACE
