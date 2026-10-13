# Landing S3 Auto Discovery — Airflow 真实集群验收（2026-10-13）

> **当前事实：** 独立 `landing_batch_discovery` 定时 Airflow DAG 已通过 gitSync 真正部署、解除暂停，且**一次手动触发的真实 DagRun + KPO Task = SUCCESS**。DAG 为只读自动扫描，不调用 Synthea、不处理 Spark、不写 PostgreSQL、不领取批次。**15 分钟 cron 已启用；截至本次验证，尚未另行留存“由 cron 自然触发”的 DagRun 证据**。TASK004 总体仍 IN PROGRESS，TASK005 ON HOLD。

## 1. 已合入的功能代码

| 部分 | 实际实现 |
|---|---|
| 定时 DAG | `airflow/dags/landing_batch_discovery.py`，ID `landing_batch_discovery` |
| DAG 任务 | 仅 `scan_ready_manifests`：KubernetesPodOperator |
| 频率 | `*/15 * * * *`、`catchup=False`、`max_active_runs=1`、初次创建 `is_paused_upon_creation=True`，真实验收后已通过 CLI **unpause** |
| 独立镜像 | `ghcr.io/johnzhang-dataforge/healthcare-landing-discovery@sha256:06a5caaf1d62e62fa7f6227de2422690f1c8e4bf7a893c6c239456affce0bfbd`；non-root 10001，`boto3==1.40.40` |
| Airflow KPO | `dw-spark` / worker02，S3 Secret `dw-spark-s3-secret`，只 LIST/GET S3，成功 Pod 自动清理 |
| 真正 S3 验证核心 | `apps/landing_discovery/scan_ready_batches.py`；READY Manifest v1/18 CSV 元数据/完整性 fingerprint；旧格式隔离 |
| KPO runner | `apps/landing_discovery/run_airflow_scan.py`；`/airflow/xcom/return.json` 的限定 25 Batch 预览，附 ready_count、quarantined_count、`processing_authorized=false`、`database_mutation=false` |
| 安全边界 | 无 Synthea、无 Spark、无 PG Credentials、无 S3 PUT，**只是发现 Inventory，未做 Claim/Ledger 或 DB Commit** |
| 原有 DAG | `task004_processing_pipeline` 原样不改，保留历史冻结实现，不是新正式入口 |

**业务代码采用功能语义命名，未来新模块不要使用 task 编号作为主语义名称。**

## 2. 真实 Actions 验证

| 证据 | 链接 | 真实结果 |
|---|---|---|
| Healthcare 镜像发布 | [Image Build Run 38465747656](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38465747656) | SUCCESS；真正 GHCR 发布，固定上面的 sha256 digest，构建前单元测试通过 |
| Self-Runner 第一轮 | [Run 38466141089](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38466141089) | FAIL：测试器引用了 Airflow 3 已删除的 `DAG.schedule_interval`；修正为 `DAG.timetable`。**不是业务 DAG 的解析失败** |
| 真实 DAG 预合并/镜像验收 | **[Run 38466311935](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38466311935)** | **SUCCESS**；13 单元测试 PASS、Airflow 3 Scheduler DagBag `REAL_AIRFLOW_DAGBAG_IMPORT=PASS`、`DAG_SCHEDULED_AND_INITIAL_PAUSED=PASS`；worker02 临时 Job 使用 pinned Image 真读 S3，6 READY、1 legacy quarantine，`DISCOVERY_IMAGE_REAL_S3_RUNTIME=PASS`，无 PG/S3 mutations |
| 真正 Airflow 部署与执行 | **[Run 38466518057](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38466518057)** | **SUCCESS**：`AIRFLOW_GITSYNC_EXACT_SOURCE=PASS`、`AIRFLOW_SCHEDULED_DAG_VISIBLE=PASS`、`AIRFLOW_DAG_IMPORT_ERRORS=NO`、`AIRFLOW_15MIN_SCHEDULE_ENABLED=YES`、`AIRFLOW_MANUAL_DAG_TRIGGER=PASS`、`AIRFLOW_DAG_RUN_STATE=success`、`AIRFLOW_DISCOVERY_TASK_STATE=success`、`GENERATOR_TRIGGER=NO`、`SPARK_TRIGGER=NO`、`DATABASE_MUTATION=NO` |

合并情况：

- Healthcare **[PR #74](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/74)**，Main commit **`c940471da577e21fd22432cff08e4dbd46307e2c`**；此 exact Main SHA 通过 gitSync 文件内容核对与实际 DagRun。
- Self-Runner **[PR #72](https://github.com/JohnZhang-DataForge/Self-Runner/pull/72)**，Main commit **`cdf4eca37f469d93a40a0ee4ec58c21d05add84b`**；premerge/pass 的 feature SHA `15457dd9fa2c6b193e0561148bd058f164d1227a`，postmerge/pass 的 workflow SHA `4bf8cd68dde8094fa2b6d75413aa73bb457deb8c`。

**当前已确认：Airflow 定时发现入口部署且 schedule enabled、实际人工触发整 DAG PASS。** 不得声称新 DAG 已领取并处理 6 个批次；它只是观察列表。也不得把 `is_paused_upon_creation=True` 理解为运行时仍暂停：Live 工作流明确执行了 `unpause` 并记录成功。

## 3. 下一开发阶段：Landing Batch Claim / Processing Ledger

当前 S3 会每 15 分钟重新发现同一组 READY Batch，但**只有 Inventory，不代表需反复处理**。因此下一个独立工程闭环必须先完成：

1. 只读了解现有 `etl.task004_batch_ledger` 与受控消费状态表；决定**新的通用命名**（建议 `landing_batch_ledger` / `claim_ready_batch`）；明确 status + manifest SHA + lease/heartbeat、并发原子 claim。
2. 对同一 `source + batch_id + manifest_sha256`：新批次才能 CLAIM；成功的 SKIP；正在运行的不会重复占有；FAILED 可受控 RETRY；同 batch ID 不同 SHA 必须 BLOCKED；遗留旧版 Manifest 继续 QUARANTINE。
3. 在 DB mutation 单独授权前，先验证只读扫描与 claim 逻辑的离线测试/ROLLBACK；任何新的 `Person/Visit` ETL/PG COMMIT 均属于**下一轮独立开发工作**，不得悄悄扩展。
4. 之后才是新 `Airflow → Spark Person/Visit → Dynamic PG Writer COMMIT → DB Reconciliation → Retry/Replay`，需要源 Person ID 无碰撞的全新可提交批次。
5. 如需更强的“自动”验收，可独立查看 15 分钟 cron **自然触发**的 DagRun 与 XCom 结果；本轮只对真实手动触发的 DagRun 留下最终明确 PASS 证据。

**结论：S3_DISCOVERY_CORE=PASS；AIRFLOW_SCHEDULED_S3_DISCOVERY_DEPLOYED_AND_MANUAL_RUN=PASS；BATCH_CLAIM=NOT_IMPLEMENTED；DYNAMIC_OMOP_COMMIT=NOT_IMPLEMENTED；TASK004=IN_PROGRESS；TASK005=ON_HOLD。**
