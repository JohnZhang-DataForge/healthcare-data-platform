---
status: active
scope: fabric-notebook-git-offline-contract
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

> **P2 文档归属**：完整保留原 `azure-fabric/notebook-development/README.md` 的独有安全约束与历史试验结论。下面按原版本的运行范围解释；最新 Fabric 业务与环境验收需核对 [总 CODE](../CODE.md)、正式 Notebook/Environment CODE 与真实 Runs。本次没有访问或修改任何云端资源。

# Fabric P2 FHIR Notebook — Git-first source and offline validation

The **single authoritative Notebook business source** is now
[`nb_fhir_ingest.Notebook/notebook-content.py`](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py).
It is a real FabricGitSource item with Fabric-generated nonzero `.platform` logicalId
and the actual existing healthcare-omop Lakehouse metadata. The previous
[`fhir_ingest_notebook.py`](../../../../azure-fabric/notebook-development/fhir_ingest_notebook.py) is now an offline-only
compatibility loader that imports the Native Notebook; it MUST NOT be separately
published or modified as a business implementation.

The Notebook contains the P2 Manifest/SHA verification, Shared Engine FHIR
Patient/Encounter canonical transformation, Bronze receipt, immutable Delta
Silver staging, quarantine, idempotency, independent physical readback, and
explicit approval guards. It intentionally starts with `run_mode=HALT`,
`write_authorized=False`, `retention_preflight_verified=False`, and its
Fabric startup cell **always stops with HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED**.
Authoring the source is not cloud authorization.

The actual Pipeline source is
[`pl_fhir_ingest.DataPipeline/pipeline-content.json`](../../../../azure-fabric/workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/pipeline-content.json).
It has one `TridentNotebook` activity referencing verified real Workspace and
Notebook GUIDs, no automatic retries/schedules, and passes only disabled
write parameters. A manual Run now would fail closed and could still incur a
Spark startup cost; **do not run it**. Run status is not business acceptance.

**Historical Git-first 2026-10-31 build baseline:** Shared Engine was one Python Wheel, `healthcare-data-engine==0.1.0`
(SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7`).
The GitHub-hosted [offline CI](../../../../.github/workflows/fabric-fhir-notebook-offline.yml)
builds, verifies and uploads this Wheel as an artifact; a CI artifact is **not**
a published Fabric Environment. At this historical checkpoint, Environment binding/publish, effective library readback and Lakehouse retention checks were HOLD. **Do not apply this historical HOLD to later verified releases:** [current system CODE](../CODE.md) records Wheel 0.1.3 published and separately scoped runtime import/readback; business Gold remains gated.

Run the static Gate (expected exit 2 even after valid Git native export):

```sh
python azure-fabric/notebook-development/native_item_readiness.py
```

Expected `HOLD_NATIVE_RUNTIME_DEPLOYMENT`, not the old
`BLOCKED_NATIVE_EXPORT`. At the original 2026-10-31 checkpoint, an operator-only workspace Git branch switch from `fabric/native-bootstrap-20261031` to `main` was still pending after CI and a no-delete/no-recreate review. **This is a historical instruction, not a request to repeat a branch switch today.**

Further release gates: attached/published Environment with effective Wheel,
valid retained FHIR source/Manifest/Contracts, approved runtime bindings,
capacity/cost, job identity, and Bronze/Silver physical readback. Do not mark
Gold COMMITTED from Notebook or Pipeline success.
