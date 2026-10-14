# Healthcare Data Platform — Agent START HERE（当前有效文档）

> **Portal A4 独立 Spark OpenLineage Smoke（2026-10-14 EDT）**：[A4 实测 Closeout](platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)。专属 `dw-spark` SparkApplication `COMPLETED`、3 行 CSV 聚合 PASS；Marquez 中有 `healthcare-platform-spark-probe` 的真实 Spark facets 和 `COMPLETED` Run。首次完整 Workflow 因错误名称查询 **FAIL**，三次只读回读 **SUCCESS**；Job 关联/数据集 I/O 血缘仍未完成。Portal 临时 Pod/ConfigMap/SparkApplication 全清理。没有修改 TASK004 的 Spark 代码、Writer、OMOP 或业务 S3。未来 Spark 联调仍需执行 Portal 人工跨 Session 协调规则。

> **2026-10-14 EDT — TASK004 第三个真正独立 NEW_ONLY S3 READY 已发布并完成真实只读核验（尚未 Airflow COMMIT）。** [本轮当前 Handoff](tasks/TASK-004-THIRD-READY-FINAL-ACCEPTANCE-PENDING-2026-10-14.zh-CN.md) / [生成源 Run 38588671004](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588671004)（1 Person、244 Visit）/ [immutable S3 READY Run 38588933989](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588933989) **SUCCESS** / [真实集群与 PG 只读 Run 38589912611](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38589912611) **SUCCESS**。新批 `synthea-new-only-gh-38588671004`、Manifest SHA `22b6c386b5c165e0c9cff3d3ce5fbae2115aee87b4761fc4c11fb43a2c4720b1`；第三批 Claim/Stage/Checkpoint/Writer ledger 全 **0**，旧两批仍 COMPLETED，PG Person207 Visit21690，Airflow DAG paused、Writer KPO 14 Tasks+固定 digest 验证成功。临时高权限 KPO Commit Secret 仍不存在；**第三批 Spark/Writer 真 COMMIT、重复 SKIP 均尚未运行**。继续保持 **TASK004 IN PROGRESS / TASK005 ON HOLD**；不重生源、不重复历史业务写。

> **2026-10-14 EDT — TASK004 Airflow NEW_ONLY Writer 正式接线并在 Main 实际 GitSync + DagBag + 已完成批次安全 SKIP 通过。** [最新 LIVE Closeout](tasks/NEW-ONLY-AIRFLOW-WRITER-LIVE-MAIN-GITSYNC-COMPLETED-SKIP-2026-10-14.zh-CN.md) / [Self-Runner 38583147075](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38583147075) SUCCESS：Airflow 14 Task、新 Writer KPO 摘要已固定、已完成第二批即使双开 `spark_processing:true,writer_commit:true` 仍走 `already_completed_no_replay`，真实 Spark/Writer 均 skipped、DAG re-paused；PG Person207/Visit21690/Claim2 完全不变。**Writer 自动 COMMIT 的源码和编排已就绪，但独立 commit Secret 仍不存在、第三个新 READY 的真正 Airflow COMMIT 还没跑；TASK004 仍 IN PROGRESS。** NEXT 只需第三个新 S3 READY 的 Spark→Writer→PG COMMIT→独立回读→重复 SKIP 最终验收。TASK005 HOLD。


> **2026-10-14 EDT — TASK004 Airflow NEW_ONLY 原子 Writer KPO 已接线，镜像已发布并在 worker02 真实验证。** [最新 Closeout](tasks/NEW-ONLY-AIRFLOW-GATED-WRITER-EXECUTOR-2026-10-14.zh-CN.md) / [Self-Runner 38582267163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38582267163) SUCCESS（53 Landing +58 Writer=111 tests）、[Docker Build 38581579633](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38581579633) SUCCESS。新增人工 `spark_processing:true,writer_commit:true` 双启用 → Spark Handoff 后 `execute_new_only_writer`：真 S3/PG audit、同事务 Claim/Fencing/Person/Visit/完整 Reconcile/COMMIT/独立 PG readback、完成批次 Skip，禁止自动 retry。**当前 commit credential/enable Secret 未部署，没有第三批真实 COMMIT**；PG Person207 Visit21690 Claim2 不变，不重跑前两个 Batch。NEXT Main GitSync+DagBag、第三批真正 NEW_ONLY READY 的安全 Airflow live end-to-end。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 第二个真实 NEW_ONLY Batch 70 Person + 11487 Visit 已正式业务 COMMIT、独立 PG 对账 SUCCESS。** [当前权威 Closeout](tasks/NEW-ONLY-SECOND-BATCH-FIRST-REAL-PG-COMMIT-2026-10-14.zh-CN.md) / [Self-Runner 38575457166](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38575457166)：Person137→**207**、Visit10203→**21690**、两个 Source ID Maps 同步增加、Claim 总数1→**2**，此新批 Claim `COMPLETED`、Stage **11557**、2 VERIFIED Checkpoints，源键与父子键独立 PG readback 全 PASS；103 个回归测试 PASS，重复 Claim 正确 SKIP。上轮 38572127827 仅 Bash 安全断言解析失败、业务无写。**切勿重跑这次一次性 Writer**；原 Airflow DAG Writer KPO 尚未自动接通，Auto Claim 仍关闭。NEXT 新未入库批次的 Airflow Writer 尾端自动化。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 第二个 NEW_ONLY Batch 真实 70 Person /11487 Visit 同事务 Fencing + OMOP 联合 ROLLBACK 成功。** [最新 Closeout](tasks/NEW-ONLY-SECOND-BATCH-FENCED-JOINT-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner 38566745511](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38566745511) SUCCESS：Airflow 已存在新批 XCom + 真实 S3 Parquet + `cdm_reader` 真 PG preflight，原子事务 3 次 Fencing→Person70/Visit11487→整行 DB Reconciliation→强制 ROLLBACK，SQL 无业务 COMMIT，独立 PG Person137/Visit10203/旧 COMPLETED1/新 Claim0、Stage0、Checkpoint0 Before/After 相同，99 tests PASS。无需重跑 Spark；NEXT **新批次第一次真正业务 COMMIT 需单独明确授权**，随后接 Airflow Writer KPO，实现端到端自动入库。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 第二个真实 NEW_ONLY Batch（70 Person / 11487 Visit）Airflow→S3→PG Readonly Precommit 已全绿。** [最新 Closeout](tasks/NEW-ONLY-SECOND-BATCH-REAL-S3-PG-READONLY-PRECOMMIT-2026-10-14.zh-CN.md) / [Self-Runner 38565372429](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38565372429) SUCCESS。复用 PR #130 已成功的 Airflow Spark XCom（Run 38563933551），不再运行 Spark；真实 worker02 Pod 重新 S3 GET Manifest/Patient70/Encounter11487 Processing Parquet，强验证指纹与父子键，再由 `cdm_reader` PG READ ONLY 检查 0 Source ID overlap、Claim ABSENT、Stage/Checkpoint0，独立 PG Person137/Visit10203/旧 Claim COMPLETED 前后不变。95 tests PASS。**下一步只针对该批做联合 Writer 同事务 Fencing ROLLBACK-only，真实 COMMIT 需明确授权**；Auto Claim NO，双 Writer 负载 FUTURE ENHANCEMENT。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 新 SECOND NEW_ONLY READY 的真实 Airflow→Spark Person70/Visit11487→Writer Handoff LIVE PASS。** [最新验收文档](tasks/NEW-ONLY-AIRFLOW-SPARK-FRESH-70-11487-LIVE-HANDOFF-2026-10-14.zh-CN.md) / [Self-Runner 38563933551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38563933551) SUCCESS / Healthcare PR #130 + Runner PR #104 merged。真正 `synthea-new-only-gh-38489944582` S3 READY 经手工 `spark_processing=true` 选取、Claim READ ONLY ABSENT、worker02 v2 Spark Person/Visit/Reconcile，实际 Processing Parquet readback 70/11487 + immutable Writer Handoff PASS；实际 DagRun success、手工结束重新暂停 DAG，90 regressions PASS。**Processing S3 新增 Parquet，但原 READY/Manifest 没有改，PG Person137/Visit10203/Claim1 COMPLETED/新批 Claim0/Stage0 不变，Business COMMIT=NO。** NEXT 已真实生成新批的 `cdm_reader` S3/PG read-only preflight + 受控 Writer ROLLBACK，然后才授权真实 COMMIT；不得重跑 Spark 或旧已提交批次。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 NEW_ONLY Airflow Spark→Writer 动态批次合同与单事务 SQL Renderer 已通过测试。** [当轮权威 Closeout](tasks/NEW-ONLY-AIRFLOW-ATOMIC-DYNAMIC-WRITER-HANDOFF-2026-10-14.zh-CN.md) / [Self-Runner 38562133245](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38562133245) SUCCESS（Claim26/26、Writer42/42、Landing46/46，共114）。既有一次性成功 Writer 逻辑抽取为批次身份绑定的私有原子 Claim→Fencing→Person/Visit→整行 DB Reconciliation→COMPLETED→COMMIT Renderer，历史已提交 Batch 固定拒绝动态重写；新增纯 Airflow Spark XCom→不可变 Writer Handoff。实际业务 SQL **仅 Render、没有执行**；新 DAG 的 `unclaimed_batch_hold` 暂未连接 Spark/Writer，Airflow 自动 Claim 仍 NO。PG 只读 Person137/Visit10203/Claim1 COMPLETED/Stage813/2 Checkpoints 不变。NEXT 共享 Spark 人工协调后接实际 Spark→Handoff、真实新批 S3/PG preflight→受控 Writer ROLLBACK→COMMIT；不重跑历史已完成批次。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 NEW_ONLY Airflow 已完成批次安全跳过 LIVE 全绿。** [正式 Closeout](tasks/NEW-ONLY-AIRFLOW-CONSUMER-COMPLETED-SKIP-REAL-LIVE-2026-10-14.zh-CN.md) / [Self-Runner 38560309400](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38560309400) **SUCCESS** / Runner [PR #102](https://github.com/JohnZhang-DataForge/Self-Runner/pull/102) merged。真实 Scheduler GitSync 与 DagBag PASS；手工 NewOnly DAG Run `success`，COMPLETED 安全跳过、不触发 unclaimed 路线，DAG 测试后已恢复 paused；PG Person137/Visit10203/Claim1/Stage813 以及 2 VERIFIED checkpoints Before/After 不变。52/52 回归 PASS，无 Spark、无自动 Claim、无业务 COMMIT。**NEXT 受控单批新 READY 的 Claim→Spark→Writer 合同/编排，Portal/Spark live 需 Session 人工协调**。旧 Runner XCom 验收 blocker 已解除。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT — TASK004 Airflow NEW_ONLY consumer 第一阶段已经落地，真实 Airflow DagRun success，但 Self-Runner 全部断言未绿。** [最新真实验收及停止交接](tasks/NEW-ONLY-AIRFLOW-CONSUMER-REAL-COMPLETED-SKIP-HANDOFF-2026-10-14.zh-CN.md) / [Runner 38559222216](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38559222216)：Healthcare PR #126 已合并 Main，新 DAG GitSync 字节匹配、DagBag 正式解析。只读 S3 Discovery→真实 PG Claim 检查，已完成 NEW_ONLY Batch 的真实 DagRun `success`，TaskInstance 证实 `already_completed_no_replay=success`、`unclaimed_batch_hold=skipped`，PG Person137/Visit10203/Claim1 无变更。**Runner job conclusion=failure** 因测试错误要求 BranchPythonOperator 的 XCom return_value 非 None。三轮修复后按约定 STOP；Runner 测试 workflow 未合并，下一轮优先仅修复验收断言。**没有自动 Claim、Spark、业务 COMMIT；新 Batch 仍 HOLD。** TASK004 IN PROGRESS / TASK005 ON HOLD，Portal A4 HOLD。


> **2026-10-14 EDT — TASK004 首次真正 NEW_ONLY v2 PostgreSQL 业务 COMMIT 已 LIVE SUCCESS。** [真实首次 COMMIT / Reconciliation Closeout](tasks/NEW-ONLY-V2-FIRST-REAL-PG-COMMIT-RECONCILIATION-2026-10-14.zh-CN.md) / [Self-Runner Run 38555481037](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38555481037)：真实 S3 Processing Parquet Person **1** + Visit **812**，cdm_reader 碰撞预审通过，单 PG 事务中最小权限 role-separated Claim→Fenced Writer Person/Visit→整行 DB Reconcile→Claim COMPLETED→**首次业务 COMMIT**。独立回读 Person136→**137**、Visit9391→**10203**、Map 同增，Claim0→**1 COMPLETED**、Stage **813**、VERIFIED Checkpoints **2**；重复 Claim 冲突路径正确跳过不写入。Claim26/26、Writer37/37 regression PASS。**本批已经真实入库，不能再次当未处理 READY 强制 Writer；尚未 Airflow 自动消费或全链路重复运行。** 不重跑 Spark、Synthea，不修改 S3。NEXT 正式 Claim API SKIP_COMPLETED readback + 单 Writer Airflow 自动化面向新 Batch；双 Writer 并发/复杂 Recovery 改 FUTURE ENHANCEMENT。TASK004 IN PROGRESS / TASK005 ON HOLD，Portal A4 HOLD。


> **2026-10-14 EDT — TASK004 NEW_ONLY 真实 Person 1 / Visit 812 同事务 Writer Fencing PostgreSQL ROLLBACK 已 PASS（仍无业务 COMMIT）。** [当前权威 Closeout](tasks/NEW-ONLY-REAL-S3-OMOP-WRITER-FENCED-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner 38554330163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38554330163) SUCCESS：最小权限 SECURITY DEFINER Function 已持久部署并隔离 cdm_writer Ledger 权限；原有 S3 Processing Parquet 真正 1 Person + 812 Visit 在同一数据库事务以 cdm_writer 有效角色执行前后两次行锁校验、完整 Writer SQL、最终显式 ROLLBACK。Claim fixture **仅当前事务暂存**、真实 READY 仍未正式 Claimed；PG Person136/Visit9391/Claim0 等 Before/After 不变。未重新运行 Spark/Synthea、未动 S3、未开启 Airflow Auto Claim、未做业务 COMMIT。NEXT 单 Writer 受控正式 Claim→真实 COMMIT→独立 DB Reconciliation→幂等重放（正式 COMMIT 另需授权）；双 Writer 并发与复杂恢复下调 FUTURE ENHANCEMENT。TASK004 IN PROGRESS / TASK005 ON HOLD，Portal A4 HOLD。


> **2026-10-14 EDT — NEW_ONLY Writer SECURITY DEFINER 最小权限同事务 Fencing 候选，真实 PG ROLLBACK PASS（尚未部署）**：[正式验收与限制](tasks/NEW-ONLY-WRITER-SAME-TX-LEAST-PRIVILEGE-FENCE-REAL-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner Run 38551210536](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38551210536) SUCCESS：Claim 26/26 + Writer 30/30 测试；真实 cdm_writer 无 Claim 直读，但可通过隔离 NOLOGIN Owner 的 SECURITY DEFINER 在**同事务**锁 Claim 并验证 Owner/Attempt/Manifest/Lease；合成 Claim/角色/Schema/Function **全部 ROLLBACK**，Person136/Visit9391/Claim0 不变。**未持久安装 DB 函数、未真正重跑 Person1/Visit812、未多会话并发或正式业务 COMMIT**。NEXT DB DDL 安全审查/真实并发竞争/受控 fenced Writer ROLLBACK。TASK004 IN PROGRESS、TASK005 ON HOLD、Portal A4 HOLD。


> **2026-10-14 EDT — TASK004 NEW_ONLY Claim Owner/Attempt/Lease Fencing v1 真实 PostgreSQL ROLLBACK PASS（**非**正式 Writer COMMIT）。** [最新正式 Closeout](tasks/NEW-ONLY-CLAIM-LEASE-TOKEN-FENCING-REAL-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner 38529634738](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38529634738) SUCCESS：Claim 26/26 + Writer 25/25 regressions，worker02 真 `landing_claim_worker` 合成批次测试 NOWAIT 行锁/Lease Owner/Attempt/Manifest/Heartbeat/过期拒绝/FAILED HOLD/旧 token 拒绝后 ROLLBACK；PG 真实 Person136/Visit9391/Claim0、新批 Ledger/Stage/Commit0 Before/After 不变。Healthcare #121 / Self-Runner #98 merged；**真正 READY 未 Claim，Writer 未绑定同事务权限锁，COMMIT NO**。NEXT cdm_writer 同事务数据库权限隔离 Fencing（防跨连接 TOCTOU）+ 并发负例 → 再 COMMIT/Reconciliation/幂等。TASK004 IN PROGRESS / Portal Spark A4 HOLD / TASK005 ON HOLD。

> **2026-10-13 EDT / 2026-10-14 UTC — TASK004 NEW_ONLY v2 真实 S3 → OMOP Writer Person+Visit 单 PostgreSQL 事务正向 ROLLBACK 已 LIVE PASS！** [正式 Closeout](tasks/NEW-ONLY-V2-OMOP-WRITER-JOINT-PG-ROLLBACK-REAL-LIVE-2026-10-13.zh-CN.md) / [Self-Runner 38508357752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508357752) SUCCESS：真正处理上轮 Person=1、Visit=812 Parquet，cdm_reader 预审 PASS，cdm_writer 一次 BEGIN → Person→Visit→联合核验→ROLLBACK PASS。PG Person=136、Visit=9391、两个 ID Map、Claim/Batch Ledger/Stage/Commit 表行前后均不变；**PG sequences 可能因 nextval() 前进（不受回滚）**。Healthcare PR #119 / Self-Runner PR #97 merged，旧冲突 Writer PR #109 由 #119 取代关闭。**NEXT Claim owner/lease fencing + 受控一次性 COMMIT/幂等 Reconciliation；当前未 COMMIT。** Portal Spark A4 仍 HOLD。TASK004 IN PROGRESS / TASK005 ON HOLD。

> **2026-10-13 EDT / 2026-10-14 UTC — TASK004 NEW_ONLY v2 Airflow→Spark Person/Encounter→Processing Parquet→Reconciliation 真实 PASS。** [正式 Closeout](tasks/NEW-ONLY-V2-AIRFLOW-SPARK-PERSON-VISIT-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner Run 38505927396](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38505927396) SUCCESS：独立 READY v2 Batch `synthea-new-only-gh-38497355290` 实际 Airflow 8/8 Task SUCCESS、Spark Person=1/Encounter=812、真实 Processing Parquet 双 URI/XCom/Readback/Reconcile PASS。真实 PG Person=136/Visit=9391/Claim=0 前后不变。Healthcare PR #116、Self-Runner PR #96 merged。**NEXT Writer 真实联合事务 ROLLBACK，尚未 COMMIT，Claim NO。** Portal A4 共享 Spark HOLD / 需人工协调继续生效。TASK004 IN PROGRESS / TASK005 ON HOLD。

> **2026-10-13 EDT / 2026-10-14 UTC — NEW_ONLY v2 Spark Source Bridge worker02 实测通过（尚未运行 Spark）**：[完整 Closeout](tasks/LANDING-PROCESSING-V2-SOURCE-BRIDGE-WORKER02-LIVE-2026-10-13.zh-CN.md) / [Self-Runner 38503213376](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38503213376) SUCCESS：38 测试 PASS、不可变新镜像 `healthcare-landing-processing-v2@sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937`，真实 worker02 读 v2 Patient=1/Encounter=812 与 v1 73 Person 均 PASS。Healthcare PR #112 / Self-Runner PR #93 merged。**当前 NEXT：新的 v2 Airflow manual Processing-only 真 Spark/Parquet；Claim NO、SPARK_APPLICATION 尚未执行、PG DML NO。** TASK004 IN PROGRESS / TASK005 ON HOLD。

> **Portal 正式入口（Marquez + OpenLineage）**：[platform-portal 文档](platform-portal/README.md) → [**多 Session 人工协调规则（必读）**](platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md) → [架构](platform-portal/architecture.md) → [部署与恢复](platform-portal/deployment-guide.md) → [真实验收](platform-portal/validation.md)。Marquez + PostgreSQL14 已部署，A3 Airflow OpenLineage Task/Run 已成功验收。**TASK004 另一 Session 正在开发 Spark：Portal A4 只做静态开发，任何共享 Spark/Airflow 运行或变更必须先问用户对方是否暂停并释放资源，再只读核验；未确认时 HOLD，不擅自启动 Workflow/Pod。**

> **2026-10-13 EDT / 2026-10-14 UTC — FIRST REAL NEW_ONLY V2 S3 READY + AIRFLOW XCOM LIVE PASS。** [最新权威 Closeout](tasks/SYNTHEA-NEW-ONLY-FIRST-REAL-V2-S3-READY-AIRFLOW-2026-10-13.zh-CN.md) / [真实 Synthea 生成 Run 38497355290](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497355290) / [v2 S3 发布+重放 Run 38497549237](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497549237) / [实际 Airflow XCom Run 38497724825](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497724825) 全 SUCCESS。真 NEW_ONLY Batch `synthea-new-only-gh-38497355290` 为 1 Person / 812 Encounter / 18 CSV，其中确实 1 个合法 header-only 辅助 CSV；S3+PG 历史 source-ID 冲突均 0，v2 `manifest_version=2.0` 的 immutable Manifest SHA `dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`，首次 `PUBLISHED_NEW`、独立 18/18 SHA 回读、原始请求幂等 `REUSE_EXISTING` 及 Airflow 真 DagRun XCom 相同 SHA 均 PASS，Claim NO、Spark skipped、PG DML NO。历史两个 v1 READY 均不变；现有**2 个 v1 + 1 个 v2 READY**。Healthcare PR #107、Self-Runner PR #91 merged。**NEXT**：把通用手工 NEW_ONLY Workflow 升级到已验收 v2 镜像的版本化选择，再独立扩展 Airflow Claim/Spark/Writer 与 COMMIT 安全验证；TASK004 IN PROGRESS，TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC — 实际运行中的 Airflow Landing v2 Reader 已完成 LIVE 升级验收。** [完整中文 Closeout](tasks/LANDING-AIRFLOW-V2-READER-REAL-DAGRUN-LIVE-2026-10-13.zh-CN.md) / [真实 Airflow Run 38496119114](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38496119114)：Healthcare PR #104、Self-Runner PR #89 merged。官方既有 GHCR 镜像精确 digest `sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924`，worker02 现有 KPO ServiceAccount 无临时 token 拉取 PASS，S3 旧 73/70 Person 两个 READY 完整兼容 PASS；scheduler GitSync 文件 SHA、DagBag 新镜像和 Claim NO PASS；实际无参数 DAG Trigger success，scan + Claim Guard success，全部 Spark/Recon skipped。**重要 NEXT**：新版 Consumer 已部署，但 `contracts/synthea/new-only/csv-contract-v2.json` 发布标记仍关闭，未存在真实 v2 S3 READY。先版本化审核解除 v2 Publisher 安全发布门槛，再从新的实际 Synthea 小人口请求进行源键防撞、18 CSV/Manifest S3 READY、回读重放。不开放 Writer/COMMIT，TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC NEW_ONLY v2 不可变 Publisher 代码及真实安全门槛验收 PASS，但尚未发布实际 v2 READY。** [最新 Closeout](tasks/SYNTHEA-NEW-ONLY-V2-PUBLISHER-STAGED-LIVE-2026-10-13.zh-CN.md) / [Self-Runner Run 38492827750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38492827750) SUCCESS（42 单元测试 + Fake S3 18 文件上传/最终 Manifest PUT/同 SHA 重放 + 真实 worker01 70 人原始 CSV v2 Draft 和 v2 未部署发布拒绝）。新 GHCR digest `sha256:4a456ee4f186bcfdcf5e22c6477ac92ce32941ca4bae9ba685b0b1a2ca3840c5`；Healthcare PR #102 / Self-Runner PR #88 merged。**AIRFLOW_CONSUMER_V2_DEPLOYED=NO、REAL_S3_V2_READY=NO**；不能将合成数据合同测试当成真实 v2 S3 批次。NEXT：实际运行中的 Airflow v2 Discovery/Resolver 升级/Live 回归，再按版本化合同解开 Publisher 发布门槛、生成真实有辅助 0 行的 Synthea Request 完成 S3 v2 PUT/readback/replay。旧 v1 和 PG Writer / Drift Gate 未动，TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC NEW_ONLY v2 Reader 严格兼容已真实验收 PASS（不代表 v2 S3 READY）。** [Closeout](tasks/SYNTHEA-NEW-ONLY-V2-CONSUMER-READER-LIVE-2026-10-13.zh-CN.md) / [Self-Runner Run 38491626783](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38491626783) / Healthcare PR #100 / Self-Runner PR #87：33 tests PASS、严格 18 CSV header/schema/contract SHA、16 辅助 CSV 可以合法 0 row、Person/Encounter 必须非空且 NEW_ONLY 专属 Batch ID，原 v1 Validator/Resolver 默认路径未放宽；新专用 Reader 镜像 GHCR digest `sha256:d53a706feba8aff30375836f84c9228d22e61aa35578349b01ddcb1b5d532350` 已 push、worker01 对原 73+70 Person 两个真实 v1 READY 各自 18/18 GET SHA 验收 PASS。**V2 Publisher / 真正 v2 S3 READY / Airflow runtime Consumer V2 部署均 NOT YET**，保持 `HOLD_V2_CONSUMER_REQUIRED` 和 Claim NO。NEXT 实施独立 v2 不可变 Publisher、真实含零行辅助表 NEW_ONLY Batch 发布及 Airflow 实际 v2 Consumer 升级；DB Writer/Drift 保留，TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC NEW_ONLY 独立 Digest Runtime 和第二个真实 READY PASS**：[完整 Closeout](tasks/SYNTHEA-NEW-ONLY-DIGEST-RUNTIME-SECOND-READY-LIVE-2026-10-13.zh-CN.md) / [镜像 Build Run 38490227474](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38490227474) / [新批次回读与重放 Run 38490367050](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38490367050)。最终 `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:36b69a26f25f9b627da693fc1aa70b8d0a37de0af755bcb7d95d140568efa909`，29 tests PASS；新持久化 `synthea-new-only-gh-38489944582` Person=70/Encounter=11487，S3 READY Manifest SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`，实际 PUBLISHED_NEW 后 REUSE_EXISTING 同 SHA，18/18 GET PASS；再加旧 73 人 READY，现已有**两个**独立真实 READY 批次。Self-Runner Main 新增可手工 Run workflow 的 `Synthea NEW_ONLY - Run New Independent Request`，**该 Main Dispatch 本身尚未单独触发实测**。新的 1～100 人若辅助表合法零行则 HOLD 等待 v2 Consumer；旧 Writer/PG Existing Target Drift 无更改，TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC — 首个 Synthea NEW_ONLY 不可变 S3 READY 已真实 PASS。** [完整 Closeout](tasks/SYNTHEA-NEW-ONLY-FIRST-REAL-S3-READY-2026-10-13.zh-CN.md) / [Self-Runner Run 38488453236](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38488453236)：固定 PVC Batch `synthea-new-only-gh-38484300008`，Person=73、Encounter=12159、总 CSV bytes=119147940，旧严格 v1 Contract **18/18 全非空 PASS**，SeaweedFS S3 **首次 PUBLISHED_NEW → 逐文件 GET SHA256 18/18 → 最后 Manifest `INTAKE_VERIFIED`**，独立既有 v1 Discovery/Resolver 再读 PASS，重放 `REUSE_EXISTING` 同 SHA `66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9`。没有重新生成 Person；没有 Postgres DML、没有 Airflow 自动 Claim。**NEXT：独立 NEW_ONLY image digest/任意新 request 的自动生成-发布闭环 + 小人口 v2 Consumer；然后 Airflow 新批 claim/Spark/DB Writer ROLLBACK/COMMIT 的单独门槛。** 下文关于 NEW_ONLY「尚未上传 S3」为旧时点事实。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 三独立 Generator 命名冻结**：`synthea-new-only-`（现有本地生成已验证）、`synthea-update-only-`（既有人更新，ON HOLD）、`synthea-mix-data-`（新旧混合，ON HOLD），[版本化 Batch ID 合同](../contracts/synthea/producer-batch-identity-v1.json)及[架构命名修订](architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)。SeaweedFS PV 不是 Synthea 的存储前置依赖：`synthea-local` Retain / worker01 `/data/synthea/` 已持久验收，剩余容量监控不是 NEW_ONLY S3 发布前的无条件阻塞。**未开放新前缀 Writer 权限，旧 `task004-airflow-` 仍按原样安全拒绝**。当前 NEXT 仍是固定 73 Person 批次的严格 v1 CSV 验证和受控独立 S3 发布；TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 NEW_ONLY 全局源 ID 发布前安全预检 LIVE PASS（尚未 S3 READY）**：[正式 Closeout](tasks/SYNTHEA-NEW-ONLY-PREPUBLISH-SOURCE-IDENTITY-LIVE-2026-10-13.zh-CN.md) / [Self-Runner Run 38486092750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38486092750) / Healthcare PR #89。现存 LocalPath Batch `synthea-new-only-gh-38484300008` 真正 73 Person/12159 Encounter，18 CSV 全部非空，历史 S3 14 个 Person/Encounter CSV + PG Person map 136/Visit map 9391 源 ID overlap 均 **0**；只读核验 PASS 不等于 S3 READY/PG COMMIT。已开发 NEW_ONLY versioned v2 Contract 和 streaming prepublish gate，但当前运行 Consumer 仅 v1，因此 **NEXT 首选用这个非空批次验证既有 v1 严格 Validator，再做独立 Immutable S3 Payload→Readback→最后 Manifest 发布**；未来空表要另走版本化 Consumer。PG Writer Existing Target Drift 保留，TASK004 IN PROGRESS，TASK005 ON HOLD。


> **2026-10-13 独立 NEW_ONLY Generator 的 LocalPath 阶段已经真实 PASS**：[完整 LIVE Closeout](tasks/SYNTHEA-NEW-ONLY-LOCAL-GENERATOR-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner Run 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008) / Healthcare [PR #87](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/87)。worker01 `/data/synthea/` 的 `synthea-local` Retain SC、5Gi Bound PVC 已部署，真实 Synthea v3.3.0 独立 Job 生成 Person **73**、Encounter **12159**、CSV **18/18**，第二 Pod same request 固定重放 PASS；8 单测通过。**这还不是全局 Source ID 无撞车 / 完整 S3 READY Producer**：仅 NEW_ONLY 本地注册表防撞；未验证 PG 历史 source keys、未上传 S3、未发布独立镜像 Digest、未执行 Writer；NEXT 是 versioned 18-CSV Landing 合同与全局源键只读核验 → immutable S3 READY。TASK004 IN PROGRESS；TASK005 ON HOLD。


> **2026-10-13 NEW_ONLY NEW-A 真实只读预检已通过（并记录阻塞）**：[worker01/Contract Preflight](tasks/SYNTHEA-NEW-ONLY-READONLY-PREFLIGHT-2026-10-13.zh-CN.md) / [Self-Runner Run 38481854395](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38481854395)：worker01 Ready、`dw-synthea` 存在，但专用 PVC=0；默认 `local-path` reclaim=`Delete`、实际独立磁盘与容量未确认；18 CSV V1 全表非空、历史 20/50 限制，新 ID 被 Writer V1 正确拒绝。**NEW-A AUDIT PASS ≠ NEW_ONLY READY/DEPLOYED**；后续先补 host mount/Secret 名称核验与 Retain 卷方案，再做 NEW-B；没有生成、S3 发布或 PostgreSQL COMMIT。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **新 Session 的唯一最新交接（2026-10-13）**：先读 [当前 TASK004 Agent Handoff](tasks/TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md) → [用户已批准的 Producer/Consumer 解耦架构](architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md) → [最新真 S3→Writer 验收](tasks/OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md)。**旧累积式 Handoff 的多个“CURRENT NEXT”已归档**。当前准确状态：Airflow Discovery/Claim 只读、手动历史 Spark PASS；真正新 Batch Claim 自动消费未启用；PG Writer 真 S3 漂移拦截 PASS、无冲突真实正向 ROLLBACK 和 COMMIT 均未完成；新 Generator NEW_ONLY 仅设计获批、未部署。NEXT：先做 worker01 NEW_ONLY 只读前置审计和 Writer Plan ID 版本兼容预检，再制造真正无撞车 S3 READY Batch，用于第三层正向 ROLLBACK。TASK004 IN PROGRESS、TASK005 ON HOLD。以下旧阶段 banner 请看对应历史 Closeout，**不能作为最新 NEXT**。


> **2026-10-13 第三层 Writer 真 S3 接线已验收“预期冲突阻断”，而非成功 ROLLBACK 正例。** [OMOP S3→PG Gate 实测](tasks/OMOP-WRITER-REAL-S3-PG-ROLLBACK-GATE-2026-10-13.zh-CN.md) / [Self-Runner Run 38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382)：真实 SeaweedFS immutable Manifest SHA/Person 23 + Visit 3588 Parquet PASS → 固定 CDM Writer Runtime 实际连 PG，预期 `BLOCKED:EXISTING_TARGET_DRIFT` PASS → 独立读回 Person=136/Visit=9391/Claim=0、该 Batch Ledger/Stage/Commit=0，**无数据持久化**。**该 Run Workflow SUCCESS 仅表示安全拒绝正确，Writer Job 没有完成整笔 ROLLBACK 正例，COMMIT 禁止。** 当前下一步是取得真正无 Source ID 撞车的 NEW_ONLY 批次（并处理 Writer Plan 的旧 `task004-airflow-` ID 依赖），然后 Person→Visit 真 S3-to-PG 成功 ROLLBACK→Claim fencing→COMMIT/对账；不能拿旧批强行入库。Task004 IN PROGRESS / Task005 ON HOLD。下方旧 NEXT 为历史阶段。


> **2026-10-13 第三层 OMOP Writer 最新进度：NEW_ONLY Pre-COMMIT 安全门槛已通过真实 PostgreSQL 只读验证。** [OMOP Writer Precommit Live Closeout](tasks/OMOP-WRITER-PRECOMMIT-SAFETY-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner Run 38478501009](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38478501009) SUCCESS：9 个 Unit Tests + worker02 真 PG `cdm_reader` 读-only，证明源 Person ID 撞车、历史 batch、未领取 batch 均会被拦截；Reader 仅新增对 `etl.landing_batch_ledger` 的 SELECT 权限，CDM Person=136/Visit=9391、新 Ledger=0 前后不变。**正例是人工构造的测试行/计划，不是 S3 新 Batch，COMMIT 仍 NOT IMPLEMENTED。CURRENT NEXT = 真 S3 Processing→安全 PG ROLLBACK & 独立 Writer Runtime，之后才受控 COMMIT、DB 对账和自动消费；旧历史 S3 重合数据不可强行入库。** TASK004 IN PROGRESS、TASK005 ON HOLD。以下旧 NEXT 已过时。\n\n
> **2026-10-13 最终最新状态：Landing → Spark Person/Visit → Processing Reconciliation 已通过真实 Airflow 手工历史批次验收。** 详见 [Landing Spark LIVE Closeout](tasks/LANDING-SPARK-PROCESSING-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452)：真实 Main GitSync、Airflow 3 DagBag、手工 DagRun **8/8 TaskInstance SUCCESS**（Scan、Claim Guard、Manual Gate、Patient Spark、Encounter Spark、Spark Reconcile、最终 Processing 验证）。在真实 S3 历史批次 `task004-airflow-task004-step03e-38324111846` 上重新生成独立 Processing 结果；**不调用 Generator，不修改 OMOP：Person=136 / Visit=9391 / Claim Ledger=0 前后不变**。最初两轮 Live 分别遇到 Airflow 3 GitSync helper 导入路径与 Jinja 手工 JSON conf 解析问题，分别通过 [PR #80](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/80) / [PR #81](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/81) 修复，第三轮 PASS。**当前每15分钟定时流程只扫描+评估，Spark 是经显式 manual opt-in 的历史 Processing-only 重放；实际新 Batch Claim 仍关闭、Writer COMMIT 未实现。NEXT 是安全新批 Claim / Spark 自动消费所需的完整队列、Source ID 防撞和动态 PG Writer 事务。TASK004 IN PROGRESS、TASK005 ON HOLD。** 以下旧 NEXT 均为历史记录。\n\n
> **2026-10-13 最新真实验收：S3 Discovery 已与 PostgreSQL Claim Guard 在同一个 15 分钟 Airflow DAG 正式串联。** [Landing Discovery→Claim Live Closeout](tasks/LANDING-DISCOVERY-TO-CLAIM-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [真实 Airflow Run 38471287896](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38471287896) **SUCCESS**：`scan_ready_manifests → evaluate_batch_claims` 两个 KPO Task 均 success；Main GitSync SHA/真实 Scheduler DagBag PASS；PostgreSQL 独立读回 Claim Ledger=0、OMOP Person=136、Visit=9391 不变。Claim 持久化目前**故意关闭**（`CLAIM_ENABLE=NO` / 空 allowlist），因为 Spark/Writer 尚未对接，也防止自动误领已入库的 6 个历史 S3 Batch。此阶段完成**实际接线/历史排除验证**，没有 CLAIMED 真实批次、没有 Spark、没有动态 PG COMMIT。**当前 NEXT = 受控 Landing Consumer → Spark Person/Visit → Writer 安全设计及单批闭环**，不是重新实现 Discovery/Claim。TASK004 IN PROGRESS、TASK005 ON HOLD；以下旧 NEXT 已过时。


> **2026-10-13 最新开发：Landing Batch Claim / Processing Ledger 安全核心已实际验证。** [真实 PostgreSQL ROLLBACK Closeout](tasks/LANDING-BATCH-CLAIM-ROLLBACK-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner Run 38468961485](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468961485)：在 `omop` 新增独立 `etl.landing_batch_ledger`、`landing_claim_worker` 最小权限身份 + K8s Secret（确有 DB schema/role 持久变更），12 tests PASS，真实 worker02 PG 独立领取/重复 BUSY/身份漂移/FAILED 显式重试/旧 token/过期 lease 等 ROLLBACK 验收；模拟记录没有持久留下，CDM Person=136 Visit=9391 未变。**现有 `landing_batch_discovery` 仍然只做 S3 Inventory，并未自动调用 Claim 或 Spark、PG Writer。新 CURRENT NEXT = 独立 Consumer Claim 接线/历史批次保护，再逐步 Spark / Dynamic PG COMMIT。** 以下旧 NEXT 已过时。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 最新已完成：真正独立的 Landing S3 Discovery 已接入 Airflow 3 并启用每 15 分钟调度。** [权威 Live Closeout](tasks/LANDING-BATCH-DISCOVERY-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner 实际 DagRun Run 38466518057](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38466518057)：GHCR 独立 digest 镜像、13 Tests、真实 Scheduler DagBag、main GitSync exact source、`landing_batch_discovery` DAG 可见+无导入错误、`*/15` 调度已解除暂停、一次真实手工 DagRun + KPO Task = **success**，无 Generator/Spark/PG mutation。**新 CURRENT NEXT = Landing Batch Claim / Ledger（并发、SHA、SKIP/RETRY）；不是再做 S3 Discovery，也不是 NEW_ONLY Generator**。此步骤只发现 Inventory，尚未自动处理数据/动态 COMMIT，TASK004 IN PROGRESS、TASK005 ON HOLD。下方旧 NEXT 均是历史快照。


> **2026-10-13 最新开发进度 / 新优先级（当前 NEXT）：S3 READY Batch Discovery 核心逻辑已通过真实 SeaweedFS 只读验证。** [实测 Checkpoint](tasks/LANDING-BATCH-DISCOVERY-READONLY-CHECKPOINT-2026-10-13.zh-CN.md) / [Self-Runner Run 38460137577](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38460137577)：8 单元测试 PASS、6 个 verified READY Batch、1 个旧格式 Manifest 隔离、K8s worker02 Pod 真实读取、**DAG_TRIGGER=NO / DATABASE_MUTATION=NO**。用户正式批准**先完成 Airflow S3 消费侧**：新 NEXT = 以业务语义命名的 `landing_batch_discovery` 定时 Airflow DAG + 独立发现镜像 / Secret / 实际 Airflow 验收；**此 DAG 还没开发/部署**。之后才完成 PostgreSQL 动态 COMMIT + DB Reconciliation。Synthea NEW_ONLY 仍是独立后续工作，非当前唯一 NEXT。历史编号命名保留为冻结源码，**新模块按功能命名**。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 架构决议（最高优先级；覆盖本文历史 Airflow generate_publish NEXT）：Synthea 独立 Producer / Airflow 仅按时读取 S3 verified Manifest，完全解耦。** **不是**由 Airflow 向 Synthea 传随机 Seed/人口/州，也**不是** Airflow 运行/重试时重新生成数据。用户要求三套各自独立的 Kubernetes Job/Pod、业务代码/镜像（NEW_ONLY、EXISTING_ONLY、MIXED），只先开发 **NEW_ONLY**（人数随机 1～100，随机州、Seed、当次日期）；Synthea 在 worker01 / dw-synthea 使用待验证的**专用 LocalPath 磁盘/PVC**保存自身恢复状态，发布后 SeaweedFS verified Manifest 为数据交换接口。**已批准设计，尚未部署新 Pod/PVC/DAG、未生成新批次或写库。** 下一步只执行 [NEW_ONLY 实施 NEXT](tasks/TASK-004-INDEPENDENT-GENERATOR-NEW-ONLY-NEXT-v1.0.zh-CN.md)，完整设计见 [独立 Generator & Airflow S3 Consumer 架构 v1.0](architecture/TASK-004-INDEPENDENT-SYNTHEA-GENERATORS-AND-AIRFLOW-CONSUMER-v1.0.zh-CN.md)。历史 STEP03E 的四任务 DAG 和旧 CDM 计划原样保留为验收证据，绝不当作新架构已实现；**TASK004 IN PROGRESS、TASK005 ON HOLD**。


> **2026-10-13 最新技术排查：Synthea Seed / Reference Date Source ID 冲突根因已通过真实 READ-ONLY AUDIT 验证。** 见 [根因验收文档](tasks/TASK-004-STEP04F-SYNTHEA-SEED-REFERENCE-DATE-ROOTCAUSE-READONLY-CLOSEOUT.md) 和 [Self-Runner Run 38447127571](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38447127571)。两批 23 人的 seed/clinician_seed 均为 `20261012`，唯一不同的生成入参是 reference_date（20261012→20261013）；原始 23/23 Patient Id 完全重合，23/23 BIRTHDATE 恰好 +1 天；OMOP 只在 23 人的 `birth_datetime` / `day_of_birth` 存在漂移。**新 NEXT = 明确跨批次 Seed/Source ID 与 batch replay 固定 Reference Date 策略；不是重新调查、不是新批次运行。Person Writer 继续 BLOCKED，不允许 COMMIT；TASK005 ON HOLD。**下文旧 NEXT 段落保留为历史说明。


> **2026-10-13 最新进度：STEP04F Person Source-ID READONLY AUDIT = PASS。** [实时证据 Closeout](tasks/TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md)：Self-Runner [Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614) SUCCESS；新批次 23 个 Source ID 全部存在于 mapping、相同 Person=0、不同 Person=23、新 Person=0、dangling=0；失败批次 ledger/stage/commit=0/0/0。Self-Runner [PR #69](https://github.com/JohnZhang-DataForge/Self-Runner/pull/69) 已合并。**目前唯一 NEXT = 下一轮审查 Synthea Seed / Reference Date 与 Source ID 批次隔离策略（仍需单独授权）；禁止 Writer COMMIT、禁止开始 TASK005。**下文旧“修复只读审计”和 STEP04A NEXT 均为历史记录。

> **2026-10-13 当前状态更新：先读 [TASK004 最新 Agent 交接](tasks/TASK-004-AGENT-HANDOFF-CURRENT-2026-10-13.zh-CN.md)。** 新 Synthea 全流程已 PASS（Person 23/Visit 3588），新批次 Person Writer 因 EXISTING_TARGET_DRIFT 正确拒绝；最新只读审计 Run 38434861465 因 Python 模块路径错误 FAILURE。**唯一 NEXT = 修复只读审计并得出 Source ID overlap 汇总；本文后面旧“STEP04A NEXT”已过时，不是新 Agent 的开工点。**


> **CURRENT / 2026-10-12 EDT（2026-10-13 UTC 审计）**。本目录是新 Agent 的唯一文档入口。历史资料移入 `docs/archive/YYYY-MM-DD[-topic]/`，**不要将 Archive 的 NEXT / Candidate / Pilot 状态当成当前状态**。

## 按顺序阅读

1. [当前 TASK 状态与下一步](tasks/TASK-STATUS.md)：当前主线真实完成什么、下一步是什么。
2. [TASK004 Person/Visit OMOP 入库与同批次幂等实施计划](tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)：**当前唯一 NEXT = STEP04A READ ONLY**，提供 Agent 可直接开工的步骤、风险、验收矩阵和 DB 安全门槛。
3. [TASK004 MVP 历史 Final Closeout](tasks/TASK-004-FINAL-CLOSEOUT.md)：真实 DAG/Runner 验收、三轮只读集群审计、关闭边界与未执行项。
4. [TASK005 Condition 开发方案 v1.0](tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md)：下一业务任务的设计基线、Processing/DB 分段授权与 STEP00 唯一开工入口。
5. [STEP03E End-to-End Acceptance](tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md)：Synthea→Landing→Person/Visit→Reconcile；本次正式验收。
6. [TASK004 Airflow Processing Orchestration Mainline Closeout](tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md)：GitHub → git-sync → Airflow → Person/Visit → Reconcile 正式主线验收。
7. [TASK004 Batch Reconciliation Mainline Closeout](tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md)：Reconciliation 正式主线验收证据。
8. [正式双仓库开发操作手册](development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)：Healthcare feature PR → exact SHA → Self-Runner / ARC → PASS → Merge → post-merge validation → Checkpoint。
9. [Agent 开发 Skill](skill/SKILL-cn.md)：一步一验、canonical source、数据安全、Git 与文档治理。
10. [通用开发经验](runbooks/development-lessons-cn.md) 与 [TASK004 专项经验](runbooks/development-lessons-task004-cn.md)。
11. [当前总架构（中文）](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.zh-CN.md) / [English](architecture/Healthcare-Data-Platform-Architecture-and-Implementation.v4.en.md)。
12. [文档生命周期规范](development/DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md) / [历史归档](archive/README.md)。

## 当前主线状态

**TASK004 overall status = IN PROGRESS（完整 OMOP 入库闭环）**。原 STEP03E Processing MVP 仍 COMPLETE/FROZEN，历史人工只读集群审计见 [`TASK-004-FINAL-CLOSEOUT.md`](tasks/TASK-004-FINAL-CLOSEOUT.md)；但 **Airflow 同批次 Person + Visit PostgreSQL CDM 入库、数据库对账与同批次幂等重放尚未完成**。当前唯一 NEXT 是 [TASK004 STEP04A READ-ONLY PRE-FLIGHT](tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)。TASK005 Condition ON HOLD。

```text
Synthea generation          PASS
Landing publication         PASS
Generic lineage resolver    PASS
Control runtime             PASS
Standalone Person           PASS
Standalone Visit            PASS
Batch Reconciliation        PASS / MAINLINE ACCEPTED
Airflow Processing           PASS / MAINLINE ACCEPTED
Airflow upstream ingestion   PASS / STEP03E BUSINESS ACCEPTED
Self-Runner STEP03E validation   PASS / MAINLINE MERGED
```

以下是历史 STEP02 Processing 正式主线验收（STEP03E 新结果见上方新增 Closeout）：

~~~text
Healthcare main = 5e043b8f00d89a01b72ae6264f35903ceff93de9
DAG = task004_processing_pipeline
Airflow = 3.2.2
Kubernetes provider = 10.17.1

Self-Runner live Run = 38311805385
Artifact = 11775098927
Digest = sha256:570901ce456778457fecc3a1c718ea88aa9ea9dafe8281028e917b3f678cf0ed

Person    success
Visit     success
Reconcile success
DAG run   success

Successful SparkApplication residual = NO
Successful control Pod residual       = NO
PostgreSQL mutation                    = NO
~~~

Post-merge git-sync exact source、default unpaused 和 runtime unpaused 均已再次验证 PASS。

Batch Reconciliation 已完成正式主线验收：

```text
Healthcare PR #24
tested PR HEAD = ee16f5265b0ebb8c30e7e65ec665215613956e77
Healthcare merge/main = 91d96f436e7697d70025cc1c9a045ecfb20f41b1

Self-Runner pre-merge Run  = 38287060452
Self-Runner post-merge Run = 38287401518
Self-Runner PR #31 merge   = 8ab26784cd0229cce96989e3691c122049e3c23a
```

两个真实 Spark reconciliation 都 PASS；20 Patient、2459 Encounter、0 orphan；Processing/PostgreSQL 均无 mutation；成功临时 K8s 资源独立确认已清理。

测试期 Candidate Status 已按文档治理规则原文归档，不再是 current 状态。

## TASK004 当前完整流程新定义（后续执行请先看这里）

- 用户正式完成标准：Synthea → verified Landing → Person/Visit Processing → **PostgreSQL OMOP Person/Visit 入库** → 独立数据库 Reconciliation；**相同 batch_id/manifest SHA replay、失败恢复逻辑上幂等**。
- **TASK004 原 STEP03E 已验收，仅 Processing MVP CLOSED，不能当作完整 CDM 终验**。旧 DB 的 Person=113、Visit=5799 是独立历史数据，不能算此次 Airflow 23/3592 已入库。
- 新计划：[`TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`](tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md)，STEP04A–04H，**只授权 STEP04A 只读盘点**。任何新的 PG/S3/K8s mutation 或 Live Run 必须另行明确批准；禁止原样重跑旧 TASK003 一次性加载脚本。
- **TASK005 Condition 设计保留但 ON HOLD**；直到 TASK004 CDM 入库与重放验收真正 PASS。

## 历史 STEP03E Processing MVP 验收证据与新目标衔接

**真实 Airflow 业务链已 PASS。** Generate → Landing verified → Person (23) / Visit (3592) → Reconcile：Airflow run `task004-step03e-38324111846` 四个 Task 和 DAG 都 success。原始 GitHub workflow 因后置 XCom 取证返回 failure；独立 post-success Run `38326695107` 已 PASS。

STEP03E **当时验收的 Healthcare 源码 SHA**：`d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`。当前 `main` 可以继续前进，新 Agent 须实时查询 GitHub HEAD，不能把此历史 SHA 当成今天的 `main`。

Self-Runner PR #38 已合并到 main（`6f72c05ad8eb1a0abeb19f3cff9e89ac698cff87`），post-merge 只读 Run `38328600074` 已 PASS；Self-Runner PR #39 的历史只读 SHA gate 修复亦已合并，post-merge Run `38329852476` = SUCCESS。本 STEP03E 收尾已包含 Self-Runner 正式验证与文档归档；TASK004 Final Audit 又确认 Airflow Metadata、git-sync 源码、成功运行资源清理及 `dw-seaweedfs` S3 健康，**在原限定 Processing MVP 范围内历史关闭**，见 [MVP Final Closeout](tasks/TASK-004-FINAL-CLOSEOUT.md)。**Phase E 的第一实体已确定为 TASK005 Condition，设计与分步验收方案已形成；实施尚未开始**。历史讨论当时将 TASK005 STEP00 视为 NEXT，**已被当前 TASK004 CDM 计划取代**；现在 TASK005 ON HOLD，不授权自行生成 batch、写 Processing 或写 PostgreSQL。**不要重做已经成功的上游业务链，也不要自动重跑会写入新的数据的 Live 验证。** 下一步按当前 TASK-STATUS 和 TASK004 CDM 计划的 STEP04A 只读预检执行。

## 冲突优先级

- 当前业务进度：`docs/tasks/TASK-STATUS.md`。
- **当前 TASK004 真实剩余工作与唯一 NEXT**：`docs/tasks/TASK-004-OMOP-CDM-INTEGRATION-AND-IDEMPOTENCY-PLAN-v1.0.zh-CN.md`。
- TASK004 原限定 Processing MVP 验收及历史边界：`docs/tasks/TASK-004-FINAL-CLOSEOUT.md`。
- TASK005 Condition 受控开发设计（**ON HOLD，不是当前 NEXT**）：`docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md`。
- 最新 STEP03E 全链验收：`docs/tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md`。
- 历史 STEP02 Airflow Processing 验收：`docs/tasks/TASK-004-AIRFLOW-PROCESSING-ORCHESTRATION-MAINLINE-CLOSEOUT.md`。
- 当前 Reconciliation 验收：`docs/tasks/TASK-004-BATCH-RECONCILIATION-MAINLINE-CLOSEOUT.md`。
- 开发工作流：当前 Operations。
- 业务语义与冻结边界：Contract / 已验收主线 Checkpoint。
- 历史状态：Archive / historical Closeout / GitHub Actions。
- TASK001–TASK003 整体冻结；TASK004 Synthea / Landing / Resolver / Control Runtime / Person / Visit / Reconciliation / STEP02 Processing 均为冻结基线；STEP03E End-to-End 业务验收 PASS，CI 正式收尾单独记录；TASK004 既定 Processing MVP **COMPLETE / CLOSED / FROZEN**；**TASK004 按新明确目标的整体 CDM 入库/幂等闭环仍 IN PROGRESS**。
- 新 STEP 默认直接维护 Git canonical source；历史 generator-owned 文件修复仍必须同步 Generator。
