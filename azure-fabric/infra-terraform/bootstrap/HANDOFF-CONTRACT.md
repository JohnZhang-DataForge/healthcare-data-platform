# Bootstrap → Fabric Root non-secret handoff contract (offline v1)

> **Status: HOLD.** `fabric_bootstrap_handoff.py` validates the four already supplied **value-only** JSON objects: strict Bootstrap Profile v1, independent resolved Client IDs (Tenant + Client GUIDs), the `bootstrap/storage` `storage_target` value, and the `bootstrap/capacity` `capacity_target` value. It does NOT fetch Terraform State or live Azure/Fabric data; do not supply raw `terraform output -json` wrappers, cloud credentials, private State files, secrets, or access tokens.

Run manually on already prepared **non-secret, synthetic or independently cleared** files:

```bash
python3 azure-fabric/infra-terraform/tools/fabric_bootstrap_handoff.py \
  --profile /path/to/strict-profile.json \
  --resolved-clients /path/to/identity-value-only.json \
  --storage-target /path/to/storage-target-value-only.json \
  --capacity-target /path/to/capacity-target-value-only.json
```

All root outputs remain **unverified** even if populated. The validator rejects unknown fields, duplicate JSON keys, mismatched Tenant, Storage subscription/resource group/account ARM scope, role collision, State prefix, Capacity provenance, false-turned-true verification flags, and use of an ARM resource path as a Fabric Capacity UUID. **No file is created; stdout is a preview only, never Terraform variables or an approval.**

## Mode matrix (both support same-Tenant A→A′ and cross-Tenant A→B)

| Storage mode | Capacity mode | Non-secret result | Hard stop |
| --- | --- | --- | --- |
| `reuse-existing` | `reuse-existing` | `STATIC_HANDOFF_HOLD_EXTERNAL_INVENTORY`; preview of existing `fabric_environment_preflight.py` schema with separate Tenant A/B Client IDs and `fabric/<env>/*.tfstate` | Existing `johnzhang` Storage ID/State inventory, actual Capacity UUID/tenant, GitHub OIDC and RBAC not checked. No commands, remote reads or approvals. |
| `fresh-bootstrap` | `reuse-existing` | `STATIC_HANDOFF_HOLD_FRESH_STORAGE_ROOT_GAP`; no new-environment config | Existing `fabric_environment_preflight.py`, `fabric_deployment_target.py`, `fabric_backend_config.py` and `new-environments/connection` **hard-code `johnzhang`**. They must be deliberately generalized and retested before any fresh deployment; never silently fall back to old Storage. Private networking/state custody are also unresolved. |
| Either | `create-new` | `STATIC_HANDOFF_HOLD_PAID_CAPACITY_UUID`; no new-environment config | Azure ARM Capacity ID is **not** workspace `fabric_workspace.capacity_id` (Fabric Capacity UUID); external verified readback, actual billing authorization, SKU, quota, budget and deployment approval all required. |

The review flags `verified`, `capacity_id_verified`, `backend_state_checked`, `billing_approved`, `github_oidc_verified`, `terraform_executed` are always **false**. Even a passing replay cannot confirm remote State emptiness, guard IAM policies, or authorize Terraform Init/Plan/Apply/Import.

**Ownership chain:** Bootstrap/Identity is sole owner of its newly-created identities; Bootstrap/Storage sole owner of fresh RG/account/containers/RBAC; Bootstrap/Capacity sole owner of optional paid Capacity. The existing three `new-environments` roots own only `fabric_workspace`, `fabric_lakehouse`, `fabric_connection` respectively, and Notebook/Pipelines belong exclusively to future fabric-cicd. Old seven Roots/`dev/*.tfstate` and `healthcare-omop` remain untouched.

Test: `python3 -m unittest discover -s azure-fabric/infra-terraform/tests -p test_fabric_bootstrap_handoff.py -v` in GitHub-hosted offline CI. Next work must resolve the fresh-Storage Root parameter contract **as a distinct reviewed PR** before changing default-deny Terraform creation semantics.
