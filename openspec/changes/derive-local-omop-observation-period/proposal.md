# Proposal — Local OMOP Observation Period (Encounter-bounded v1)

## Why

本地 PostgreSQL17 的 CDM 5.4 已有真实 1,394 Person、200,556 Visit，ATLAS3/WebAPI3 的 23 张 Cohort Results 表已经完成物理初始化；但 `cdm.observation_period` 精确行数为 0，导致真实 Cohort 研究无法完成。不能把注册 Source、生成 ACHILLES 报表或初始化 Results 误称为 Cohort Generation 已通过。

OHDSI CDM5.4 允许 EHR 缺乏明确参保/持续跟踪时间时，**声明假设**后以首末可信临床事件推断 Observation Period。当前是明确的**纯合成 Synthea/EHR 数据**，已有 100% Person/Visit source ID mapping，可以先采用保守的就诊边界模型而不声称患者从出生到现在连续被监测。

## What Changes

- 新增独立业务 Change（不修改 `deploy-local-ohdsi-atlas` 的 UI/部署、旧 NEW_ONLY Writer、FHIR/HL7 Shared Mapper 或 Fabric）。
- **v1 规则**：只对现有真实 CDM 的 Person/Visit 形成一个 encounter-bounded Observation Period：`start=min(visit_start_date)`、`end=max(visit_end_date)`、`period_type_concept_id=44814724`（本地词表独立读回为有效 `Period covering healthcare encounters`）。
- 用 `person_id` 作为只针对**空表且每人恰好一条**模型的确定性 `observation_period_id`；不重用/改动 Visit/Person ID Map，不写新的重复 Mapper。
- 在**当前唯一精确批次/数据快照**上执行：完整只读 FK/日期/Source Map/后台任务/权限检查、目标表专属不可覆盖 Blob 备份与 SHA/restore-list、事务内 ROLLBACK 演练、一次性受控 COMMIT、独立 PG17 物理读回。失败不自动重试。
- 独立记录已知两类来源治理缺口：113 Person/5,799 Visit 是早期 pre-Stage 历史记录；19 个 task004 Ledger 中 1 个未与 Landing Manifest SHA 匹配（Stage=23 Person/3,592 Visit）。不伪造修复，也不把它们当作完整的源追溯证据。

## Capabilities

- 新增 `local-omop-observation-period`：可测试的 Event-bounded Observation Period Candidate、SQL-only controlled atomic writer 及独立读回。

## Impact

- 数据面：允许**唯一业务变更** `cdm.observation_period` 从 0 行受控增长到预期 1,394 行。既有 `cdm.person`、`cdm.visit_occurrence`、Vocabulary、WebAPI/Results、K8s/Cloudflare 等保持不变。
- 业务面：完成 Cohort 前置必要数据，但不自动创建 Concept Set / Cohort Definition、并不自动执行 Cohort Generation；其业务 E2E 单独验收。
- 成本：复用 PG17、Self-Runner、已有私有 Azure `landing` 容器；不建立额外 PG/PVC/Fabric Capacity。
- 约束：默认安全拒绝；不可用“连续参保”“终身完整 EHR”的表述描述此推断模型。2 个小于 30 天的观察期在研究时必须显式限制最短观察时长。

## Non-goals

- 不修复历史 Landing 记录、不补造死亡日期/保险覆盖、不从原始 Synthea 再加工第二套 Mapper。
- 不迁移/扩展整个 OHDSI CDM 或替换 ATLAS3。
- 不自动刷新 ACHILLES（已物理生成）或重跑失败的历史 Job。
