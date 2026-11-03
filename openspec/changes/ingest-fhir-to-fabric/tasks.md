# Tasks

> **2026-10-31 用户授权 P0–P2 离线源码开发；真实云端发布与写入仍未授权。** 详细权威设计：[ADR](../../../documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md)。完成文档不等于运行时验收。

> **2026-11-02 Current live supersession:** G2 正式 `nb_fhir_ingest` Spark 4.1 / `healthcare_data_engine` Wheel 0.1.1 Runtime 已真实 PASS；Task 2.4 的 G0 只读 FHIR Spark Intake **5 人 + 100 人均 PASS**（见下方 2026-11-02 真实报告）。先前历史段落中对 Runtime 的 “HOLD / NOT_RUN” 只描述当时状态，已被后续实机证据取代。**G0 Azure 保留策略与 G3/G4 Bronze/Silver Delta 物理写入仍 OPEN / NOT_RUN；勿把读取验证等同 Delta E2E。**

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

- [x] 2.3 G0 子任务：与真实 Azure Publisher landing-manifest-v1 对齐的 **离线 FHIR Manifest 解析及负向合同**；Notebook Offline Contract CI [#41494321679](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41494321679) SUCCESS。此项仅证明离线正负向测试通过；G0 Blob 实机读回、保留策略、权限和 G3/G4 仍 OPEN。
- [x] 2.4 G0 Fabric Spark 真实 Intake 只读验收：`nb_fhir_ingest` 的 `INTAKE_READONLY` 模式从已验证的 OneLake `Files/fhir_landing` Shortcut 读取旧 5/100 合成 FHIR Manifest 和逐对象字节，严格校验各自固定 Manifest SHA、对象 SHA、FHIR Patient/Encounter 解析和运行退出标记；无 Silver/Delta 写入。只在实际 Spark Jobs Completed 和准确 exitValue 证据后勾选。
- [ ] G0：只读校验 Manifest 原始字节/对象 SHA/ETag、真实 FHIR Profile、Blob Shortcut RBAC/保留策略。
- [x] G1：[P1 offline tests/wheel verified; Fabric runtime remains HOLD] 冻结 synthetic FHIR fixtures；离线 Bundle/ref/Patient/Encounter、Contract/Quarantine/缺失/重复/冲突负向测试。
- [x] G2：独立解决三次 Trial Notebook Create/GetDefinition LRO/exitValue HOLD；得到新授权后才进行免费受控的真实结果 SHA Smoke。
- [x] 2.5 G3 前置只读 Canonical Spark 探针：复用同一冻结 5/100 FHIR Manifest/Shortcut、真实 v1 Patient/Encounter Contract **原字节 SHA**，调用唯一 Shared Wheel 0.1.1 完成 Canonical Transform、PK/FK、DQ 分组汇总；不触发 Delta/Approval/正式 Pipeline，实际 Fabric Job Completed + 精确 exitValue 和 read-only 证据后才能勾选。此项不替代 G3 新合成批次及物理 Bronze 写入。
- [ ] 2.10 G4 guarded Silver first implementation + offline CI (NOT real cloud acceptance).
- [x] 2.8 G3 real persisted positive acceptance: 5 FHIR source objects written as raw byte Delta snapshot; independent Spark readback and same-request replay SKIP PASS in three real Fabric Notebook Jobs. Live drift-HOLD/unknown-ACK negative tests, G0 Azure WORM, and G4 Silver remain open.
- [x] 2.7 G3 raw source snapshot retention alternative after real G0 strict WORM HOLD; independently verify original bytes, Delta readback and replay. Does NOT assert Azure WORM or physical Delta PASS.
- [x] 2.6 G3 first implementation slice: reviewed Git-native Notebook Bronze request-scoped Delta receipt/independent readback/replay/drift/unknown ACK and offline negative/positive CI; **does not count as G3 real Delta PASS**.
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
- [ ] 4.17 [PR #572 merged; Run #41252713432 build SHA256 PASS and staged one native Wheel in feature/fabric-p2-wheel-41252713432, Main PR review pending, Fabric Publish NOT_RUN] Prepare fixed-SHA Wheel build and Environment CustomLibraries packaging under separate CI/build provenance, publish only after artifact integrity and effective runtime availability checks. Never invent .platform/library metadata or use a PyPI fake wheel.
- [x] 4.18 [2026-11-01 verified Git first and manual Fabric branch switch / incoming updates; no Spark] PR/CI merge in GitHub `main` first. Only then request the user manually switch Fabric Git-connected branch to `main` and review Update-from-Git preview; the Agent MUST NOT initiate Git Sync, Environment Publish, Pipeline/Notebook execution, Terraform or data writes in this Git authoring task.

### Git-first authored P2 branch pre-merge verification — 2026-10-31

- [PR #571](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/571) adds the native FabricGitSource Notebook, the single-source compatibility import for offline tests, a guarded Pipeline Activity referencing the existing Notebook/Workspace IDs, and nonzero logicalId native-source preflight. This is **Git authoring only**; it changes neither the Fabric-connected bootstrap branch nor the live Workspace.
- [Offline Run #41252153769](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41252153769) succeeded: 18/18 PySpark and static Native contract tests; Shared Wheel deterministic SHA256 check PASS and archived in GitHub Artifact `fabric-p2-shared-wheel-a567538717c30c3730836c36dfcd47036724366e` ID `13061572778`; Native source probe `HOLD_NATIVE_RUNTIME_DEPLOYMENT` (intentional, not runtime release).
- Still pending: copy verified Wheel into exact Environment CustomLibraries, publish and verify effective version, attach Notebook Environment and validate Fabric API/Job id, manually switch Workspace connected Git branch `fabric/native-bootstrap-20261031` → `main` with a guarded no-delete/no-recreate review; live Bronze/Silver Delta E2E NOT_RUN.

### Native Shared Wheel immutable Git review — 2026-10-31

- [Run #41252713432](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41252713432) succeeded on trusted healthcare Main (SHA c8f863d831b034e54c146965e89d7111a4f8ca44): Python 3.11, frozen tooling, deterministic Wheel SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7` PASS **before** any Git write. Created exactly one new Git review branch `feature/fabric-p2-wheel-41252713432` at `e6da53704b6ea269ee6eb6a7081ac382612892f1` with real Environment CustomLibraries Wheel and CODE source map. No Workspace Git branch switch, no Fabric API call, no Environment Publish, no Notebook/Pipeline execution, no Bronze/Silver data write.
- The review branch must run Native contract SHA/Wheel integrity and owner-map CI, merge by PR to Main, then remain **HOLD_ENVIRONMENT_PUBLISH_AND_EFFECTIVE_LIBRARY_READBACK** until Fabric manual switch/publish and independent API proof.

- [x] 4.19 [2026-11-01 Git-first Pipeline correction deployed and actual safe params readback PASS] Normalize Native `pl_fhir_ingest.DataPipeline/pipeline-content.json` to Notebook `.platform.config.logicalId` + current-workspace zero GUID + documented `typeProperties.parameters`, add fail-closed unit contracts, review the separate Notebook change, and deploy through Git only after no-conflict verification; do not auto-Commit/Undo workspace changes or execute Spark.

- [x] 4.20 [2026-11-01 canonical parameter marker deployed; live Notebook definition has parameter marker and HALT] Fix confirmed noncanonical Notebook parameter-cell marker (# PARAMETERS CELL instead of generic # CELL) and offline contract. The live Notebook still exports mostly empty; do NOT interpret this static fix as proof of the missing business-code root cause, and do NOT deploy until read-only GetDefinition and a minimal valid Git-to-Fabric round-trip are verified. Protect Git main from Workspace Changes commits.


- [x] 4.21 [2026-11-01 isolated source parser reproduction plus successful manual Git import and dual-format live GetDefinition] Fabric read-only GetDefinition after accepted Git main f0603576 returned exactly 26 bytes (only the notebook source header), although the Git file contains 396 lines. Isolate source-format discrepancy: official Microsoft Fabric examples place blank separators after source header, before/after notebook METADATA blocks and code cell markers; original Git-authored Notebook lacked these. Stage canonical separator normalization and negative tests in a PR only; do not claim root cause or deploy until a minimal real Fabric round-trip proves body retention. Preserve .platform IDs, runtime HALT, Pipeline and Environment; no Spark or Delta writes.

### Native Notebook source restoration — independently verified (2026-11-01)

**G1 definition-import issue RESOLVED; G2–G4 runtime/data gates still HOLD.**

- Initial live readback after Git sync `f0603576732448507835d48922f1fb43a86ddd92`: `FabricGitSource=26 B`, `ipynb=145 B`, `ipynb code_cells=0`; full P2 code absent. `Pipeline safe_parameters=True` throughout.
- [Self-Runner PR #359](https://github.com/JohnZhang-DataForge/Self-Runner/pull/359) added GET-only dual-format definitions; [Run #41261523505](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41261523505) confirmed both formats truncated while Git Workspace head was `f0603576`. A successful sync SHA alone did not imply deployed code.
- [Self-Runner PR #360](https://github.com/JohnZhang-DataForge/Self-Runner/pull/360) isolated 3 temporary Notebook API Create/GetDefinition tests. [Run #41261920081](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41261920081) confirmed `official_spacing=True`, `compact_spacing=False`, `ipynb_control=True` for retained marker; `cleanup=True` (all temporary items removed). This reproduced the parser sensitivity to section separator spacing with no production edits, Spark, or Delta writes. The isolated native API path by itself was not proof of Git import.
- [Healthcare PR #576](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/576) merged as `9e667468e278f68c3b26f7eb46b81e58b87bf119`: 13 blank-line separators added to the real `nb_fhir_ingest.Notebook/notebook-content.py` without changing business code, HALT guard, parameters, logical IDs, Pipeline, Environment, or Lakehouse. Git source now has 409 lines and 2 normal code markers plus 1 parameter marker.
- User manually completed Fabric portal Git incoming Update after reviewing **only `nb_fhir_ingest`**. Trusted Self-Runner job **re-run** of [Run #41262254996](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41262254996), live job `124718913119`, independently read back: `git_sync.workspace_head=9e667468e278f68c3b26f7eb46b81e58b87bf119`; `FabricGitSource=20053 B`, `ipynb=21689 B`, `ipynb code_cells=3`; `format_comparison=BOTH_FULL`; core `execute_native_notebook`, parameter cell and HALT present; `Pipeline safe_parameters=True`; **`FABRIC_P2_READBACK_OUTCOME=PASS`**. Fabric-exported representation need not be byte-identical to the checked-in text; independently tested required code and guards were retained.
- `GET /git/status` under Self-Runner Service Principal still returned `FABRIC_HTTP_400` (no remote-change inventory); this is a separate SP Git API diagnostic, **not** a definition-import failure, and does not override the successfully read Workspace Git sync head. No automated Git update was used.
- **Release boundary remains:** no Environment Publish/effective Wheel binding proof, no Notebook/Pipeline execution, no Spark/Delta E2E, and no Bronze/Silver data writes. Do not remove `run_mode=HALT`, `write_authorized=False`, `retention_preflight_verified=False`, or the runtime HOLD exception merely because definition readback passed. Before any write release, verify Environment effective published custom Wheel SHA and Notebook environment attachment, then run an explicitly approved non-writing smoke, finally audited data E2E with containment/recovery gates.


### G2 effective Environment Wheel gate — read-only live findings (2026-11-01)

- [x] **Read-only staging vs published inspection completed** via [Self-Runner PR #362](https://github.com/JohnZhang-DataForge/Self-Runner/pull/362) / [Run #41263018957](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41263018957). Real Workspace `env_healthcare` staging libraries GET (release API, `beta=false`) found `healthcare_data_engine-0.1.0-py3-none-any.whl` by **filename**. The corresponding published library list GET returned **HTTP 404**. This does not prove there has never been a prior publish.
- [x] **Read-only publish-metadata inspection completed** via [Self-Runner PR #363](https://github.com/JohnZhang-DataForge/Self-Runner/pull/363) / [Run #41263182097](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41263182097). `GET Environment` returned `publishDetails.state=Success` and `componentPublishInfo.sparkLibraries.state=Success`, but the published libraries endpoint still returned HTTP 404 while the expected Wheel remained in staging. A prior successful publish is NOT evidence that the newly staged Wheel is effective.
- [ ] **Remaining Task 4.17 release work:** user/reviewer must verify Environment staged dependencies and whether a publish is appropriate; publish as a **separately approved action** (no automated Runner publish was performed), then independently GET published libraries to confirm Wheel filename. The listing API does not expose wheel content hash; verify exact effective package version/SHA and Notebook `env_healthcare` binding through an additional controlled runtime/environment inspection. G2 remains HOLD; G3 Notebook/Spark execution and G4 Bronze/Silver Delta E2E remain NOT_RUN.
- Notebook readback remains fully PASS with 20,053-byte `FabricGitSource`, 21,689-byte `ipynb`, three code cells, main Git sync `9e667468`, Pipeline safe parameters; the Environment gate is strictly separate.


### 4.22 Fabric Native Git authoring lessons and regression prevention — 2026-11-01

- [x] 4.22 Record the actual Fabric Notebook source-loss incident, isolated canonical/compact/ipynb reproduction, corrective PR #576, and live BOTH_FULL GetDefinition readback in [Fabric Native Git Authoring Runbook](../../../documents/systems/azure-fabric/notebooks/FABRIC-GIT-AUTHORING-RUNBOOK.md).
- [x] Link the runbook from Notebook/Environment CODE maps and replace the obsolete “business Notebook not developed / Wheel not in Git” documentation.
- [x] Preserve existing offline contract checks for canonical separators, PARAMETERS CELL / META JSON, sole business implementation, .platform logicalId and Pipeline HALT; cloud readback remains an independent gate.
- [ ] Environment latest custom Wheel effective Published listing/hash and Notebook attachment remain HOLD; Spark execution and Delta E2E remain NOT_RUN. Do not infer these from the user-visible Publish success alone.


### 4.23 Guarded Git-to-Fabric native Notebook transport smoke — 2026-11-01

- [x] 4.23 Introduce one inert Notebook code-cell comment as a Git Native source transport marker, without changing business logic, .platform identity, Parameters Cell metadata, Pipeline configuration, HALT gates, Environment or any data writes. Source-of-truth remains Healthcare GitHub main.
- [x] Trusted Self-Runner completed reviewed GitHub Notebook import with last-synced canonicalization checks, 3 full Notebook code cells, ipynb/FabricGitSource, safe Pipeline parameters and physical references; evidence Run #41304159509 and independent readback Run #41303691776.
- [x] Maintain release separation: Environment Wheel effective publication, Notebook execution and Spark/Delta E2E were NOT validated by this transport smoke.
- [x] Preserve Git logical Notebook ID / zero Workspace placeholder and keep physical IDs only in Fabric runtime, verified by cloud definition readback.

### 4.24 Git-to-Fabric push dispatch

- [x] 4.24 Trigger private Self-Runner on Healthcare main push, with CI and source SHA validation.
- [x] Configured dispatch secret accepted Healthcare push commit d4e7bd80 and started private Self-Runner Run #41311668606; original deployment was no-write for docs-only update.

### 4.25 Healthcare push-to-Fabric event-driven E2E smoke

- [x] 4.25 Add one inert comment to the existing Native Notebook in a review branch to exercise the Healthcare main-push dispatcher without changing runtime logic or HALT safety parameters.
- [x] Healthcare main commit 8188cddc auto-dispatched private Self-Runner Run #41311994774; UpdateFromGit and cloud Notebook/Pipeline readback PASS (3 cells, code match, safe parameters); immediate rerun was CANONICAL_SERIALIZATION_ONLY_NO_WRITE.
- [x] Keep Environment Publish, Spark execution and Delta write release gates separately HOLD; the event-driven transport test performed none of these operations.

### 4.26 Event-driven Git transport closeout — 2026-11-01

- [x] 4.26 Official chain: Healthcare `push main` → SHA-pinned GitHub Actions dispatch → private Self-Runner Fabric Git Auto Update → native definition readback; successful E2E Cloud run #41311994774.
- [x] Repeat private Runner run was no-write, proving Git-to-Fabric idempotency after deployment; Self-Runner workflow fallback polling reduced from twice hourly to daily in PR #381.
- [ ] Environment Wheel effective publish, Notebook Spark execution, Fabric capacity/runtime and Delta transformations must use independent approvals and acceptance tests; transport PASS never releases them.

### G0 offline Publisher-v1 Manifest compatibility — 2026-11-02

- Discovered by comparing real `local-data-platform/apps/clinical_producers/azure_blob_publisher.py` with P2 Fabric `_manifest_objects`: the delivered `healthcare-azure-blob-landing-manifest-v1` uses `objects[].blob_key` (full container-relative path) plus ETag/version, *not* the P2 isolated test fixture's `objects[].path` and `source_system`. Reusing only P2 fixtures would fail real Intake despite a green Spark import test.
- Implemented a strict **offline-only** adapter in the **single** Git-native business Notebook, preserving the legacy isolated synthetic test contract: validate publisher schema/version, hospital/feed/request, FHIR_R4, full `clinical/v1/<hospital>/<feed>/<request>/FHIR_R4/fhir/*.json` Blob path namespace, exact object keys, ETag/version shape, SHA256, size and duplicate JSON keys. `source_manifest_sha256` belongs to the upstream generator, not the delivered Manifest SHA captured by BatchContext.
- Negative offline tests protect cross-hospital, unsupported version/format, unexpected keys, malformed ETag and traversal. These are **not** evidence that Fabric has actual Blob access, retention policy or Shortcut/Copy readback.
- **G0 remains OPEN** until independent read-only Azure/Fabric permission, real Publisher Manifest SHA/object ETag/retention and exact source bytes are verified. **G3/G4 NOT_RUN**: no Bronze/Silver cloud data writes, 5–10 or 100 Patient job, replay or approval is claimed by this code change.

### 2026-11-02 G0 Task 2.4 real Fabric FHIR Intake acceptance

- 正式业务 Notebook `nb_fhir_ingest`，Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`，Notebook `8311ab6b-3484-4e96-8370-badeeb751633`；Shared Engine Wheel `0.1.1`，Default Lakehouse `lh_omop_analytics`。本验收没有使用临时或 Portal 手工替代 Notebook。
- **Git-first 真实同步与 Notebook 定义独立读回 PASS**：Runner [Run #41510571554](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41510571554) `FHIR_GIT_RECONCILED_READBACK_PASS`，`ERROR=NONE`，正式云端 .py/.ipynb 源码与当时 Healthcare main `da20a75235af546b98a48c264fda2bba09a5938f` 精确语义校验；Environment/已发布 Wheel 0.1.1、Pipeline HALT 和预存 OneLake Shortcut `fhir_landing` 独立 GET PASS。注意原本 Git Workspace 的三个 Item 本地变化及 Notebook Conflict 经过 last-synced baseline semantic audit 证实，未删除 Lakehouse/Shortcut。
- **源数据来源**：真实 Azure Publisher 既有不可变合成批次 `atlanta-fhir-gh-40238053772`（5 FHIR 对象）、`atlanta-fhir-gh-40245591533`（100 FHIR 对象）；Azure Blob/Manifest 历史独立 GET/HEAD/SHA/ETag 证据 [Run #41495354432](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41495354432)，Shortcut 读回 [Run #41497778418](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41497778418)。**这些不自动证明 Azure Blob 保留策略。**
- **5 人真实 Spark PASS**：[Runner Run #41511268873](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41511268873)，Fabric Job `713b934c-1d11-4306-a95d-a2c95d956476`，状态 `Completed`，已通过 Core/Beta 独立读回的准确 `exitValue=FHIR_INTAKE_READONLY_5_SPARK_SOURCE_SHA_PASS_20261102`。Notebook 在返回标记前对 5 个源对象、Manifest/对象 SHA 及 Patient=5、Encounter 至少 5 条的约束进行真实 Spark 校验；这不是精确 Encounter 条数报告。
- **首次 100 人失败被独立分类，未盲目重试**：同一 Runner Run #41511268873 的 Job `7e39d28f-3258-42ca-aeff-16c9a874ca20` 约 1.2 秒后 Failed，原因 `CAPACITY` / `SPARK_SESSION`，`spark_session_entry=NOT_ESTABLISHED`，未开始 FHIR 业务读取。使用 GET-only [Run #41512895190](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41512895190) 找回确切 Job ID 和 Core/Beta 终态；没有将 GitHub Job 或 POST 成功误认作 Spark 数据 PASS。
- **100 人真实 Spark PASS**：在重新验证已完成 5 人 Job、先前 100 人失败及无活跃 Notebook Job 后，独立 main-only 一次性 [Runner Run #41513568875](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41513568875) 只提交固定 100 人 request；Fabric Job `36cc44e5-787c-4814-b570-76975bd1815d`，`Completed`，`exitValue=FHIR_INTAKE_READONLY_100_SPARK_SOURCE_SHA_PASS_20261102`。Notebook 精确验证 Manifest SHA、100 对象 SHA、Patient=100、Encounter 至少 100 条；报告 `FHIR_INTAKE_READONLY_5_PREVIOUS_100_NEW_FABRIC_SPARK_PASS`。
- 当前明确的验收层级：**offline contract PASS**、**Azure Blob GET/HEAD PASS**、**Fabric Git native definition PASS**、**Fabric Spark Intake read-only 5 + 100 PASS**；**Azure 保留策略 G0 余项 OPEN**；**Bronze raw/ref、Silver canonical Delta 物理独立读回/审批、幂等 replay、Quarantine、正式 Pipeline E2E 均 NOT_RUN**。两个受控测试没有修改业务 Delta，也没有执行正式 Pipeline。只有完成 G3/G4 实机写入后才能声称 Delta E2E PASS。

- **Operational regression guard:** capacity/session establishment failures before Spark execution must be investigated with independent Job GET and retried only after verifying the preceding Job terminal state, absence of competing active Notebook jobs, source pin, and idempotency scope. No 5/100 Spark Intake proof releases the separate Bronze/Silver write flags.

### 2026-11-02 G3 prerequisite: Canonical read-only Spark source change

- Native Notebook 新增单独 `CANONICAL_READONLY` 受限模式；仅接受既有固定 5/100 FHIR Request，不允许任意 URI/Manifest/root、禁止开启 `write_authorized` 或 `retention_preflight_verified`；Notebook 参数里的两个 Canonical Contract 必须分别匹配 **Local 原始 JSON 文件 SHA256**（Shared Wheel `load_pinned_contract`）后才读取云端源数据。
- 仅执行真实 Spark Source GET、Shared Engine Canonical Patient/Encounter 转换与内存 DataFrame 的 PK/FK/DQ 检查；`FHIR_CANONICAL_READONLY_*_SPARK_PK_FK_PASS_20261102` 才代表转换合格；`FHIR_CANONICAL_READONLY_*_DQ_HOLD_*` 是未获准写 Silver 的诊断结果。源解析及 Manifest SHA 仍然使用 Task 2.4 固定历史证据。
- 此处代码/Offline CI 提交不等于实机通过；需要单独 Runner 主分支授权执行、Spark 精确 exit 读回及 OpenSpec 更新才勾选 Task 2.5。保留默认 `HALT`、`write_authorized=False`、`retention_preflight_verified=False`，不开放正式 Delta 写入。

### 2026-11-02 G3 prerequisite real Fabric 5 + 100 Canonical read-only acceptance

- **Native business implementation**：Healthcare [PR #617](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/617) merged as `70e32df832b128746dc6c0e886ec07c18d0c3e63`; new `CANONICAL_READONLY` mode reuses frozen 5/100 Manifest, source object SHA, one published Shared Wheel 0.1.1 and exact Local v1 Patient/Encounter Contract raw-byte SHA. Before any source read it rejects write/retention flags, arbitrary URIs/override source roots and tampered Contract. Offline Notebook test + OpenSpec change gates PASS; Git-native default `HALT` and existing Pipeline disabled.
- **Cloud deployment**：ordinary Healthcare → Self-Runner Git push [Run #41526965330](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41526965330) was a safe `UNAPPROVED_LOCAL_ITEM_PRESENT` HOLD (0 writes). Independent GET [Run #41527445281](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41527445281) verified exactly the three previously known local serialization/Shortcut states and the old synchronized baseline. Narrow single-update [Run #41527915973](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41527915973) `FHIR_GIT_RECONCILED_READBACK_PASS`, cloud Notebook `.py/.ipynb` and Pipeline HALT readback, existing Shortcut retained.
- **5-person real Spark Canonical PASS**：[Run #41528259767](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41528259767) Fabric Notebook Job `ecbdd022-4091-4d90-af5e-75ed90e0c13c` `Completed` (21:26:47–21:27:34 UTC), precise `exitValue=FHIR_CANONICAL_READONLY_5_SPARK_PK_FK_PASS_20261102`; Core/Beta independent [Run #41529654770](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41529654770) showed an actual Spark application `application_1793654176653_0001`, not just a job POST ACK.
- **100-person initial capacity failure, not DQ**：same Run #41528259767 first 100 Job `f46b810f-de15-4998-8d3e-65ae6215a1ea` `Failed` at 21:27:45–21:27:46 UTC; GET-only [Run #41529654770](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41529654770) confirmed categories `CAPACITY` / `SPARK_SESSION`, `spark_session_entry=NOT_ESTABLISHED` (no business Spark application started). Prior 5 Job independently stayed exact PASS. No automatic/blind retry or physical Delta writes.
- **100-person real Spark Canonical PASS**：bounded single-request [Run #41530178149](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41530178149), Fabric Job `11eb81a7-72de-411f-8348-8b8a02bdfe3c` `Completed` with exact `exitValue=FHIR_CANONICAL_READONLY_100_SPARK_PK_FK_PASS_20261102`; artifacts record `FHIR_CANONICAL_100_ONLY_SPARK_PK_FK_PASS`, prior 5 PASS, prior 100 pre-Spark failure, present zero other active job, published Wheel and current cloud Git definition, Pipeline HALT, and `business_delta_writes=false`.
- **Result boundary**：Task 2.5 **PASS = actual 5/100 FHIR source bytes → canonical Patient/Encounter in-memory Spark transformations with v1 Contract and PK/FK/DQ**. This does NOT prove durable Delta physical row counts, Bronze raw/ref receipts, readback, replay SKIP/HOLD, approved/quarantine publication, Azure retention policy or Pipeline E2E. Therefore G0 retention remainder, G3, G4 and downstream tasks remain **OPEN**, and defaults `HALT`/`write_authorized=False`/`retention_preflight_verified=False` remain unchanged.


### 2026-11-02 G3 Bronze receipt implementation and live release gates

- [ ] **G3.a (source approval)** Independently verify Azure Blob storage container's actual retention/immutability settings, source access permissions and request-unique conditional publisher behavior. A SHA/ETag GET or the existing Shortcut does not establish the container's enforcement. Preserve proof URI/run ID; do not claim preflight PASS without actual evidence.
- [x] **G3.b (new source)** Generate and publish a fresh synthetic Atlanta FHIR 5–10 person batch; record request ID, actual manifest byte SHA, objects/ETags and expected counts. Historic read-only 5/100 batches do not substitute for this.
- [x] **G3.c (staging code)** Git-first Notebook \`BRONZE_RECEIPT\` + \`BRONZE_READBACK_ONLY\` with pinned path, manifest/source byte SHA, request-scoped collision/HOLD, Delta \`errorifexists\`, durable rows readback, replay SKIP and unknown ACK read-only recovery. Must pass offline PR CI before live release; code-only does **not** mark the parent G3 complete.
- [ ] **G3.d (real runtime)** Exact Lakehouse GUID readback, cloud definition HEAD readback, retention/permission authorization, one real Fabric write Job, a separate readback-only Job and explicit Replay/Drift evidence with source counts and physical Delta location. No automatic retries on unknown ACK.
- [ ] **G4 (Silver)** After G3 proof, develop/reuse \`execute_native_notebook\` for managed \`canonical_patient\` and \`canonical_encounter\` Delta, durable ledger/Approval, independent PK/FK/DQ/quarantine/readback and conflict/recovery; use a new 100-person synthetic batch. G4 not released by G3's Bronze receipt alone.

- **G3 Task 2.6 offline acceptance (not physical cloud write):** [Fabric FHIR Notebook Offline Contract Run #41537970856](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41537970856) SUCCESS, including new `test_g3_bronze_receipt` positive/negative, request-drift, SHA, persisted replay, unknown ACK and readback-only tests. OpenSpec strict validation [Run #41537971023](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41537971023) SUCCESS, and both change gates SUCCESS. Reviewed [PR #619](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/619) staging; G0 retention and actual G3/G4 Delta write/readback still NOT_RUN.


- **G0 live audit 2026-11-02:** [Self-Runner #41541369688](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41541369688) completed GET-only checks against newly published five-person source; six Blob HEADs verified, zero enforceable locked WORM/legal holds. Container strict protection remains \`HOLD_G0_SOURCE_WORM_NOT_VERIFIED\`. Do **not** check G0 container WORM PASS. [Publisher #41539769718](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41539769718) independently proved five exact source SHA/ETags, replay and wrong-SHA denial.
- [x] **G3.e (raw preservation alternative)** Replace metadata-only Bronze receipt with request-scoped \`bronze_source_snapshot\` Delta containing exact original \`source_payload binary\` for all five objects and atomically stored provenance. Gate on pinned \`source_preservation_strategy=DELTA_RAW_SNAPSHOT_V1\`; real WORM is **not** claimed. Independent byte/SHA replay and unknown-ACK recovery tests must PASS before any live write.

- **Task 2.7 offline evidence, not cloud Delta acceptance:** [Healthcare Notebook Offline Contract #41542138728](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41542138728) SUCCESS: 43 tests, including 11 G3 raw-bytes/legacy-receipt/tamper/unknown-ACK/replay cases; OpenSpec static+change gates SUCCESS. No Fabric Spark write Job or physical Delta row data exists yet from this change. **G0 Azure WORM remains HOLD**; only the explicitly reviewed atomic Delta raw snapshot alternative is being released to Git for future real Jobs.


### 2026-11-02 G3 real Bronze Delta acceptance — positive path PASS

- **G3 persisted positive path: [Self-Runner Run #41542977044](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41542977044) completed SUCCESS, and logs report FHIR_GIT_RECONCILED_READBACK_PASS, then FHIR_G3_BRONZE_OUTCOME=FHIR_G3_BRONZE_WRITE_READBACK_REPLAY_PASS and FHIR_G3_BRONZE_ERROR=NONE. Three distinct Fabric Spark Job UUIDs were checked for Completed and exact expected exit markers. This supersedes earlier pre-run NOT_RUN statements for the positive G3 path only.
- **Source:** [new Azure Publisher Run #41539769718](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41539769718); request atlanta-fhir-gh-41539769718; five source FHIR objects; delivered Manifest raw SHA256 2f9ef5a555f164464a79a5dc457a6d7f9ef79156edca11b2f1fb49789c785c35; upstream source SHA256 29573663d7b7ce7fe5378d1e84ccdf7b3b327d9cbdd66f2c94745636b09d231a.
- **Exact Lakehouse:** e67c42ee-5ab2-4bc8-a013-7bdf9741ef68. **Persisted Delta path:** Files/bronze/fhir_r4/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/atlanta-fhir-gh-41539769718/bronze_source_snapshot. Five raw source_payload binary objects and associated source SHA/size, Manifest SHA, source batch ID, processing version and request ID were stored together with errorifexists. Notebook code validates raw payloads via independent Delta reopen and SHA/size comparison.
- **Job 1 write:** 782c92b1-66a1-44c2-8861-05ffe374f225; BRONZE_RECEIPT; expected exact exit FHIR_G3_BRONZE_WRITTEN_5_DELTA_READBACK_PASS_20261102.
- **Job 2 separate readback:** 4a307c02-b01f-418c-b97f-13599e12d000; BRONZE_READBACK_ONLY; expected exact exit FHIR_G3_BRONZE_SKIP_VERIFIED_5_DELTA_READBACK_PASS_20261102.
- **Job 3 same-request replay:** 7154430d-9618-4dad-a204-2424beff5250; BRONZE_RECEIPT; expected exact exit FHIR_G3_BRONZE_SKIP_VERIFIED_5_DELTA_READBACK_PASS_20261102; matching persisted Delta resulted in SKIP, no second write.
- **Git evidence:** Healthcare [PR #620](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/620) merged 94f87ea5b6aa7c4d5b5b1cc24e807b85ab9ed8a5; 43 Notebook offline tests PASS. Runner [PR #457](https://github.com/JohnZhang-DataForge/Self-Runner/pull/457) merged 120d2294d03dfcaea6343bc69ede8cb0af058850; source/physical GUID/Shortcut/Git readback and three-job execution preflight recorded in the successful run.
- [ ] **2.9 G3 outstanding negative cases:** A separate real same-request changed-Manifest drift-HOLD and independent unknown-ACK read-only recovery drill are still open. Offline negative tests PASS but do not constitute live negative proof. Parent G3 acceptance is PARTIAL (persisted write/readback/replay positive PASS).
- [ ] **G0 Azure Blob strict WORM:** [GET-only Run #41541369688](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41541369688) inspected six source objects and found 0/6 with locked WORM or legal-hold evidence; G0 strict policy is HOLD. The bounded synthetic Fabric Delta raw-byte snapshot is an alternative for development, not an Azure container retention/compliance claim.
- [ ] **G4 Silver:** no real canonical_patient/canonical_encounter Delta/Approval/Quarantine/PK/FK/DQ independent readback PASS yet. Advance separately with a new 100-person synthetic source after independent preflight.

### G4 real 100-person Silver Delta release gates (2026-11-02)

- [ ] **G4.a Notebook code:** one guarded SILVER_WRITE / SILVER_READBACK_ONLY entry reusing Shared Engine 0.1.1 Canonical v1, raw source preservation, request-scoped Silver physical Delta and final approval fence; offline positive/negative/partial-commit/replay/PK/FK/DQ tests and CI.
- [ ] 2.11 G4 real Fabric: exact new 100-person delivered source/Manifest SHA, two pinned canonical Contract raw hashes, first Delta Silver write (Patient + Encounter + Approval) and 100-byte raw snapshot, independent separate Spark readback Job and SKIP replay. Record physical GUID, Delta paths, count, timestamps, complete job UUIDs and exit values.
- [ ] 2.12 G4 real negative: source drift HOLD, DQ quarantine/Approval-denied and unknown ACK read-only recovery; never infer tests from mock. G0 source Azure WORM remains open even if synthetic Fabric raw snapshot passes.
