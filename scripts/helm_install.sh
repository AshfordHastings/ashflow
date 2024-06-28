
TERRAFORM_PATH="../terraform"

ACR_NAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_name)
RESOURCE_GROUP=$(terraform -chdir=$TERRAFORM_PATH output -raw resource_group)
REGISTRY_NAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_login_server)
ACR_USERNAME=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_username)
ACR_PASSWORD=$(terraform -chdir=$TERRAFORM_PATH output -raw acr_password)

CHART_PATH="helm/ashflow-app-base"
TAG="0.0.1"

helm pull oci://$(REGISTRY_NAME).azurecr.io/$(CHART_PATH) --version $(TAG) --untar
