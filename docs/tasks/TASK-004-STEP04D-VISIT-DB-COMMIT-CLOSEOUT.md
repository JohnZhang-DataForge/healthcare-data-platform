# TASK004 STEP04D — Visit CDM 入库与同批次重放正式验收

**STEP04D fixed-batch Visit database commit: COMPLETE / PASS. TASK004 总体仍 IN PROGRESS。**

## 授权和边界
用户在 2026-10-13 明确授权固定批次的 **最多 3,592 条 Visit Mapping 和 3,592 条 `cdm.visit_occurrence` INSERT**，以及同批次重放。固定批次 `task004-airflow-task004-step03e-38324111846`，S3 Manifest SHA `ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1`。

**真实 Run [38393486251](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38393486251) SUCCESS**：固定 Healthcare SHA `c75551f68f942efc75a02eba7131bc414bd8c343`，测试 → S3 Parquet readback → PostgreSQL 完整 ROLLBACK 演练 → 正式 COMMIT → 独立只读数据库对账 → 相同批次 COMMIT 重放 → 再次独立只读计数对账。

较早的 [38393127107](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38393127107) 在时间戳校验处 fail-closed：Canonical Parquet timestamp-NTZ；更新明确 UTC 解释规则后 [38393298605](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38393298605) 独立 ROLLBACK PASS，方进行正式 COMMIT。

## 来源类型概览
原始 Encounter class 分布（汇总，无个人数据）：ambulatory 1891、emergency 171、home 19、hospice 3、inpatient 6、outpatient 419、snf 7、urgentcare 147、virtual 3、wellness 926；合计 **3592**。

映射依据已有 `spark/contracts/omop/visit-class-v1.json`，访视类型 32827，Visit Concept 使用 9201/9202/9203/581476/722455，数据库验证 standard_concept='S' 且 invalid_reason IS NULL。Canonical NTZ 输入明确按 UTC 处理后写入 PostgreSQL 无时区 timestamp；日期取 UTC 日期。Visit Person FK 使用已有稳定 `etl.person_id_map`，不生成新 Person。保留 `visit_source_value` 原始 class，其余未支持 FK 字段为空，不伪造映射。

## Post-COMMIT 和 Replay 双重独立 Readback

| 指标 | Baseline | COMMIT 后 | 重放后 |
|---|---:|---:|---:|
| `cdm.person` | 136 | **136** | **136** |
| `etl.person_id_map` (synthea) | 136 | **136** | **136** |
| `cdm.visit_occurrence` | 5799 | **9391** | **9391** |
| `etl.visit_occurrence_id_map` (synthea) | 5799 | **9391** | **9391** |
| Batch Visit Stage | 0 | **3592** | **3592** |
| Batch Visit Commit VERIFIED | 0 | **1** | 重放继续 VERIFIED |
| 当前批次 Visit Stage→Visit Map→CDM Visit→Person Map 四表匹配 | 0 | **3592** | 同源事务字段比对 PASS |
| Visit 引用缺失 Person | 0 | **0** | 无新增孤儿 |

关键 Runner 标记：`VISIT_ROLLBACK_PREFLIGHT=PASS`、`VISIT_DATABASE_COMMIT=PASS`、`VISIT_INDEPENDENT_POSTCOMMIT_READBACK=PASS`、`VISIT_SAME_BATCH_REPLAY=PASS`、`VISIT_REPLAY_COUNTS_UNCHANGED=PASS`。

**结果解释**：固定批次首次新增 3592 Visit 和 3592 Map（5799→9391）；相同批次重复数据库执行没有再次增加行数。SQL 对映射到当前批次的已存在 Visit 执行字段一致性检查，冲突则失败，不更新历史 Visit。独立校验确认现有 136 Person 行数未变，全部 Visit FK 无孤儿。本轮未做 5799 条历史 Visit 的逐行哈希前后比对，因此不能据此声称已验证所有历史记录的字节级不变。

## 代码与下游工作
- `apps/task004/step04d_visit_sql_builder.py`: 3592 Visit 的确定性转换、Stage/Mapping/目标事务、失败拒绝和幂等重放。
- `apps/task004/step04d_visit_runner.py`: 严格 Manifest/Processing S3 数据源、受限 PostgreSQL 执行，日志不输出源 ID。
- `tests/task004/test_step04d_visit_loader.py`: 6 项正/负例，以及真实 ARC 演练验收。
- `Self-Runner/.github/workflows/task004-step04d-visit-loader.yml`: 实际 COMMIT 与独立对账。

**STEP04E 下一步**：Person/Visit 联合跨表 Reconciliation、历史快照差异与业务级清点；随后 STEP04F 将独立写库动作纳入 Airflow 编排。STEP04G 仍须验证 DAG 真正重试、未知提交结果恢复、并发和批次级端到端 Replay。此时 TASK005 继续 ON HOLD。
