# Tasks — Unified FHIR → OMOP Gold

## P0 — 接管及证据（2026-11-04）

- [x] 0.1 独立核对双仓 main、PR、最近 Actions；确认 Marquez 并行 PR 不应覆盖。
- [x] 0.2 G5 Source Readonly #41874126635 Job `e5038133-8120-4afe-b132-9abf6fb652ab` 确认实际 PASS，补入原 G5 OpenSpec，关闭 3.5–3.7 而保留 Candidate/Gold OPEN。
- [x] 0.3 核对实际 etl/audit 五张 SQL 管理表字段、纯身份 Preview、Candidate Mapper 接口和正式 0.1.3 基线。

## P1 — Concept Profile

- [x] 1.1 建立不硬编码临床值的来源代码/词表 Concept 校验函数（仅纯函数/离线），包含有效日期、Domain、标准标记、SHA、防截断和异常 HOLD。
- [x] 1.2 P1 离线正负向 CI 完成并合并 main：Healthcare PR #662 / 合并 commit `5a67d12cb13dbea98b732e5a80e1a1f3fda3eef4`，6 项 PR checks SUCCESS、31/31 Python Tests PASS。仅证明 P1 纯函数预检。
- [x] 1.3a 正式 Notebook 新增 `G5_CONCEPT_SOURCE_INVENTORY_READONLY` 模式，复用 G5 真实物理 Approval Reader 后获取五组源代码/频数和源值长度，带 SHA、来源身份、行数的受控 JSON read-only receipt；仅 CODE/OFFLINE，真实云端仍待执行。
- [ ] 1.3 从已批准 G4 Silver 真实独立读回四组 code/count；对账 Patient=100、Encounter=5918，核验 source_system/hospital。
- [ ] 1.4 从真实 F1 Warehouse 读回这些 Concept 明细；核对九文件 release/manifest、许可、有效日期、Domain、Vocabulary 审计。
- [ ] 1.5 临床映射审查与正式版本 SHA 冻结；未知、不合法、无授权的全部 HOLD；禁止发布伪 Profile。

## P2–P5 — 候选、事务、管线

- [ ] 2.1 以真实 Warehouse 完整 ID/Allocator/Gold/Ledger 快照验证跨医院稳定 INT 分配，保留并发 Single-writer fence。
- [ ] 3.1 真正 Candidate Delta 物理写入、独立读回、Approval-last、同 Request Replay SKIP。
- [ ] 4.1 Warehouse 单事务 Map/Allocator/Person/Visit/Ledger/Audit COMMIT；独立 SQL 新连接读回、Rollback/Unknown-ACK/Replay/DQ 负向验证。
- [ ] 5.1 原生 Pipeline 实际 FHIR→OMOP E2E：默认 HALT/无自动 Schedule/retry=0；记录 Job、Spark、SQL 三类独立证据。

## Evidence

- Offline P1 pure-profile CI initial [Run #41917799155](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41917799155): 31/31 OMOP Foundation unit tests PASS (9 new Concept Profile tests included), no cloud writes. PR gate checks are tracked separately; initial PR body omitted required OpenSpec tags, corrected before re-run.
- Source-only [Run #41874126635](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41874126635) PASS；G4 request `atlanta-fhir-gh-41552666929`，Manifest `425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1`。
- F0/F1 DDL / Vocabulary、F2 ROLLBACK 维持历史真实验收；**P1 real concept mapping / Candidate / Gold COMMITTED / E2E 均未通过**。
