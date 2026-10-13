# Healthcare Data Platform — Agent 交接 / 当前唯一执行基线（2026-10-13）

> **CURRENT / 先读本文，禁止使用下面历史文档的旧 NEXT 替代本页。** 截至本轮核实，Healthcare `main=067679104afc5a179fb50215210f290569fce28e`，Self-Runner `main=cdc5958dc30d3b42b18fd96a30272adb90503c2a`（均为本次文档交接**开始时**的基线；合并本 PR 后须重新查询实际 Main SHA）。此文档为**文档交接，不包含业务代码/Kubernetes/数据库更改或新一轮测试**。
>
> **项目状态：TASK004 IN PROGRESS；TASK005 Condition ON HOLD。** 历史固定批次的 PostgreSQL Person/Visit COMMIT 与重复验证完成；新的 Generator 与 Airflow 完全解耦的自动流水线 **尚未全程 COMMIT/重放闭环**。
>
> 原本累积式 14KB 旧 handoff 已保留全文在 [历史归档](../archive/2026-10-13-agent-handoff-refresh/tasks/TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md)，旧版本包含先前排查期间的**过时 NEXT**。本文重新整理当前唯一事实，而非丢弃历史证据。

## 1. 用户最终批准的设计（已在 Main 文档中，**但 Generator 尚未部署**）

权威新架构：[独立 Generator 与 Airflow S3 Consumer v1.0](../architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)；具体 Producer 起步方案：[NEW_ONLY NEXT](TASK-004-INDEPENDENT-GENERATOR-NEW-ONLY-NEXT-v1.0.zh-CN.md)。此设计已于 Healthcare [PR #72](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/72) 合并，后续 Consumer/Writer 的运行进度也不断写入架构文档。**是的，设计已经更新到仓库 Main**。

冻结的不可变协议：

```text
[worker01 / dw-synthea]                      [worker02 / dw-airflow + dw-spark]
Independent Synthea NEW_ONLY Job
     │  LocalPath PVC / /synthea-state
     │  生成请求 + 随机参数本地持久冻结
     │  检验 18 CSV + 校验原始 Source ID
     ▼
SeaweedFS health-landing 不可变批次
    最后 PUT verified manifest.json   ──────► S3 READY Discovery / 每15分钟
                                                    │
                                              PostgreSQL Claim Ledger
                                                    │
                                               Spark Person + Visit
                                                    │
                                           Processing Reconciliation
                                                    │
                                             OMOP Dynamic Writer
                                                    │
                                         DB Reconciliation / COMPLETED
```

- **Generator 与 Airflow 完全解耦**：Airflow **不能**触发 Synthea、传随机 Seed/State/日期/人口；重试只重消费同一个已发布的 Manifest，不能重新生成数据。S3 最后发布不可变 Manifest 才表示 READY。
- **三种不同业务 Job/Pod、代码和镜像**：`NEW_ONLY`、`EXISTING_ONLY`、`MIXED`。不是同一代码入口 `--mode` 三分支。**当前只批准实现 NEW_ONLY；后两种 ON HOLD**。
- NEW_ONLY：worker01、namespace `dw-synthea`、专用物理设备/LocalPath 持久卷（目标 PVC `Retain`、Pod 挂载 `/synthea-state`，不复用 SeaweedFS 卷；实际设备、StorageClass 与 PVC 必须先只读核实）。每次独立生成请求随机**美国合法州**、人数目标 1～100（实际 Person `<=100`）、Seed/Clinician Seed 与参考日期，原子写入持久 `params.json`；重复同一 request ID 不重新随机/改写已发布 S3。
- Synthea v3.3.0 的人口溢出和 18 CSV 对小人口非空约束需要真实测试/versioned Contract；不能悄悄放宽历史合同。生成器不能仅靠随机种子假设不会产生 Source ID 碰撞。
- 旧 `airflow/dags/task004_processing_pipeline.py` 含 `generate_publish`，**冻结为历史入口**，尚不能删除或宣称“新生成器已替换”。新的 `landing_batch_discovery` 是消费者入口。
- 命名规范：新功能采用 `landing_batch_discovery`、`landing_claim`、`omop_writer`、`synthea-new-only` 等**表示功能的名字**，不继续随意新建 `task004_step04x` 业务模块。

## 2. 已完成的真实验收与精确边界

| 层/能力 | 真实状态 | 验收证据 |
|---|---|---|
| 基础设施 / 历史固定批次 OMOP Person/Visit | **PASS**：历史已入库且固定批次 replay 过；最近读回 Person=136、Visit=9391 | 历史 `TASK-004-STEP04E-*`、`STEP04F-*` Closeout；务必区分冻结历史与新动态 |
| S3 READY Discovery | **PASS**：独立镜像、真实 S3 6 READY + 1 旧 Manifest quarantine、Airflow 每15分钟 Schedule 已启用；实际手工 DagRun PASS，**自然 Cron 产生 DagRun 的完整证据未单独保留** | [Run 38466518057](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38466518057) |
| PG `etl.landing_batch_ledger` / atomic Claim | **核心 PASS**：新增表、`landing_claim_worker` 受限账号与 K8s Secret 已持久创建；状态机 real PG `ROLLBACK` 测试 PASS，模拟 Probe 零持久行；过期 Lease 不自动抢占 | [Run 38468961485](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468961485) |
| Discovery → Claim Guard Airflow 接线 | **PASS（只读决策）**：2 个 KPO 的真 DagRun PASS、历史批次排除；默认 `CLAIM_ENABLE=NO`、空 `CLAIM_ALLOWLIST`，**没自动持久 CLAIM 新 Batch** | [Run 38471287896](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471287896) |
| S3 → Airflow → Spark Person/Visit → Processing Reconcile | **PASS（手工明确指定历史 READY 批次）**：真实 Airflow 8 个任务 success，Spark 新 Processing 运行，DB 未写；**常规15分钟定时不会自动触发 Spark** | [Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452)；[Spark Live Closeout](LANDING-SPARK-PROCESSING-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) |
| OMOP Writer NEW_ONLY Pre-COMMIT 安全只读审查 | **PASS**：人工合成候选及历史冲突负例、真 `cdm_reader`、9 unit tests，**不是对 S3 新批次实际授权**；Reader 新获 Claim Ledger SELECT | [Run 38478501009](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38478501009)；[Precommit Closeout](OMOP-WRITER-PRECOMMIT-SAFETY-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) |
| 真实 S3 Parquet → OMOP Writer → PG drift gate | **真实负例 PASS**：读取 Person=23 / Visit=3588，连接真实 writer，`BLOCKED:EXISTING_TARGET_DRIFT` 正确中止，业务及 Ledger/Stage/Commit 零变更；**Writer 的完整成功 ROLLBACK 正例 = NO** | [Run 38479261229](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479261229) 真实 S3 inventory；[Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382) 真实预期拦截；[详细结果](OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md) |
| 新 Generator NEW_ONLY 的独立真实批次 | **DESIGN ONLY / 尚无部署与真实 READY 输出验收** | [Generator 规划](TASK-004-INDEPENDENT-GENERATOR-NEW-ONLY-NEXT-v1.0.zh-CN.md) |
| 真实新 Batch Claim→自动 Spark→动态 PG COMMIT→DB Reconciliation→幂等 replay | **NOT DONE**。不能用旧历史批次测试新增 COMMIT | 必须完成下述后续闭环 |

**现有事实基线**：PostgreSQL `cdm.person=136`、`cdm.visit_occurrence=9391`、新 `etl.landing_batch_ledger=0`（截至 [Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382)）。Agent 开始新 Session 时仍应独立 SELECT 查询，不能假设永远不变。

## 3. 已找到的真实阻塞：历史 Source ID 复用，不能关闭 Drift Guard

历史旧已入库 Batch：`task004-airflow-task004-step03e-38324111846`，23 Person / 3592 Visit 处理，历史固定 COMMIT 基线包含在 Person=136、Visit=9391 中。

2026-10-13 问题 Batch：`task004-airflow-task004-step03e-38431103586`，**真实 S3 Processing Person=23、Visit=3588**，但 23/23 个 Person Source ID 与既有 Patient 映射重合，出生日期受 reference_date 跨日变化影响 **23/23 +1 天**；同 Seed + Clinician Seed=`20261012`，引用日期变动。证据：[根因排查](TASK-004-STEP04F-SYNTHEA-SEED-REFERENCE-DATE-ROOTCAUSE-READONLY-CLOSEOUT.md) / [Run 38447127571](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38447127571)。

- 新错位 batch Manifest SHA256：`e6dc34dd45357a43561f5e970185c5e44da4368647440a78363f43b1a762bc8a`。
- Writer/Source 真实业务代码成功读到 Parquet，但这个批次在真实 PG `BLOCKED:EXISTING_TARGET_DRIFT`，所以 **Workflow SUCCESS（预期负例）!= Writer Job SUCCESS/ROLLBACK 正例/COMMIT**。
- 不能通过 `allow_commit=True`、SQL 绕过条件、复用旧 Batch 新名字、手动 UPDATE 出生日期、直接重命名 Manifest 来规避。**必须取得真实全新的、无源身份碰撞的 S3 READY Batch**。

## 4. 已有代码入口（不要重复从头造轮子）

```text
Healthcare (business source of truth)
  airflow/dags/landing_batch_discovery.py       # 每15分钟 Discovery + Claim Guard + 手工历史 Spark 分支
  airflow/dags/landing_spark_processing.py      # MANUAL + 精确 S3 Manifest/旧 Ledger 决策门槛
  apps/landing_discovery/{scan_ready_batches,run_airflow_scan}.py
  apps/landing_claim/{claim_discovered_inventory,batch_ledger}.py
  sql/landing_claim/create_landing_batch_ledger.sql
  apps/omop_writer/precommit_gate.py            # 严格 read-only 校验
  apps/omop_writer/build_s3_rollback_plan.py    # 显式不可变 S3 Processing URI → NO COMMIT Plan
  apps/task004/cdm_runtime_cli.py               # 老固定镜像的 --validate-source / --rollback-from-s3，无 --commit
  airflow/dags/task004_cdm_dynamic_{source,adapters,pg_writer}.py
  airflow/dags/task004_cdm_postgres_rollback_executor.py
  airflow/dags/task004_cdm_materialization_plan.py
  tests/landing_discovery/ tests/landing_claim/ tests/omop_writer/

Self-Runner (operations and real evidence)
  .github/workflows/landing-spark-processing-acceptance.yml   # 手工批准再回放旧批次
  .github/workflows/landing-batch-claim-rollback.yml
  .github/workflows/omop-writer-precommit-readonly.yml
  .github/workflows/omop-s3-processing-inventory.yml
  .github/workflows/omop-s3-writer-real-rollback.yml
```

- Node：`worker01` SeaweedFS + **未来**独立 Synthea NEW_ONLY；`worker02` Airflow/Spark、CDM Runtime；`worker03` PostgreSQL。实际 nodeSelector、namespace、Secret 使用前按当前运行时查证。
- DB roles：`cdm_reader`（SELECT）、`cdm_writer`（受控旧 Writer）、`landing_claim_worker`（仅新 Ledger DML + 旧 Legacy Ledger SELECT）；按职责用已存在的 K8s Secret，不输出任何密码或 Patient PHI。
- 当前测试用固定 CDM Runtime 镜像 `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e`；它**不支持 COMMIT CLI**。不随意更换已经验证的 digest。
- 兼容难点：旧 `task004_cdm_materialization_plan.plan()` / Writer Contract 约束 Batch ID 前缀 `task004-airflow-`。新功能名与独立 Generator 产生的 batch_id 要通过**显式版本化 Contract 扩展**解决，不得伪造旧前缀骗过验证。
- Legacy Ledger 的字段语义与新 Claim Ledger 不完全等同；新批次 Commit 必须在同事务里验证 `lease_owner` + 非过期租约 + Source ID 冲突，不能凭只读预检时间点自动允许写库。
- Airflow 当前 Discovery XCom 预览有 **25 个候选上限**；超过会 Fail Closed，不能说已实现不限批次数量的生产可靠队列/分页。
- 真双 Worker 竞争压测、Lease heartbeat/恢复、未知 COMMIT 结果查账与原子 COMPLETED **尚未**闭环。

## 5. 后续有界开发路线（避免误说第三层已经完成）

**当前最直接的阻塞是“缺少真实 NEW_ONLY 无冲突源数据”**。因为用户目前正在推进第三层 Writer，允许把一轮限定在 Writer Contract 的只读/静态适配预检，但真正成功的端到端 ROLLBACK/COMMIT 都需要新源。推荐按以下顺序，**每次只完成一个有开发+测试+证据的有效闭环**：

1. **NEXT-A：NEW_ONLY 只读基础设施/Contract 预检**。先检查 worker01 独立设备/local-path PV/PVC（专用 Retain）、namespace、18 CSV/人口上限/Synthea v3.3.0 CLI、源身份规划，输出正式 preflight 文档。**本步不修改磁盘、不创建 Pod/PVC、不触发数据生成**。同时只读审视 Writer Plan 对 Batch ID 的旧前缀强耦合，给出 versioned 新合同改动边界。
2. **NEXT-B：真正独立 Synthea NEW_ONLY**：专用业务源码+镜像+Job+持久化 Request Params，三种 Pod 仅实现 NEW_ONLY，worker01 Job 产出一批真实无冲突 S3 READY/18 CSV Manifest；必须单独核准才实际部署创建资源。**Airflow 完全不参与 Generator。**
3. **NEXT-C：新批次经过受控 Spark→真实 S3 Person/Visit Parquet→全量 NEW_ONLY 源键审查→实际 writer Person+Visit ROLLBACK 成功正例**；PG 独立 readback 后始终 Person/Visit/Ledger/Mapping 不变。保留已通过的冲突 Batch 负例。
4. **NEXT-D：事务级 Writer**：建立新独立 digest-pinned Writer Runtime、Active Claim Token Fencing、单批状态机/unknown-COMMIT 恢复；先测试失败/重试/锁与并发，再对清洁批次进行**明确授权的真实 COMMIT**。
5. **NEXT-E：最终独立 DB Reconciliation / COMPLETED / 同批重放不重复**，接入 Airflow 自动 Claim→Spark→Writer / Cron，移除 25 上限或安全分页；之后才考虑关闭历史 `task004_processing_pipeline`，并最终宣布 TASK004 完成。TASK005 此前一律 ON HOLD。

**验收原则：** 禁止把 “K8s Job PASS / 预期 BLOCKED PASS / 成功 ROLLBACK / 真 COMMIT / 最终 COMPLETED” 混为一谈。每轮列明实际所见与未完成内容、提供准确 Run ID。

## 6. 新 Agent 操作规则

- 新 Session 先读 `docs/README.md`、[本交接](TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md)、[当前状态](TASK-STATUS.md)、[正式开发流程](../development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)、[新架构](../architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)、[最近 Writer 真 S3 验收](OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md)。
- **先查询 GitHub main HEAD + PR/文件真实状态**，以 Healthcare 业务源码为 canonical；使用 connected GitHub 与 Self-Runner 的 GitHub Actions/Kubernetes ARC 证据，不让用户手工执行大 Shell。Feature Branch → PR → 按准确 SHA 测试 → 真实回读 → Merge → 更新 Current docs。
- 按用户偏好：**有效的小闭环**（至少实现、执行、验收），不是每个微小文件都单独开一轮。连续失败最多 3 次停止排查；避免耗尽上下文。新业务模块以功能命名；旧冻结源码/数据未经必要依据不改。
- 文档生命周期遵守 [归档规范](../development/DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md)。历史 Closeout 保留真实证据，不要给历史文字加虚假的新结论；新状态索引指向最新权威文档。
- **本 handoff 更新只涉及 Git 文档**，不触发新的 Airflow、Spark、Synthea、DB DML、PVC、Secret 变更。

**一句话交接：新架构已正式写入 Main；消费侧 Discovery/Claim Guard 和手工历史 Spark 通过真实验收；OMOP Writer 已连接真实 S3，但只有“历史 Source-ID 冲突被安全拒绝”的成功证据；必须先取得真正独立 NEW_ONLY、无冲突的 READY Batch，才能继续 Writer 成功 ROLLBACK→真实 COMMIT→DB Reconciliation/自动消费闭环。**
