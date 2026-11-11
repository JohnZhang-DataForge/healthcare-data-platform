# Design — Encounter-bounded Observation Period v1

## Context and exact evidence

- Healthcare Main 截至设计启动：`5cc16968026e1fe3602d91837ba0f902e928d142`；Self-Runner Main：`9c9c67e631fda8e6241d5c904893364589a05d24`。执行前重新读取 Main，不把上述 SHA 视为永远最新。
- 独立真实预检：[Run 42984417059](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42984417059) Person 1,394、Visit 200,556、Person-FK 缺失=0、时间错误=0，1,271/604/64 人存在 >365/>730/>1825 天就诊间隙；不能因此机械拆分。
- [Run 43011219322](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43011219322) Source Map 完整：1,394/1,394 Person 与 200,556/200,556 Visit，已完成 Landing=18 个批次。
- [Run 43011610827](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43011610827) Task004 Ledger 共 19 批，其中 18 批 Landing Manifest SHA 匹配；Stage 1,281 Person、194,757 Visit，已全部物理映射。另有早期 pre-Stage 数据 113/5,799，不等于未映射的 CDM 记录。
- [Run 43012017794](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43012017794) 证实未匹配批次 Stage=23 Person/3,592 Visit，需单独治理；但候选 min/max Visit 可覆盖 1,394 Person，0 before-birth，0 invalid，0 future Visit；2 名病人跨度小于 30 天。真实 vocab 44814724 有效，44814725 为 `Period inferred by algorithm`；此规则更具体地采用 44814724。
- OHDSI CDM 5.4 Observation Period: https://ohdsi.github.io/CommonDataModel/cdm54.html （在缺少正式连续覆盖时间的 EHR 情况下，可基于最早/最晚可信事件推导，具体假设由 ETL 定义；必须标记来源类型和后续研究限制）。
- Synthea `exporter.years_of_history=0` 可导出全历史，但 **不等于**这个数据源具备保险覆盖证据；原始 `DEATHDATE` 没有映射到现有 `cdm.death`，本轮不臆测死亡时间，不把边界延长超过最后就诊。

## Decision 1 — Candidate only from materialized CDM

依赖唯一已有的 `cdm.visit_occurrence` 物理结果和已有 `cdm.person`、`etl.person_id_map`、`etl.visit_occurrence_id_map`。

```sql
WITH bounds AS (
  SELECT person_id,
         MIN(visit_start_date) AS observation_period_start_date,
         MAX(visit_end_date) AS observation_period_end_date
  FROM cdm.visit_occurrence
  GROUP BY person_id
)
SELECT person_id AS observation_period_id,
       person_id,
       observation_period_start_date,
       observation_period_end_date,
       44814724 AS period_type_concept_id
FROM bounds;
```

**重要解释**：这是 synthetic EHR event-bounded *heuristic*，不主张间隔内所有历史事实都绝对完整；不是以生日/今天生成跨度，也不按 365 日断点臆测数据缺失。保留两名观察期短于30天的病人，在 Cohort 定义/研究分析中按所需最短观察期限制。

只有当所有 Person 至少一条 Visit、无 null/非法日期、没有 future Visit、没有早于出生日期、全部 target IDs 可映射且 `cdm.observation_period` **仍然空表**时才可进入 ROLLBACK 演练。若后续增量批次已写入，新 Change 负责调整范围；本方案不得默认重算或覆盖。

## Decision 2 — Snapshot, safety and writer

- Writer 与现有 Share Engine / Source Adapters 严格解耦：这里只是 **CDM 后处理的标准 Observation Period 派生**，不重新做 Person/Visit Mapping。不为 FHIR、HL7、Fabric 建立单独 Mapper。
- 执行器仅走已批准的 Self-Runner 一次性分支工作流，`--execute-once` 且 `GITHUB_RUN_ATTEMPT=1`，不是 `workflow_dispatch`、定时、Main merge 自动触发；所有权限/当前 Job/Source count/表状态漂移时 HOLD。
- **备份前置**：读取当前 Postgres17 `cdm.observation_period`（0 行）及表约束，利用固定私有 Azure Blob `landing` 创建目标表专属 `pg_dump -Fc -t cdm.observation_period` 归档与 Manifest，`If-None-Match: *`，独立 GET/SHA 与 PG17 `pg_restore --list` 检验；原有 2026-11-02 整体 CDM 快照是较旧状态，不得冒充当前完整 CDM 备份。可恢复性演练应另设受控隔离库且禁止导入现有 `omop`。
- 先运行全部 DDL/DML 在明确 `BEGIN ... ROLLBACK` 的独立事务演练；只输出脱敏聚合与 pg SQLSTATE，不打印患者/原始 Manifest。确认事务退出0且独立读回原表仍0后才能进入独立正式提交。
- **提交 SQL**：`BEGIN`、短锁/超时、可选统一 advisory transaction lock、再次检查硬门禁（0 OP / 1,394 Person / 200,556 Visit / Source Map 100% / valid vocab / no source drift）、唯一 `INSERT INTO cdm.observation_period`、同事务校验候选行数/每人唯一/没有端点越界、`COMMIT`。失败连线断开后必须独立只读核实是否部分/全部 COMMIT，禁止无检查重放或自动回滚别人数据。
- `observation_period_id=person_id` 仅适用于**此空表、纯合成、每人唯一**范围；不是后续所有数据源的全局 ID 规范，未来 Shared Engine 多源增量必须采用持久 ID Registry/Writer 设计。
- 物理读回必须由新 PG session 以只读方式校验精确 1394 OP、覆盖全部 1394 person、0 visit outside bounds、0 overlapping periods、Period Type=44814724、原 Person/Visit/Vocab/ACHILLES/Results 不变。

## Decision 3 — Workflow phases and operations

1. **G0 Source audit**：19 批来源、历史 113/5799 与 unmatched 23/3592 以明确的例外状态归档，不自动补写历史 Landing。
2. **G1 Proposal/Spec/Tests**：审查规则、负向测试与源码地图、OpenSpec CI，通过后合并。
3. **G2 Targeted backup + ROLLBACK**：验证私有 Blob、空表目标归档和 restore-list，事务回滚演练。
4. **G3 One-shot commit + independent readback**：严格 scope only `cdm.observation_period`；无新 K8s Job、无 Fabric/Cloudflare/ATLAS 发布。
5. **G4 Research acceptance**：用户源仍是 `LOCAL_OMOP`，验证 WebAPI `/cdmresults/LOCAL_OMOP/observationPeriod` 及真实 Cohort Definition/Generation；不是完成 G3 就自动标记 Cohort E2E PASS。

## Rollback/recovery

事务报错时无 COMMIT，不影响既有 Person/Visit。成功 COMMIT 后若发现问题，**不自动执行 DELETE/TRUNCATE/DROP**；只能先独立比对本次确定性 1,394 ID/值及目标表专属备份，再另审授权范围的恢复/迁移方案。无裸露密码、真实 Source ID、Blob JWT、患者记录、数据库归档写入 Git 或公开 Actions Log。
