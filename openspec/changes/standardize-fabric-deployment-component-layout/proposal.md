# Establish a stable Fabric deployment/component layout and migrate SQL/lineage assets

## Context

Healthcare Fabric has canonical Git-native Notebook/Pipeline/Environment/Lakehouse items, separate Warehouse SQL and Writer files, and an offline OpenLineage Listener plan/Publisher. Current paths predate a consistent source-vs-deployment architecture. Owners have asked to finalize future component locations now and complete the small, controlled Warehouse/OpenLineage deployment-asset migration instead of repeated broad cleanups.

## Change

- Define one architecture contract for Fabric native items, component source, deployable artifacts, deployment execution adapters, infrastructure, shared-engine Python, docs and quality assets.
- Reserve `azure-fabric/deployment/{notebook,pipeline,environment,lakehouse,warehouse,openlineage,common}` in a tracked machine-readable owner registry; don't create arbitrary empty directories.
- Physically relocate **deployable** Warehouse SQL/metadata and OpenLineage Listener candidate configuration into their matching `deployment/` owners, preserving **byte-for-byte source content and Warehouse physical identity**.
- Retain Warehouse Writer/Python business rules under `azure-fabric/warehouse/` and OpenLineage RunEvent Publisher under `azure-fabric/openlineage/`; do not disguise business modules as deployment scripts.
- Update affected Healthcare tests/workflows/CODE docs and the private Self-Runner consumers **before deleting old source paths**, including guarded historical SHA behavior.
- Extend existing layout validation rather than adding an untrusted or unenforced parallel policy.

## Non-goals / safety

No Fabric UpdateFromGit, Notebook execution, DDL/DML, data/Gold COMMIT, Azure/K8s/Marquez operations, Terraform apply, schema drift repair, new Warehouse Native Git item, or duplicated Shared Wheel. Previous evidence remains scoped to its pinned SHA. The existing Workspace-only Warehouse and its GUID remain untouched.
