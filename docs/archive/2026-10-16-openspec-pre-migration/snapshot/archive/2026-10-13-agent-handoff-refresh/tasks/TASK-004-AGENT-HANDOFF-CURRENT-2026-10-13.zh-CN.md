# TASK004 Agent 交接与唯一 NEXT — 2026-10-13

> **2026-10-13 第三层最新交接：先读 [OMOP Writer Real S3→PG 预期冲突阻断](OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md)。** 实际 [Run 38479261229](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479261229) 读取并精确定位旧/新历史批次的真实 Parquet URI；[Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382) 真 S3 Source 验证 Person=23/Visit=3588、固定 digest CDM Runtime 真 PostgreSQL Writer 命中 `BLOCKED:EXISTING_TARGET_DRIFT`（已证实 23/23 源 ID 冲突），独立数据库业务/Ledger/Stage/Commit 都没有改变。此 Run 的 SUCCESS 仅是负例拦截，**没有正向成功 ROLLBACK、更没有 COMMIT**。已新增功能命名 Plan Builder `apps/omop_writer/build_s3_rollback_plan.py` 和测试。NEXT 应与独立 NEW_ONLY Generator 协调取得无冲突新 Batch、解决 legacy Writer Plan `task004-airflow-` ID 前缀、真实 Person→Visit ROLLBACK 正例，再处理事务内 Claim Token Fencing、Writer/DB Readback/幂等 COMMIT；严禁绕过 Drift Guard。保留现有正常 Airflow 每15分钟只发现/Guard、手工历史 Spark，TASK004 仍 IN PROGRESS、TASK005 ON HOLD。


> **2026-10-13 第三层当前接力：必须先读 [OMOP Writer Precommit Safety Live Closeout](OMOP-WRITER-PRECOMMIT-SAFETY-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。** 新功能名 `apps/omop_writer/precommit_gate.py` 已有 NEW_ONLY 对 Person+Visit 计划/行指纹/源 Source ID 冲突、旧 Ledger、实时 Claim 状态的只读检查；[Run 38478501009](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38478501009) 真实 worker02 + PG `cdm_reader` 9 单元+实际阻断 PASS，Reader 新增 Claim Ledger SELECT，Person=136/Visit=9391/Landing Ledger=0 无业务变更。**真实测试用构造 plan/rows，未读取真实新 S3 Processing；未授权/未执行任何动态 COMMIT；新 Claim 保持 OFF**。CURRENT NEXT：受控从 immutable S3 Manifest/Parquet 建立真 Source Writer ROLLBACK、独立 image、事务内 Claim owner fencing、最终 DB Reconciliation；不能把上述人工正例当可提交 Batch。保留已完成的 S3 Discovery/Claim Guard/历史手动 Spark，Generator 与 Airflow 解耦，别重做已有层。TASK004 IN PROGRESS / TASK005 ON HOLD。\n\n
> **2026-10-13 当前接力最优先先读 [Landing Spark LIVE Closeout](LANDING-SPARK-PROCESSING-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。** 已在真正 Airflow 3 的 `landing_batch_discovery` DAG 中串联 S3 manifest 发现、PG Claim Guard 与**手工可控历史批次** Spark Patient/Visit/Reconciliation。最后 [Self-Runner Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452) 真 DagRun 8 个 TaskInstance SUCCESS；独立 PG 只读回查 Person=136/Visit=9391/Claim Ledger=0，Generator 不参与。开始两次 Live 未通过分别为 Airflow GitSync helper 路径错误（[#80](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/80) 已修）和 Jinja 手工 conf 是 JSON 字符串（[#81](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/81) 已修），第三轮 PASS。**绝不把此结果标为已自动领取/自动跑新 S3 Batch，CLAIM_ENABLE=NO，Spark 必须手工历史 Batch+精确 SHA opt-in，Dynamic Writer COMMIT 和真正 DB Reconciliation 尚未完成**。旧 DAG `task004_processing_pipeline` 冻结不动，新业务代码按功能命名。CURRENT NEXT 为真实新 Batch 的安全领用/完整队列与 Source-ID 防撞→受控 Spark 消费→动态 PG Writer COMMIT/Reconciliation/幂等恢复；后两种 Generator 模式仍 ON HOLD。TASK004 IN PROGRESS / TASK005 ON HOLD。\n\n
> **2026-10-13 新 Agent 最优先接力：** 请先读 [真实 Landing Discovery→Claim Live Closeout](LANDING-DISCOVERY-TO-CLAIM-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)。当前 Main 已包含功能名 `landing_batch_discovery` DAG **两 KPO 串联**：S3 manifest inventory XCom → `evaluate_batch_claims`（查询旧/新 PostgreSQL Ledger 并历史排除）。实际 [Self-Runner Run 38471287896](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471287896) 两 Task **success**、Main GitSync exact SHA、真实 PG 0 Claim rows、CDM Person=136/Visit=9391 不变；[`38470907298`](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38470907298) 通过真实历史批次排除和受限权限。由于尚无下游 Spark/Writer，`CLAIM_ENABLE=NO` 且 allowlist 为空，不能误称**已 COMMIT 真实 Claim 或完成自动 ETL**。NEXT = 受控队列/全量批次、历史 Source ID 碰撞安全门槛、Spark Person/Visit 消费、动态 DB Writer / Reconciliation、可恢复租约；保持 Generator/Airflow 解耦、功能语义命名、小型闭环及最多3次测试。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 最新 Agent 交接：Batch Claim 核心已实际完成，下一环是 Consumer 接线。** [Ledger / Claim Real PG ROLLBACK Closeout](LANDING-BATCH-CLAIM-ROLLBACK-CLOSEOUT-2026-10-13.zh-CN.md)；新 `sql/landing_claim/create_landing_batch_ledger.sql` 的 **etl.landing_batch_ledger 已 COMMIT**，专用 PostgreSQL `landing_claim_worker` + `dw-spark/landing-claim-db` Secret 已配置；`apps/landing_claim/batch_ledger.py` 事务状态机在 [Run 38468961485](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468961485) 真实 worker02/PostgreSQL 模拟批次中通过完全 ROLLBACK 与独立读取；12 Unit Tests PASS，0 探针行、CDM 无数据变更。**Airflow `landing_batch_discovery` 仍每 15 分钟只读扫描，不调用 Claim、Spark、OMOP。** 当前 NEXT 是安全连接 Discovery→Claim（不得误领原先已入库 6 个历史批次），然后批次消费/动态 Writer/独立 DB 对账。不要重复开发 Claim 基础表，不要把 ROLLBACK 测试说成生产真实 Batch COMMIT；自然 Cron 和真实并发验证仍待补。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 最新接力锚点：S3 Discovery 不是待开发——它已经跑进了真实 Airflow！** 详细 [Landing Discovery Airflow Live Closeout](LANDING-BATCH-DISCOVERY-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)：`landing_batch_discovery`（功能命名）部署到 gitSync、每15分钟 Schedule 已 unpause、真实 [Run 38466518057](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38466518057) 的 Airflow DagRun/唯一 KPO Task success；13 unit tests，独立 GHCR `healthcare-landing-discovery@sha256:06a5caaf1d62e62fa7f6227de2422690f1c8e4bf7a893c6c239456affce0bfbd` 真 S3 读取 6 valid + 1 quarantine；无 Generator、Spark、Postgres 数据改动。**下一步不是再次从头设计 S3 Discovery，而是独立 Batch Claim/Ledger（原子领取/跳过/重试），此后才接 Spark 和动态 PG Writer COMMIT。** 此 DAG 只扫描 Inventory，不允许误当作 ETL 闭环完成；此前 NEW_ONLY 优先级与 STEP04F 只读排查 NEXT 均过时。TASK004 IN PROGRESS，TASK005 ON HOLD。


> **2026-10-13 最新 Agent 交接：消费端 S3 READY 探测核心已完成真实 K8s 验证。** [Landing Discovery Checkpoint](LANDING-BATCH-DISCOVERY-READONLY-CHECKPOINT-2026-10-13.zh-CN.md) / [Run 38460137577](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38460137577)：源码 `apps/landing_discovery/scan_ready_batches.py`、8 单测、6 valid READY + 1 legacy Manifest quarantine；真实 S3 只读，**没有 Airflow DAG、Writer COMMIT、PG 变更**。用户优先级现调整为**先开发新的功能命名 `landing_batch_discovery` 定时 DAG → 再做自动消费/动态 PostgreSQL 事务与恢复**；之前标题下 NEW_ONLY（Producer）优先顺序属于过时记录，仍保持设计但不在当前 NEXT。新消费 DAG 禁止调用 Generator；现有 `task004_processing_pipeline` 历史冻结，不动。TASK004 IN PROGRESS，TASK005 ON HOLD。


> **2026-10-13 用户最新决策/新 Agent 先读：** [独立 Producer / S3-Consumer 架构设计](../architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md) → [NEW_ONLY 唯一实施 NEXT](TASK-004-INDEPENDENT-GENERATOR-NEW-ONLY-NEXT-v1.0.zh-CN.md)。**Generator 与 Airflow 完全解耦**：Generator 自主随机并推 S3（verified immutable Manifest 为 READY），Airflow 只定时发现批次并调用 Spark/CDM；禁止 Airflow 传 Seed/州/人口，禁止把重试等同于重新生成。用户坚持 **三套独立 Kubernetes Job/Pod、镜像与业务代码**，不是一个入口用 mode 切换；**先开发 NEW_ONLY**，EXISTING_ONLY/MIXED ON HOLD。NEW_ONLY 实际患者 <=100、目标随机 1～100/随机合法州、固定生成时间；worker01 `dw-synthea` 专用 LocalPath PVC/独立磁盘做任务恢复，S3 仍是已发布数据的权威。**NEXT 先只读审计存储/Contract，再分轮实现 NEW_ONLY。** 本次为文档修改、没有执行新 Synthea Job / PVC / Consumer DAG / Writer COMMIT；原 STEP03E DAG 仍使用 `generate_publish`，只作为历史冻结基线。源 ID 23/23 全重合/出生日期 +1 天的根因已由 [Run 38447127571](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38447127571) PASS；下方老手递 NEXT（修 import 与查 seed）均已完成或过时。TASK004 IN PROGRESS、TASK005 ON HOLD。


> **2026-10-13 新的权威增量交接（覆盖本文历史 NEXT）：Seed/Reference Date 冲突已定位。** [根因只读验收](TASK-004-STEP04F-SYNTHEA-SEED-REFERENCE-DATE-ROOTCAUSE-READONLY-CLOSEOUT.md)：同 Seed+Clinician Seed `20261012`，唯一不同源生成参数为 `reference_date=20261012` vs `20261013`。两批各有 23 patients，ID 重合 23、原始出生日期 **23/23 正好 +1 天**，对应已存在 OMOP Person 的 `birth_datetime/day_of_birth` 各 23 漂移；没有新 Person ID。Self-Runner [Run 38447127571](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38447127571) SUCCESS，exact feature SHA `9c0d6e538f43364845876e404cdf72fd42fbee92`，Self-Runner [PR #70](https://github.com/JohnZhang-DataForge/Self-Runner/pull/70) merged `f3f1a65fd9e30bd549ce352fb429031627827404`。**最新 NEXT 不是排查，而是后续单独阶段设计跨批次 Seed/Source ID 隔离、同批次 Reference Date 固定及重放策略；没有授权任何新 Synthea、Writer ROLLBACK/COMMIT 或 TASK005。**本文下方旧第3/5节是已完成的历史工作。


> **2026-10-13 READONLY AUDIT 已收尾，此前“唯一 NEXT = 修复 PYTHONPATH”已过时。** 新增[只读 Source ID 审计 Closeout](TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md)：[Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614) **SUCCESS**，23/23 Source ID 在 mapping 中已存在；与目标 Person 完全一致 0、内容不同 23、全新 0、dangling 0；失败批次 ledger/stage/commit 0/0/0；CDM Person/Visit 总数 136/9391；数据库无业务写入。Self-Runner [PR #69](https://github.com/JohnZhang-DataForge/Self-Runner/pull/69) merged SHA `9c2ad3ce33b5c3a877608defbbdcd25118978c15`。**下一轮只讨论并验证 Synthea Seed / Reference Date / Source ID 的批次隔离设计**（同 Seed 导致漂移仅为原因假设）；需另行授权任何新批次、ROLLBACK、Writer COMMIT。**本文件下方第3/5节仍为交接时历史断点，不是当前 NEXT。TASK004 IN PROGRESS；TASK005 ON HOLD。**


> **CURRENT / 权威增量交接。新 Agent 从 `docs/README.md` 进入后首先阅读本文件；历史 TASK-STATUS / Plan / Closeout 中的旧 NEXT（例如 STEP04A / STEP04B）均被本文件的当前进度取代。不要从头重新实施 STEP04A–04F。**

## 1. 用户目标与开发方法

真正的 TASK004 完成标准：一次 Airflow DAG 自动触发 Synthea → Landing → Spark Person/Visit → 共同批次 PostgreSQL OMOP Person + Visit → DB reconciliation，并对同一 batch/manifest 的重新执行保证逻辑幂等、恢复验证。TASK005 Condition **ON HOLD**。

**开发约束**：以 GitHub 为代码/文档唯一来源；Healthcare feature 分支、Self-Runner Actions/ARC 验证真实结果、PR → protected main；每轮一个有意义的代码+实测+证据闭环，≤3 次失败后停止调查，不允许以 Workflow 被预期拒绝视为业务成功。无需让用户本地手工执行 shell；不擅自修改冻结历史数据，不直接推 main。每轮准确区分源码测试/容器构建/集群测试/DB COMMIT。

## 2. 已经完成并验证，不要重做

- STEP04C/D/E **固定历史批次** PostgreSQL Person/Visit COMMIT+重放+联合核对通过。历史 `task004-airflow-task004-step03e-38324111846`（Person 23，Visit 3592）；CDM 既有总量 **Person=136、Visit=9391**；该批次 ledger 为旧合同版本，不能将它当作新的 dynamic-v1 批次重写。
- STEP04F 动态 Plan、S3 Manifest SHA + 一份 Parquet 检查、Person/Visit canonical→OMOP Adapter、PG SQL Builder（默认 ROLLBACK）、Airflow 6-task DAG **解析成功但尚未实际串接入库**。
- 独立 CDM Runtime：实际 SeaweedFS 读取 Person/Visit、镜像构建/GHCR 发布；read-only `cdm_reader` 与 insert-scoped `cdm_writer` 凭据分别存放 `dw-spark/task004-cdm-reader-db`、`dw-spark/task004-cdm-writer-db`；PG Role 权限核实，独立 Runtime 只读 SELECT 成功；合成 Person 事务借由真实 Runtime ROLLBACK 成功，确认没留下 ledger/stage/map/CDM 数据。
- 已发布 S3→Writer ROLLBACK 桥接镜像：`ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e`。CLI：`--plan-file <json> --rollback-from-s3 person|visit`，无 COMMIT 参数；另有 `--validate-source`、`--validate-postgres`、`--rollback-entity/--rollback-rows-file`。K8s worker02、`dw-spark`。
- 历史批次用于新 Writer 时被 `BLOCKED:LEDGER_DRIFT` 拒绝 **安全门禁 PASS 而不是写入成功**（Self-Runner 38430437561）。
- **2026-10-13 新 Synthea 完整流程实测 SUCCESS：** Airflow `task004_processing_pipeline`，新批次 `task004-airflow-task004-step03e-38431103586`，Synthea v3.3.0，2026-10-13 ingest；Landing 发布→Person 23 / Visit **3588** Processing→Reconcile；[Self-Runner run 38431103586](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38431103586) SUCCESS；Self-Runner PR #68 / Healthcare PR #67 已合并。
- **新批次动态 Person Writer ROLLBACK 尚未成功**：[run 38432556422](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38432556422) 接入真 S3/PG 后在 `BLOCKED:EXISTING_TARGET_DRIFT` 处中断。此验证 Workflow FAILURE，未进入预定独立 readback。不要绕过此门禁，更不要执行 COMMIT。可能因新旧批次默认 Synthea `seed=20261012` / `clinician_seed=20261012` 相同、参考日期变更而发生 source_id 重合、Person Payload 不同；**目前只是待验证假设**。

## 3. 最近一次排查的精确断点（NEXT）

目标是仅用 SELECT 计算 **新批次 23 个 Person ID**：
(1) 新 ID 个数；(2) 已存在且目标 OMOP 完全一致个数；(3) 已存在且目标不同个数；(4) 映射存在但 Person 目标丢失个数。只输出汇总数字，不输出任何患者标识。还要独立核实失败批次 `etl.task004_batch_ledger/stage/commit` 是否为 0、Person/Visit 总数是否仍为 136/9391。

目前代码尚在 **Self-Runner 未合并 feature 分支** `feature/task004-person-readonly-audit-20261013`，SHA（创建交接前）`bfad7e9b604006bc6d514bc5afabb9769732df2b`：
- `task004/smoke/read_only_person_overlap.py`
- `.github/workflows/task004-person-readonly-audit.yml`

[Run 38434861465](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38434861465) **FAILURE**，实际 Kubernetes Job 超时后报 `ModuleNotFoundError: No module named 'task004_cdm_materialization_plan'`。脚本以 `python /code/audit.py` 启动，从 ConfigMap 挂载脚本；CDM 镜像中模块位于 `/opt/task004`，而 `sys.path` 只有 `/code`。**最小修复**：在 `read_only_person_overlap.py` 顶部、其余 `from task004_...` 导入前加 `import sys; sys.path.insert(0, "/opt/task004")`，或在 Job 环境设置 `PYTHONPATH=/opt/task004`。推荐只改测试 Job 的 `PYTHONPATH`，镜像和 PostgreSQL 权限不需要变。

**注意：** 上次运行用了 `kubectl wait --for=condition=complete` 超时 240 秒，却未及时发现 Job 已 Failed，导致不必要的等待。修改为有限时间同时查询 Failed/Complete 状态并早停；失败时显示最近 25 行 Pod 日志（不得打印 secret/PHI）；成功后按 `READONLY_PERSON_RECONCILIATION=PASS` 等 marker 验收。只重新触发同一个只读审计一次，失败再查原因，不要重复启动 Synthea/Airflow 或 Writer。

脚本核心：读取新 batch 的固定 SeaweedFS Landing Manifest、发现唯一 Person/Visit Processing Parquet path，通过 `task004_cdm_dynamic_source.read()` 转换 23 Person OMOP row，用 `cdm_reader` 的严格 READ ONLY transaction 逐条 SELECT `etl.person_id_map` / `cdm.person`，使用 `to_jsonb(p) IS NOT DISTINCT FROM to_jsonb(jsonb_populate_record(NULL::cdm.person, payload||id))`（与真实 Writer 一致）比较，按四类 aggregate 并输出独立 DB readback。Secret 取自现有 `dw-spark-s3-secret` + `task004-cdm-reader-db`，无 CREATE/GRANT/INSERT/COMMIT 业务写入（只读事务的结束 COMMIT 不等于业务写入）。

**边界：** 有可能验证后 23 个 Person source_id 全部存在且内容不一致；只有实际成功 SELECT 才能下结论。若 overlap+drift 成立，分析 Synthea Seed/Reference Date/Business Key 政策，优先设计**新的独立 Seed 批次**或有明确版本化规则，不覆盖既有 Person，不取消 drift gate。用户之前要求单轮小闭环和≤3 次测试循环，完成排查后单独规划新的 Synthea 批次与 ROLLBACK。**不立即开新批次、不启用 writer COMMIT、不触发 Airflow 数据库写入。**

## 4. 关键证据与当前 Repo 状态

| 验收 | Self-Runner / Healthcare Actions | 结果 |
|---|---|---|
| 独立 reader PG service + CDM Runtime | 38425638192 | PASS |
| cdm_writer scoped role & rollback | 38427294423 | PASS |
| CDM Runtime standalone synthetic rollback | 38429423958 | PASS |
| S3→Writer historical ledger rejection | 38430437561 | expected rejection PASS |
| **new Synthea + Spark Airflow** | **38431103586** | **PASS, 23/3588** |
| fresh S3→Person dynamic SQL | 38432556422 | **FAIL, EXISTING_TARGET_DRIFT** |
| latest source ID readonly investigation | **38434861465** | **FAIL, Python import** |

Healthcare main **截至交接前** `0b54b4ca42f5a1dd53d7afdbcf678dc316357378`（须重新查询最新 SHA）；Self-Runner main 亦须实时查询。历史文档多次记录不同 SHA，**不要当成今天的 HEAD**。

已完成文档：
- `docs/tasks/TASK-004-STEP04F-FRESH-SYNTHEA-AIRFLOW-SOURCE-PASS.md`
- `docs/tasks/TASK-004-STEP04F-FRESH-PERSON-TARGET-DRIFT-BLOCKER.md`
- `docs/tasks/TASK-004-STEP04F-S3-WRITER-ROLLBACK-INTEGRATION.md`
- `docs/tasks/TASK-004-STEP04F-CDM-RUNTIME-WRITER-ROLLBACK-CLOSEOUT.md`
- `docs/tasks/TASK-004-STEP04E-JOINT-DB-RECONCILIATION-CLOSEOUT.md`
- `docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md`（开发操作手册）

## 5. 下一 Agent 第一轮验收要求

**本轮唯一 NEXT：修复只读审计模块路径 → Self-Runner GitHub Actions 在 K8s 读取真 S3 + PostgreSQL SELECT → 取得四类 Person overlap 数字与失败批次 DB residual → 记录文档、PR 合并。** 若再失败，按工具日志查明原因、控制迭代次数。完成前不得将 STEP04F 标注为完成，也不能开始 TASK005。

特别提醒：不要声称 `38434861465` 已成功或用户取消；它以 FAILURE 结束，失败原因已从真实 Job 日志核实。
