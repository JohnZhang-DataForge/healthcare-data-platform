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
