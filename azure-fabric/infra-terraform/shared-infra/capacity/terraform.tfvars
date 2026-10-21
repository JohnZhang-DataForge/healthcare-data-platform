# Paid Azure F2 capacity. Creating this resource starts PAYG charges.
# Only permitted for the explicitly approved johnzhang-test E2E run.
capacity_name       = "fcjohnzhangtest"
resource_group_name = "OMOP"
location            = "eastus"
sku_name            = "F2"
additional_admins   = ["johnzhang-fabric@guangbinzhang8888gmail.onmicrosoft.com"]
