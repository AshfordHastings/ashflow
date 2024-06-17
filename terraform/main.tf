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