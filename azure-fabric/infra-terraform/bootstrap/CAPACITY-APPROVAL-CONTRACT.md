# Bootstrap Capacity Creation — Detached Billing Gate (Offline)

> Active Change \`bootstrap-fabric-infrastructure\`, Task 1.3. **This is NOT an authorization or a pricing quote**. The program \`tools/fabric_capacity_approval.py\` can never authorize paid creation; it is a safe shape-check for future independently reviewed evidence.

- Profile \`capacity.mode=reuse-existing\` is the default and requires an independently verified existing Capacity ID; never creates or adopts it. A separate billing-evidence file in reuse mode is rejected.
- Profile \`capacity.mode=create-new\` must specify an F-series SKU, Azure Region, Subscription ID, monthly estimate, budget, billing owner and cost review reference. Schema/format validity never proves that the SKU is offered, the provider version supports it, a quota exists, or costs are approved.
- If cost evidence is absent, output \`HOLD_PAID_CAPACITY_EXTERNAL_APPROVAL\`. When evidence is present, strict matching covers environment, Fabric Tenant, Subscription, SKU, Region, budget, cost estimate, exact source SHA and separate independent reviewer, dated expiring review record URI. It still returns \`cost_review_verified=false\` and \`paid_creation_authorized=false\`. **External trusted verification of the document, scope, approver authority, amount, validity and GitHub protected Environment is required** before a future controlled Plan/Apply gate can permit any Azure creation.
- No review document, secret or approval token is committed to the repository. Keep actual review in an access-controlled billing workflow outside untrusted PR input; a URL or text label is *not* a signed approval.
- The future Terraform Capacity module will have independently default-false creation flags, \`prevent_destroy\`, no automatic suspend/resume, and a separate manual authorization gate in a protected environment. Never interpret \`prevent_destroy\` as cost protection, and never turn this offline validator into an Azure token issuer.
- Test file: \`tests/test_fabric_capacity_approval.py\`; CI is GitHub-hosted and executes Python only. A green run is a **static shape assertion**, not a live Budget, IAM, Provider or billing test.

## Future live approval checklist (not yet authorized)

Exact Main SHA; requested Tenant/Subscription/Region/SKU and Capacity administrator UPN/Object ID; current subscription price/region/quota quote; estimated 24-hour and full-month expense at requested SKU; approved maximum and expiry; approval identity separate from request owner; protected GitHub Environment + ref/reviewers; explicit permission for Azure Cost Management/ARM read and then separately for any Plan/Apply; resource inventory and ownership review; evidence of credentials/privilege without storing actual tokens. Absence of any item means **HOLD**.

Sources:
- [Microsoft Fabric Capacity ARM schema 2023-11-01](https://learn.microsoft.com/en-us/azure/templates/microsoft.fabric/2023-11-01/capacities)
- [Fabric Terraform Provider Capacity guide](https://registry.terraform.io/providers/microsoft/fabric/latest/docs/guides/fabric_capacity_setup)
