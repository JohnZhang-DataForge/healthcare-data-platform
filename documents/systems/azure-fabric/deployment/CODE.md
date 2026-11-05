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

The [static ownership checker](../../../../.github/quality/scripts/check_fabric_deployment_ownership.py) and [CI](../../../../.github/workflows/fabric-deployment-ownership-offline.yml) reject unregistered deployment paths, misplaced READMEs/tests and missing CODE-map edits in changed deployment-source PRs. At introduction (PR #699), this was only a head-branch CI check. The subsequently merged [trusted default-branch owner workflow](../../../../.github/workflows/fabric-deployment-ownership-trusted.yml) **is now Required by active Ruleset #25365902** (GitHub Actions integration 15368), independently confirmed with positive PR #703 and blocked negative PR #704. The original head-branch `ownership-offline` remains supplemental.

## Actual deployable assets (source-only; no live execute)

- [CDM54 Source Manifest](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/manifest.json), [39 Warehouse SQL DDL files](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/tables/), [OHDSI original DDL blob](../../../../azure-fabric/deployment/warehouse/omop-cdm-5.4/upstream/OMOPCDM_sql_server_5.4_ddl.sql).
- [OMOP Foundation Manifest](../../../../azure-fabric/deployment/warehouse/omop-foundation/manifest.json), [INT identity contract](../../../../azure-fabric/deployment/warehouse/omop-foundation/identity-key-v1.json), [5 audit/etl DDL files](../../../../azure-fabric/deployment/warehouse/omop-foundation/sql/).
- [OpenLineage Spark listener compatibility plan](../../../../azure-fabric/deployment/openlineage/compatibility.py).
- Python source that **did not move**: [Warehouse identity planner](../../../../azure-fabric/warehouse/omop-foundation/writer/identity_plan.py) and [OpenLineage publisher](../../../../azure-fabric/openlineage/publisher.py).

## Trusted PR ownership checking

The [trusted owner workflow](../../../../.github/workflows/fabric-deployment-ownership-trusted.yml) uses `pull_request_target` and loads policy, registry and test code solely from the default branch; candidate PR Git paths and CODE map are passive data. Its stable job name is `require-trusted-fabric-deployment-owner`. **Enforcement is confirmed:** Ruleset #25365902 lists this job as Required (integration ID 15368) alongside `require-trusted-change` and `validate-openspec`, no bypass actors. [Positive PR #703](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/703) passed and merged; [negative PR #704](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/704) was made non-Draft, the trusted owner job failed for `deployment/rogue/`, GitHub reported `mergeable_state=blocked`, and the PR was closed unmerged. The existing `ownership-offline` job is optional diagnostic feedback, not the authoritative trusted gate.
