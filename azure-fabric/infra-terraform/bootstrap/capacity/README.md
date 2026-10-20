# Fabric Capacity Bootstrap Root — CODE ONLY / PAID HOLD

OpenSpec Task 2.4. This Root is not deployed. No Terraform init, plan, apply, destroy, import, Azure/Fabric API call, paid resource creation or Capacity suspend/resume has been authorized.

Default `capacity_mode=reuse-existing`: zero Terraform managed resources and zero data sources. The optional existing Fabric Capacity UUID is a caller-supplied **unverified** reference. No Import, Adopt or changes to existing Capacity, Storage, `healthcare-omop`, Remote State or seven legacy Roots.

Opt-in `capacity_mode=create-new`: candidate `Microsoft.Fabric/capacities@2023-11-01` through **Azure/azapi 2.8.0**, an explicit Fabric Tenant B/subscription, existing approved `rg-hdp-*` ARM ID, new environment-isolated name `hdp<environment>capacity`, Region, F SKU and administrator list. Separate creator, subscription/RG/SKU/name inventory, source SHA, budget and independent billing approval + protected Environment / human reviewer gates ALL default false; any one missing keeps resource count=0. These booleans are untrusted claims and cannot authorize a live action. The trusted executor must verify the cost approval against an immutable source SHA and separate Terraform Init/Plan/Apply permissions.

IMPORTANT: output `created_azure_arm_id` is an Azure ARM resource ID, **not** automatically a Fabric workspace-compatible Capacity UUID. The latter remains `created_fabric_uuid=null` until independent authorized runtime readback; Task 3.1 is responsible for safe downstream handoff.

Account A→A′ and A→B are explicitly supported. Storage belongs to Tenant A and Fabric Capacity to Tenant B, so **their subscription IDs are independent**. This fixes the earlier offline-profile same-subscription restriction. Capacity Root never owns or creates the Storage Root RG. Fresh Capacity RG ownership/inventory must be independently established for Tenant B.

No automatic suspend, resume, timed scale-down, task-based create/destroy or unlimited billing. `prevent_destroy` does not prevent ongoing cloud charges. Backend is independent protected local Bootstrap State; never `init` against newly declared Storage. Offline CI runs only Terraform `fmt -check` and Python static tests; Provider schema, tenant support, price and quotas remain UNVERIFIED.

Official sources: [Microsoft Fabric 2023-11-01 Capacity ARM + AzAPI](https://learn.microsoft.com/en-us/azure/templates/microsoft.fabric/2023-11-01/capacities), [Cost-approval contract](../CAPACITY-APPROVAL-CONTRACT.md), [Provider freeze](../PROVIDER-SCHEMA-REFERENCE.md).
