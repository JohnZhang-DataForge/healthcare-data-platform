# TASK004 STEP04F — Fresh Person Source ID 只读 Reconciliation 验收（2026-10-13）

**结论：READONLY SOURCE-ID AUDIT = PASS；动态 PostgreSQL Person Writer = BLOCKED（不得 COMMIT）。** 此结论只针对固定的新批次 `task004-airflow-task004-step03e-38431103586`；不代表 STEP04F Airflow DB 入库、Visit 入库或同批次重放已经验收。

## 真实来源和运行证据

- 上游 Synthea → SeaweedFS Landing → Spark Person/Visit → Reconciliation：[Self-Runner Run 38431103586](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38431103586)，SUCCESS；**Person 23，Visit 3588**。
- 动态 Person Writer：[Run 38432556422](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38432556422)，FAILURE，数据库正确拒绝 `BLOCKED:EXISTING_TARGET_DRIFT`；该失败的后置 SELECT 曾被跳过。
- 只读排查第一次：[Run 38434861465](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38434861465)，FAILURE，`ModuleNotFoundError: task004_cdm_materialization_plan`，失败域为镜像脚本 Python import path。
- 最小修复：Self-Runner Kubernetes Job 环境加 `PYTHONPATH=/opt/task004`，`kubectl wait` 限时从 240s 降到 90s；未修改 CDM 镜像或数据库角色。Self-Runner feature 验证 SHA：`bfad7e9b604006bc6d514bc5afabb9769732df2b`。
- **权威实时验收**：[Self-Runner Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614)，SUCCESS，实际在 `dw-spark` 中对 SeaweedFS S3 和 PostgreSQL 执行只读查询；Workflow step SUCCESS，日志同时包含 `READONLY_PERSON_RECONCILIATION=PASS` 与 `DATABASE_MUTATION=NO`。
- 已合并审计代码：[Self-Runner PR #69](https://github.com/JohnZhang-DataForge/Self-Runner/pull/69)，squash merge SHA `9c2ad3ce33b5c3a877608defbbdcd25118978c15`。上述成功运行针对确切的 **PR feature HEAD**；合并后未触发新的 main 运行（工作流只监听 feature push），不得虚构 post-merge 集群验证。

## S3 Person ↔ PostgreSQL OMOP 只读统计

| 统计项 | 真实 SELECT / 运行输出 |
|---|---:|
| 新批次 Person 源记录 | **23** |
| Source ID 在 `etl.person_id_map` 中已存在（含不同与相同） | **23** |
| 已存在且 `cdm.person` 内容完全一致 | **0** |
| 已存在且 `cdm.person` 内容发生变化 | **23** |
| Source ID 全新（无 mapping） | **0** |
| Mapping 存在但 Person 目标不存在（dangling） | **0** |
| `cdm.person` 只读总行数 | **136** |
| `cdm.visit_occurrence` 只读总行数 | **9391** |
| 失败新批次 `etl.task004_batch_ledger` 残留 | **0** |
| 失败新批次 `etl.task004_batch_stage` 残留 | **0** |
| 失败新批次 `etl.task004_batch_commit` 残留 | **0** |

实现从新批次 Landing manifest 取得 SHA、定位唯一的 Person/Visit Processing Parquet 目录并通过发布过的 CDM 适配器生成 Person OMOP payload。用 `cdm_reader` 和 PostgreSQL `transaction_read_only=on`，对 `etl.person_id_map` / `cdm.person` 进行逐条 SELECT，并使用 Writer 同语义的 `to_jsonb` 完整记录比较；然后统计业务行数和失败批次 ledger/stage/commit。日志只打印汇总数字，不打印患者标识或 PHI。Kubernetes 创建临时 Job/ConfigMap 并在结束时清理；**数据库无业务写入，也未执行 Writer COMMIT**。

## 结论与后续边界

- **已确认的事实**：新批次 23 个 Source ID **全部与现有 Person mapping 重合**，且拟写入的 OMOP Person payload **23 个全部与已有目标不同**。因此 Writer 的 `EXISTING_TARGET_DRIFT` 拦截与数据库只读证据一致，不能绕过。
- **仍是待证实的根因机制**：两批 Synthea 使用相同固定 `seed=20261012` / `clinician_seed=20261012`，而 reference/ingest date 不同，可能导致“ID 相同但内容不同”。本次只读审计证明**重合和内容漂移**，不独立证明 Seed 是唯一成因。
- **下一轮建议（需单独授权）**：审查 Synthea source ID / seed / reference date 和批次隔离契约，设计新独立 Seed 及稳定 ID 策略或显式版本化更正规则；之后再针对新批次执行受控 ROLLBACK 验证，最后才考虑独立授权 Writer COMMIT、完整 Airflow 入库及 idempotent replay。**不得复用冲突 Source ID 覆盖历史数据**。
- TASK004 整体仍 **IN PROGRESS / CDM WRITE BLOCKED**；TASK005 Condition 仍 **ON HOLD**。
