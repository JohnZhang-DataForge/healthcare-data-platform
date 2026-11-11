# Local synthetic OMOP Observation Period v1

## ADDED Requirements

### Requirement: Observation Period SHALL have explicit encounter provenance and bounded meaning

- 在纯合成 Synthea EHR 的 PostgreSQL17 OMOP CDM 5.4 中，首版规则 SHALL 基于已经物理提交、具 Source ID Map 的 `cdm.visit_occurrence` 生成观察期。
- 每名 Person SHALL 最多一条首版记录，`observation_period_start_date=min(visit_start_date)`，`observation_period_end_date=max(visit_end_date)`，`period_type_concept_id=44814724`。不得借助生日、系统当前日期、批次 `ingest_date`、自动 365 天窗口或人工编造覆盖日期。
- 不得将推断区间宣称为保险参保、全生命周期完整病史或经过证实的连续 EHR 完整捕获；Cohort 研究 MUST 处理小于30日的观察期。

#### Scenario: Candidate includes real mixed historical and newly staged records

GIVEN 当前 `cdm.person=1394`、`cdm.visit_occurrence=200556`，且早期 113/5799 人/访视有历史 Source Map、不在新的 Stage 表中
WHEN 以当前 OMOP CDM 事件生成候选
THEN 候选 SHALL 仍是 1394 人、全部 ID 可回读、0 Null/invalid date、0 early-than-birth、0 future Visit
AND 历史 Batch 来源差异 SHALL 被记录为来源治理异常，而非默默丢掉或生成伪造 Manifest。

#### Scenario: Short periods and long gaps

GIVEN 两名 Person 的 Visit-bound 观察期小于30日，且其他 Person 有多年就诊间隙
WHEN 生成 Candidate
THEN SHALL 保留合法的短时观察期并披露研究限制
AND SHALL NOT 自动把没有 Visit 的日子当成明确缺失数据的断点或补造日常就诊记录。

### Requirement: Controlled one-shot writer MUST be scoped, backed up and atomic

- 对已存在任何 `cdm.observation_period` 记录、源计数漂移、词表 44814724 无效、Person/Visit FK/ID map 缺失、日期非法、并行任务、缺私有快照的情形，执行器 SHALL fail closed。
- 备份 MUST 仅覆盖目标表 `cdm.observation_period` 当前归档，并以 Blob 条件创建、独立 GET/SHA 与 PG `pg_restore --list` 证明可读取；禁止覆盖。
- 预演 SHALL 明确事务 ROLLBACK 并证明无持久化数据；正式 COMMIT SHALL 仅 Insert `cdm.observation_period`，对 Person、Visit、Vocabulary、Results 只读。
- 重新执行任何成功或不确定结果的工作流 SHALL 被拒绝；失败后必须独立只读核查提交状态，不能自动 DELETE 或重跑。

#### Scenario: Successful live writer

GIVEN 实际 Source/Schema/Role 预检、私有快照、ROLLBACK 演练全部 PASS
WHEN 单次事务执行标准 Observation Period 插入和同事务读回
THEN SHALL 生成预期 1,394 条，并由独立全新只读会话验证 1:1 Person 与日期覆盖
AND 原有 1,394 Person、200,556 Visit 和 ACHILLES/Results 数据 SHALL 不变。

#### Scenario: Backup or source state drift

GIVEN 任何前置证据缺失、目标表不为空、源数据增加或出现一个不合法候选
WHEN 执行器尝试执行
THEN SHALL 拒绝，而不是以 IF NOT EXISTS、UPSERT 或仅更新不匹配数据等方式继续。

### Requirement: Observation Period readiness SHALL NOT imply Cohort study completion

- Observation Period 完成后，ATLAS 的真实 Concept Set、Cohort Definition、Generation、Results 物理 E2E SHALL 分开验收。还没有执行 Cohort 的状态 MUST 标为未完成。
