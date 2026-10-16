# TASK004 STEP04D — Visit 入库前真实数据库检查

**结论：READ-ONLY PREFLIGHT PASS；Visit 入库尚未授权/执行。**

证据：Self-Runner [38391860713](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38391860713) 成功。只读事务直接检查 Kubernetes PostgreSQL `omop`。

| 项目 | 实际观测 |
|---|---:|
| cdm.person | 136 |
| cdm.visit_occurrence | 5,799 |
| etl.person_id_map (synthea) | 136 |
| etl.visit_occurrence_id_map (synthea) | 5,799 |
| 当前批次 Person Stage | 23 |
| 当前批次 Visit Stage | 0 |
| 当前批次 Person VERIFIED Commit | 1 |
| 当前批次 Visit Commit | 0 |
| Visit Mapping 重复键 | 0 |
| Visit Mapping 指向不存在的 Visit | 0 |
| 既有 Visit 指向不存在的 Person | 0 |
| Visit Mapping 业务键唯一索引 | 存在 |

固定源批次：`task004-airflow-task004-step03e-38324111846`。STEP04A 已验证 3592 条 Visit Canonical、3592 个新业务键、所有其引用的 Person 在同批次 23 人里。实际目标 `cdm.visit_occurrence` 含 17 列且有必填 concept/date/person FK，详情参见日志。

## 进入写库前必须完成

1. 建立 Visit 27-column canonical → 17-column OMOP 规则，确定 `visit_concept_id` 和 `visit_type_concept_id` 对应的**实际有效** vocab，不能猜概念编码；处理 `encounter_class`、开始/结束时间和空值。
2. Person FK 必须通过 `etl.person_id_map(source_system,source_person_id)` 映射，拒绝空/缺失、重复 Encounter 键、逆序/无效日期。
3. 使用已创建的 batch ledger/stage/commit，同批次固定 Manifest、幂等 fingerprint、不允许覆盖历史 Visit；保护 136 Person、5,799 Visit 以及两个 ID map 的历史部分。
4. 先完成 **ROLLBACK** 真实事务演练和只读前后对账，再按**另行明确授权**的 Visit 范围执行 COMMIT 和同批次 replay。先前用户授权明文“不包括 Visit 写入”，因此不得把 STEP04C Person 授权扩展到 Visit。
5. 当前 TASK004 IN PROGRESS，TASK005 ON HOLD。

**这是 STEP04D 的只读准备结果，并非 STEP04D 入库成功。**
