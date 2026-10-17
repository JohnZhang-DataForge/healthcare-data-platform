# Azure / Microsoft Fabric — source code

This folder contains the **Azure/Fabric analytical-replica subsystem** of Healthcare Data Platform. The local PostgreSQL OMOP database remains authoritative: a future read-only exporter will publish consistent, verifiable snapshots to an **existing Azure Blob landing**; a **Fabric Data Pipeline** will orchestrate a PySpark Notebook that validates and loads a OneLake Lakehouse.

**Scope and status (October 2026):** the Terraform infrastructure source is present and all seven roots have passed the post-copy **Plan-only** regression. The exporter, Blob publishing process, Fabric-native Notebook/Pipeline business implementations, and independent end-to-end reconciliation are **not implemented**. A successful Plan is not a Fabric Apply, active Notebook/Pipeline, or data E2E acceptance. Warehouse is optional, outside the initial OneLake-first MVP.

## Code ownership and directory layout

```text
azure-fabric/
├── README.md
├── infra-terraform/                  # Existing Terraform infrastructure code
│   ├── README.md                     # Terraform developer entry
│   ├── components/                   # Seven independent Terraform root modules
│   ├── modules/                      # Seven matching implementation modules
│   └── docs/ARCHITECTURE.md          # Technical IAM / State / deployment boundaries
├── exporter/                         # Future: local PG snapshot + immutable Blob publication
│   └── .gitkeep
├── workspace/
│   └── healthcare-omop/              # Intended Git scope for existing Fabric Workspace
│       ├── notebooks/
│       │   └── ingestion/            # Future: native *.Notebook/ items
│       │       └── .gitkeep
│       └── pipelines/                # Future: native *.DataPipeline/ items
│           └── .gitkeep
└── tests/                             # Future: exporter, contract, Fabric and readback tests
    └── .gitkeep
```

| Area | Responsibility | Where to begin |
| --- | --- | --- |
| [`infra-terraform/`](infra-terraform/README.md) | Provisioning, Azure/Fabric identities and resource ownership, independently keyed remote State | [Terraform README](infra-terraform/README.md) and [IAM/State design](infra-terraform/docs/ARCHITECTURE.md) |
| `exporter/` | Future **local** read-only OMOP consistent snapshot, Parquet, checksum, READY manifest, Blob publication | Placeholder only; do not recreate or mutate the completed local OMOP batches |
| `workspace/healthcare-omop/notebooks/ingestion/` | Future Fabric-native ingestion and Delta-loading **Notebook items** | Placeholder only; no `*.Notebook` or Git integration has been established by the directory |
| `workspace/healthcare-omop/pipelines/` | Future Fabric-native **Data Pipeline items** to pass `export_id` and `manifest_uri` and enforce failure gates | Placeholder only; no `*.DataPipeline` item |
| `tests/` | Future unit, snapshot-contract, idempotency, integration and independent PG ↔ Lakehouse reconciliation | Placeholder only |

### Fabric Git items vs Terraform resources

This repository uses **two different source formats**, and they must not silently become independent deployment owners:

- The current [Terraform Notebook definition](infra-terraform/modules/notebook/main.tf) provisions a **fail-closed bootstrap** from [`modules/notebook/definitions/notebook-content.py`](infra-terraform/modules/notebook/definitions/notebook-content.py). The Notebook explicitly raises `RuntimeError`; it is **not** business ETL.
- The current [Terraform Data Pipeline definition](infra-terraform/modules/data-factory/main.tf) selects a [Fail activity](infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) until a real Notebook GUID is supplied. The alternate [Notebook activity](infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) is only an unexecuted definition.
- **Later**, actual Fabric Git-integrated Notebook sources should live in `<item>.Notebook/` folders containing `notebook-content.py` and Fabric-generated `.platform` metadata; Pipelines use `<item>.DataPipeline/` with `pipeline-content.json` and corresponding metadata. Do **not** hand-invent `.platform` logical IDs or mislabel the current Terraform bootstrap files as synchronized Fabric items.
- Before Git integration is enabled, choose and document **one** deployment owner for each Notebook/Pipeline item (Terraform item definition or the Fabric Git delivery path); manage the transition deliberately, preserving item identity. Do not make both mechanisms overwrite the same item.

References: [Microsoft Fabric Notebook source control](https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment) and [Fabric Git source format](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format).

### Infrastructure copy and execution

The original [`azure/infra-terraform/`](../azure/infra-terraform/README.md) has **not** been removed. The new copy under `azure-fabric/infra-terraform/` is now the workflow-selected path; the [Self-Runner Azure-Infra-TF workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) uses `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`. A seven-component **Plan-only** run from that path passed on October 16, 2026; see [verification evidence](infra-terraform/docs/ARCHITECTURE.md#verified-plan-evidence).

All seven component roots retain their existing remote Azure Blob backend keys: `dev/<component>.tfstate`. **Never Apply through both directory copies.** The workflow exposes an explicit `apply` option, but **none is authorized by a documentation/code-layout cleanup**. Terraform State, Fabric workspace import, IAM changes, actual resource creation and data operations require their own review.

**Documentation boundaries:** this README explains physical code organization. Cross-platform design is owned by [Architecture](../documents/architecture/SYSTEM-OVERVIEW.md), current Azure/Fabric system explanation by [Systems / Azure-Fabric](../documents/systems/azure-fabric/README.md), and project status by [Project Status](../documents/engineering/status/PROJECT-STATUS.md). These are separate from infrastructure execution instructions.
