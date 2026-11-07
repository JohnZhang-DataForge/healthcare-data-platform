# Design — FHIR→OMOP unified acceptance

## 已验证事实与不变量

- Healthcare 起始 main `4267d6b4ddb48173b6c020c815a4ed4e0a525edc`；Self-Runner `ece535b956f6fa0d6f1fbc17470658d60fd167ad`。实际执行前必须重查两仓 main/PR/Actions。
- G5 #41874126635 仅完成 G4 已批准 P100/E5918/Q0 实际物理 Source Readonly；不是 Candidate Approval、持久化 ID 或 Gold COMMIT。
- 正式 Wheel 是 0.1.3；历史 G4 `engine-0.1.1` 分区必须原样保留。
- 目标资源固定为 Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`、Lakehouse `e67c42ee-5ab2-4bc8-a013-7bdf9741ef68`、Warehouse `7a6d08da-278d-4603-8a3b-28640110984c`。

## P1：Concept Profile Gate

- 调用者通过 **独立的真实 Silver/Approval Delta 读回**提取四组原始代码及其频数；必须验证其总数与 G4 Patient/Encounter 物理源行数一致。
- 调用者从 **已验收的真实 F1 Warehouse Vocabulary** 读取所有 profile 引用的 Concept ID、Domain、standard、validity、invalid_reason；记录实际 release ID 和九文件 Manifest 的固定 SHA（禁止合成 release）。
- 纯函数 `writer/concept_profile.py` 复用 Shared Engine 0.1.3 的现有 profile checksum/schema 解析器，拒绝未知代码、source-value 超长、大小写冲突、缺失/重复 Concept、非标准或无效 Concept、错误 Domain/日期以及 SHA 漂移。
- 返回状态 **P1_CONCEPT_PREFLIGHT_ONLY_NOT_CLINICALLY_APPROVED**。输入由调用者提供，函数不能独立证明云端真实性；还须人工映射复核、真实源/词表双重证据后才建立正式版本化映射。当前没有臆造 Concept ID 或源值。
- Warehouse 的 `Type Concept` 亦需以正式 Vocabulary 确认；若实际标准标记与此门禁不符应 HOLD 调查，不得调宽校验后假报 PASS。

## 2026-11-06：开发门禁与临床发布门禁解耦（用户批准）

- **开发不依赖固定 Vocabulary 版本**：FHIR/Canonical、Person/Visit Mapper、ID 预览、Candidate 重放计划、Gold Writer 事务算法和 Pipeline 编排均接受版本/规则 SHA 作为外部输入；不能将 `v5.0 27-FEB-26` 或未经审查的 Concept ID 硬编码进业务算法。
- **不同失败分流**：源值未映射、无有效标准 Concept、Domain 错误、失效日期等归类为可保留原始值的 `DATA_QUARANTINE_CANDIDATE_HOLD_PUBLICATION` *建议*，具体行级 Quarantine/剩余数据的部分发布须经业务合同单独批准；Profile SHA/版本/Approval、Identity Snapshot 漂移与未知 ACK 属于 `BATCH_HOLD_NO_PUBLICATION`。目前严格 Mapper 遇不完整映射仍对整批 HOLD，不能通过新的分类辅助函数暗中绕过既有门禁。
- **P3 源码可并行开发，实际临床 Candidate 写入不能擅自执行**：同一个 Shared Engine Pure Planner 仅冻结 Request、Silver Publication、Mapping SHA、Snapshot SHA、数量和 `PROVISIONAL/PERSISTED` 标志；输出 `PLAN_NEW_OFFLINE_ONLY`、`VERIFY_READONLY`、`SKIP_VERIFIED_CANDIDATE_ONLY` 或 `HOLD_*`。计划不自行执行 Spark/SQL/Delta 写入；由 Native Notebook 在获得独立真实审批及资源授权后执行 `errorifexists` 两张 Candidate Delta、独立重开对账、**最后**写 Approval 并二次读回，异常/部分状态先 GET，不自动重试。
- **P4/Gold 边界不变**：Candidate ID 仍是提议；只有同一 Warehouse single-writer 事务真实提交的 Map/Allocator/Person/Visit/Ledger/Audit 才是持久 Gold。源业务字段映射失败与源数据无效不应自动生成假 Concept ID 或假 Gold 成功。新增 Shared 纯 Planner 不更新已经 Published 的 0.1.6 Wheel；后续版本化发行/Notebook Integration 单独验收。

## P2→P5：分阶段可恢复写入

1. P2 复用 `identity_plan.py`、`silver_identity.py` 做已冻结真实 Warehouse 快照下的稳定 INT Preview；后续仅在 Gold 单写入者事务中原子持久化。
2. P3 仅在映射/身份/Approval Fence 全部获批准后写独立 Candidate Delta；独立新 Spark 读回、Approval-last、Replay SKIP。没有真实 ID 的临床正式输出必须 HOLD。
3. P4 事务内复核 Snapshot/Allocator/Map，原子提交 Identity、Person、Visit、Ledger、Audit；未知 ACK 必须先独立 SQL GET；失败 ROLLBACK，不自动重试。
4. P5 真实 Notebook/Pipeline Run 和独立 SQL、Spark readback 分别归档，默认 HALT、retry=0、无 schedule，Marquez 并行工作不在本 Change 改动范围内。

## 兼容与回滚

P1 代码为无 I/O 的离线门禁，不改变云端 Wheel 0.1.3、G4、F0/F1 数据。未来带写入的 PR 必须单独审批并走真实执行；任一门禁失败停在 HOLD。不能用 CI/Notebook Completed 冒充 COMMITTED。
