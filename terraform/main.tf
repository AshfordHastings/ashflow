data "azurerm_client_config" "my-client" {}

resource "azurerm_resource_group" "rg" {
    name = "airflow-rg"
    location = "East US 2"
}

resource "azurerm_container_registry" "acr" {
    name = "airflowacr695"
    resource_group_name = azurerm_resource_group.rg.name
    location = azurerm_resource_group.rg.location
    sku = "Standard"
    admin_enabled = true
}

resource "azurerm_key_vault" "key-vault" {
  name                        = "airflowkeyvault"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  tenant_id                   = data.azurerm_client_config.my-client.tenant_id
  sku_name                    = "standard"
  
  soft_delete_enabled         = true
  purge_protection_enabled    = true

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }
}

resource "azuread_application" "airflow-app" {
    display_name = "airflow-app"
}

resource "azuread_service_principal" "airflow-spn" {
    service_principal_id = azuread_application.airflow-app.id
}

resource "random_password" "pass" {
    length = 16
    special = true
}

resource "azuread_service_principal_password" "airflow-spn-ps" {
    service_principal_id = azuread_service_principal.airflow-spn.id
    value = random_password.pass.result
    end_date = "2099-01-01T00:00:00Z"
}

resource "azurerm_role_assignment" "spn_key_vault_access" {
    principal_id = azuread_service_principal.airflow-spn.object_id
    role_definition_name = "Key Vault Secrets User"
}

# Assign Key Vault access policy to the logged-in user
resource "azurerm_key_vault_access_policy" "client_access" {
  key_vault_id = azurerm_key_vault.keyvault.id

  tenant_id    = data.azurerm_client_config.my-client.tenant_id
  object_id    = data.azurerm_client_config.my-client.object_id

  secret_permissions = [
    "get",
    "list",
    "set",
    "delete",
    "recover",
    "backup",
    "restore",
  ]
}

# Assign Key Vault access policy to the service principal
resource "azurerm_key_vault_access_policy" "spn_access" {
  key_vault_id = azurerm_key_vault.keyvault.id

  tenant_id    = data.azurerm_client_config.my-client.tenant_id
  object_id    = azuread_service_principal.airflow-spn.object_id

  secret_permissions = [
    "get",
    "list",
    "set",
    "delete",
    "recover",
    "backup",
    "restore",
  ]
}