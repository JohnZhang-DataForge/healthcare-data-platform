# Fabric Deployment — canonical owner map

This document defines deployment **configuration/assets and release tooling**, not OMOP row-level business logic, native Fabric Git items, or infrastructure provisioning. It is the CODE-map owner referenced by the tracked [seven-component registry](../../../../azure-fabric/deployment/owners.json).

## Reserved components

| Registered component | Intended owner | Current state |
| --- | --- | --- |
| notebook | `azure-fabric/deployment/notebook/` | Reserved; existing Native Notebook code stays in workspaces |
| pipeline | `azure-fabric/deployment/pipeline/` | Reserved; native Pipeline JSON stays in workspaces |
| environment | `azure-fabric/deployment/environment/` | Reserved; Shared Engine source stays in its single src package |
| lakehouse | `azure-fabric/deployment/lakehouse/` | Reserved; Native metadata stays in workspaces |
| warehouse | `azure-fabric/deployment/warehouse/` | Reserved pending checked SQL/manifest relocation from `azure-fabric/warehouse/` |
| openlineage | `azure-fabric/deployment/openlineage/` | Reserved pending Listener compatibility configuration move from `azure-fabric/openlineage/` |
| common | `azure-fabric/deployment/common/` | Reserved for independently justified shared deployment logic |

The only deployment tree file currently tracked is the registry itself. Empty folders are intentionally absent; Git does not track directories without files. The existing Warehouse Writer and OpenLineage RunEvent Publisher remain in their component source folders.

## Boundaries and release workflow

GitHub Actions triggers live in `.github/workflows/`, focused offline tests in `.github/quality/tests/azure-fabric/deployment/`, and Terraform in `azure-fabric/infra-terraform/`. Private Self-Runner owns OIDC credentials and authorized cloud execution. Do not copy its deploy scripts into this repository.

The [static ownership checker](../../../../.github/quality/scripts/check_fabric_deployment_ownership.py) and [CI](../../../../.github/workflows/fabric-deployment-ownership-offline.yml) reject unregistered deployment paths, misplaced READMEs/tests and missing CODE-map edits in changed deployment-source PRs. At introduction this is a **head-branch CI check, not yet a trusted Required Check**. Only the approved protected-policy/Ruleset route can make it enforcement; never falsely claim the gate is protected.
