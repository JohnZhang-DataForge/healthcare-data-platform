---
status: active
scope: azure-fabric-system-overview
last_verified: 2026-11-05
---

# Azure / Microsoft Fabric — Lakehouse and OMOP Analytics

Fabric analytics is separated from the Local PG17 transactional OMOP writer. The physical Warehouse is an existing Workspace item; never invent a synthetic native Warehouse Git folder. [Fabric CODE](CODE.md) is the source owner map.

## Ownership at a glance

| Work | Source and map |
| --- | --- |
| Native Notebook, Pipeline, Environment, Lakehouse | [Native Git Items](../../../azure-fabric/workspaces/healthcare-omop/) · [Notebook](notebooks/CODE.md) · [Pipeline](pipelines/CODE.md) · [Environment](environments/CODE.md) |
| Warehouse SQL, Schema and manifests | [deployment/warehouse](../../../azure-fabric/deployment/warehouse/) · [Deployment CODE](deployment/CODE.md) |
| OMOP Writer business Python | [Writer source](../../../azure-fabric/warehouse/omop-foundation/writer/) · [Warehouse CODE](warehouse/CODE.md) |
| OpenLineage Publisher and Listener deployment | [Publisher](../../../azure-fabric/openlineage/) · [OpenLineage CODE](openlineage/CODE.md) |
| Terraform resources | [IaC modules](../../../azure-fabric/infra-terraform/) · [Terraform CODE](infra-terraform/CODE.md) |
| Shared pure Python engine | [Shared Engine](../data-platform/shared-engine/README.md) |

## Verified scope and acceptance boundaries

Shared Engine version 0.1.3 is [published to Environment](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41834029745) with an independently [completed isolated Spark 4.1 import](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167). This does not prove the formal business Notebook's Engine guard is aligned or that FHIR→Bronze/Silver Approval→OMOP Gold warehouse COMMIT, replay and physical readback succeeded. See [FHIR E2E Change](../../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) and [OMOP Foundation](../../../openspec/changes/fabric-omop-foundation/tasks.md).

Current development follows [Native execution ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md), [Deployment ownership spec](../../../openspec/specs/fabric-deployment-component-ownership/spec.md) and [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md). Azure Capacity, Terraform apply, Notebook run and SQL/Delta write require independently authorized, observed execution.

The previous [Fabric system history and exact past configuration inputs](FABRIC-HISTORY-20261105.md) remains byte-identical; old dated architecture assumptions are not current deployment proof.
