output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "acr_username" {
  value = azurerm_container_registry.acr.admin_username
  sensitive = true
}

output "acr_password" {
    value = azurerm_container_registry.acr.admin_password
    sensitive = true
}

output "tenant_id" {
    value = azuread_service_principal.airflow-spn.application_tenant_id
}

output "client_id" {
    value = azuread_service_principal.airflow-spn.object_id
}

output "client_secret" {
    value = azuread_service_principal_password.airflow-spn-ps.value
    sensitive = true
}

output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}