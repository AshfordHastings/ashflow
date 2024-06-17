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

output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}