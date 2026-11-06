---
status: active
scope: azure-fabric-notebooks-source-map
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

# Fabric Notebooks — CODE 源码地图

**真实 Native Item 归属：** [`nb_fhir_ingest.Notebook/`](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/)（Fabric Git Integration 自动生成的根级目录）。早期 `notebooks/ingestion/.gitkeep` 只是占位，已从当前 Git 清理，不是 Native Item 定义。

**2026-10-31 真实初始化完成：** Fabric Portal 将 `nb_fhir_ingest` Item 原生定义同步到 GitHub `fabric/native-bootstrap-20261031`，Commit `a6c3d0d6`；`.platform` 的 logicalId 非零。这是最初的空壳初始化历史；当前 Git 主文件已恢复完整 P2 业务代码，并经两种真实 Fabric 定义读回验收。


**2026-10-31：**旧 `johnzhang-test` Trial Native Notebook/Pipeline Smoke 及其测试已正式从源码树退休（Self-Runner [PR #350](https://github.com/JohnZhang-DataForge/Self-Runner/pull/350)、Healthcare 清理 PR）。不再维护该测试 Workspace 的原生 Item 文件。历史 Item 定义可查阅 [退役前固定 Git 历史](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/e4640eb4ce4edd8570ca60c9ad2c1b6152941743/azure-fabric/workspaces/johnzhang-test)，不得照旧发布。**曾通过 Terraform Apply 的 Workspace/Lakehouse 尚未确认云端删除，等待独立 State-aware teardown。**

## 实际拥有的 Fabric 原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| [nb_fhir_ingest.Notebook/.platform](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/.platform) | Fabric Git 同步的真实 Notebook Item 元数据；不要手工改 logicalId |
| [nb_fhir_ingest.Notebook/notebook-content.py](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py) | P2 单一实现的 Git Native Notebook，含 Fabric Cell/Parameters Cell 与启动 HOLD；已完成手工 Git Sync，并由 Self-Runner 双格式 GetDefinition 证实业务代码保留 |

## FHIR 5/100 source read-only Spark Intake (2026-11-02)

The same Git Native `nb_fhir_ingest` offers a second non-mutating mode `INTAKE_READONLY`, distinct from `RUNTIME_SMOKE` and from gated `execute_native_notebook` Delta writer. It only accepts two **previously verified synthetic** Atlanta FHIR Publisher request IDs and exact Manifest SHA256 values, reads `Files/fhir_landing/clinical/v1/.../landing-manifest.json` and each manifest-listed FHIR Bundle via native Spark binaryFile, verifies SHA/size, parses Patient/Encounter, reports aggregate counts and exits with a pinned marker. The default `HALT`, write-authorized false, and Pipeline HALT are unchanged. Tests reject unpinned IDs and any nonblank source/manifest/target or write flag.

**Cloud status:** Fabric Shortcut creation and actual Notebook Spark source readback are separate gates; no Silver/Delta/FHIR E2E acceptance until both independently pass. Existing Blob Publisher 5/100 independent Azure GET/HEAD verified in [Self-Runner #41495354432](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41495354432); this does not prove Fabric Spark I/O. OpenSpec `ingest-fhir-to-fabric` task 2.4 remains unchecked.

## Azure Publisher Manifest v1 Intake compatibility (2026-11-02)

The same authoritative [Native FHIR Notebook source](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py) now validates the **actual** Azure publisher v1 `landing-manifest.json` schema, distinct from the earlier isolated synthetic Manifest fixture. The deployed Azure Publisher produces `objects[].blob_key`, `etag`, `version_id` and no `source_system`; the Intake adapter requires exact hospital/feed/request and versioned FHIR path, validates delivered-Manifest SHA separately from upstream Generator source_manifest_sha256, and fails closed on conflict. Offline positive/negative tests: [P2 Notebook tests](../../../../.github/quality/tests/azure-fabric/notebook/test_notebook_offline.py). Actual Blob permissions, object readback, Bronze/Delta writes and replay are **NOT_RUN**; OpenSpec `ingest-fhir-to-fabric` G0/G3/G4 remain open.

## Business Notebook gated Runtime smoke (2026-11-02)

The one canonical `nb_fhir_ingest.Notebook/notebook-content.py` now has an explicit import-only `RUNTIME_SMOKE` execution mode for the **existing** Fabric business Notebook. In the original 2026-11-02 implementation checkpoint it checked Shared Engine v0.1.1 and PySpark 4.1; for the current v0.1.3 environment use the separately verified published-wheel evidence and emits a pinned exit marker. The default `HALT`, the independent `execute_native_notebook` write guard, and the Pipeline default remain unchanged. Offline negative checks are in [Native Contract tests](../../../../.github/quality/tests/azure-fabric/notebook/test_fabric_git_native_contract.py). Live service-principal execution, exact exit and independent evidence remain required before declaring this code cloud-verified. See [Git onboarding OpenSpec task 3.3](../../../../openspec/changes/archive/2026-11-05-fabric-native-notebook-git-onboarding/tasks.md).

## Git-first new Notebook deployment (2026-11-02)

The trusted Healthcare [Fabric Git Deploy](../../../../.github/workflows/fabric-git-deploy.yml) dispatches on any root-level `nb_*.Notebook/**` change, including new `.platform` files. The Self-Runner updater owns authorization: it requires Git-native identity, remote-only `Added` for creation, and independent workspace item/definition readback. A dispatched workflow is NOT proof of creation. The existing `nb_fhir_ingest` HALT and Pipeline contracts remain pinned. Do not manually precreate a Notebook of the same name in the Portal; do not copy a smoke logicalId.

The initial generic contract accepts root-level `nb_*.Notebook` items only; moving items into a new Fabric UI folder or adding a new Pipeline/Environment requires separate review. See [Notebook onboarding OpenSpec](../../../../openspec/changes/archive/2026-11-05-fabric-native-notebook-git-onboarding/tasks.md).

**以后如何更新：**每增加一个真实 Notebook Item，应在上表使用**指向实际文件的相对 Markdown 链接**登记其真实 `.platform`、`notebook-content.py` 及其他生成文件。静态 CODE-map CI 会检查源码完整性、链接归属，并要求新增、删除或迁移文件时在同一个 PR 更新本 `CODE.md`。

现有 [Terraform Notebook Bootstrap](../../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 故意抛出异常，由 [Azure/Fabric 总 CODE.md](../CODE.md) 导航。不能把它直接改名放入 Workspace 并声称是 Fabric Git 已同步的 Notebook。

**强制开发规范：** [Fabric Native Git Authoring Runbook](FABRIC-GIT-AUTHORING-RUNBOOK.md)（Notebook 格式、参数 Cell、13 行分隔空行事故和真实云端验收；Agent 修改前必读）。

**继续阅读：**[Notebooks 职责](README.md) · [Pipelines CODE.md](../pipelines/CODE.md) · [Azure/Fabric 概览](../README.md)。

## G5 Candidate input approved Silver readonly gate (2026-11-04)

- The **real Git Native Notebook** [`nb_fhir_ingest.Notebook/notebook-content.py`](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py) owns a new isolated `G5_CANDIDATE_SOURCE_READONLY` mode. This entry point is **strictly read-only**, pinned to approved G4 request `atlanta-fhir-gh-41552666929` and delivered Manifest SHA `425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1`. It requires both original canonical v1 JSON contract bytes and `DELTA_RAW_SNAPSHOT_V1` with `write_authorized=False`, `retention_preflight_verified=False`, no source/target override.
- It first invokes the existing `verify_fhir_g4_silver(mode="SILVER_READBACK_ONLY")` physical data + source-byte + single Approval fence check. It then performs **fresh** Spark Delta reads for Patient / Encounter / Approval, verifies P100/E5918/Q0, exact SHA/provenance/namespace, unique PKs and Encounter→Patient FK. The historical `_G4_PROCESSING=...engine-0.1.1` is intentionally retained to locate the already approved physical Delta, while executing Wheel is the **real published v0.1.3**. Do not rename the processing partition.
- [Offline synthetic tests](../../../../.github/quality/tests/azure-fabric/notebook/test_g5_candidate_source_readonly.py) verify guard-before-read, rejection of malformed/unapproved requests, count drift, Approval tamper/duplicates and orphan FKs. A passing unit test is **not** Fabric Spark runtime acceptance. **No code** in this slice reads the Warehouse ID Map, uses unapproved Concept IDs, writes Candidate Delta, publishes Gold or triggers an automatic Pipeline.
- Only an actual separately controlled Fabric Spark run returning exact `FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_APPROVAL_DELTA_PASS_20261104` plus independent job verification can close the live gate. Read-only G5 source success is **not** candidate write or F2/F3 Warehouse success. See [G5 OpenSpec](../../../../openspec/changes/fabric-g5-approved-silver-omop-candidate/tasks.md). Keep Native Notebook's 2 ordinary cells, 1 Parameters Cell, all metadata separators and default HALT intact.


## G5 0.1.3 published / 0.1.6 candidate isolation (source-only)

- [Notebook Offline CI](../../../../.github/workflows/fabric-fhir-notebook-offline.yml) uses **two independent installed Wheel environments**: the one already-published Git Native `0.1.3` SHA-verified binary for all native HALT/G3/G4 tests; reproducibly built source-only `0.1.6` for G5 Candidate import/test on Python 3.13 / Spark 4.1. The legacy Notebook must explicitly reject the 0.1.6 package before any Spark/Delta/Cloud I/O until a separately approved Native source upgrade. The older `0.1.3` binary is **not rebuilt from current `0.1.6` sources**.
- [Release isolation regression](../../../../.github/quality/tests/azure-fabric/notebook/test_g5_release_isolation.py) checks sole staged Git wheel SHA, both version metadata values, HALT and fail-closed G3/G5/smoke guards without cloud execution. This is a source-only release preflight; it neither publishes a new Environment Wheel nor changes any native Notebook file. A future Notebook update would trigger [Fabric Git dispatcher](../../../../.github/workflows/fabric-git-deploy.yml), requiring separate user coordination and live side-effect review. G4 historical processing `engine-0.1.1` stays immutable.

## G5 0.1.6 Git-native and independently verified Cloud staging vs legacy effective 0.1.3

- The reviewed Git Native Environment and real Fabric Cloud **staging** both contain the sole 0.1.6 Wheel as proven by [GET-only Run #42283214760](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42283214760), while Fabric **Published** Library was 0.1.3 at that independent readback. That gate was subsequently **physically accepted** in [GA Publish Run #42284453546](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42284453546) with independent [GET-only Run #42283214760](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42283214760), which confirmed Published 0.1.6 and Staging 0.1.6. The separate **real isolated Spark 4.1 import passed** in [Self-Runner Run #42285486908](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42285486908), with exact 0.1.6 exit, Job Completed and temporary cleanup. The **official business Notebook remains pinned to 0.1.3/HALT** and is not yet migrated; this import is not a G5 Candidate/Gold E2E. Offline Notebook tests install the historical byte-pinned 0.1.3 Wheel from immutable Git commit `b56b73207f7abe9d98e3fa4c3603fe045af6e15a`, and independently verify newly staged 0.1.6 bytes. The official Native Notebook still has `engine_version == "0.1.3"` and `HALT`; it is deliberately **not** synchronized/migrated with this Environment-only PR. See [Environment CODE map](../environments/CODE.md).

## G5 Native business Notebook 0.1.6 alignment — source and real Git readback VERIFIED

- Sole Git Native business file [nb_fhir_ingest.Notebook/notebook-content.py](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py) now uses the GA Published and isolated Spark 4.1-import-verified `healthcare_data_engine==0.1.6` guard for all existing runtime and read-only paths; new exact import-only `RUNTIME_SMOKE` marker is versioned 0.1.6. It was initially a Git SOURCE change; it has now passed a separate real native Notebook Git deployment/definition readback (details below).
- [Fabric Notebook offline CI](../../../../.github/workflows/fabric-fhir-notebook-offline.yml) installs sole Git-native 0.1.6 with immutable SHA256 and runs all 89+ original G3/G4/native Notebook regression tests; separately verifies historical 0.1.3 rollback bytes and rejects an old 0.1.3 runtime even with read-only flags. Shared 0.1.6 synthetic G5 Candidate tests remain independent. No Cloud/SQL/Delta actions inside tests.
- The Native format, Parameters Cell, canonical Adapter wire `0.1.0`, G3/G4 historical `engine-0.1.1` processing paths, HALT, false write flags and restricted G5 source-only modes are unchanged. Prior real Workspace Notebook was **local-only Modified**. The existing [Git dispatcher](../../../../.github/workflows/fabric-git-deploy.yml) safely reconciled the verified canonical serialization conflict after comparing local/native definitions; [Self-Runner #42291355563](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42291355563) reports `AUTO_UPDATE_DEPLOYMENT_READBACK_PASS`, `notebook_business_cells_match_git=true` and 3 native code cells, while Pipeline safe parameters remained PASS. The **separate official business Notebook import-only RUNTIME_SMOKE remains unexecuted**; the earlier temporary Notebook import cannot substitute. No G5 clinical/Gold acceptance.

## P3 统一测试归属（2026-11-04）

上述 Notebook、G3、G4、G5 的离线测试文件现仅在 `.github/quality/tests/azure-fabric/notebook/` 维护；`azure-fabric/notebook-development/` 中的 `fhir_ingest_notebook.py` 和 `native_item_readiness.py` **仍是实际离线辅助源码**，不因测试迁移而移动。CI 执行文件是 [Fabric Notebook Offline Contract](../../../../.github/workflows/fabric-fhir-notebook-offline.yml)，必须断言 9 个测试文件与至少 89 个可发现用例，避免空测试集 PASS。


### P4 原位保留决定

`fhir_ingest_notebook.py` 是 Native Notebook 的 17 行离线兼容导入层，不是生产中的第二套 Notebook；`native_item_readiness.py` 是 63 行只读 Git Native 元数据预检并被 Hosted CI 直接调用。它们目前依赖原相对路径及明确 `PYTHONPATH`，移动将触及测试/Workflow 的执行路径但不会带来可验证的收益，因此**经审计决定两者原位保留，不移动到质量脚本目录**；所有新测试仍放集中质量目录。
