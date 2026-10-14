# Healthcare Data Platform — 当前 TASK 状态与下一步（2026-10-12 EDT，更新 TASK004 OMOP 完整闭环验收范围）

> **2026-10-14 EDT — Airflow 新批次 70 Person /11487 Visit → PG Reader Precommit 实际通过。** [Closeout](NEW-ONLY-SECOND-BATCH-REAL-S3-PG-READONLY-PRECOMMIT-2026-10-14.zh-CN.md) / [Runner 38565372429](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38565372429) SUCCESS：真正 Airflow 38563933551 Handoff XCom→当前 S3 两实体 Parquet 真实 GET/指纹/parent FK→cdm_reader PG READ ONLY；0 源 ID 碰撞，新 Batch Claim/Stage/Checkpoint 全0，Person137/Visit10203与旧 COMPLETED 不变，Writer47 + Landing48 tests PASS。**NEXT：** 70/11487 同事务 Fencing Joint Writer ROLLBACK + 独立 readback，随后新 Batch 独立授权下 COMMIT；禁重跑已成功 Spark，Auto Claim 仍 NO。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — Airflow 新批次 Writer Handoff + 动态原子 SQL 渲染合同 PASS。** [Closeout](NEW-ONLY-AIRFLOW-ATOMIC-DYNAMIC-WRITER-HANDOFF-2026-10-14.zh-CN.md) / [Runner 38562133245](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38562133245) SUCCESS：114 tests、真实 PG 只读完成批次数据 137 Person /10203 Visit / Claim1 COMPLETED 不变。Spark 两实体只读结果通过 versioned Plan SHA/Manifest/URI/行数校验后可调用动态 Writer Renderer；复用已经成功的单事务 Claim+Person/Visit Fencing/整行 Reconciliation/COMPLETED/COMMIT，支持 Visit 动态 1 和812。**本轮仅生成 SQL，不执行真正业务 COMMIT，新 Airflow DAG 的 unclaimed 分支仍 HOLD。** NEXT Spark 新批输入安全接线（先协调另一 Session）+ 新批只读/ROLLBACK/真实 COMMIT，绝不重新写旧 COMPLETED 批次。双 Writer 压测 FUTURE ENHANCEMENT。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — NEW_ONLY Airflow 已完成批次安全跳过真实验收 SUCCESS（旧 XCom blocker 解除）**：[Run 38560309400](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38560309400) / [Closeout](NEW-ONLY-AIRFLOW-CONSUMER-COMPLETED-SKIP-REAL-LIVE-2026-10-14.zh-CN.md) / Self-Runner PR #102 merged。真实 DagRun `success`、Branch 路线已完成 `already_completed_no_replay`、unclaimed hold `skipped`、DAG 事后重新暂停 PASS；PostgreSQL Person137/Visit10203/Claim1/Stage813/Verified2 前后完全不变，52 tests PASS、Spark NO、Auto Claim NO。**NEXT：** `unclaimed_batch_hold` 连接真正全新 v2 READY Batch 的安全 Claim ticket→Spark→Fenced Writer→COMPLETED，不得对已完成 `synthea-new-only-gh-38497355290` 重复 COMMIT；双 Writer 并发/复杂恢复 FUTURE ENHANCEMENT。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT TASK004 Airflow NEW_ONLY 新入口首轮实装，真实 DagRun success、Runner acceptance blocked。** [完整证据/交接](NEW-ONLY-AIRFLOW-CONSUMER-REAL-COMPLETED-SKIP-HANDOFF-2026-10-14.zh-CN.md) / [Runner 38559222216](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38559222216)。Healthcare Main PR #126 新 `new_only_omop_consumer` schedule=None/paused 默认，S3 Discovery→PG Claim READONLY→COMPLETED 安全跳过；真实 GitSync 与 DagBag PASS，DagRun state=success，5 主路径 success/unclaimed HOLD skipped，Person137/Visit10203/Claim1/Stage813/2 Checkpoints Before/After 不变。**Self-Runner job 最终 failure：BranchOperator 的 XCom return_value=None，不是业务失败**。执行轮次达到用户约定修复上限，STOP。下一步只修 Runner 该断言并全绿合并，再开展未来新 READY Batch 受控 Claim/Spark/Writer。Airflow 自动 Claim 尚关闭、Spark 未运行，TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 首个真 S3→OMOP NEW_ONLY v2 业务 COMMIT 正式成功。** [本轮完整验收](NEW-ONLY-V2-FIRST-REAL-PG-COMMIT-RECONCILIATION-2026-10-14.zh-CN.md) / [Run 38555481037](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38555481037) SUCCESS。固定真实 Batch `synthea-new-only-gh-38497355290`，Person **1** / Visit **812** 已持久化、前后 Fencing/合并的 Person→Visit SQL/整行 CDM 对账/Claim COMPLETED 全在单一 PG COMMIT。独立核验 Person136→**137**、Visit9391→**10203**、ID Map 同步 +1/+812、Claim **1 COMPLETED**、Ledger1、Stage813、VERIFIED2。Claim26 + Writer37 回归 PASS，后续重复 Claim `ON CONFLICT DO NOTHING` 确认 COMPLETED 未变化。**下一步：只读验收原 Claim API `SKIP_COMPLETED` 与已入库批次对账，再开发 Airflow 受控单批 Claim/Writer，使用未来未入库新批测试；本批不可二次执行 Writer。** 当前自动 Claim 仍关闭，双 Writer 竞争/复杂恢复为 FUTURE ENHANCEMENT。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — NEW_ONLY v2 真正 1/812 Writer 同事务 Fencing 及 PG ROLLBACK 完成。** [最新真实验收](NEW-ONLY-REAL-S3-OMOP-WRITER-FENCED-ROLLBACK-2026-10-14.zh-CN.md) / [Run 38554330163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38554330163) SUCCESS。受控最小权限 Function 已持久安装（行政 DDL COMMIT，不是业务 COMMIT），cdm_writer 有效角色以单 BEGIN + 合成未提交 Claim 行锁，执行真 S3 Person1/Visit812 SQL，在 COMMIT 前再次核验并整体 ROLLBACK；PG Person136/Visit9391/Claim0 前后不变，真正 READY 未 Claimed。Claim26/26 + Writer33/33 regressions；无 Spark 重跑/Airflow Auto Claim/正式业务 COMMIT。**NEXT：** 真正 READY 单次 Claim→Writer COMMIT→DB Reconciliation→幂等重放、自动 Airflow 主线。真实业务 COMMIT 仍需明确授权。双 Writer 并发竞争与复杂 Recovery 标记为 FUTURE ENHANCEMENT、不再阻塞 Demo TASK004。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — 当前 TASK004 NEW_ONLY Writer 同事务权限隔离 Fencing：真实 PG 合成回滚实验 PASS、尚未部署。** [完整证据](NEW-ONLY-WRITER-SAME-TX-LEAST-PRIVILEGE-FENCE-REAL-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner 38551210536](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38551210536) SUCCESS：Claim26/26、Writer30/30 regressions，SECURITY DEFINER + NOLOGIN Owner + 仅 SELECT/单列 UPDATE + cdm_writer EXECUTE，PG 真角色切换与 Owner/Attempt/Manifest/过期/FAILED、同一事务两次检查 PASS，DDL 与合成行全 ROLLBACK；业务 Person136/Visit9391/Claim0 Before/After 保持。**注意：这个 DB 端 Function 和新 Python fenced rollback adapter 并未在运行环境正式部署，真正 1/812 fenced Writer、两会话并发锁竞争、COMMIT/Reconciliation 均未完成。** NEXT 先 DB 最小权限 DDL 审计 + 真并发安全场景设计，然后才是完整真实 fenced Writer ROLLBACK。TASK004 IN PROGRESS / TASK005 ON HOLD；Portal Spark A4 HOLD。


> **2026-10-14 EDT TASK004 NEW_ONLY Claim/Lease Fencing v1 LIVE PASS（仅 Claim 侧、回滚探针）。** [正式状态](NEW-ONLY-CLAIM-LEASE-TOKEN-FENCING-REAL-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner 38529634738](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38529634738) SUCCESS。严格 v2 Token 48hex + Attempt + Manifest SHA/URI + PostgreSQL clock_timestamp + SELECT FOR UPDATE NOWAIT；Heartbeat 不续过期租约，FAILED 不自动恢复，旧 token/attempt 拒绝。合成 Claim 全 ROLLBACK；真实 NEW_ONLY 无 Claim，PG Person136/Visit9391/Claim0 前后不变。Healthcare #121 / Runner #98 merged。**尚未实现 cdm_writer 与 Claim 锁同事务的安全最小权限代理，也未做真实多会话竞争或 COMMIT/Recovery**；NEXT 优先这个安全边界。TASK004 IN PROGRESS / TASK005 ON HOLD。

> **2026-10-13 EDT / 2026-10-14 UTC — TASK004 PG Writer 的真实联合 ROLLBACK 完成：SUCCESS。** [本轮完整验收和下步](NEW-ONLY-V2-OMOP-WRITER-JOINT-PG-ROLLBACK-REAL-LIVE-2026-10-13.zh-CN.md) / [Self-Runner 38508357752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508357752)：NEW_ONLY v2 真实 Processing Parquet 1 Person / 812 Visit，经 cdm_reader 零碰撞审核，再以 cdm_writer **同一 PG 事务**完成两实体 Stage/ID Map/CDM/Checkpoint/FK 和最终 ROLLBACK。前后 Person136/Visit9391/两 Map/Claim/Batch Ledger/Stage/Commit **表行数零变化**；PostgreSQL 序列计数器可能前进，不能说所有内部状态完全无变化。Healthcare PR #119 / Self-Runner #97 merged，旧 #109 closed/superseded。**NEXT：版本化 Claim owner/lease token/Fencing/恢复 + COMMIT/Reconciliation/幂等；目前真实入库尚未完成。** TASK004 IN PROGRESS；UPDATE_ONLY/MIX_DATA/TASK005 ON HOLD。

> **NEW_ONLY v2 Spark 消费阶段 REAL LIVE PASS（2026-10-13 EDT / 2026-10-14 UTC）**：[正式证据](NEW-ONLY-V2-AIRFLOW-SPARK-PERSON-VISIT-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Runner 38505927396](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38505927396) SUCCESS，Airflow 8/8 Task、真实 Spark Person=1/Encounter=812 的 S3 Processing Parquet URI/XCom/Readback/Reconciliation PASS。真实 PostgreSQL 只读基线 Person=136/Visit=9391/Claim=0 Before/After 不变；新 Batch Stage/Commit 尚 0、CLAIM_ENABLE=NO。Healthcare PR #116、Self-Runner PR #96 merged。**NEXT：Writer 显式 Batch Identity 版本合同 PR #109 处理后，对这两个真实 Processing URI 开展安全 Person→Visit 同事务 ROLLBACK 正例，最后再做 fenced COMMIT/幂等；现在未完成真实入库。** TASK004 IN PROGRESS、TASK005 ON HOLD。

> **2026-10-13 EDT / 2026-10-14 UTC 最新 TASK004 NEXT：NEW_ONLY v2 Spark 源解析桥接真实通过，但还没有实际 SparkApplication。** [完整 Closeout](LANDING-PROCESSING-V2-SOURCE-BRIDGE-WORKER02-LIVE-2026-10-13.zh-CN.md) / [Runner 38503213376](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38503213376)。新 digest `ghcr.io/johnzhang-dataforge/healthcare-landing-processing-v2@sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937` 真读 1 Patient/812 Encounter v2 + 73 Person v1，38 tests PASS；Claim NO / Spark NO / PG DML NO / S3 mutation NO。**NEXT**：限定真实 v2 Batch/SHA，独立 Airflow 人工授权只进行 Person/Visit Spark、Processing S3 Parquet readback/reconcile，再研究联合事务 Writer ROLLBACK。不可跳过 Existing Target Drift / 旧 ID 保护。TASK005 ON HOLD。

> **2026-10-13 EDT / 2026-10-14 UTC 最新任务权威进展：NEW_ONLY 第一份真实 v2 S3 READY 已发布、Airflow 实际读取验收成功！** [中文 Closeout](SYNTHEA-NEW-ONLY-FIRST-REAL-V2-S3-READY-AIRFLOW-2026-10-13.zh-CN.md)。独立真 Synthea worker01 Request `gh-38497355290`：1 Person / 812 Encounter、18 原始 CSV，实际 1 份 header-only 辅助表；所有历史 S3/PG Source ID/Batch Ledger 零碰撞，成功首次 `PUBLISHED_NEW` v2 Manifest：`s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/manifest.json` SHA `dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`，18/18 GET SHA PASS、重放 `REUSE_EXISTING` 同 SHA；真实 Airflow DagRun + 实际 XCom 完全相同的新 v2 Batch 与 SHA 匹配，Claim NO、Spark 跳过、PG DML NO。[Run Generate 38497355290](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497355290)、[Run Publish 38497549237](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497549237)、[Run Airflow 38497724825](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497724825) 均 SUCCESS。版本化新 Release Policy 保留旧 v2 CSV 合同字节 SHA 不变；本轮完成真正 v2 READY，不要按旧 handoff 重复部署 Reader/Publisher。**NEXT：通用手工 NEW_ONLY 新批 Workflow 的 v1/v2 选择，再安全衔接 Claim/Spark/PG Writer，保留 Existing Target Drift；TASK004 IN PROGRESS、TASK005 ON HOLD。**


> **2026-10-13 EDT / 2026-10-14 UTC 权威最新 NEXT — 已经真实部署 Airflow Landing Consumer v2 Reader，不应再重复开发/部署。** [LIVE Closeout](LANDING-AIRFLOW-V2-READER-REAL-DAGRUN-LIVE-2026-10-13.zh-CN.md) / [Run 38496119114](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38496119114) SUCCESS：Airflow 真实 GitSync Exact SHA、DagBag 正式 `healthcare-landing-discovery@sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924`、Claim=NO、真实无参数 DagRun success，scan/Claim Guard success，Spark/Recon skipped。原 v1 73/70 Person S3 两个 READY 在新镜像下兼容 PASS，官方 GHCR 自身 Owner Repo 构建通过，实际 ServiceAccount 可无 token 拉取。**下一轮唯一焦点：审核/版本化激活 v2 Publisher 发布门槛，然后生成一个真实存在合法空辅助表的 NEW_ONLY 小人口新 Request，经过独立 S3/PG Source ID 审计后完成真正 v2 S3 Manifest-last/Discovery/Replay 安全闭环；不能把合成测试当真实 v2 READY。** 此轮 PG DML/Claim=NO、TASK004 IN PROGRESS/TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC 当前唯一权威 NEW_ONLY NEXT：v2 Publisher 已实现并真实安全验收，实际 v2 S3 READY 仍刻意阻断。** [Closeout](SYNTHEA-NEW-ONLY-V2-PUBLISHER-STAGED-LIVE-2026-10-13.zh-CN.md) / [Self-Runner Run 38492827750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38492827750)：42 tests PASS；Fake S3 18 CSV Upload + 18 GET checksum + Manifest last + Replay 不变 PASS；真实 worker01 70 Person /11487 Encounter 冻结 CSV v2 Draft PASS，并真实验证 `BLOCKED:NEW_ONLY_V2_V2_RUNTIME_CONSUMER_NOT_DEPLOYED` 的安全拒绝；GHCR digest `sha256:4a456ee4f186bcfdcf5e22c6477ac92ce32941ca4bae9ba685b0b1a2ca3840c5`。**当前 v2 contract=NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY；下一步先实际部署和验证 Airflow v2 Consumer（Claim NO），再版本化批准真实 v2 S3 发布和原始 Synthea 空辅助表集成。** 此轮 S3/PG mutation=0，原有两个 v1 READY 不变；TASK004 IN PROGRESS/TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC 最新 NEW_ONLY NEXT：v2 Reader 实现 + 回归验证已完成，v2 Publisher 尚未完成。** [Closeout](SYNTHEA-NEW-ONLY-V2-CONSUMER-READER-LIVE-2026-10-13.zh-CN.md) / [Run 38491626783](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38491626783) SUCCESS。新版 `validate_new_only_v2_manifest.py` 只在 `manifest_version=2.0` 和 `synthea-new-only-*` 时接受辅助 header-only 零行 CSV；Person/Encounter 仍必须正数，Manifest 18 个文件/header/Contract SHA/Provenance/Remote Readback 严格核验。33 unit tests PASS，正式 GHCR digest `sha256:d53a706feba8aff30375836f84c9228d22e61aa35578349b01ddcb1b5d532350` 已 push，worker01 新镜像对既有 73 Person 和 70 Person 两个 v1 READY 逐份 18/18 回读 PASS。**没有发布 v2 Manifest、没有升级运行中 Airflow Consumer**；后续必须独立 v2 Publisher + 实际零行 Synthea 生成验证 + 受控 Airflow v2 读取验收，不能跳过恢复/安全门槛。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC 最新权威 NEXT：NEW_ONLY 已经使用正式 Digest 镜像生成第二个真实 READY Batch**。[Closeout](SYNTHEA-NEW-ONLY-DIGEST-RUNTIME-SECOND-READY-LIVE-2026-10-13.zh-CN.md) / [Run 38489944582](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38489944582)（新生 70 Person/11487 Encounter、S3 首次 PUBLISHED_NEW；其旧 verify 硬编码门槛失败，不代表 S3 失败）/ [修正验收 Run 38490367050](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38490367050) 全流程成功，18/18 S3 SHA GET、`REUSE_EXISTING` 同一 Manifest SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`。正式 image `sha256:36b69a26f25f9b627da693fc1aa70b8d0a37de0af755bcb7d95d140568efa909` 已 GHCR push，29 tests PASS。**当前 NEXT**：从 Self-Runner Main 手工 Run `Synthea NEW_ONLY - Run New Independent Request` 进行首次 Main Dispatch 实测；对少人数合法空表则实施 v2 Consumer 版本兼容，不可强行 v1 READY；消费侧 Airflow 自动 Claim、真实 Spark→PG Writer ROLLBACK/COMMIT 保持下一阶段，数据库 Existing Target Drift 不得修改。TASK004 IN PROGRESS，TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC 现时权威 NEXT（覆盖本页历史所有「NEW_ONLY S3 尚未发布」NEXT）**：[首个 NEW_ONLY 真正 S3 READY 与重放闭环](SYNTHEA-NEW-ONLY-FIRST-REAL-S3-READY-2026-10-13.zh-CN.md) / [Run 38488453236](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38488453236) SUCCESS。已固定 NEW_ONLY `synthea-new-only-gh-38484300008`，Person 73、Encounter 12159、18/18 非空、119147940 bytes；PG/S3 只读源键碰撞 0；旧 v1 Validator + S3 18 payload SHA readback + **最后 immutable Manifest INTAKE_VERIFIED** + 独立原有 v1 Discovery/Resolver + 同 SHA replay `REUSE_EXISTING` 全部 PASS，manifest sha256 `66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9`。**NEXT 才是构建正式 NEW_ONLY 独立 digest image 和参数化/自动生成-发布 Job、处理未来辅助零行 v2 Consumer，随后按安全门槛推进 Consumer Spark→PG ROLLBACK 正例→COMMIT；不重发本批，不绕过 Writer Batch ID 与 Drift Guard。** `CLAIM_ENABLE=NO` / DB 0 Mutation；TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 命名/存储决策补充（不更改当前 NEXT）**：三套独立 Producer 前缀为 `synthea-new-only-` / `synthea-update-only-` / `synthea-mix-data-`，[合同](../../contracts/synthea/producer-batch-identity-v1.json)。后两种 **DESIGN ONLY / ON HOLD**。`synthea-local` Retain PVC 已在 worker01 `/data/synthea/` 经跨 Pod 持久化真实验收；SeaweedFS PVC 只与自身 S3 服务存储有关，Synthea 不复用该卷，磁盘容量监控属于运营项。旧 Writer Batch ID 正则 `task004-airflow-` 与现有 Existing Target Drift 防护**完全不变**；新模式仍需版本化消费者/Writer 身份兼容测试，不可直接 COMMIT。当前仅推进 NEW_ONLY 固定 73 Person 批次的 S3 READY 发布，TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 CURRENT NEXT：独立 NEW_ONLY S3 Ready 发布（不是重新生成）**。NEW_ONLY v2 local Contract + S3/PG 历史 Source ID READ-ONLY LIVE PASS，[验收](SYNTHEA-NEW-ONLY-PREPUBLISH-SOURCE-IDENTITY-LIVE-2026-10-13.zh-CN.md) / [Run 38486092750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38486092750)：固定本地批次 Person=73、Encounter=12159、18 CSV 全部非空、历史 S3 14 个源 CSV + 真 PG Person 136/Visit 9391 source keys，**Person/Visit overlap 均为 0**。streaming CSV 修复 64MiB 问题；Source ID 审计不是并发事务锁。下一轮先通过旧 v1 validator 验证当前这批数据，再独立 S3 18 object upload/checksum GET + 最后 Manifest immutable READY，保留 `CLAIM_ENABLE=NO` / Writer Drift Guard；新 v2 Consumer 仍未启用。**S3 READY/PG ROLLBACK 正例/COMMIT 均未完成**。TASK004 IN PROGRESS，TASK005 ON HOLD。


> **2026-10-13 最新 NEW_ONLY 真实 Local Generator 验收**：[LIVE Closeout](SYNTHEA-NEW-ONLY-LOCAL-GENERATOR-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Run 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008) 全部 Job SUCCESS：`synthea-local` Retain StorageClass + worker01 5Gi PVC Bound / 实际 Person=73 Encounter=12159 18 CSV，重放同一个冻结 request ID 没有重新生成，`S3_READY=NO` / `PG_MUTATION=NO`。**当前 NEXT 改为 NEW_ONLY S3 发布准备：正式 versioned contract（零行辅助表需兼容消费者）、PG/S3 历史 source IDs 全局 read-only 防撞、独立镜像 Digest、Manifest 最后发布与读回。** 不重做前轮存储 PVC、也不在此刻直接开放动态 COMMIT；TASK004 IN PROGRESS，TASK005 ON HOLD。下方历史 NEXT 仅作历史记录。


> **2026-10-13 NEW_ONLY NEW-A READ-ONLY PREFLIGHT 最新验收**：[真实 worker01/Contract 检查](SYNTHEA-NEW-ONLY-READONLY-PREFLIGHT-2026-10-13.zh-CN.md) / [Run 38481854395](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38481854395) PASS（审计完成且阻塞明确）。worker01 Ready；`dw-synthea` 存在但新 PVC 0、`local-path` 默认 Delete、专用宿主设备/剩余容量 NOT VERIFIED；18 CSV 全非空对随机 1..100 尚未有真实测试，Writer Legacy ID 拒绝独立 `synthea-new-only-`。**NOW NEXT：补只读 host mount 和 S3 Secret 名称、确定 Retain PV/PVC，再 NEW-B 独立业务源码测试。NEW_ONLY 未部署，Dynamic PG ROLLBACK 正例和 COMMIT 未完成；TASK004 IN PROGRESS / TASK005 ON HOLD。**


> **2026-10-13 最新权威 NEXT（新 Session 交接）**：[TASK004 CURRENT Agent Handoff](TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md)。第三层 Writer 到真实 S3/PG 已验证 **`BLOCKED:EXISTING_TARGET_DRIFT` 安全负例** ([Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382))，不是新批 COMMIT 或成功 ROLLBACK 正例；源数据 23 Person/3588 Visit，OMOP Person=136/Visit=9391、新 Claim=0 读回不变。第四层 Airflow Discovery→PG Claim Guard→历史批次**手动** Spark Processing PASS ([Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452))；`CLAIM_ENABLE=NO`，新批**自动处理未开启**。设计已更新为 Generator/Airflow 解耦的三套独立 Job/Pod、只实现 NEW_ONLY；**尚未真实部署 NEW_ONLY**。当前下一有界闭环推荐 **NEW_ONLY worker01 LocalPath/Contract 只读前检 + Writer 版本化 Batch ID 兼容性预审**，取得新无冲突 READY 后才能正向 PG ROLLBACK→COMMIT/DB Reconciliation。原始旧 handoff 快照位于 `docs/archive/2026-10-13-agent-handoff-refresh/`。TASK004 IN PROGRESS / TASK005 ON HOLD。以下历史 NEXT 不再有效。


> **2026-10-13 第三层 CURRENT NEXT = 真正无患者 Source ID 冲突的 NEW_ONLY 输入 + 成功 S3→PG Person/Visit ROLLBACK 正例**。现已通过 [Writer 真 S3 安全负例](OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md) / [Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382)：确实下载并转换 23 Person、3588 Visit Parquet，真实 `cdm_writer` PostgreSQL ROLLBACK-only CLI 按已证实的 23/23 source ID 内容漂移触发 `BLOCKED:EXISTING_TARGET_DRIFT`；独立 DB readback Person=136/Visit=9391/Claim=0、目标 batch ledger/stage/commit=0，**无业务持久化**。Workflow PASS 是“预期阻断”而非真实 Writer 成功事务；不能标为 ROLLBACK 全部 PASS 或 COMMIT。新 `apps/omop_writer/build_s3_rollback_plan.py` 通过 4 单元+现有17单元测试；下一步需独立 Generator NEW_ONLY 全新批次、适配旧 Plan ID 前缀限制、完整正向 S3/PG ROLLBACK、再设计 COMMIT fencing/最终 DB reconciliation。TASK004 IN PROGRESS、TASK005 ON HOLD。


> **2026-10-13 CURRENT NEXT（第三层）：动态 Writer 实际 S3 Processing→PostgreSQL ROLLBACK（非 COMMIT）+ 专用镜像和真实 S3 绑定。** [OMOP Writer Precommit Safety Live Closeout](OMOP-WRITER-PRECOMMIT-SAFETY-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Run 38478501009](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38478501009)：`apps/omop_writer/precommit_gate.py` 源数据计划/行指纹/Person/Visit 一致性与现有 source-key/历史 ledger/Claim 的读-only 判定已验证，9 单元测试、真实 worker02 PostgreSQL `cdm_reader` PASS；实际 Reader 最小 `etl.landing_batch_ledger SELECT` GRANT 已持久化，不授予 OMOP INSERT。**测试正例只是人工准备、无真实 S3 真实性绑定且绝不代表允许 COMMIT**；Person=136/Visit=9391/Claim Rows=0 都未变。旧 Writer renderer 可以生成 COMMIT SQL，但并没有事务内 fencing/完整独立对账，不应直接放行。下一轮先独立真 S3/PG ROLLBACK，接着新批安全 COMMIT/DB 对账。TASK004 IN PROGRESS / TASK005 ON HOLD。\n\n
> **2026-10-13 最新真实验收：Spark 消费集成（历史批次手动 Processing-only）PASS。** [LIVE Closeout](LANDING-SPARK-PROCESSING-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452) **SUCCESS**：`landing_batch_discovery` 经 S3 Discovery→PG Claim Guard→手工历史批次选择→Spark Person、Visit→Spark Reconciliation→Processing 校验，真实 **8 个 Airflow TaskInstance success**；历史 S3 batch/SHA 校验有效；PG CDM Person=136、Visit=9391、Claim Ledger=0 不变。新 Main 代码为 Healthcare [PR #79](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/79) 加 [PR #80](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/80) / [PR #81](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/81) 修复。**但真实 Claim 开关继续 NO，自动每15分钟定时扫描只执行前半段、不会自动触发 Spark；新 Batch 自动领取/自动 Spark/动态 OMOP COMMIT/最终 DB Reconciliation 仍未完成。当前 NEXT 是为新批次设计受控 Claim + 完整发现队列、历史 Source ID 防撞与动态 Writer COMMIT 的安全闭环。** 不应再重复开发已有的 S3 Discovery/Claim 基础/手动历史 Spark。TASK004 IN PROGRESS / TASK005 ON HOLD。下面旧 NEXT 已过时。\n\n
> **2026-10-13 CURRENT NEXT：从已接通的 Landing Discovery→PostgreSQL Claim Guard 进入受控 Spark Consumer。** [权威 Live Closeout](LANDING-DISCOVERY-TO-CLAIM-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner Run 38471287896](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471287896) 成功证明 Airflow `landing_batch_discovery` 的 **`scan_ready_manifests → evaluate_batch_claims` 两 KPO DAG 真正运行/通过**、Claim KPO 读取有独立授权的 PostgreSQL Ledger，并且 Claim Enabled=NO、实际新 Ledger 0、OMOP Person=136/Visit=9391 均未变。另 [Run 38470907298](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38470907298) 证实历史已处理批次正确隔离（最小 legacy SELECT 授权）。**自动真实 Claim 目前尚未打开**，不可称已自动领取/处理 6 个 Batch，也没有后继 Spark/Writer COMMIT。下一步先处理全量/分页 Manifest、Source IDs 新旧安全门槛、受控单批 Spark/Writer 与 Lease 恢复，再允许开启 Claim。TASK004 IN PROGRESS / TASK005 ON HOLD；以下历史 NEXT 已被覆盖。


> **2026-10-13 CURRENT NEXT：受控 Landing Consumer Claim 接入。** [Batch Claim / Ledger 真 PG Closeout](LANDING-BATCH-CLAIM-ROLLBACK-CLOSEOUT-2026-10-13.zh-CN.md) / [Run 38468961485](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468961485) PASS：新 `etl.landing_batch_ledger` 已真实持久创建、专用受限 PostgreSQL `landing_claim_worker` + `dw-spark/landing-claim-db` Secret 已创建，核心 `apps/landing_claim/batch_ledger.py` 验证 CLAIMED/BUSY/SKIP/显式 FAILED Retry/过期 Lease BLOCKED/Owner Fencing，12 Tests 与真实 PG 事务 **ROLLBACK**、独立 0 探针行 readback PASS，Person=136/Visit=9391 不变。**仍未**自动从 Airflow 领取任何历史 READY 批次、未调用 Spark/DB Writer。下一步安全接线前必须审计过去已经入库的 Batch/Source ID，不能将 Scanner 当前的 6 个候选直接当成全新未处理数据；之后才 Person/Visit→动态 COMMIT→replay。自然 Cron 证据与双 Pod 并发/Heartbeat 还需补，TASK004 IN PROGRESS / TASK005 ON HOLD。以下旧 NEXT 均过时。


> **2026-10-13 CURRENT NEXT = Landing Batch Claim + Processing Ledger 设计/实现（先安全测试）。** 已完成 [Airflow S3 Discovery Live Closeout](LANDING-BATCH-DISCOVERY-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)：Healthcare [PR #74](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/74) merged，Self-Runner [PR #72](https://github.com/JohnZhang-DataForge/Self-Runner/pull/72) merged，Real DAG [Run 38466518057](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38466518057) SUCCESS；真实 Airflow `landing_batch_discovery` **每15分钟 Cron 已启用**、GitSync Exact SHA PASS、手工 DagRun/Task success，已经正式**不再调用 Generator**；Scanner 显示 6 verified READY + 1 old quarantine（独立镜像实测）。**自然 cron 产生的 DagRun 尚未单独留证**。当前只做 Inventory，不做 Claim、Spark 或 PostgreSQL COMMIT；下一步 Claim/Ledger → Consumer Spark → Dynamic Writer → DB Reconciliation/Replay。NEW_ONLY Producer 与 EXISTING/MIXED 仍按独立阶段，不属于当前消费端 NEXT。TASK004 IN PROGRESS，TASK005 ON HOLD；以下历史 STEP/Seed/NEW_ONLY NEXT 全部被此行覆盖。


> **2026-10-13 当前最高优先级 / 用户新批准的开发顺序：先 Landing S3 Discovery + Airflow 消费侧，再动态 PostgreSQL Writer。** **已真实验证** [Landing Discovery 只读 Checkpoint](LANDING-BATCH-DISCOVERY-READONLY-CHECKPOINT-2026-10-13.zh-CN.md) / [Run 38460137577](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38460137577)：6 verified READY + 1 legacy quarantine、8 tests PASS、S3 真读、DB mutation NO。**当前 NEXT** = 做有周期的、功能命名 `landing_batch_discovery` DAG（独立只读镜像、Airflow gitSync/parse/runtime 验证），与 Generator 无耦合；后续 Claim/Ledger → Spark → CDM Dynamic COMMIT → DB Reconciliation/Replay。**目前只读 Scanner 已完成，Airflow 自动调度/Claim 尚未实现**。Synthea NEW_ONLY 实施暂不抢占此消费端优先级；EXISTING_ONLY/MIXED 继续 ON HOLD。TASK004 IN PROGRESS，TASK005 ON HOLD。下方曾写 NEW_ONLY NEXT 或 STEP04A 等均是旧顺序，不再作为当前开工点。


> **2026-10-13 当前最高优先级 NEXT（覆盖下面历次旧 NEXT）：独立 Synthea NEW_ONLY Producer 设计已确定，实施尚未开始。** Airflow 与 Generator **完全解耦**：三个独立的短生命周期 Job/Pod 代码和镜像（NEW_ONLY / EXISTING_ONLY / MIXED），生产侧自行决定随机人数 1～100、州、Seed、生成日期，worker01 `dw-synthea` 上的**专用 LocalPath PVC/磁盘**保存生成恢复状态；SeaweedFS S3 通过 verified immutable Manifest 发布 READY；新 Airflow Consumer DAG（尚未开发）只定期发现/读取已存在的批次，不能调用 Generator。**当前只允许按步骤推进 NEW_ONLY**：先 local-path/18 CSV 契约只读 preflight，再 NEW_ONLY 独立实现+测试、最后单批 S3 实证；**EXISTING_ONLY、MIXED 代码/Pod 暂不实施**。具体 [架构权威 v1.0](../architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md) 和 [NEW_ONLY NEXT](TASK-004-INDEPENDENT-GENERATOR-NEW-ONLY-NEXT-v1.0.zh-CN.md)。**本轮文档 PR 不代表已部署/运行；旧 DAG 仍耦合并被冻结。** 完整 CDM Writer 仍未闭环，TASK004 IN PROGRESS，TASK005 ON HOLD。以下旧 STEP04A / seed/date 排查 NEXT 不再是当前开工点。


> **2026-10-13 最新主线结论：STEP04F Synthea Source ID 根因只读排查 PASS，动态 Person Writer 仍 BLOCKED。** [根因验收文档](TASK-004-STEP04F-SYNTHEA-SEED-REFERENCE-DATE-ROOTCAUSE-READONLY-CLOSEOUT.md) / [Run 38447127571](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38447127571)：同一 Seed/Clinician Seed、Reference Date 差一天 → 23 个患者 ID 完全重复，23 条 CSV 的 BIRTHDATE 全部 +1 天，对应 OMOP 23 条的 `birth_datetime` 和 `day_of_birth` 不同；原 PostgreSQL 漂移保护正确生效。**新的唯一 NEXT = 方案设计：为独立批次采用确定性隔离 Seed，并冻结 batch 参考日期，或明确同 ID 后续版本修正契约；本轮没有新批次 / 任何 Writer COMMIT。TASK004 IN PROGRESS；TASK005 ON HOLD。**以下旧 NEXT 均为当时阶段性说明。


> **2026-10-13 新增权威状态：READONLY Person Source ID Reconciliation 已 PASS（STEP04F DB 写入仍 BLOCKED）**。[验收记录](TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md) / [Self-Runner Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614) ：固定新批次 Person 23，Source ID 已存在 23（完全一致 0，内容不同 23），全新 0，dangling map 0；数据库 Person 136 / Visit 9391；失败批次 Ledger/Stage/Commit 0/0/0；`DATABASE_MUTATION=NO`。审计路径修复、Self-Runner PR #69 已合并。**唯一 NEXT = 独立规划/验证 Source ID + Seed/Reference Date 隔离语义，不开始新的批次，不执行 Writer COMMIT，TASK005 ON HOLD。**以下旧 STEP04A/04B/只读审计 NEXT 均为历史阶段说明。

> **2026-10-13 当前权威 NEXT / 见 [TASK004 最新交接](TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md)：** 固定批次 STEP04C/D/E 已完成；STEP04F S3/CDM Runtime reader+rollback writer 已构建实测，新 Airflow Synthea Batch `task004-airflow-task004-step03e-38431103586` Processing PASS（Person=23，Visit=3588），但新 Person 入库测试 `BLOCKED:EXISTING_TARGET_DRIFT`，不允许 COMMIT。最新只读 Source ID 审计 Run `38434861465` 为 FAILURE（`ModuleNotFoundError: task004_cdm_materialization_plan`），Self-Runner feature `feature/task004-person-readonly-audit-20261013` 尚未合并。**唯一 NEXT = 修复该测试 Job PYTHONPATH，真实只读查 23 人的 existing/changed/new/dangling 数量与失败批次 DB residual；不重新跑 Synthea、不得绕过漂移保护。**本文件后面遗留 STEP04A/04B NEXT 是过期阶段说明，以最新交接为准。TASK005 仍 ON HOLD。


> **CURRENT STATUS / MAINLINE AUTHORITY**。本文件描述唯一正式业务主线当前状态。历史 Candidate / Pilot / Closeout 只说明当时事实，不能覆盖本文件。

## 已验证 / 下一步

| 范围 | 当前主线状态 | 当前动作 |
|---|---|---|
| TASK001 | 历史冻结 Landing / batch 基线 | 不重跑、不改冻结文件 |
| TASK002 | Person V2 历史回归与冻结基线 | 不擅自修改 |
| TASK003 | **COMPLETE / CLOSED** | 只读参考实现 |
| **TASK004 — overall（完整闭环）** | **IN PROGRESS** | **STEP04A CLOSED; STEP04B OFFLINE REPLAY CONTRACT BASELINE PASS (15/15), NEXT: controlled mapping/loader implementation subject to separate DB write authorization**；正式开发计划见 [Person/Visit CDM + Idempotency Plan](TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md) |
| TASK004 — Processing MVP（既有验收） | **COMPLETE / CLOSED / FROZEN** | 保持历史业务/Runner PASS，见 [MVP Closeout](TASK-004-FINAL-CLOSEOUT.md) |
| TASK004 — CDM Person/Visit Materialization | **STEP04C/D DB LOAD + STEP04E JOINT RECONCILIATION PASS** | 固定 batch Person 23、Visit 3592 已分别真实写入 PostgreSQL，Person 136 / Visit 9391，重复加载不新增，Visit FK 缺失 0。证据见 [Person Closeout](TASK-004-STEP04C-PERSON-DB-COMMIT-CLOSEOUT.md)、[Visit Closeout](TASK-004-STEP04D-VISIT-DB-COMMIT-CLOSEOUT.md) 与 [Joint DB Closeout](TASK-004-STEP04E-JOINT-DB-RECONCILIATION-CLOSEOUT.md)；STEP04F Airflow DB 编排为 NEXT |
| TASK004 — STEP04F Airflow Dynamic CDM Plan | **6-TASK DAG PARSE PASS / DB AUTO LOAD PENDING** | 已在 reconcile→cdm_load_preflight 后接入 cdm_materialization_plan，动态批次 URI/Manifest 指纹、来源漂移检查 PASS；真实 Airflow scheduler DagBag 解析 SUCCESS；无新 DAG Run 或数据库写入。见 [STEP04F Dynamic Plan Closeout](TASK-004-STEP04F-DYNAMIC-BATCH-PLAN-CLOSEOUT.md) |
| TASK004 — STEP04F Dynamic PostgreSQL Writer | **REAL POSTGRESQL ROLLBACK PASS / COMMIT DISABLED** | 动态批次 Person/Visit 事务 SQL 已在真实 PG 进行联合 ROLLBACK 演练，并独立确认无数据遗留；Airflow 自动写库、镜像和新批次 COMMIT 仍待做。见 [STEP04F Dynamic PG Writer](TASK-004-STEP04F-DYNAMIC-PG-WRITER-ROLLBACK.md) |
| TASK004 — 同批次 Airflow replay/retry 幂等性 | **PERSON + VISIT DB REPLAY PASS / FULL DAG NOT VERIFIED** | STEP04C/D 同 batch Person 与 Visit 各自数据库重放已实测不增加记录；跨批次并发、未知提交恢复、整条 Airflow DAG 重放仍未验证 |
| TASK004 — Synthea | **PASS** | frozen baseline |
| TASK004 — Resolver / Control | **PASS** | frozen baseline |
| TASK004 — Person | **PASS** | frozen baseline |
| TASK004 — Visit | **PASS** | frozen baseline |
| TASK004 — Batch Reconciliation | **PASS / MAINLINE ACCEPTED** | frozen baseline；正式证据见 Mainline Closeout |
| TASK004 — Airflow STEP02 Processing orchestration | **PASS / HISTORICAL MAINLINE ACCEPTED** | frozen baseline |
| **TASK004 — Airflow STEP03E end-to-end** | **PASS / BUSINESS + SELF-RUNNER MAINLINE ACCEPTED** | frozen STEP03E baseline，Final Audit PASS；旧 Live 新批次未重跑 |
| **TASK005 — Condition (Phase E)** | **ON HOLD / DESIGN BASELINE ONLY** | 等 TASK004 Person + Visit 同 batch CDM 入库和重放验收完成后再解锁 STEP00 |
| Azure/Fabric/dbt/MLflow 等 | 后续分阶段设计 | 不阻塞已完成的 Airflow MVP |

**TASK004 overall status = IN PROGRESS（按用户明确的完整流程完成标准）。** 既有 Synthea → verified Landing → Person/Visit Processing → Reconcile 的 **MVP COMPLETE / FROZEN**、历史真实验收未被推翻；但 **OMOP Person/Visit 同批次入库 + 数据库级对账 + Airflow 重放幂等** 尚未完成。权威 NEXT = [`TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`](TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md) 的 **STEP04B CODE / TEST ONLY**；STEP04A 实际只读调查已经验收，见 [STEP04A Final Closeout](TASK-004-STEP04A-READONLY-FINAL-CLOSEOUT.md)，但写库前 batch isolation 仍 BLOCKED。过去 [`TASK-004-FINAL-CLOSEOUT.md`](TASK-004-FINAL-CLOSEOUT.md) 仅证明原限定 Processing MVP，属历史里程碑。TASK005 暂缓。

## 历史 STEP02 Airflow Processing orchestration 正式主线验收

以下是历史 STEP02 Processing DAG（STEP03E 的最新四 Task DAG 见新增 Closeout）：

~~~text
GitHub main
→ git-sync
→ Airflow 3.2.2
→ Person + Visit (KubernetesPodOperator, parallel)
→ dynamic XCom
→ Reconcile
~~~

Healthcare：

~~~text
PR #26 merge/main = e99a68e8b24a3dee97ea38ce7dc426a63c6fb119
runtime image digest =
sha256:bf7f4611a9dcbd8bd79b420f80c5f97f4ec92e0dbd5ba8132cea4be59fdf57bf

PR #27 merge/main = f82a70e28038d87bb9e7e60670dfb0c39e928b0b
PR #28 merge/main = 5e043b8f00d89a01b72ae6264f35903ceff93de9
~~~

Self-Runner acceptance：

~~~text
Airflow parse             38309576088  PASS
KPO PodSpec dry-run       38309911048  PASS
scheduler RBAC            38311231070  PASS
control-runtime kubectl   38311402840  PASS
live orchestration        38311805385  PASS
DAG unpause               38312544761  PASS
post-merge git-sync       38313275171  PASS

Self-Runner PR #35
squash merge/main         a67a75c15e5c6385131b056c1af0d1aa8eb34077
~~~

Live evidence：

~~~text
AIRFLOW_GITSYNC_DAG_VISIBLE=YES
AIRFLOW_GITSYNC_EXACT_SOURCE_GATE=PASS
AIRFLOW_DAG_TRIGGER=PASS
TASK_STATE_PERSON=success
TASK_STATE_VISIT=success
TASK_STATE_RECONCILE=success
AIRFLOW_DAG_RUN=PASS
SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO
SUCCESSFUL_CONTROL_POD_RESIDUAL=NO
POSTGRESQL_MUTATION=NO
TASK004_AIRFLOW_STEP02C_LIVE=PASS
RESULT=PASS
~~~

Live artifact：

~~~text
Artifact = 11775098927
Digest =
sha256:570901ce456778457fecc3a1c718ea88aa9ea9dafe8281028e917b3f678cf0ed
~~~

Post-merge authority：

~~~text
Healthcare main =
5e043b8f00d89a01b72ae6264f35903ceff93de9

LOCAL_DAG_SHA256 =
6269920737ca616194f6282994dca711dac98afabf7a4b4f992c01d84789ac1c

GITSYNC_DAG_SHA256 =
6269920737ca616194f6282994dca711dac98afabf7a4b4f992c01d84789ac1c

DAG_IS_PAUSED=false
~~~

正式 Closeout：

- TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md

## Batch Reconciliation 正式主线验收

Candidate review 结论：

```text
REVIEW_DECISION=MODIFY_BEFORE_ACCEPTANCE
```

完成 canonical source 加固后：

```text
Healthcare PR #24
final tested PR HEAD = ee16f5265b0ebb8c30e7e65ec665215613956e77
merge/main SHA       = 91d96f436e7697d70025cc1c9a045ecfb20f41b1
```

Self-Runner：

```text
pre-merge exact PR HEAD Run = 38287060452  PASS
post-merge exact main Run   = 38287401518  PASS
Self-Runner PR #31 merge    = 8ab26784cd0229cce96989e3691c122049e3c23a
```

最终业务 evidence：

```text
PATIENT_ROWS=20
PATIENT_UNIQUE_IDS=20
ENCOUNTER_ROWS=2459
ENCOUNTER_UNIQUE_IDS=2459
REFERENCED_PATIENTS=20
ORPHAN_ENCOUNTERS=0
SOURCE_SYSTEM=synthea
SOURCE_VERSION=v3.3.0
SOURCE_BATCH_ID=task004-p20-first-landing-20261011
SOURCE_INGEST_DATE=2026-10-11
PROCESSING_MUTATION=NO
POSTGRESQL_MUTATION=NO
SUCCESSFUL_SPARKAPPLICATION_RESIDUAL=NO
SUCCESSFUL_CONFIGMAP_RESIDUAL=NO
SUCCESSFUL_DRIVER_POD_RESIDUAL=NO
RECONCILIATION_STATE_GATE=PASS
RESULT=PASS
```

Artifacts：

```text
pre-merge:
  Run      = 38287060452
  Artifact = 11763243392
  Digest   = sha256:171fb1d9bdfd6506ef150c8e37a529fb26a2f3225ebce9deba344ec057307292

post-merge:
  Run      = 38287401518
  Artifact = 11764107251
  Digest   = sha256:c0f72a2dc7c84bccfa96af344432241de0ab6ace8a69ae5c959e5bcf3ac2d1f7
```

两次早期失败均未进入业务 mutation：

- Run `38286850393`：Workflow YAML parse failure，jobs=0。
- Run `38286943030`：source test assertion failure；Spark execution skipped。

## 最新 STEP03E 全链业务验收（2026-10-12）

STEP03E 业务验收时固定的 Healthcare 源码 SHA = `d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`（**历史已验收 SHA，不是持续变化的当前 main**；新 Agent 先查当前 GitHub main）；DAG = `task004_processing_pipeline`，现已形成 `generate_publish >> [person, visit] >> reconcile`。

- Self-Runner live Run `38324111846`：**GitHub failure**（发生在 DAG 成功后的后置 XCom 取证）。Airflow DagRun 及 generate_publish、person、visit、reconcile 四个 Task 均为 **success**。
- 新 Landing batch = `task004-airflow-task004-step03e-38324111846`；source_version `v3.3.0`；ingest date `2026-10-12`；18 verified files；manifest SHA256 `ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1`。
- Person `23` canonical rows + Visit `3592` canonical rows，Processing readback 均 PASS；Reconcile 同 batch、同 version / ingest date，PASS。
- Self-Runner 独立 post-success Run `38326695107` = **SUCCESS**，真实 Airflow 日志 lineage 与 Synthea Job、ConfigMap、Control Pod、SparkApplication 成功后 residual 检查 PASS；无 PostgreSQL 写入。
- Self-Runner 正式验证代码收尾：[PR #38](https://github.com/JohnZhang-DataForge/Self-Runner/pull/38)。最终固定 PR HEAD `49da2267aed6eca73b2fa735d5145f3ee9427e51`；pre-merge Run `38328528372` = SUCCESS；PR #38 squash/main = `6f72c05ad8eb1a0abeb19f3cff9e89ac698cff87`；post-merge exact-main Run `38328600074` = SUCCESS，Artifact `11781762914`。`38328025745` 因上传流程卡住，不作为主线成功证据。

正式细节、源码身份、证据、限制：`TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md`。历史 STEP02 Closeout 仍有效，但它当时写的 `upstream ingestion NEXT` **已经过期**。

## TASK004 原限定 Processing MVP Final Audit & Closure（历史里程碑，2026-10-13 UTC）

- runner01 分别执行 STEP01、STEP02、Final Storage Check 的只读审计：四节点 Ready、历史 DAG/四 Task success、成功 run Synthea Job 和 Control Pod residual=NO、Airflow 当前 DAG GitSync 源码 SHA256 与 GitHub main 一致。
- S3 正确 namespace 是 `dw-seaweedfs`，四个 Pod 全部 1/1 Running，S3 EndpointSlice 存在。早期失败运行的历史 Job/Pod 不等同于成功运行的残留，不擅自删除。
- Self-Runner [PR #39](https://github.com/JohnZhang-DataForge/Self-Runner/pull/39) 已修复历史只读固定 SHA 检查，post-merge [Run 38329852476](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38329852476) SUCCESS；**修复后 Live mutating 新批次回归未执行**。
- PostgreSQL `omop` 历史状态：Person=113、Visit=5799、Condition=0；STEP03E 的 23/3592 是 Processing，**数据库新批次写入不属于 TASK004 验收范围**。
- 当时限定的 Processing MVP 范围、非阻塞项、证据：[`TASK-004-FINAL-CLOSEOUT.md`](TASK-004-FINAL-CLOSEOUT.md)。**本条是历史关闭证据，当前 TASK004 扩展目标及 NEXT 已由上方状态表与新增 CDM 计划取代**。

## TASK004 OMOP Person/Visit + Replay 新增完成标准（当前 NEXT）

- 用户最终目标：一个批次从 Airflow 触发 Synthea → verified Landing → Person/Visit Processing → **Person CDM 入库 → Visit CDM 入库 → 独立数据库对账**，同一 batch 重放/部分失败恢复**不产生重复数据或重分配稳定 ID**。
- **唯一当前授权 STEP：STEP04A 只读数据库与真实输入调查**；STEP04B 为逻辑/契约设计。后续任何 PG/S3/K8s mutation 或新的 Airflow Live Run 均需单独明确授权。
- 入库顺序与动态业务键：Person Mapping + CDM commit/readback → Visit Mapping + CDM commit/readback → batch-scoped final database reconciliation。**不能原样复用历史追加写入共享 etl.person_stage 和 TASK003 冻结的 5799 行脚本。**
- 正式执行契约、PR 结构、失败重试/同 batch replay 与 A1–A11 验收矩阵详见 [`TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`](TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)。
- 当前状态：TASK004 Processing MVP PASS/FROZEN；CDM loop NOT IMPLEMENTED；replay idempotency NOT VERIFIED；**TASK004 overall IN PROGRESS；TASK005 ON HOLD**。

## TASK005 Condition 设计基线与历史 NEXT（当前 ON HOLD）

- 业务实体：Synthea v3.3.0 `conditions.csv` → `condition_occurrence`；七列表头 `START, STOP, PATIENT, ENCOUNTER, SYSTEM, CODE, DESCRIPTION`，**没有 Id**，必须证明可重复且保留重复事件的唯一 occurrence key。
- 设计文档：`TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`（STEP00–06）。
- **当前状态：ON HOLD**。原 STEP00 Condition 只读 preflight 属 TASK005 将来解锁后的下一步，**不是此刻可启动的工作**。先完成 TASK004 STEP04A–04H 的完整入库与重放闭环；Condition 设计计划仍保留。
- Processing Candidate 与 PostgreSQL `cdm.condition_occurrence` materialization 必须分别验收；OMOP mapping 的源码 code 不得当成 `concept_id`；修复后的 STEP03E Live Workflow 不得未经授权自动重跑。
- Condition 当前不开发、不部署、不写库；待 TASK004 完成正式 DB 闭环后才按 STEP00 的小范围 PR + exact-SHA Runner 开工。

## 下一位 Agent 如何开始（唯一当前主线）

1. 读取 `../README.md`、本状态表、**TASK004 OMOP CDM Integration & Idempotency Plan**、STEP03E 历史真实 Closeout、TASK003 Final Closeout、Operations、Skill 和 Lessons。
2. 实时核对 Healthcare / Self-Runner main SHA，确认 TASK004 已验收 Processing MVP 不动；旧 MVP 的 CLOSEOUT 属 **历史限定范围**，不代表本次数据库终验。
3. 只进入 **TASK004 STEP04A**：固定一个只读 verified batch，盘点真实 Postgres DDL、既有 ID mapping 和 Processing 结构，提交 read-only 预检源码/报告 PR，绑定 exact SHA Self-Runner 验证，写证据。
4. 不得运行旧的 TASK003 数据库一次性脚本，不得直接读取共享 Person Stage 当作新批次，禁止无批准触发新 Airflow/Synthea、Postgres DML/DDL、S3/集群写入。
5. STEP04A PASS 或 BLOCKED 后更新状态并再决定 STEP04B；**TASK005 Condition ON HOLD**。

## 冻结与安全

- TASK001–TASK003：task-level frozen。
- TASK004 既有 Processing MVP frozen baseline：Synthea / Landing / Resolver / Control Runtime / Person / Visit / Batch Reconciliation / STEP02 Processing / STEP03E；Self-Runner PR #38/#39 与 Final Audit 验收 PASS。**新增 OMOP 入库/幂等性扩展是未完成工作**，不得改写旧验收。
- TASK004 整体（新定义的完整闭环）：**IN PROGRESS**；新批次 PostgreSQL Person + Visit 入库、数据库对账及同 batch replay 未通过前不允许 CLOSED。TASK005 **ON HOLD**。
- 不把 DAG parse、render-only 或单个 operator 构造成功冒充真实 Airflow orchestration PASS。
- 历史文档原文归档，不追溯改写。

## 相关文档

- `TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md` — **当前 TASK004 开发权威计划 / NEXT STEP04A**
- `TASK-004-FINAL-CLOSEOUT.md` — 原限定 Processing MVP 历史验收（仍然有效，但不能充当 CDM 终验）
- `TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md` — Condition 已设计，**ON HOLD**（当前不是 NEXT）

- `TASK-004-PHASE9-CLOSEOUT.md`
- `TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`
- `TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`
- `../archive/2026-10-12-mainline-reconciliation-acceptance/tasks/TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md`
- `../archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md`
