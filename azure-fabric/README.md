# Azure / Microsoft Fabric — source code

The Azure/Fabric subsystem owns the **cloud analytical replica**, separate from the local OMOP ingestion platform. Its immediate target is a read-only PostgreSQL OMOP snapshot → existing Azure Blob landing → Fabric Data Pipeline → Fabric PySpark Notebook → OneLake Lakehouse. Neither the exporter nor the Fabric business ETL has been implemented.

## Two source areas

```text
azure-fabric/
├── README.md
├── infra-terraform/                   # IaC, independent Terraform roots and modules
│   ├── components/                   # Seven root components
│   ├── modules/                      # Seven matching implementation modules
│   ├── docs/ARCHITECTURE.md
│   └── README.md
└── workspaces/
    └── healthcare-omop/              # Existing Fabric Workspace name (not a new resource)
        ├── notebooks/
        │   └── ingestion/            # Reserved grouping for native *.Notebook items
        └── pipelines/                # Reserved for native *.DataPipeline items
```

| Source area | Purpose and ownership | Read first |
| --- | --- | --- |
| [`infra-terraform/`](infra-terraform/README.md) | Terraform-managed resource definitions, Workspace/OneLake identities, RBAC and remote State; **not** production ETL source | [Terraform developer guide](infra-terraform/README.md), [technical architecture](infra-terraform/docs/ARCHITECTURE.md) |
| [`workspaces/healthcare-omop/notebooks/`](workspaces/healthcare-omop/notebooks/) | Actual Fabric-native Notebook item sources for validation and Delta loading (future) | [Notebooks component](../documents/systems/azure-fabric/notebooks/README.md), [CODE](../documents/systems/azure-fabric/notebooks/CODE.md) |
| [`workspaces/healthcare-omop/pipelines/`](workspaces/healthcare-omop/pipelines/) | Actual Fabric-native Data Pipeline item sources for orchestration (future) | [Pipelines component](../documents/systems/azure-fabric/pipelines/README.md), [CODE](../documents/systems/azure-fabric/pipelines/CODE.md) |

The `notebooks/ingestion/` and `pipelines/` directories currently contain **only `.gitkeep` placeholders**. Neither a Fabric `*.Notebook/` item nor a `*.DataPipeline/` item exists in this source tree, and this repository layout does not connect the existing Fabric Workspace to Git.

When creating native Fabric items, retain Fabric's actual generated `.platform` metadata and item content files. Do not create arbitrary item IDs or treat repository folder names as Fabric resource IDs. If Notebook business processing is split into reusable Python modules, decide its packaging and source ownership explicitly rather than putting arbitrary helper code into the Git-synchronized item folder.

## Avoid dual Notebook / Pipeline deployment ownership

The Terraform Notebook module still uses [a fail-closed bootstrap Python definition](infra-terraform/modules/notebook/definitions/notebook-content.py) that deliberately raises `RuntimeError`. The Terraform Data Pipeline uses [a Fail activity](infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) until a real Notebook ID is available; its [Notebook activity JSON](infra-terraform/modules/data-factory/definitions/pipeline-notebook.json) is not a live pipeline. These definitions **remain under Terraform**; they are not copied into the empty native Git item folders.

Before adopting Fabric Git Integration, settle one authoritative delivery mechanism and existing item identity for each Notebook/Pipeline, so Terraform and Fabric Git do not overwrite the same object. [Notebook source control](https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment) · [Fabric Git item formats](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/source-code-format).

## Local exporter and tests — not Fabric Workspace items

The older `exporter/` and `tests/` folders here contained **only empty `.gitkeep` markers**; they were retired so that `azure-fabric/` has exactly the two agreed source areas. The future read-only PostgreSQL exporter still belongs to the project design, but it runs on the **local** side and its eventual implementation/test location will be selected alongside its API and deployment workflow. Do **not** treat removing the placeholders as cancelling the exporter, tests or independent reconciliation requirement.

## Existing infrastructure and safety

Self-Runner [Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) now targets `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`. All seven component roots previously passed new-path **Plan-only** checks; [run evidence and scope](infra-terraform/docs/ARCHITECTURE.md#verified-plan-evidence). The original [`azure/infra-terraform/`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/41be1aba4d8b730b2a9e17fadfc0450e6aec5095/azure/infra-terraform/README.md) was retired from Main after source parity and reference checks, and remains retrievable only from a pinned Git commit. Do not restore it as a parallel Terraform execution root or assume identical definitions imply imported resources.

All State keys remain `dev/<component>.tfstate` in the existing remote Azure Blob backend. **No Apply, Fabric Git connection, business Notebook/Pipeline deployment or data E2E is authorized by a source-tree refactor.** Read the [system overview](../documents/systems/azure-fabric/README.md) and the [project status](../documents/engineering/status/PROJECT-STATUS.md) for architecture and current acceptance boundaries.
