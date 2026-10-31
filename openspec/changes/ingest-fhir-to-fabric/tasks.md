# Tasks

> **2026-10-31 用户授权 P0–P2 离线源码开发；真实云端发布与写入仍未授权。** 详细权威设计：[ADR](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)。完成文档不等于运行时验收。

## 1. Architecture decisions

- [x] 1.1 2026-10-27 已核查 Local NEW_ONLY 真实 DAG、Canonical/OMOP Contract、Publisher v1 Manifest 和 Fabric 旧 POC 状态（静态）。
- [x] 1.2 2026-10-27 曾建立独立 Draft PR #533、两份历史初稿；最终架构已于 2026-10-31 合并 main，草稿后续按 Task 1.13 从当前树退休。
- [x] 1.3 2026-10-30 讨论确认 Bronze raw / Silver Canonical Delta / Gold OMOP 业务分层。
- [x] 1.4 确定 Source + Entity Adapter 插件化；Silver 后共用 OMOP Mapper、DQ、Identity、Reconciliation；Local 引擎逐步抽到 shared-data-engine，现有运行代码不动。
- [x] 1.5 明确 PySpark 优先、dbt MVP 暂缓；Gold Warehouse T-SQL 事务首选 POC、全 Delta visibility 备选，均非既有已验收成果。
- [x] 1.6 同步权威 ADR、原两份初稿的历史声明和 OpenSpec proposal/design/tasks。
- [x] 1.9 2026-10-30 用户确认采用独立 `shared-data-engine` Python Package 的目录规则、唯一源码归属、依赖方向和渐进 Local 迁移策略；建立仓库根/Scoped AGENTS 规则、组件 README/CODE 与专门开发规范；同步更新旧“禁止重复 src”对独立 Wheel 的例外。**此项仅代表规范落地，不代表已创建业务包或 CI 自动拦截。**
- [x] 1.11 从 Main 真实源码核对 Local Mapper 与 JDBC 耦合、Terraform Existing Workspace/OneLake、Trial Git Native Items/硬编码 Publisher；制定 Shared/Fabric 两只 Wheel（2026-10-31 已废止，最终只有一只 Shared Wheel） 的精确源码文件名、OneLake schema/table/approval 目录、Environment Publish/Readback、P0–P5 交付顺序与禁止迁移清单（**仅文档提案，所有业务实现与运行仍未开始**）。
- [x] 1.12 2026-10-31 用户确认最终开发架构：Notebook/Pipeline 必选、Git Native Workspace Item 映射、Environment Publish 唯一 Shared Wheel、原生 Fabric I/O、不预建额外 ingestion/runtime/io Wheel；新增权威 ADR 并更新 Agents/OpenSpec。**只代表设计定版，无源码/云端运行。**
- [x] 1.13 2026-10-31 设计文档去重：从 main 退休 2026-10-27 Fabric FHIR 初稿与 Local→Fabric Draft（保留固定 Git Commit 历史），修复 ADR/OpenSpec/目录索引引用，加入历史稿去重治理规则；不动 Local 运行代码、Terraform/云资源。
- [x] 1.10 [P0 merged as #559; main 5ca37a395dc9ef648b0e064a788bfb1e26674a6a] 首个真实 Python Source PR 前扩展 CODE-map 静态所有权及 shared→platform 禁止 import 检查、配套正负向单元测试；验证冻结 Local Contract 单一权威和跨版本 package pin 后再允许业务代码提交。
- [ ] 1.7 通过实机/成本验证后，最终敲定 Shortcut/Copy、Warehouse/Delta Writer、ID namespace、Canonical v2 和 Update 政策，完善正式 delta spec/测试及 CODE 导航。
- [x] 1.8 用户于 2026-10-31 确认正式入库为开发依据；实际 Git 合并仍须 CI/分支保护通过，未来实施另行授权。

## 2. Offline implementation authorized; cloud execution remains HOLD

- [x] 2.2 P2 仅离线 Notebook 业务源码与 Native Export prepublish 静态 Gate：Manifest/source SHA/Retention、Bronze receipt、Shared Engine、Quarantine、受控 Delta、两表独立 readback/approved、幂等/unknown ACK，Fabric Native Item 文件未实际导出时 BLOCKED。完成真实 CI 后才能勾选源码部分，Native Item/E2E 不可打勾。

- [x] 2.1 P1 实现唯一 Shared Engine Wheel v0.1.0、FHIR R4 Patient/Encounter、合成数据、Local v1 Contract、正负/重放/跨源测试、Spark Schema，实际 CI 构建/安装后才能打勾。业务运行、Fabric Publish 尚未授权。

- [ ] G0：只读校验 Manifest 原始字节/对象 SHA/ETag、真实 FHIR Profile、Blob Shortcut RBAC/保留策略。
- [x] G1：[P1 offline tests/wheel verified; Fabric runtime remains HOLD] 冻结 synthetic FHIR fixtures；离线 Bundle/ref/Patient/Encounter、Contract/Quarantine/缺失/重复/冲突负向测试。
- [ ] G2：独立解决三次 Trial Notebook Create/GetDefinition LRO/exitValue HOLD；得到新授权后才进行免费受控的真实结果 SHA Smoke。
- [ ] G3：5–10 新 synthetic Patient → Intake + Bronze raw/ref + receipt，按 Source Batch/Processing Version 验证 replay SKIP 和漂移 HOLD。
- [ ] G4：100 新 synthetic Patient/Encounter → managed Silver canonical_patient/encounter Delta；PK/FK/DQ/来源/hash/readback、quarantine、approved 证据。
- [ ] G5：Shared Silver→OMOP Person/Visit Candidate + Concept/Identity/row reconcile，证明相同输入/版本结果稳定。
- [ ] G6：Warehouse staging + Person/Visit/IdentityMap/Ledger T-SQL 单事务（首选）故障、回滚、并发、未知 ACK、NOT ENFORCED 约束/读回；不能用时重新评审 Delta visibility。
- [ ] G7：正式受控 Pipeline E2E、实际 Lineage、Compute/Cost/CI-CD/Runtime 兼容及清理证据。
- [ ] G8：HL7/CSV Fabric Adapter、PG OMOP Snapshot、dbt、Canonical v2 等未来各自单独 Change。

## 3. Explicit non-goals / safety

本轮只提交 Git 设计文档；允许在 PR 检查通过后将文档合并 main。**不触发 Fabric/Azure/Blob/K8s/PostgreSQL 写入；不变更 Warehouse/Notebook/Pipeline/Connection/Terraform/paid capacity；不改 Local 或发布器生产实现。** Warehouse 跨表事务能力不代表跨系统事务；未通过实机 Gate 不得标记 Gold COMMITTED。

### 2026-10-31 P0 execution evidence

- 本 PR 新增 `check_shared_fabric_boundaries.py` / 正负向 `test_shared_fabric_boundaries.py` 并接入现有 Component Code Naming CI；冻结 Local Canonical v1 原字节 SHA256。
- Task 1.10 GitHub Actions P0 CODE-map/Shared boundary **PASS** 于 [Component Code Naming Run #41230354918](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41230354918)，151/151 单测（含 11 个新的 Shared 负向/正向单测）PASS、SHARED_FABRIC_BOUNDARY_PASS；PR 合并前仍非 Main 已交付。本 PR 的 P0 工具自身不等于 Shared Wheel/Fabric 运行验证。
- 后续离线实施：G1 为独立 P1 Shared Engine PR；P2 为 Native Item 发布准备 PR。G2–G7 仍需明确云端授权。

### 2026-10-31 P1 scope and dependency boundary

- Owner: `shared-data-engine/src/healthcare_data_engine/`,唯一 Wheel；输入为 caller 提供的精确源字节、独立 receipt、显式 BatchContext 与 Local v1 Contract 原字节；输出为 TransformResult + 可选 caller Spark DataFrame，禁止 Azure/Local/Fabric writer。
- Contract: Patient v1 SHA256 `e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab`、Encounter v1 SHA256 `473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837`；Local 源码原位不动；v2 未获批需 Quarantine。
- Test/rollback: synthetic fixture/negative/ref/duplicate/cross-hospital/Spark Schema/replay; PR 未部署，回滚仅撤销分支或后续发布版本。CI Wheel hash/readback 提供本轮证据。

### P1 verified offline evidence 2026-10-31

- [GitHub Actions Run #41230857875](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41230857875), exact source HEAD `87a8693590ffa81bbb5afdfbed3952088e37150c`: 15/15 synthetic Python/PySpark tests PASS; pinned Python 3.11, Java 17, PySpark 3.5.7, setuptools 75.8.2, wheel 0.45.1; wheel built/installed offline and independently imported outside checkout.
- Single wheel `healthcare_data_engine-0.1.0-py3-none-any.whl` SHA256: `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7` (final reproducible build); CI Artifact contains Wheel and SHA256SUMS. This is the PR source HEAD's build, not a Fabric published library.
- CI HEAD `87a8693590ffa81bbb5afdfbed3952088e37150c`: CODE-map/Shared boundary, Trusted OpenSpec, OpenSpec validation and documentation links PASS. Cloudflare Workers Builds for unrelated Portal reported failure; not a required Main ruleset context and unchanged by Shared code.
- No Fabric/Blob/OneLake/Local/PG/Kubernetes/TF writes; Fabric Native Item definition, environment Publish and real Spark Runtime compatibility remain BLOCKED pending new authorization/read-only preflight.

- Wheel reproducibility regression: initial P1 rerun rebuilt unchanged source but generated a different hash (`fd301439...` vs `ab50e5bf...`), owing to ZIP build timestamp instability. Updated CI sets `SOURCE_DATE_EPOCH=1704067200` and builds twice with byte comparison; prior hashes are historical CI evidence, **not canonical release pin**. Replace final SHA only after new reproducibility verification succeeds.

- Final **reproducible** Wheel CI: [Run #41231145393](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41231145393) at `1b45d5ac671076bb86a6102eb29b99f2d2c2d5c3`, 15/15 tests PASS, two consecutive source builds byte-identical via `cmp`, Wheel SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7`, independent offline Wheel import PASS. Fixed `SOURCE_DATE_EPOCH=1704067200`. Any new source version requires its own new hash/evidence, not reuse this pin.

### 2026-10-31 P2 offline development scope

- Owner: `azure-fabric/notebook-development/fhir_ingest_notebook.py` 是预发布的单一 Notebook 源码，不属于 `workspaces/healthcare-omop` Fabric Git 选定目录，**不能冒充** `.Notebook` Item。真实 Native Notebook/Pipeline/Environment Item 必须从该 Workspace 导出，有效 ID/文件内容验证后另审。唯一共享 Wheel SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7`。
- No second framework or package: native `spark.read.format('binaryFile')` and `DataFrame.write/read.format('delta')` only within the future Notebook. Pipeline runtime retry/monitor/status/failure branch still BLOCKED until real Native Pipeline definition; Environment Publish/version readback still BLOCKED.
- Replay: separate source batch / processing version / publication hash; unknown ACK or partial Delta staging is `VERIFY_READONLY`, no blind writes. `SILVER_APPROVED` only after independent Spark/Delta two-table PK/FK/count/version readback and approval evidence. Never Gold COMMITTED.
- Offline-only tests and CI cannot establish live Workspace/Git connection/Lakehouse/Capacity/permissions/schema/cost/retention; no cloud mutation authorized.

### P2 offline verified CI evidence (not a Fabric deployment)

- GitHub Actions [Run #41231571043](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41231571043) at source commit `b4186e9d1f968b7873c4ec679a4f35a64c05b8ef`: 14/14 synthetic Manifest/PySpark/canonical/Patient-Encounter PK-FK/replay-stability/authorization-negative tests **PASS**; only Shared Wheel 0.1.0 installed with SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7` verified by `sha256sum --check`.
- Native Notebook/Pipeline/Environment exporter check: `BLOCKED_NATIVE_EXPORT` exit code 2, CI confirms `NATIVE_ITEM_PUBLICATION_BLOCKED_AS_DESIGNED`; no `.platform`, logicalId, pipeline content, Environment format or published runtime invented.
- Notebook is **unpublished offline working source**; literal Spark native I/O/Delta/write/readback steps are coded but **not executed against Delta or Fabric**. Actual Silver APPROVED/readback, Pipeline E2E, live Git binding, identity/schema/permissions/cost, Environment Publish remain HOLD. P2 offline tests are not Fabric runtime proof.


## 4. Authorized Fabric Native Item bootstrap (2026-10-31)

> 用户 2026-10-31 明确授权创建需要的 Fabric 资源，限制在 healthcare-omop Notebook、DataPipeline 和 Environment；不授权 Capacity 收费资源、业务数据覆盖或历史资源销毁。

- [x] 4.1 核对最新 Self-Runner GET Run 41241521584：Lakehouse=1、SQLEndpoint=1；Notebook/Pipeline/Environment=0；核实 Microsoft 官方 Create/GetDefinition API 和 LRO。
- [x] 4.2 设计固定目标名的 CREATE-IF-ABSENT、真实 Item ID 读回与 getDefinition 导出；先确认证据再保存 .platform；未知 ACK/HOLD，严禁并行 Terraform 所有权。
- [x] 4.3 [Self-Runner PR #353, Main 5607678ba81c0ff405b741215e69dfaad3191224; PR #354 fixed LRO] 在 Self-Runner 开发正式受控 bootstrap Workflow、Python REST 客户端和无凭据正反单测。经 PR CI 后在 Main 一次性运行实际创建。
- [x] 4.4 [Run 41242815706 created all three; Run 41243074326 all definitions exported; Run 41243367360 Git=NotConnected] 记录真实创建/读取 HTTP、GUID、Run/Artifact 与 Capacity/权限错误；绝不把空 Item 视为业务 E2E。
- [ ] 4.5 从真实 Fabric getDefinition 导出 .platform/Item 内容到 Healthcare Git 目录；同步 Notebook/Pipeline/Environment CODE.md，验收 Git Sync/实际 UI 文件夹映射。
- [ ] 4.6 将唯一固定 SHA Shared Wheel 加入 Environment 并 Publish，接入 P2 Notebook 源码与安全 Pipeline，独立验证版本/引用；不自动运行数据作业。
- [ ] 4.7 小规模 Synthetic FHIR→Bronze→Silver 实机试运行，独立核验 Delta/权限/费用，仍不得修改历史业务数据或把 Mock 当实机结果。

### Permission & rollback

- 允许仅创建 nb_fhir_ingest (Notebook)、pl_fhir_ingest (DataPipeline)、env_healthcare (Environment)，读取真实定义并记录原始 ID。
- 不 Resume/创建付费 Capacity，不删除已有资源，不覆盖已有 Item，不执行 Notebook/Pipeline，不修改 Terraform State。首次不明结果先读回，禁止盲目重发 POST。
- 新资源部分创建也不得自动删除；保留准确 ID 供审核。真实运行与发布属于后续 Tasks，不因创建成功而提前认定 P2 E2E。

### Native live verification — 2026-10-31

- Source: trusted Self-Runner/main `fabric-native-items-bootstrap.yml`; [PR #353](https://github.com/JohnZhang-DataForge/Self-Runner/pull/353) initial implementation; [PR #354](https://github.com/JohnZhang-DataForge/Self-Runner/pull/354) async 202 JSON null correction and hidden .platform artifact; [PR #355](https://github.com/JohnZhang-DataForge/Self-Runner/pull/355) GET Git connection.
- [Run 41242815706](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41242815706) **native creation**: actual HTTP CREATE with independent GET readback confirms Notebook `8311ab6b-3484-4e96-8370-badeeb751633`, DataPipeline `fc67962e-28dd-47eb-8c6e-3104068241c6`, Environment `d85a4218-8da0-46ed-8517-b5eced219dd5` in Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`. First Run ended HOLD_NATIVE_DEFINITION_EXPORT (202 null response handling), not fully green; preserved Artifact 13057803632.
- [Run 41243074326](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41243074326) **export PASS**: all three exact IDs EXISTING, readback PASS, all native GetDefinition PASS, Artifact `fabric-native-bootstrap-41243074326` ID `13057339472`, includes actual Notebook `.platform`/`notebook-content.py`, Pipeline `.platform`/`pipeline-content.json`, Environment `.platform`/`Setting/Sparkcompute.yml`. No new create, no Spark jobs, no Environment publish or data writes.
- [Run 41243367360](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41243367360) **Git readback PASS**: `gitConnectionState=NotConnected`, provider empty; all 3 Items EXISTING and definition exports PASS (Artifact `fabric-native-bootstrap-41243367360` ID `13058450410`). REST-exported `.platform` config.logicalId was `00000000-0000-0000-0000-000000000000` for every item. These real REST responses cannot prove Git Integration / valid nonzero Git logical IDs. DO NOT mark Task 4.5 or Native Git Publish PASS.
- Next blocker: verify a Fabric GitHub configured cloud connection accessible to Service Principal (Git integration Connect API requires `ConfiguredConnection` and Workspace Admin); connect exact GitHub repo/main/folder only after preflight, then initialize/read back without overwriting existing Workspace or Git history. Do not synthesize logicalId.

### GitHub credential preflight — 2026-10-31

- [Self-Runner PR #356](https://github.com/JohnZhang-DataForge/Self-Runner/pull/356) implemented a bounded `GET /v1/connections` credential inventory via existing OIDC principal; mock negative/positive tests PASS.
- [Real Run #41243652551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41243652551) all jobs PASS; Artifact `fabric-native-bootstrap-41243652551`, ID `13057924712`: `gitConnectionState=NotConnected`, `credentials_probe=PASS`, `available_connection_types={AzureBlobs:1}`, `github_candidates=[]`. Exact same 3 Items remain EXISTING and exported; zero duplicate creates, no paid Capacity/Spark/Environment/data write.
- **Task 4.5 remains HOLD_GITHUB_CONFIGURED_CONNECTION_MISSING**. Microsoft Fabric Git Connect from SP requires Workspace Admin and an existing `ConfiguredConnection` accessible to SP, cannot use Automatic GitHub credentials. This API prerequisite is not a GitHub Actions workflow token or normal GitHub Connector permission. Do not invent a Connection ID or use storage/GitHub traffic token.
- Required external setup: through Fabric Manage Connections/Git integration create or select an authorized GitHub Cloud Connection targeting owner JohnZhang-DataForge / healthcare-data-platform, grant access to existing Fabric Service Principal, then rerun read-only /connections and exact Workspace ID GET. Only after visible correct connection may the controlled /git/connect + initialize flow be reviewed; never blind sync/overwrite main.

### Decision — Fabric Git Integration is portal-managed, NOT Terraform (2026-10-31)

- [x] 用户决定 GitHub 与 `healthcare-omop` Workspace 的 Git Integration **手工通过 Fabric Workspace settings → Git integration → GitHub 配置**，不使用 Terraform，不创建 `fabric_workspace_git` 或 GitHub `fabric_connection` TF resource，也不要求 Terraform Import。既有 Terraform Workspace/Lakehouse/Connection 基础设施保持不变。
- [ ] 4.8 Workspace Admin 使用仅限 `JohnZhang-DataForge/healthcare-data-platform` 的 Fine-grained GitHub PAT（Contents Read and write），在 Fabric Git integration → Add account 授权；拟连接路径 `/azure-fabric/workspaces/healthcare-omop`，首次使用受审查的初始化分支，不直接向 main 覆盖写入。
- [ ] 4.9 人工检查 Connect and sync 的方向，**保留 Fabric 已存在的 Notebook `nb_fhir_ingest`、Pipeline `pl_fhir_ingest`、Environment `env_healthcare` 及 Lakehouse**。先将 Workspace 项目提交到隔离分支，审查生成的真实 `.platform`（非全零 logicalId）和 folder mapping，再 PR 合并 main；禁止先 Update from Git 覆盖已有资源。
- [ ] 4.10 Git 集成后用正式 Self-Runner 的 GET `/git/connection`、GET Items 和 GitHub PR/Commit 验证连接状态、路径、版本、Item GUID；Provider credentials 与 PAT 不写入 repo、workflow 日志或聊天。
- [ ] 4.11 若日后要让 Service Principal 调 Fabric Git REST 同步，需另将 Fabric 中已配置的 GitHub Cloud Connection 共享给现有 SP，并按实际可见的 Connection ID 设置 `ConfiguredConnection`/myGitCredentials；这**不是手工 Git Workspace 连接的前置要求**，也不代表此次应改用 Terraform。

### Fabric Portal first-sync evidence (2026-10-31)

- [x] 4.12 人工从 Fabric Workspace `healthcare-omop` 执行 **Workspace → Git** 首次同步：GitHub 仓库 `JohnZhang-DataForge/healthcare-data-platform`，隔离分支 `fabric/native-bootstrap-20261031`，目录 `azure-fabric/workspaces/healthcare-omop/`。真实 Git Commit [`a6c3d0d6226e0b4084c681104ef9aec6dd3f33c6`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/commit/a6c3d0d6226e0b4084c681104ef9aec6dd3f33c6) 基于当时 main `116d27d74a20860c681e4ac67bfa3681a0739536`，只新增 4 个 Item 的 10 个原生文件，零删除，未修改 `main`。四个 `.platform` logicalId 均非零；Notebook 为 `# No content`、Pipeline 活动为空、Environment 未发布 Wheel。Fabric UI 显示 Source control `0`、Changes 空、Items 为 Synced。
- [x] 4.13 [PR #570 merged, main bce1f79e348897c0f2fdd48a6b1dc2bf5f785c1a] 经 PR/CI 审查并合并原生定义和同步更新的 Notebook/Pipeline/Environment CODE 源码地图到 `main`；当前 Workspace 仍连接初始化分支，**不自动切换，也不从 Git 更新 Workspace**。



### P2 Git-first authored implementation after verified bootstrap (2026-10-31)

- [x] 4.14 [Healthcare PR #571; offline CI Run 41252153769 PASS; 18 tests; Native Gate HOLD] Replace the stale nested Native paths with the verified flat `*.Notebook`, `*.DataPipeline`, and `*.Environment` directories; check real .platform nonzero logicalIds, item type/name, and native file names. A native definition being present can only advance the preflight to HOLD_PENDING_PUBLICATION, not assert Fabric/Spark business deployment.
- [x] 4.15 [Healthcare PR #571; offline CI Run 41252153769 PASS; 18 tests; Native Gate HOLD] Prepare real FabricGitSource Notebook source from the P2 candidate, preserving Shared Wheel as sole mapper, exact Manifest and SHA/Delta guards. Avoid a second independent business implementation; leave startup fail-closed until explicit runtime and retained-source verification. Validate Python syntax and local PySpark tests without cloud writes.
- [x] 4.16 [Healthcare PR #571; offline CI Run 41252153769 PASS; 18 tests; Native Gate HOLD] Add a `TridentNotebook` Pipeline activity that references the live Notebook/Workspace IDs, has no automatic retry, safe parameters, no schedule, and no implicit data-write grant. Validate JSON IDs and notebook parameter contract offline.
- [ ] 4.17 Prepare fixed-SHA Wheel build and Environment CustomLibraries packaging under separate CI/build provenance, publish only after artifact integrity and effective runtime availability checks. Never invent .platform/library metadata or use a PyPI fake wheel.
- [ ] 4.18 PR/CI merge in GitHub `main` first. Only then request the user manually switch Fabric Git-connected branch to `main` and review Update-from-Git preview; the Agent MUST NOT initiate Git Sync, Environment Publish, Pipeline/Notebook execution, Terraform or data writes in this Git authoring task.

### Git-first authored P2 branch pre-merge verification — 2026-10-31

- [PR #571](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/571) adds the native FabricGitSource Notebook, the single-source compatibility import for offline tests, a guarded Pipeline Activity referencing the existing Notebook/Workspace IDs, and nonzero logicalId native-source preflight. This is **Git authoring only**; it changes neither the Fabric-connected bootstrap branch nor the live Workspace.
- [Offline Run #41252153769](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41252153769) succeeded: 18/18 PySpark and static Native contract tests; Shared Wheel deterministic SHA256 check PASS and archived in GitHub Artifact `fabric-p2-shared-wheel-a567538717c30c3730836c36dfcd47036724366e` ID `13061572778`; Native source probe `HOLD_NATIVE_RUNTIME_DEPLOYMENT` (intentional, not runtime release).
- Still pending: copy verified Wheel into exact Environment CustomLibraries, publish and verify effective version, attach Notebook Environment and validate Fabric API/Job id, manually switch Workspace connected Git branch `fabric/native-bootstrap-20261031` → `main` with a guarded no-delete/no-recreate review; live Bronze/Silver Delta E2E NOT_RUN.
