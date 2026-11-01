# P3 Wheel 0.1.1 — Fabric live preflight and release decision (2026-11-01)

> **Current verified state: P3 Git Sync + Environment Publish + Notebook declarative binding/readback PASS; actual Spark Runtime import remains HOLD.** This file retains the **historical pre-release snapshot** below for traceability. User explicitly authorized advancing this **development-only** Environment on 2026-11-01, and the two cloud changes were performed independently with exact SHA gates; there is still no patient data write/ETL authorization from this release.

## 最新 2026-11-01 — Notebook 绑定确认与真实 Spark Smoke HOLD

**证据级别**：真实 Notebook metadata/Environment declaration 已验证；不是 Spark Session 动态加载证明。真实 Fabric Job 仍没有一轮 Completed / 精确 0.1.1+PySpark4.1 import exit 的成功结果。**不得将 P3 Runtime、FHIR ETL、Delta write、最终验收标为 PASS**。

- **绑定 PASS（声明 / 云端定义）**：Healthcare [PR #594](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/594) / main `381a23d5024448896f4d530b61a0f03c5ad22a85`，Self-Runner 独立只读 [Run #41341350800](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41341350800)。目标 Published `env_healthcare` 物理 ID `d85a4218-8da0-46ed-8517-b5eced219dd5`；`engine_version=0.1.1`，数据契约 `adapter_version=0.1.0` 保留。已有原业务 Notebook `HALT`/不写保护不变。
- **失败 1 / 2**：Self-Runner [Run #41342534629](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41342534629) 首次 Job `Failed`；[Run #41343169292](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41343169292) Core Job `Failed/BadRequest`，Artifact `13098322693`，Job `28b01bd9-e065-4398-bffa-bfe3c7f7491b`。Job 的 POST 已被接受（HTTP 202），此 BadRequest 来自**异步执行阶段**，不是最初 POST HTTP 400。
- **失败 3（更安全诊断）**：Self-Runner [PR #390](https://github.com/JohnZhang-DataForge/Self-Runner/pull/390) / [Run #41353132947](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41353132947)，Artifact `13101689917`，Job `c3a6c7e4-0c12-455f-8494-85e1c0216eff`，`Failed/BadRequest`，Request ID `3a159b16-0f7a-4167-a7a3-b245a4a5d37c`，Root Activity ID `e7c008f3-73a9-4c13-8a49-b32dde37455f`。beta 附加错误详情未获取。
- **失败 4（显式 Spark + Environment release API）**：Self-Runner [PR #391](https://github.com/JohnZhang-DataForge/Self-Runner/pull/391) / main `d857f2f3e01a35675915cd4b2651aab7d853e5ab` / [Run #41353644397](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41353644397)，Artifact `13101968471`，Job `c14a1ab3-16ee-48a8-a212-37a36ac80907`。按微软 [Notebook release Job 文档](https://learn.microsoft.com/en-us/rest/api/fabric/notebook/background-jobs/run-on-demand-notebook) 使用 `POST /notebooks/{id}/jobs/execute/instances?beta=false`，执行参数固定 `compute=Spark` + Published `attachedEnvironment`，Job 仍 `Failed/InvalidRequest`；Request ID `4821e253-d66e-458b-ba47-6b595e1c4fe4`，Root Activity ID `417d411d-4ef8-473e-ac61-44985544450a`。**不能**据此断定是哪一个执行参数错误。
- **每轮安全性**：最新两轮发布前的 Git HEAD/Published 0.1.1/Notebook physical Environment 预检 PASS；临时 Notebook 已清理；没有运行 `nb_fhir_ingest`、读取患者数据、写入 Delta/OneLake、重复 Publish。两个执行请求都返回并记录了终态 Failed。Git 自动同步仍安全地 `HOLD/NOTEBOOK_HEADER_OR_ORDER_DIFFERENT`，与 Spark 故障单独处理，禁止绕过保护。

**接下来的动作保持 HOLD**：Fabric 官方 Monitoring hub/Spark diagnostic（如有对应 Job）或 Microsoft Support 以以上 `requestId` 和 `rootActivityId` 跟踪后台真实失败原因；无后端证据不要重复相同 Job。之后才讨论单点修复 + 新独立 Smoke。正式验收必须同时具备新 Session `healthcare_data_engine.__version__ == 0.1.1`、`metadata.version() == 0.1.1`、PySpark 4.1.x、Job Completed、精确 exit 值和临时资源清理。

## Verified rollout and official Fabric effective-library evidence — 2026-11-01

| Release gate | Concrete cloud evidence | Result |
| --- | --- | --- |
| Git update / Staging | Self-Runner [PR #384](https://github.com/JohnZhang-DataForge/Self-Runner/pull/384), trusted [Run #41323755874](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41323755874), artifact `fabric-p3-environment-sync-41323755874` ID `13091005258` | `P3_GIT_STAGING_011_VERIFIED`; exact old synced HEAD `8188cddcd79f0654eff1d95b81fd97ad94604f2d` → reviewed Healthcare main `66335f9544217e2109d43061f265f22bab871d0e`; Staging sole Custom Wheel **0.1.1**, legacy 0.1.0 absent |
| Preserve Workspace-only definitions | Same artifact stores pre/post Notebook `.py`, Notebook `.ipynb`, Pipeline JSON backups | All 3 pre/post content SHA256 exactly equal, local canonicalization against immutable Git baseline PASS; no Notebook/Pipeline overwrite |
| Independent GA Publish | Self-Runner [PR #385](https://github.com/JohnZhang-DataForge/Self-Runner/pull/385) merged `cd4991a412155467727e8f2812dbeb42777233e3`, trusted [Run #41325158603](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41325158603), artifact `fabric-p3-environment-publish-41325158603` ID `13090879253` | Before publish GA Published list: HTTP 404 UNKNOWN; one POST `/staging/publish?beta=false` → HTTP **202**, LRO ID present, LRO finally **Succeeded** (23 polls), `publishDetails.state=Success`, `sparkLibraries.state=Success`, targetVersion reported |
| Effective GA published library listing | After LRO, official `GET /libraries?beta=false` | **available=true; sole Custom Wheel `healthcare_data_engine-0.1.1-py3-none-any.whl`; zero External; zero legacy 0.1.0; no duplicate Wheel**. Final status `P3_ENV_011_PUBLISHED_READBACK_PASS`. |
| Release scope / limitations | Audit report | Git source provenance Wheel SHA256 `4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3`; GA list exposes filename only, **not effective installed wheel file SHA**. `spark_sessions_started=false`, `notebook_executed=false`, `delta_writes=false`, `git_update_attempted=false` in Publish run. |

**Remaining work:** `nb_fhir_ingest` currently pins `engine_version == "0.1.0"`; unlike Shared Engine package `0.1.1`, the `adapter_version == "0.1.0"` business schema check may be intentionally independent and must be reviewed separately. The notebook has not proven effective attachment to `env_healthcare`. Coordinate Notebook source version alignment + binding, and then a fresh nonwriting Spark runtime import smoke. Existing `HALT`/write authorization safeguards remain. Do **not** declare E2E ETL PASS.

## Historical pre-release read-only snapshot (superseded by verified Git sync + Publish)



## Provenance and versions

| Gate | Evidence | Observed result |
| --- | --- | --- |
| Source and package | Healthcare [PR #585](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/585), [CI #41316184936](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41316184936) | Shared Engine 0.1.1 real Wheel install PASS on Python 3.11 and 3.13; PySpark 3.5.7/4.1.1 regression PASS; repeatable SHA256 `4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3` |
| Git-native Environment | Healthcare [PR #590](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/590), merged main `4d16469349e3ed629a2ed3f4b308bbf29702bec4` | Sole Git CustomLibraries Wheel is 0.1.1; exact byte comparison to rebuild PASS; **no cloud state implied** |
| Trusted cloud metadata preflight | Self-Runner [PR #383](https://github.com/JohnZhang-DataForge/Self-Runner/pull/383), main `424d6313292420156663e407a1bdeeabe1aab3a1`, [live run #41319069996](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41319069996) | All 3 jobs PASS, including **GET-only** Fabric OIDC readback; Git provider credential rebind disabled for automatic main push |
| Cloud Git connection/status | Live `fabric-git-preflight-41319069996` artifact | GitHub `main` remote SHA `4d16469349e3ed629a2ed3f4b308bbf29702bec4`, Fabric synced workspace HEAD `8188cddcd79f0654eff1d95b81fd97ad94604f2d`; `HOLD_UNAPPROVED_CHANGES` |
| Cloud Environment staging | Live `fabric-p2-live-definition-41319069996` artifact | Exactly 1 custom library listed, **0.1.0 legacy=True**, **0.1.1 target=False**; release state `HOLD_LIBRARY_READBACK_UNAVAILABLE` |
| Cloud Environment published | Same live artifact | `GET /libraries?beta=false` HTTP 404, effective published Wheel **UNKNOWN**. Historic `publishDetails.state=Success` / `sparkLibraries.state=Success` is not proof of effective 0.1.1 |
| Notebook binding + runtime | Same live artifact | ipynb metadata `NOT_DECLARED_IN_IPYNB` (not proof of unbound); real Spark binding/import **NOT_VERIFIED**, no Spark session executed |
| Notebook and Pipeline | Live drift artifact `fabric-git-drift-41319069996` | Notebook/Pipeline safe readback PASS but cloud-local representation differs from Git (details below); Notebook runtime code still pins engine 0.1.0 with `run_mode=HALT` |

## Why automatic UpdateFromGit correctly stopped

The trusted Git status at the exact cloud HEAD/remote SHA lists **three** items, no reported `Conflict`:

| Item | Item type in live Git status | Remote change | Workspace change | Action now |
| --- | --- | --- | --- | --- |
| `env_healthcare` | `Environment` | `Modified` | `None` | Candidate incoming Git 0.1.1, **not yet cloud staged** |
| `nb_fhir_ingest` | `SynapseNotebook` | `None` | `Modified` | Preserve cloud-local item and compare serialization before any change |
| `pl_fhir_ingest` | `Pipeline` | `None` | `Modified` | Preserve physical ID references, compare before any change |

The read-only drift tool found Notebook code-cell sequence equal but **parameter metadata not semantically identical** (one end-of-file diff span). For Pipeline, its two reported property differences are physical Notebook/Workspace references in cloud versus Git logical/same-workspace sentinel references; the cloud pipeline still points to the actual notebook and same workspace, and its HALT parameters are preserved. These observations do **not** authorize discarding cloud-local definitions.

**Important limitation:** Fabric's standard Source Control Update operation updates the connected branch to the latest commit; the UI cannot select only one Environment Item for Update. The UpdateFromGit API accepts per-item **options**, but that is not a documented selective item list. It may affect relevant incoming changes according to Git status, and must never be invoked automatically here merely because the remote Env update is the only incoming one. Official references: [Git integration process](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/git-integration-process), [Update From Git REST API](https://learn.microsoft.com/en-us/rest/api/fabric/core/git/update-from-git), [Environment Git staging vs Publish](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline).

## Controlled forward sequence — **all cloud write steps require new explicit authorization**

1. **Read-only re-preflight**: check real Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`, Environment `d85a4218-8da0-46ed-8517-b5eced219dd5`, Notebook `8311ab6b-3484-4e96-8370-badeeb751633`, authenticated Git connection, `workspaceHead`, `remoteCommitHash` and full item status. Halt if new changes, conflicts, unexpected item types, unknown IDs or concurrent update/publish appear.
2. **Resolve the drift preservation plan (no write now)**: review/export a controlled backup of current Notebook/Pipeline definitions using readback, record their hashes and physical references, compare parameter metadata. Existing local-only modifications MUST NOT be silently committed, undone or overwritten. Confirm any update's precise side effects and recovery steps. No assumption of item-specific Git update.
3. **Separately authorized Git UpdateFromGit**: only after reviewing the *whole* branch update scope, approved exact HEAD pair, rollback and credential state. Never use permissive override/conflict resolution defaults to force changes. After the operation, independently GET Git status and Environment staging. Expected staging sole 0.1.1; if still 0.1.0 or API unavailable, HOLD. **Git sync does not Publish.**
4. **Separately authorized Environment Publish**: compare staging and published libraries, check in-flight Publish, Runtime 2.0/Python 3.13 compatibility and session/capacity impact; obtain explicit approval before Publish. Capture LRO/targetVersion and published readback. Published 404 remains UNKNOWN until evidence resolves it.
5. **Coordinated Notebook update and binding**: the existing Notebook explicitly requires engine `0.1.0`. Do not remove that gate as part of step 3. Separately review the 0.1.1 Notebook version pin, Fabric native `env_healthcare` binding, running Session impact and retained `run_mode=HALT`, `write_authorized=False`, `retention_preflight_verified=False`, and `HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED`.
6. **Separately authorized non-writing Spark smoke**: only inside a fresh explicitly approved environment/session, check `importlib.metadata.version('healthcare-data-engine')`, module `__version__` and path; do not read patient data, run the production Notebook or write Delta/OneLake/PG.
7. **Next development change**: only after all gates have evidence, plan the actual FHIR Bronze/Silver data execution in its own reviewed change; no inferred E2E or Silver APPROVED from isolated import.

## Hard stop / rollback

- Without explicit cloud-action authorization: **GET-only, HOLD**. There is **no automatic recovery, overwrite, Publish or Notebook execution**.
- Preserve old 0.1.0 Wheel provenance SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7` for comparison, not automatic re-upload.
- If a read-only endpoint returns an unclassified 404, mark Published UNKNOWN; do not infer that historical Publish Success means the new Wheel is effective.
- Re-run a trusted read-only preflight immediately before any separately approved mutation. Keep logs scrubbed of credentials, raw Notebook source and personal healthcare data.
