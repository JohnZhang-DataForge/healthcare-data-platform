# Design — 2026-10-30 Architecture Decision

**Data architecture + Fabric-native code layout adopted 2026-10-31; runtime NOT authorized.** 执行架构以 [Fabric-native ADR](../../../documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) 为准，数据业务以 [Medallion ADR](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) 为准。2026-10-27 的两份重复 Draft 已从当前 Git 树清理；需要历史实现细节时按 Medallion ADR 的固定 Git Commit 追溯。

## Adopted design

```text
Blob Manifest + Byte SHA → Intake
→ Bronze (Shortcut / Copy, raw source + Delta receipt)
→ PySpark FHIR Source/Entity Adapter + Canonical DQ
→ Silver Lakehouse Delta (canonical_patient / canonical_encounter, approved)
→ Shared OMOP Mapper + Concept + Stable Identity + Reconciliation
→ Candidate staging
→ Gold OMOP 5.4 person / visit_occurrence (verified controlled publication)
```

1. Bronze 保留原始事实（或可验证的不可变源引用），不是 Local 已核准 Canonical Raw；Shortcut 不等于来源对象不可变，保留/权限须 POC。
2. Silver 必须持久化二维 Canonical Delta table，附 Source/Contract/Processing 版本、质量报告和 approved 证据。FHIR Patient/Encounter 由独立 Adapter 转换；HL7/CSV Adapter 后续独立 Change。现实 FHIR Optional 与 Local v1 nonnull 冲突时 quarantine 或另审 Canonical v2，禁止造值。
3. Silver 之后复用源无关 OMOP Person/Visit Candidate Mapper、Concept、ID、DQ/PK/FK 和 Reconciliation；按版本化 Profile 处理编码差异。不同来源不按姓名生日自动合并 Patient。
4. Local 纯 DataFrame/Contract 算法逐步抽离至唯一 `shared-data-engine` Wheel；Fabric Pipeline 调度实际 PySpark Notebook，Environment 安装发布 Shared Wheel；Shortcut/Copy/Spark/Delta 使用 Fabric 原生能力，**不预建第二个 Fabric I/O/Runtime Wheel**。Local 运行代码不动，真实 Spark/Python 兼容独立验证。
5. Gold 首选研究 **Warehouse staging + Warehouse 内 Person/Visit/IDMap/Ledger 显式 T-SQL 单事务**；跨 Lakehouse→Warehouse 不属于同一事务，Warehouse PK/FK/UNIQUE NOT ENFORCED 需应用层检验。纯 Delta 多表 visibility 作为未定的备选；不能把 Delta 单表 ACID 冒充跨表原子。Gold COMMITTED 依独立数据读回。
6. MVP 必须使用 **Fabric Pipeline + 真正运行 PySpark ETL/DQ/Delta/readback 的 Notebook + Fabric Environment + 唯一 Shared Wheel**；dbt 暂不引入；Lakehouse SQL Endpoint 只读，不可用其 T-SQL 写 Silver Delta。
7. Source Batch (hospital/feed/request + manifest SHA)、Processing Version (adapter/contract/mapping/code SHA)、Publication ID (committed target version) 分离；已提交同版本重跑 SKIP、同 request 新 SHA 冲突 HOLD、未知 ACK 先只读核验。

## Final Fabric-native execution decision (2026-10-31)

[Authoritative Native Notebook/Pipeline/Environment ADR](../../../documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md) replaces earlier separate Fabric ingestion wheel and I/O framework proposals. Notebook is real Spark ETL; Pipeline orchestrates; Environment publishes exactly one Shared Engine wheel. Cloud mutation is not authorized.

## Concrete repository and Fabric delivery file plan

Practical file-by-file source layout, actual Local files to extract, verified existing Terraform/Trial-native Item paths, target Lakehouse schemas and P0–P5 development slices: [FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT](../../../documents/architecture/design/FABRIC-FHIR-PRACTICAL-SOURCE-LAYOUT.md). This is an actionable planning artifact, **not a list of files already created**. The currently running Local DP and current Terraform State remain untouched. Before new source: reconcile updated Main, verify Live Lakehouse GUID/schema and extend CODE-map/forbidden-import static tests.

## Source-directory governance confirmed 2026-10-30

[Authoritative shared package and Agent ownership policy](../../../documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) fixes one `healthcare_data_engine` package for pure DataFrame Contract/Source Adapter/Canonical/OMOP Mapping/DQ/Identity Plan/Reconciliation; platform I/O/transactions remain in Local or Fabric adapters. The `shared-data-engine/AGENTS.md` scoped instructions and root `AGENTS.md` enforce the read-before-change process for future agents; old Local `spark/contracts/` is still authoritative. Standard `src/` is allowed only for independent installable packages, not for duplicated Local source trees. Existing Local runtime files and currently deployed behavior are unchanged.

**Future code gate**: before the first new Python module, extend CODE-map CI for `shared-data-engine` + Fabric Native Notebook/Pipeline/Environment + Warehouse owner paths, with negative tests for forbidden shared→platform imports and missing CODE.md ownership; do not mark this automated gate complete based on documentation.

## Still open / implementation gates

- Shortcut/Copy 实机 RBAC、Blob 保留及 byte hash；Fabric 旧 Notebook GetDefinition/exitValue 三轮失败仍 HOLD，未经授权不再重跑。
- Gold Warehouse T-SQL Writer 在 Trial/费用/并发下的可靠性 POC；如不适用，重新审查全 Delta visibility。
- Canonical v2、Update/reprocessing policy、ID source namespace/crosswalk，及部署/成本/血缘验收都需独立版本化审查。
- 本次无云资源、数据、代码构建、Pipeline、Fabric Item 和 paid capacity 变更；未来实施门槛见 [tasks](tasks.md)。


## 2026-10-31 Authorized Native bootstrap (narrow permission update)

用户本轮授权创建 healthcare-omop 所需原生 Item；此前无云写许可声明仅对原历史阶段有效。本轮范围仅为三种 Native Item 的受控创建与真实定义导出。

Single writer = trusted Self-Runner/main GitHub OIDC Fabric REST; existing Terraform continues to own Workspace/Lakehouse/Connection and MUST NOT also create the same Items.
Trust boundary = untrusted PR runs GitHub-hosted mocked tests without id-token; only merged Main fixed-name bootstrap uses OIDC. No arbitrary URL/method/workspace/body.
Create-if-absent names: nb_fhir_ingest (Notebook), pl_fhir_ingest (DataPipeline), env_healthcare (Environment). GET inventory before every POST; refuse name/type ambiguity; nonidempotent POST never auto-retried; if acknowledgement unclear, mark HOLD and GET inventory.
LRO: handle HTTP 201/202 and bounded GET /v1/operations/<id>, followed by workspace list + Get Item independent readback. Fabric getDefinition is a POST with read-only semantics; export only real returned bytes to artifact; never guess .platform/logicalId.
Safety: no paid Capacity operation, Spark execution, Environment Publish, OneLake/Blob write or Terraform state mutation in bootstrap. No automatic delete/rollback after partial create: preserve resource IDs and disclose HOLD.
After readback: separately review exported .platform/Git integration and CODE maps, publish immutable Shared Wheel, bind Notebook and Pipeline, and only then consider explicitly gated small synthetic runtime validation.

## Live evidence qualification: Git connection not yet configured

Actual Fabric resource creation and definition export both succeeded in Self-Runner Runs 41242815706 and 41243074326. Follow-up GET `/workspaces/{id}/git/connection` in Run 41243367360 returned `NotConnected`. The REST-exported `.platform` files contain all-zero logicalId; treat as unbound initial Fabric API response, not Git-authoritative source definitions. Native source registration in Healthcare Git and Environment Publish are still pending; no business Spark run/data writes occurred.

## Verified GitHub credential blocker (2026-10-31)

Run 41243652551 independently GET-listed Service Principal-visible Connections: 1 `AzureBlobs` and **zero** GitHub candidates. Workspace Git status remains NotConnected; the three native Items are real and exportable but source control is not yet initialized. No safe automated Git Connect is possible without a real authorized configured connection ID. Continue with Fabric-owned credential setup, then read-only reverify and exact target repo/folder/branch validation before any Git initialization. Native bootstrap is complete; Wheel publish, Notebook content binding, Pipeline activity and Delta runtime remain NOT_RUN.

## Chosen owner for Workspace Git Integration — manual portal (2026-10-31)

**User decision overrides the earlier suggestion to Terraform-manage Fabric workspace Git.** Workspace-to-Git binding, GitHub PAT credential authorization and first sync are performed in Fabric portal by a Workspace Admin. No `fabric_workspace_git`, GitHub `fabric_connection` Terraform module/state/import or TF Apply for this integration; existing Terraform responsibilities for Workspace/Lakehouse/other infrastructure do not change.

Portal: healthcare-omop → Workspace settings → Git integration → GitHub → Add account (fine-grained PAT scoped to single GitHub repo with Contents: Read and write). Target repo `JohnZhang-DataForge/healthcare-data-platform`; folder `/azure-fabric/workspaces/healthcare-omop`; initial branch should be independently reviewed. Because Fabric already contains 3 Native Items and Lakehouse while Git holds only placeholders, first synchronization is an explicit conflict/overwrite gate. Favor exporting/committing Workspace items into a reviewed isolated branch before any Git-to-Workspace update; do not auto-select any direction.

User-authenticated portal Git connection is distinct from Git API automation by the Self-Runner Service Principal. If future automated Git API operations are requested, its configured GitHub connection must separately be shared with the SP and visible to `GET /connections` (historical result 0 GitHub candidates). No unaudited Git Connect, no Terraform, no token in chat. A manual portal connection alone does not prove SP Git API credentials.

## Fabric UI Git Integration initialized and independently Git-verified (2026-10-31)

The user manually configured the GitHub PAT and initialized Workspace→Git on the isolated `fabric/native-bootstrap-20261031` branch (repo root path `azure-fabric/workspaces/healthcare-omop/`). GitHub commit `a6c3d0d6226e0b4084c681104ef9aec6dd3f33c6` contains **four real Fabric Native Item definitions, ten added files, no deletions**; branch forked from main `116d27d74a20860c681e4ac67bfa3681a0739536`. Real Git `.platform` logicalIds are nonzero. The existing `notebooks/ingestion/` and `pipelines/` `.gitkeep` paths are legacy placeholders; the **actual Fabric native definitions are flat** directly beneath the selected Git folder (`nb_fhir_ingest.Notebook/`, `pl_fhir_ingest.DataPipeline/`, `env_healthcare.Environment/`, `lh_omop_analytics.Lakehouse/`). Maintain this exact generated layout and do not relocate definitions by hand. GitHub code review should be based on a separate feature branch deriving from Fabric's synced snapshot, so the live workspace-connected branch remains unchanged. No Fabric Git Update, no Environment Publish, no Spark/Notebook job, no Bronze/Silver write has occurred.

## Git-first P2 handoff — Workspace branch switch remains manual

After real Fabric Git bootstrap, change 4.13 established Git authoritative files with nonzero .platform logical IDs and fixed Item GUIDs. Author Notebook source and Pipeline JSON only on a new GitHub feature branch; never mutate the Fabric-connected bootstrap branch or live Workspace. The source of truth for business logic is the Native Git Notebook; the earlier notebook-development Python file can be retained only as an import-only offline compatibility loader, with one implementation. FabricGitSource cells and a parameter cell are required. Execution defaults disabled and never converts a Pipeline successful orchestration step into Silver approval. Pipeline JSON references the **existing** Notebook `8311ab6b-3484-4e96-8370-badeeb751633` and Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`. Environment requires sole prebuilt version-locked Shared Wheel with matching SHA256, attachment and Publish; do not pretend a local wheel build equates to a published library. Branch switch and any Git Update-from-Git must be performed by the user in Fabric portal after PR validation and a no-delete/no-recreate preview. Safe offline CI is necessary but not Fabric runtime proof.

## Verified-Wheel-to-Git stage before manual Fabric branch switch

The Shared Engine Wheel must enter the Environment's real Git item under `Libraries/CustomLibraries/healthcare_data_engine-0.1.0-py3-none-any.whl`; a CI Artifact alone does not make it part of Fabric Git Integration. Stage via a **trusted main-only GitHub-hosted** GitHub Action with contents-write restricted to creating a separate feature branch. Pin Python 3.11/setuptools 75.8.2/wheel 0.45.1 and SOURCE_DATE_EPOCH; verify the existing immutable Wheel SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7` BEFORE a Git write, fail on mismatch. Commit only that verified Wheel and the associated Environment CODE source map on a review branch, never on main and never against the Fabric-connected bootstrap branch. Re-run PR CI for source ownership and Native definition. No Fabric credentials, OIDC, Environment API, Publish, capacity or Notebook Run in this stage. Do not stage duplicate copies of the Shared Wheel in Notebook or another Fabric source folder. After PR acceptance and merge to main, user may perform one guarded manual branch switch. Publishing the effective Environment and Notebook attachment remain separate gates.


## Live Git-first Pipeline round-trip correction — 2026-10-31

Following Fabric Workspace branch switch to main, Source control showed two uncommitted changes (Notebook and Pipeline). Visual compare of the Pipeline proved Fabric canonicalizes the same-workspace TridentNotebook reference from physical itemId plus workspace GUID to Native Notebook `.platform.config.logicalId` plus all-zero workspaceId sentinel. Existing Git source incorrectly used physical GUID values. Its `typeProperties.notebookParameters` was dropped by Fabric round-trip; the current authoritative Fabric DataPipeline REST definition documents `typeProperties.parameters`. This is a contract defect in our authored Pipeline, not a user change.

Git-first fix: correct ONLY the Git Native Pipeline source on a review branch, preserve .platform IDs and other Item definitions; use Notebook logicalId read directly from the adjacent .platform and `workspaceId=00000000-0000-0000-0000-000000000000`. Under `typeProperties.parameters`, keep `run_mode=HALT`, `write_authorized=false`, `retention_preflight_verified=false` and blank request_id. Keep `policy.retry=0`, no schedule. CI must validate against live Native logicalId and exact recognized Schema field, reject physical Notebook/workspace GUID or unsupported `notebookParameters`, and verify safe defaults.

The second uncommitted Notebook difference needs independent review before touching it. Do NOT commit or Undo the Workspace Changes or run Pipeline; do NOT merge the repair into main until the independent Notebook diff and Git deployment conflict behavior are accounted for. User remains owner of manual Fabric sync.

### Second live diff: Notebook content was lost in Fabric, NOT in Git (2026-10-31)

Manual visual comparison of Fabric Source control `nb_fhir_ingest/notebook-content.py` shows Git main contained 377+ lines and the Workspace exported only `# Fabric notebook source` (376 removed, 1 added). That proves Git → Fabric branch switch direction was correct, but live Notebook cell reconstruction failed. Local PySpark tests did not validate FabricGitSource multi-line `# META` cell-block import. The original authored Notebook compressed per-cell metadata into noncanonical one-line `# META {...}` markers, unlike Microsoft's actual exported examples. The suspected incompatibility is now normalized to full multi-line FabricGitSource metadata for notebook header and each of three Python cells, including the parameter cell and terminal HALT. CI verifies parseable JSON blocks and full source presence but **cannot prove the Fabric parser accepts the repair**; that requires subsequent Git → Workspace Update and independent GetDefinition content readback. Git `main` was not overwritten. Do not commit the current Workspace's one-line Notebook back to Git; don't run Spark. If update reports conflict, explicitly review Notebook/Pipeline incoming changes only, without touching Lakehouse or Environment. Keep G2–G4 HOLD until real runtime release gates.


### Evidence-driven diagnostic: Native source section separators (2026-11-01)

Read-only deployed GetDefinition check after the user accepted incoming main f0603576 returned 26 bytes, while Git connection head advanced to f0603576732448507835d48922f1fb43a86ddd92. Pipeline safe-parameter readback PASS; Notebook still empty. This is a failed/not-retained Notebook import, not a stale branch HEAD. Programmatic authored source omitted blank separators present in Microsoft's official fabric-task-flows and fabric-cicd Notebook source examples. Hypothesis: malformed section boundaries prevent Notebook cell reconstruction. There is no documented definitive requirement that blank lines are mandatory; this remains an unverified hypothesis. Stage canonical spacing and offline tests in a separate PR; do not merge as a verified fix, or prompt more blind Git sync without a controlled, reversible Fabric round-trip. Any deployed readback <8000 bytes or lacking execute_native_notebook remains HOLD. Never commit Workspace's empty Notebook changes into main.


### Confirmed Root Cause and Live Recovery: FabricGitSource cell section separators (2026-11-01)

Status: **definition-import recovery PASS**; not a Spark/Delta runtime or Environment release. The immediately preceding section is historical pre-reproduction reasoning. The subsequent controlled tests supersede the guess that the old compact formatting might be acceptable.

A trusted Self-Runner dual definition readback found both `FabricGitSource` (26 bytes) and Notebook `ipynb` (145 bytes, zero cells) empty while `gitSyncDetails.head` had advanced to `f0603576`; it was not just a UI render defect. An isolated create/readback/delete of three *ephemeral* Notebooks (Self-Runner run 41261920081) then proved a source-format sensitivity: the same marker code was retained with official blank-line separators but lost with compact adjacency; an ipynb control retained code. All temporary item cleanup was confirmed. This isolated REST Create test demonstrated the parser issue without modifying live P2 but did not itself prove Git integration behavior.

Healthcare PR #576 merged only canonical separator formatting and corresponding tests/docs to Git main `9e667468e278f68c3b26f7eb46b81e58b87bf119`. After the user manually reviewed and accepted the one Notebook incoming update, trusted Self-Runner re-run 41262254996, live job 124718913119, obtained:
- Workspace Git sync head exactly `9e667468e278f68c3b26f7eb46b81e58b87bf119`.
- Live Notebook `FabricGitSource` 20,053 bytes; standard `ipynb` 21,689 bytes and **3 code cells**.
- Independent marker checks: business `execute_native_notebook` present, required parameter marker present and runtime HALT preserved; comparison `BOTH_FULL`.
- Live Pipeline `safe_parameters=True`; combined `FABRIC_P2_READBACK_OUTCOME=PASS`.

Therefore the Notebook Git → Fabric source import incident is **RESOLVED by deployed evidence**. This is more than offline parser tests or the UI Last sync diff. The native REST GetDefinition and Git workspace commit checks agree. The existing GET /git/status call with Service Principal yielded HTTP 400 and cannot currently be used as a separate pending-change inventory; manual Fabric Source control remains the control for Git updates until its permission/credentials are independently verified. Do not use that HTTP 400 to invalidate the successful GetDefinition check, and do not claim it represents a Git import error.

**Separate G2–G4 authorization HOLD:** the custom Shared Engine Wheel in Git does not prove published Environment status or Notebook runtime binding. Evidence of Environment published version/effective dependencies, safe Notebook run against non-writing synthetic input, and tightly controlled Bronze/Silver Delta E2E is still required. Keep defaults `HALT`, `write_authorized=False`, `retention_preflight_verified=False`, zero Pipeline retry and no schedule. No automatic promotion from Git readback PASS to writing real data.


The immediate next *read-only* release preflight should compare the Environment's **staging** libraries versus **published** libraries, because [Microsoft's Environment Git guidance](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline) states that Git updates are applied to staging, not the effective published configuration. Microsoft documents the published `GET /environments/{environmentId}/libraries?beta=false` response and matching staging libraries endpoint; only a separate reviewed Environment Publish makes the staged Wheel effective. Also verify the Notebook actually selects the published Environment (or an explicitly configured Workspace default), since Notebook source import itself does not attach the runtime. Do not issue `staging/publish` in a GET-only preflight.


### Environment publish transition is separate from Notebook Git fix (2026-11-01)

The deployed P2 Notebook definition is complete, but no runtime publish or execution is authorized by that fact. Microsoft's [Fabric Environment Git guidance](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline) states that Git-synced Environment libraries update **staging**; a separate Publish is required for effective runtime libraries. The [staging library list API](https://learn.microsoft.com/en-us/rest/api/fabric/environment/staging/list-libraries) and [published library list API](https://learn.microsoft.com/en-us/rest/api/fabric/environment/published/list-libraries) show **names**, not effective file hashes.

Live Self-Runner [Run 41263018957](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41263018957): expected custom Wheel filename found in staging (`True`), published list returned HTTP 404. Independent live [Run 41263182097](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41263182097) also fetched [Environment item metadata](https://learn.microsoft.com/en-us/rest/api/fabric/environment/items/get-environment) via GET and read `publishDetails.state=Success` and `componentPublishInfo.sparkLibraries.state=Success`; the published libraries GET still returned HTTP 404. This suggests an earlier successful publish operation may have occurred without this newly staged Wheel; do not claim current package is effective or that publishing never occurred.

Required next boundary: inspect the Environment portal staging/published diff, authorize and perform Publish separately, read back published library listing, independently validate the effective Wheel digest/version and `nb_fhir_ingest` runtime Environment attachment, and only later consider explicitly approved non-writing synthetic Spark smoke. Preserve Git as authoritative source and the Notebook's HALT / write authorization guards. No publishing or Notebook/Pipeline execution occurred in either diagnostic run.


### Fabric Native Git authoring runbook and Agent handoff rule — 2026-11-01

For all future Notebook/Environment/Pipeline Git-first work in this workspace, Agents MUST read [Fabric Native Git Authoring Runbook](../../../../documents/systems/azure-fabric/notebooks/FABRIC-GIT-AUTHORING-RUNBOOK.md) before editing. The Runbook memorializes the experimentally reproduced serialization-specific source-loss mechanism: a compact single-cell separator format caused real Fabric notebook definitions to drop code even when Python compile, Git CI and Git sync commit succeeded; canonical whitespace/parameters markers plus genuine Fabric Git update and dual-format readback restored the code. Keep the current offline native cell-format regression tests and add isolated real Fabric readback before promoting future serializer changes. Environment staging, publish, effective Wheel hash/binding, and Spark/Delta business acceptance remain separate controlled release gates; preserve HALT until each is independently authorized and verified.
