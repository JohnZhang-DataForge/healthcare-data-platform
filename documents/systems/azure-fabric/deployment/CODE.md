# Fabric Deployment — canonical owner map

This document defines deployment **configuration/assets and release tooling**, not OMOP row-level business logic, native Fabric Git items, or infrastructure provisioning. It is the CODE-map owner referenced by the tracked [seven-component registry](../../../../azure-fabric/deployment/owners.json).

## Reserved components

| Registered component | Intended owner | Current state |
| --- | --- | --- |
| notebook | `azure-fabric/deployment/notebook/` | Reserved; existing Native Notebook code stays in workspaces |
| pipeline | `azure-fabric/deployment/pipeline/` | Reserved; native Pipeline JSON stays in workspaces |
| environment | `azure-fabric/deployment/environment/` | Reserved; Shared Engine source stays in its single src package |
| lakehouse | `azure-fabric/deployment/lakehouse/` | Reserved; Native metadata stays in workspaces |
| warehouse | `azure-fabric/deployment/warehouse/` | CDM54 39-table DDL and OMOP Foundation five management-table SQL, manifest, identity-key contract |
| openlineage | `azure-fabric/deployment/openlineage/` | Offline Spark OpenLineage Listener candidate configuration, not runtime activated |
| common | `azure-fabric/deployment/common/` | Reserved for independently justified shared deployment logic |

Deployment currently tracks the registry and reviewed Warehouse/OpenLineage assets. Empty reserved folders are intentionally absent; Git does not track directories without files. The existing Warehouse Writer and OpenLineage RunEvent Publisher remain in their component source folders.

## Boundaries and release workflow

GitHub Actions triggers live in `.github/workflows/`, focused offline tests in `.github/quality/tests/azure-fabric/deployment/`, and Terraform in `azure-fabric/infra-terraform/`. Private Self-Runner owns OIDC credentials and authorized cloud execution. Do not copy its deploy scripts into this repository.

The [static ownership checker](../../../../.github/quality/scripts/check_fabric_deployment_ownership.py) and [CI](../../../../.github/workflows/fabric-deployment-ownership-offline.yml) reject unregistered deployment paths, misplaced READMEs/tests and missing CODE-map edits in changed deployment-source PRs. At introduction this is a **head-branch CI check, not yet a trusted Required Check**. Only the approved protected-policy/Ruleset route can make it enforcement; never falsely claim the gate is protected.

## Actual deployable assets (source-only; no live execute)

- [CDM54 Source Manifest](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/manifest.json), [39 Warehouse SQL DDL files](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/tables/), [OHDSI original DDL blob](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/upstream/OMOPCDM_sql_server_5.4_ddl.sql).
- [OMOP Foundation Manifest](../../../../azure-fabric/deployment/warehouse/omop-foundation/manifest.json), [INT identity contract](../../../../azure-fabric/deployment/warehouse/omop-foundation/identity-key-v1.json), [5 audit/etl DDL files](../../../../azure-fabric/deployment/warehouse/omop-foundation/sql/).
- [OpenLineage Spark listener compatibility plan](../../../../azure-fabric/deployment/openlineage/compatibility.py).
- Python source that **did not move**: [Warehouse identity planner](../../../../azure-fabric/warehouse/omop-foundation/writer/identity_plan.py) and [OpenLineage publisher](../../../../azure-fabric/openlineage/publisher.py).
