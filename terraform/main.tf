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

resource "azurerm_key_vault" "keyvault" {
  name                        = "airflowkeyvault1"
  location                    = azurerm_resource_group.rg.location
  resource_group_name         = azurerm_resource_group.rg.name
  tenant_id                   = data.azurerm_client_config.my-client.tenant_id
  sku_name                    = "standard"
  
  purge_protection_enabled    = false

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }
}

resource "azuread_application" "airflow-app" {
    display_name = "airflow-app"
}

resource "azuread_service_principal" "airflow-spn" {
    client_id = azuread_application.airflow-app.application_id
}

resource "azuread_service_principal_password" "airflow-spn-ps" {
    service_principal_id = azuread_service_principal.airflow-spn.id
    end_date = "2099-01-01T00:00:00Z"
}

resource "azurerm_role_assignment" "spn_user_access" {
    scope = azurerm_key_vault.keyvault.id
    principal_id = data.azurerm_client_config.my-client.object_id
    role_definition_name = "Key Vault Secrets User"
}

resource "azurerm_role_assignment" "spn_key_vault_access" {
    scope = azurerm_key_vault.keyvault.id
    principal_id = azuread_service_principal.airflow-spn.object_id
    role_definition_name = "Key Vault Secrets User"
}

# Assign Key Vault access policy to the logged-in user
resource "azurerm_key_vault_access_policy" "client_access" {
  key_vault_id = azurerm_key_vault.keyvault.id

  tenant_id    = data.azurerm_client_config.my-client.tenant_id
  object_id    = data.azurerm_client_config.my-client.object_id

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Recover",
    "Backup",
    "Restore",
  ]
}

# Assign Key Vault access policy to the service principal
resource "azurerm_key_vault_access_policy" "spn_access" {
  key_vault_id = azurerm_key_vault.keyvault.id

  tenant_id    = data.azurerm_client_config.my-client.tenant_id
  object_id    = azuread_service_principal.airflow-spn.object_id

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Recover",
    "Backup",
    "Restore",
  ]
}