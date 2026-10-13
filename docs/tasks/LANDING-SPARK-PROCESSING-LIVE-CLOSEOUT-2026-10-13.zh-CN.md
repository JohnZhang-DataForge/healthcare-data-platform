# Landing → Spark Person / Visit / Reconciliation — 真实 Airflow 验收（2026-10-13）

> **最终实测：PASS（受控历史批次 Processing-only 重放）。** 独立的 `landing_batch_discovery` DAG 已真正完成 **S3 READY Manifest 自动发现 → PostgreSQL Claim Guard 只读决策 → 手动明确指定既有历史 Batch → Spark Person/Visit 并行运行 → Processing Reconciliation → 最终批次 lineage 验证**。真正 Airflow 3 Scheduler GitSync / DagBag 与 **8 个 TaskInstance 均 SUCCESS**，不是只提交脚本。**没有**触发 Generator、没有把真实新批次 Claim 写入 PostgreSQL、没有 OMOP CDM COMMIT。正式每 15 分钟的自动扫描仍只经过前半程；Spark 仅由**手工指定且按历史 Ledger 通过的批次**开启。TASK004 总体 IN PROGRESS，TASK005 ON HOLD。

## 1. 当前完整架构与真实运行边界

```text
SeaweedFS READY Manifest
          │
          ▼
Airflow landing_batch_discovery（*/15 分钟，现仍启用）
          │
          ▼
scan_ready_manifests（真实 S3 LIST/GET + SHA、18 CSV 合同）
          │ XCom
          ▼
evaluate_batch_claims（真实 PostgreSQL 历史、新 Ledger 查询）
          │ Claim 开关始终关闭：CLAIM_ENABLE=NO
          ▼
authorize_processing_replay
          │
          ├─ 定时自动 DagRun / 无 processing_only 参数 → 返回 None，跳过 Spark
          │
          └─ 手工 DagRun / processing_only=true /
             batch_id、Manifest URI、SHA256 与 READY 清单精确匹配 /
             Ledger 判定 SKIP_LEGACY_BATCH
                        │
                        ▼
                processing_only_gate
                        │
                 ┌──────┴──────┐
                 ▼             ▼
             spark_patient  spark_encounter
                 └──────┬──────┘
                        ▼
                 spark_reconcile
                        ▼
              verify_spark_processing
                        │
               无 OMOP 业务写入
```

新增代码 `airflow/dags/landing_spark_processing.py`，原 `airflow/dags/landing_batch_discovery.py` 追加了 6 个新任务；所有新增任务按功能命名。暂复用**冻结且已实际验证**的历史 Spark 控制镜像 `healthcare-data-platform-task004-runtime@sha256:8d55a150e7fcd8ea9a1ed8e8c2c64d09bf4d19687822c0ec84857fdf429c05a7`，不重新调用其中的 `generate-publish`。原 `task004_processing_pipeline` DAG **未修改**。

数据合同：使用现有 `apps/landing_discovery/scan_ready_batches.py` 中 VERIFIED S3 Manifest，且 Claim Guard 明确分类为旧 ledger 历史 Batch，防止把已经入库的患者再次当作新 Person 处理。Spark 为新的 processing run_id 生成新的 S3 Processing 输出；原 S3 Landing payload 保持不变。Person / Visit 的 SparkApplication 都由 KPO 触发，结果 readback PASS；后续 Spark reconciliation 和处理 lineage validation 检查相同 batch_id、源 Manifest SHA 与 Processing URI。**这证明老批次的 Spark 消费复用，不证明新的未入库批次已被生产自动 Claim 或写库。**

受控选中的**真实历史批次**：

```text
batch_id = task004-airflow-task004-step03e-38324111846
manifest_sha256 = ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1
manifest_uri = s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-12/batch_id=task004-airflow-task004-step03e-38324111846/manifest.json
```

在 [Self-Runner 历史 Manifest 预检 Run 38474841544](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38474841544) 中真实查询 S3：6 READY、该历史批次 READY & SHA=PASS、18 CSV 合同=PASS；只读查询 `etl.task004_batch_ledger` 同一批次存在，`etl.landing_batch_ledger` 初始 0 行，OMOP Person 136 / Visit 9391。

## 2. 真实开发、测试与修复证据（3 次 live 验收边界）

| 阶段 | 证据 | 事实 |
|---|---|---|
| 初始 Spark 接线源码 | [Healthcare PR #79](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/79)，Main `b03f211cbd2f0d7c01ea903fd42dcac74ebd8829` | 添加受控 Manual Spark selector/gate / 三个 Spark KPO / 最终 Processing 校验及保护测试；**已合并** |
| 初次真实 Airflow DagBag | [Self-Runner Run 38474601823](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38474601823) | FAIL：临时测试目录漏拷贝原已有 `task004_cdm_preflight_contract`；只修测试器，不更改业务代码 |
| 修正后的 Airflow 3 预合并解析 | [Self-Runner Run 38474702379](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38474702379) | **SUCCESS**；22 个 Discovery 测试与真实临时 DagBag 解析，手工调用 Spark 门槛在 DAG 中存在 |
| 真 S3 和历史 Ledger 检查 | [Self-Runner Run 38474841544](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38474841544) | **SUCCESS**：实际 batch_id、Manifest SHA 与历史已入库 Ledger 记录核对成功 |
| **Live #1** — Main 导入路径 | [Self-Runner Run 38475069069](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38475069069) | **FAIL**：Airflow GitSync 文件 hash 已匹配，但 Airflow 3 解析新 DAG 时找不到同一 DAG 目录里的 `landing_spark_processing`；**Spark 未启动、数据库未写** |
| 模块解析修复 | [Healthcare PR #80](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/80) Main `3252e3fbdb5b67c70bb43deca50d6aa5f29ebe00`；[Self-Runner Run 38475284174](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38475284174) | 在 DAG 文件中显式增加 GitSync 所在同级目录到 `sys.path`；以**不手动设置 PYTHONPATH** 的真实 Airflow 3 DagBag 验证 `LANDING_SPARK_AIRFLOW3_GITSYNC_IMPORT_FIXED=PASS` |
| **Live #2** — 手工参数类型 | [Self-Runner Run 38475541025](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38475541025) | 实际手工 DagRun=success，但 Spark 三任务被安全 ShortCircuit **skipped**；原因：`dag_run.conf | tojson` 传入 JSON 字符串，而 selector 要求 Python dict。**未触发 Spark，没有 DB 变更**；workflow 因检测到被跳过而 FAIL |
| 手工 JSON 参数修复 | [Healthcare PR #81](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/81)，Main `95ff69519efefbb7cf5a848ce994fd2a653c4ab5`；[Self-Runner Unit Run 38475981601](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38475981601) | 对参数为字符串时先 `json.loads`，对非法 JSON 拒绝处理；24 个 Discovery 测试 + 20 Claim 测试 SUCCESS |
| **Live #3：最终真正 Spark 消费** | **[Self-Runner Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452)** | **SUCCESS**：Main exact GitSync / Scheduler DagBag PASS；手工 DAG Run 成功，8 个 TaskInstance 包括 Spark Person/Visit/Reconcile 和最终验证均 SUCCESS；PG 前后 Person=136、Visit=9391、新 Claim Ledger=0，不涉及 OMOP 写入 |

最终正式 live Run `38476079452` 的 **真实输出**（不是 CI 脚本里的打印语句）：

```text
HISTORIC_SPARK_INPUT_DB_PREFLIGHT=PASS
LANDING_SPARK_GITSYNC_EXACT_MAIN=PASS
LANDING_SPARK_DEPLOYED_DAGBAG=PASS
LANDING_SPARK_MANUAL_REPLAY_TRIGGERED=PASS
LANDING_SPARK_REAL_DAGRUN_STATE=success
TASK_SCAN_READY_MANIFESTS=success
TASK_EVALUATE_BATCH_CLAIMS=success
TASK_AUTHORIZE_PROCESSING_REPLAY=success
TASK_PROCESSING_ONLY_GATE=success
TASK_SPARK_PATIENT=success
TASK_SPARK_ENCOUNTER=success
TASK_SPARK_RECONCILE=success
TASK_VERIFY_SPARK_PROCESSING=success
LANDING_SPARK_PERSON_VISIT_RECONCILIATION=PASS
PERSON_ROWS=136
VISIT_ROWS=9391
CLAIM_ROWS=0
LANDING_SPARK_NO_OMOP_OR_CLAIM_MUTATION=PASS
LANDING_SPARK_CONSUMER_LIVE=PASS
```

注意：以上证明 Spark 输出由控制运行脚本检查、Processing readback 通过，且二者由最终 Python 验证完成同批 lineage；CI 日志未单独打印本轮 Person/Visit XCom 具体行数，因此**不应把历史基线的 Person 23 / Visit 3592 当作此轮新测出的数值**。若后续需要精确行数，可在 Airflow 本次 DagRun XCom 做只读取证；这不影响已通过的控制链验收。

## 3. 当前成功范围与未完成项目

- **完成：** S3 Discovery Core、真实 Airflow 每 15 分钟发现、Claim Guard 旧批次排除、手动指定的历史 S3 READY Batch 的 Person/Visit Spark Processing、Spark Reconciliation/Processing lineage。Generator/Airflow 独立，无 Synthea 调用。
- **受控禁用：** 真正 `CLAIM_ENABLE` 仍 `NO`、`CLAIM_ALLOWLIST` 为空，防止新 Batch 在没有 CDM Writer / 完成状态管理时被过早领取；不能误说已实现生产新增 Batch 自动领取。正常定时调度源代码经自动/手工门槛测试会跳过 Spark，但**本次真实 live 的成功路径是带 processing_only 明确参数的手工 DagRun**，不要把它表述成定时自动 Spark。
- **数据安全：** 本轮 Person / Visit / Claim Ledger 未写入（136 / 9391 / 0 前后不变）；Spark 的 **Processing S3** 有新的 run_id 数据输出，不是全系统“零存储变更”。
- **待开发：** 解决现有 XCom preview 最多 25 批次时的 Fail Closed / 分页完整队列；对新批次执行历史 Source ID 碰撞检查、受控真正 Claim、Lease 心跳/异常恢复、全自动 Spark、Dynamic PostgreSQL Writer COMMIT、DB Readback Reconciliation 和 Replay。后两个 Generator 模式 EXISTING/MIXED 仍 ON HOLD，NEW_ONLY 独立设计待实施。
- **下一步**：先在 Consumer 侧建立**新数据 Batch 的安全受控激活**（在真实新 batch 和 DB Writer 完成前不可打开正式 Claim），同时单独推进 Dynamic Writer COMMIT 安全门槛。此项需要有**真实无历史患者 ID 碰撞的 NEW_ONLY 输入批次**；旧已入库批次可以继续只读/Processing replay，但不能强行新增写入。

**验收状态：LANDING_SPARK_PROCESSING_MANUAL_REPLAY=PASS；AUTOMATIC_NEW_BATCH_CLAIM=NOT_ENABLED；AUTO_SPARK_NEW_BATCH=NOT_VERIFIED；DYNAMIC_OMOP_COMMIT=NOT_IMPLEMENTED；TASK004 IN PROGRESS；TASK005 ON HOLD。**
