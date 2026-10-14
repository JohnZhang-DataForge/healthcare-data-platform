# Healthcare Data Platform — Agent 交接 / 当前唯一执行基线（2026-10-13）

> **2026-10-14 EDT 最新 Agent 交接：第三个独立 NEW_ONLY v2 已真实生成并 immutable 发布 S3 READY，未执行 Airflow Writer COMMIT。** [第三批精确 Batch ID / Manifest SHA / Run 证据及剩余步骤](TASK-004-THIRD-READY-FINAL-ACCEPTANCE-PENDING-2026-10-14.zh-CN.md)：`synthea-new-only-gh-38588671004` Person1/Visit244，S3 publish [38588933989](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588933989) PASS，READ ONLY [38589912611](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38589912611) PASS（新 Claim/Stage/Checkpoint0，旧2 COMPLETED，PG207/21690，Airflow 14 Task GitSync）。Commit Secret 缺失且临时高权限配置未获执行安全许可，**禁止声明第三批已提交或幂等已验收**；仍需安全许可下的真实 Airflow KPO COMMIT + 独立 PG Reconcile + 重复 SKIP。**TASK004 IN PROGRESS / TASK005 ON HOLD**。

> **2026-10-14 EDT CURRENT NEXT：正式 Airflow Writer KPO 现已 Main GitSync + 真实 DagBag + 双 flag 已完成第二批安全 SKIP LIVE PASS。** [最新证据](NEW-ONLY-AIRFLOW-WRITER-LIVE-MAIN-GITSYNC-COMPLETED-SKIP-2026-10-14.zh-CN.md) / [Self-Runner 38583147075](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38583147075) SUCCESS：14 Tasks、新 digest-pinned Writer Container、无调度 `schedule=None`、Spark/Writer completed path skipped、PG Person207 Visit21690 Claim2 保持，DAG 重置 paused。**唯一剩余 TASK004 主线：第三个真正未入库 Synthea NEW_ONLY v2 READY 的人工受控 Airflow 双 opt-in → Spark Person/Visit → Handoff → 独立 Writer KPO 真 COMMIT + durable DB verify，重复 DagRun completed skip，然后才可正式 TASK004 DONE。** 物理 `task004-new-only-writer-commit` Secret 不存在，不能无监督启用 root-like PG 凭据；前两批禁止重新 Writer。TASK005 ON HOLD。


> **2026-10-14 EDT LATEST NEXT：Airflow Writer 正式源码/容器/KPO 双闸门已完成，仍需 Main GitSync 和第三批真实入库。** [当前 Closeout](NEW-ONLY-AIRFLOW-GATED-WRITER-EXECUTOR-2026-10-14.zh-CN.md) / [Self-Runner 38582267163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38582267163) SUCCESS（111 Unit/Contract tests + 实际 worker02 digest 容器 + KPO API + PostgreSQL Person207 Visit21690 Claim2 不变）。原 DAG 新 `route_writer_authorization→execute_new_only_writer→writer_committed_verified`；手工 `spark_processing:true,writer_commit:true` 且独立 K8s Secret `task004-new-only-writer-commit` 缺一不可。当前 Secret **没有部署**，保持零自动提交，**绝不重用两批已 COMPLETED 的旧 Batch**。NEXT 首先合并 Main 做真实 Airflow GitSync/DagBag 只读验收，再独立新第三批 READY、人工受控配置 Secret、Airflow Spark→Writer COMMIT→独立 DB readback→重放 SKIP。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT LATEST — 第二个真实 NEW_ONLY Batch 首次正式 COMMIT 已成功，覆盖旧文档“等待授权/仍未 COMMIT”陈述。** [当前入库 Closeout](NEW-ONLY-SECOND-BATCH-FIRST-REAL-PG-COMMIT-2026-10-14.zh-CN.md) / [Run 38575457166](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38575457166) SUCCESS。Batch `synthea-new-only-gh-38489944582` 已持久 70 Person +11487 Visit，真 PG Person=**207** Visit=**21690**，Claim Ledger **2**、新 Batch COMPLETED1、Stage11557、VERIFIED2，PG Source ID + parent FK Join 70/11487；103 tests PASS，Duplicate Claim 跳过。首次 run 38572127827 因 shell 语法失败未写库，修复后真正成功且**禁止再次提交本 Batch**。**NEXT：** 实现新的 Airflow Writer KPO/Executor 对**未来第三个未提交 READY Batch** 进行自动 Writer COMMIT；现有 `writer_awaits_live_preflight` HOLD，不能谎称端到端 Airflow Writer 完成。Auto Claim NO、TASK004 IN PROGRESS、TASK005 ON HOLD、双 Writer 压测 Future Enhancement。


> **2026-10-14 EDT CURRENT NEXT — 第二个真实 NEW_ONLY Batch 70 Person / 11487 Visit 完整 Fenced Joint PostgreSQL ROLLBACK 实际 PASS；还没有持久 COMMIT。** [新权威 Closeout](NEW-ONLY-SECOND-BATCH-FENCED-JOINT-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Runner 38566745511](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38566745511) SUCCESS。已复用 Airflow 真 XCom（Run 38563933551），真实 Processing Parquet/Source ID Preflight，动态 Writer 完整 Person→Visit/两类 Checkpoint/3次 Same-TX Fencing + full-row Reconciliation，最终强制 ROLLBACK。实际 PG Person137/Visit10203；新 Batch `synthea-new-only-gh-38489944582` Claim/Stage/Checkpoint 全0，旧首批 Claim COMPLETED1。**NEXT：用户明确授权对第二 Batch 70/11487 首次真实业务 COMMIT，然后独立 DB 对账，最后把安全的 Writer 执行器接 NEW_ONLY Airflow 尾端。** 不重跑 Spark、当前 Auto Claim 关闭；双 Writer 并发/复杂 recovery FUTURE ENHANCEMENT、TASK005 HOLD。


> **2026-10-14 EDT 当前 TASK004 唯一 NEXT：新批次 70/11487 已通过真 S3→PG Readonly Audit，直接做 Joint Fenced Writer ROLLBACK。** [最新 Closeout](NEW-ONLY-SECOND-BATCH-REAL-S3-PG-READONLY-PRECOMMIT-2026-10-14.zh-CN.md) / [Self-Runner 38565372429](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38565372429) SUCCESS。PR #130 已在 Main 启用独立新批次手动 Spark（Run 38563933551）：`synthea-new-only-gh-38489944582` Manifest SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`，Parquet Person70/Visit11487。新 `apps/omop_writer/audit_second_new_only_ready.py` 已在 worker02 真实读 S3+cdm_reader PG READ ONLY 抽查无键撞/无历史业务写；Person137 Visit10203 NEW_CLAIM0。**NEXT 不重跑 Spark、不生成 Synthea、不启动 Airflow Auto Claim；使用这份现有两个 Parquet + 真实 Airflow Handoff做同事务 Writer Fencing ROLLBACK-only、readback 验证。成功后可请求授权实际 COMMIT。** 双 Writer 并发等 FUTURE ENHANCEMENT、TASK004 IN PROGRESS/TASK005 ON HOLD。


> **2026-10-14 EDT 当前唯一 NEXT：新的实际 Airflow Spark Person70/Visit11487 已成功，紧接着做它的 Writer S3/PG 预审和 ROLLBACK。** [最新真实 CLOSEOUT](NEW-ONLY-AIRFLOW-SPARK-FRESH-70-11487-LIVE-HANDOFF-2026-10-14.zh-CN.md) / [Runner 38563933551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38563933551) SUCCESS。Healthcare PR #130、Self-Runner PR #104 均 merged。独立 Batch `synthea-new-only-gh-38489944582` / ManifestSHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`。真实新 Parquet Patient `.../run_id=task004-person-20261014T122824Z-9/work/normalized/data/`、Encounter `.../run_id=task004-encounter-20261014T122824Z-9/work/normalized/data/`（完整 URI 见 Closeout），真实 Airflow Handoff 完成，90 回归 PASS。**禁止重跑 Spark、禁止重新生成 Synthea/覆盖 READY；旧已完成 1/812 Batch 不得重做 COMMIT。** PostgreSQL Person137 Visit10203 Claim1，新批 Claim0/Writer Ledger0/Stage0/Checkpoint0，已确保不触发任何真实 OMOP DML。NEXT 从本次真实 Handoff XCom 提取 Plan，用 cdm_reader 重新读取两个 Processing S3 与 PG source map 做完整只读 Gate，然后 bounded Writer ROLLBACK + 独立 PG 对账，完成后再批准业务 COMMIT。当前 Airflow `writer_awaits_live_preflight` 是无写操作 HOLD，DAG paused, Claim AUTO=NO。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT 最新 CURRENT TASK004 NEXT：动态 NEW_ONLY Spark→Writer Handoff 代码/CI 已 PASS，尚未实际 Airflow 自动 COMMIT。** [最新开发 Closeout](NEW-ONLY-AIRFLOW-ATOMIC-DYNAMIC-WRITER-HANDOFF-2026-10-14.zh-CN.md) / [Self-Runner 38562133245](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38562133245) SUCCESS（114 回归）。新 `airflow/dags/new_only_omop_writer_handoff.py` 准备 immutable Plan/XCom 但不会改库，新 `apps/omop_writer/dynamic_new_only_commit.py` 仅 render 动态 Batch 1..100 Person/1..100000 Visit 的原子 Claim+Fenced Writer+Reconcile SQL；`commit_new_only_batch_once.py` 首次真实 batch 安全 guard 未放松。真 PG 最后只读 Person137/Visit10203/Claim1 COMPLETED。**NEXT：** 让现有 `new_only_omop_consumer` 的 `unclaimed_batch_hold` 接上 Spark→Handoff、引入未来真正 fresh READY Batch 的 S3/PG preflight + ROLLBACK →授权后 COMMIT；运行 Spark/Airflow 共用设施前必须问 Portal/另一个 Session 是否正在修改 Spark。当前没有自动 Claim/业务 COMMIT，绝不能把本轮 Renderer CI 当 live 自动入库。双 Writer 并发/复杂 recovery 非 blocker。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT 当前唯一 NEXT（覆盖本页旧 Airflow Runner 失败交接）：** NEW_ONLY Airflow 真实已完成批次跳过终于**全绿**。[验收 Closeout](NEW-ONLY-AIRFLOW-CONSUMER-COMPLETED-SKIP-REAL-LIVE-2026-10-14.zh-CN.md) / [Self-Runner 38560309400](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38560309400) SUCCESS；Runner PR #102 已 merged Main。真实 DagRun success、Branch TaskInstance 正确路由、DAG re-paused PASS，PG 137 Person/10203 Visit/Claim1 COMPLETED 未变。**无 Spark/Claim/Writer 新写。NEXT 唯一主线**：纯代码先完成 `unclaimed_batch_hold` 的安全新批接入设计/入口、Ticket Fencing/Writer 对接；实际新 S3 READY 的 Spark live / Airflow shared 变更需按 Portal Session 协调，千万不要重跑已入库批次。不要再重复修 XCom 或部署既有 Reader。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-14 EDT 当前 Airflow 接管交接：首次业务 COMMIT 已完成，NEW_ONLY Airflow 只读前半链已真实上线；不要重复 Writer COMMIT。** [最新 handoff](NEW-ONLY-AIRFLOW-CONSUMER-REAL-COMPLETED-SKIP-HANDOFF-2026-10-14.zh-CN.md) / [Runner 38559222216](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38559222216)。Healthcare PR #126 已合并 Main，`new_only_omop_consumer` 实际 DagRun=success，SELECT/Branch 已验证完成批次安全跳过，DB Person137/Visit10203/Claim1 COMPLETED 无变化，Spark NO。**Self-Runner 工作流尚未验收通过/未合并**：其脚本试图从 BranchPythonOperator XCom `return_value` 读分支字符串，但实际 None，导致 job failure；真实 Airflow TaskInstance 状态比较先通过。已达最多三轮修复上限，本轮停止；下一轮先在 Runner 分支 `feature/task004-airflow-new-only-router-20261014` 删除不可靠的 Branch XCom 断言、以各任务实际状态和 PG readback 为准，仅测已完成 Batch 的 READ ONLY DagRun（临时 unpause 后 trap 恢复 paused），收尾合并。之后才开发对未来新 NEW_ONLY READY 的受控 Claim→Spark→Writer；需 Portal Spark 人工协调。TASK004 IN PROGRESS / TASK005 ON HOLD，双 Writer 并发等 FUTURE ENHANCEMENT。


> **2026-10-14 EDT CURRENT — 首次 NEW_ONLY v2 真正业务入库已经发生，不可重复 COMMIT！** [新权威真实 COMMIT Closeout](NEW-ONLY-V2-FIRST-REAL-PG-COMMIT-RECONCILIATION-2026-10-14.zh-CN.md) / [Self-Runner 38555481037](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38555481037)。真正 `synthea-new-only-gh-38497355290` Person1+Visit812 单事务 Claim/Writer/DB full-row Reconcile/COMPLETED COMMIT PASS，独立 PG Person137 Visit10203、Map137/10203、Claim1 COMPLETED、Stage813、Verified2；Claim26/26 + Writer37/37。**原 ROLLBACK 阶段 docs 仍保留作为历史，但其对该批“未 Claimed/未 COMMIT”的措辞已过时。当前禁止再拿这批做 Writer 正式/试探性 COMMIT。** NEXT：先证明真实 Claim API SKIP_COMPLETED / 只读数据对账，然后单 Writer Airflow 自动 Claim→S3/Spark/Writer 针对新的干净 READY 批次串联。双 Writer 并发及复杂 unknown-COMMIT Recovery 按用户要求 FUTURE ENHANCEMENT，非 Demo Blocker；Airflow 自动 Claim 仍关闭、Portal A4 HOLD、TASK005 ON HOLD。Legacy Writer Ledger `status=REGISTERED` 没有本轮提升为 RECONCILED，后续评估但不得误报。


> **2026-10-14 EDT 最新交接 — Writer 同事务 Fencing 已落地 DB Function，并用真实 S3 Person=1/Visit=812 完成 PG ROLLBACK。** [新权威 Closeout](NEW-ONLY-REAL-S3-OMOP-WRITER-FENCED-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner Run 38554330163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38554330163)。已持久安装受限 `task004_writer_fence.assert_active_claim`，cdm_writer 直接不能查 Claim Ledger；同一个 BEGIN 中模拟尚未提交的 Claim fixture→SET LOCAL ROLE cdm_writer→Fencing→原 1/812 Writer 完整 SQL→Fencing→ROLLBACK，通过独立 PG Before/After。真实 READY 仍 **Claim=0**、业务数据行无持久变化；不等于真实 Claim/Writer 正式 COMMIT。**用户 2026-10-14 最新优先级指令：集中 Demo 主线，双 Writer 并发、复杂 Unknown-COMMIT 自动恢复为 FUTURE ENHANCEMENT，不作阻塞。NEXT 是受控真实 Claim→首次业务 COMMIT→独立 DB Reconciliation→同批重复零插入，再接入 Airflow；真实业务 COMMIT 必须取得明确授权，未经授权继续 NO。禁止重跑已通过 Spark、修改 S3 READY 或开启 Airflow Auto Claim。** TASK004 IN PROGRESS / TASK005 ON HOLD，Portal A4 HOLD。


> **2026-10-14 EDT NEW HANDOFF — 下一阶段 Writer 最小权限同事务 Fencing 的数据库端原型已经真实 ROLLBACK PASS，但生产部署仍 HOLD。** [新的权威 Closeout](NEW-ONLY-WRITER-SAME-TX-LEAST-PRIVILEGE-FENCE-REAL-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Self-Runner 38551210536](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38551210536)。已提交待合并候选 `sql/landing_claim/writer_fence_v1_rollback_proof.sql`、`apps/omop_writer/fenced_joint_rollback.py`、对应 tests 和 Runner；在真实 PG 中通过临时 NOLOGIN Function Owner/权限隔离、Owner/Attempt/Manifest/Lease、同事务两次 Fencing + marker SQL 的验证。**全部 SQL DDL / Claim 测试状态 ROLLBACK，尚未部署 FUNCTION，未执行真实 Person1/Visit812 fenced Writer，也没有真正多会话行锁压测，更没有 COMMIT**。NEXT：权限/DDL 安全审查和合法的并发测试窗口 → 受控真正业务 ROLLBACK；原 Claim side Run 38529634738 和真实 S3→Person1/Visit812 Run 38508357752 不必重跑。不要把上文原 handoff 的历史 NEXT 当作现在任务。TASK004 IN PROGRESS / TASK005 ON HOLD，Portal A4 HOLD。


> **2026-10-14 EDT — 最新 TASK004 接力：Claim 侧 Owner/Attempt/Lease Fencing v1 真实 PG 合成批次 ROLLBACK PASS，Writer 侧仍不能正式 COMMIT。** [新增正式 Closeout](NEW-ONLY-CLAIM-LEASE-TOKEN-FENCING-REAL-PG-ROLLBACK-2026-10-14.zh-CN.md) / [Run 38529634738](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38529634738) SUCCESS；Healthcare #121 / Self-Runner #98 merged。26 Claim +25 Writer regressions，真实 scoped `landing_claim_worker` 验证 Owner、Attempt、SHA/URI、过期/续约、失败/轮换、FOR UPDATE NOWAIT + 合成 ROLLBACK，PG 实际 Person136/Visit9391/Claim0 不变。**关键下一步：请勿再重复上一轮真正 Parquet 1/812 Person→Visit ROLLBACK，也勿启动 Claim 或 COMMIT。先做安全 `cdm_writer` 同一 PostgreSQL 事务的受限行锁代理（可审计 SECURITY DEFINER，不能用不同连接先查再写）；真实多会话竞争/失效门槛通过才讨论 fenced COMMIT 和 unknown commit reconciliation/idempotence。** 真实批次 `synthea-new-only-gh-38497355290` 未 Claim、未正式入库；Portal A4 Spark HOLD，TASK005 HOLD。

> **最新 TASK004 唯一工作接力点（2026-10-13 EDT / 2026-10-14 UTC）：真实 NEW_ONLY v2 Spark 1/812 → S3 Parquet → OMOP Writer 单事务 Person+Visit 正向 ROLLBACK 已全部 PASS！** [Writer Closeout 与准确两份 Parquet URI](NEW-ONLY-V2-OMOP-WRITER-JOINT-PG-ROLLBACK-REAL-LIVE-2026-10-13.zh-CN.md) / [Run 38508357752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38508357752) SUCCESS。Healthcare #119 / Self-Runner #97 merged，旧 Writer PR #109 因文档冲突已在新版合并后正式关闭。真 PG 表级 Before/After Person136、Visit9391、ID Map136/9391、Claim0、Batch Ledger/Stage/Commit0 完全一致；序列可能前进。**不要再开发/重跑联合 ROLLBACK；NEXT 严格设计 Claim lease token fencing + unknown commit recovery + 真正受控 COMMIT、Reconciliation 和重放幂等。** 当前没有业务 COMMIT；Portal A4 Spark 共享运行仍 HOLD，TASK005 ON HOLD。

> **最新权威进展：2026-10-13 EDT / 2026-10-14 UTC NEW_ONLY v2 实际 Spark Person/Visit Processing 已完成！** [完整 Spark Closeout](NEW-ONLY-V2-AIRFLOW-SPARK-PERSON-VISIT-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Self-Runner 38505927396](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38505927396) SUCCESS。真实 v2 Batch `synthea-new-only-gh-38497355290`：Airflow 8/8 Task success，1 Person/812 Encounter，S3 Processing Parquet 双实体 readback+Reconciliation+XCom 实证、PG Person 136/Visit 9391/Claim 0 Before/After 零变更；Claim NO。**下一个 Agent 不要再重复这一批 Spark。请直接从新 Closeout 复制两条真正的 Parquet URI，先处理 Writer 身份合同 Healthcare PR #109 仍待合并，再执行严格安全的 Person→Visit 同事务 ROLLBACK 正例与 PG 零持久化验证。** 这不是 Writer COMMIT/ROLLBACK；UPDATE_ONLY/MIX_DATA/TASK005 停止，Portal A4 实际 Spark 仍按多 Session 人工协调 HOLD。

> **最新接手提示（2026-10-13 EDT / 2026-10-14 UTC）：NEW_ONLY v2 生产端 3 READY + Airflow v2 Reader 已真实验收；新增 worker02 Spark Source Bridge 镜像也已真实验收。** [Bridge Closeout](LANDING-PROCESSING-V2-SOURCE-BRIDGE-WORKER02-LIVE-2026-10-13.zh-CN.md) / [Run 38503213376](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38503213376)：新固定镜像 `healthcare-landing-processing-v2@sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937` 从 worker02 真读 v2 1 Patient/812 Encounter、v1 73 Person，38 tests PASS；**这不是实际 Spark Application 或 Writer ROLLBACK**。Healthcare PR #112 / Self-Runner PR #93 merged。下一阶段优先开发安全手工 NEW_ONLY Airflow Spark Processing-only 并进行真实 Parquet/PG 零写核验，注意现有 `task004_cdm_preflight_contract.py` 与 `landing_spark_processing.py` 均只允许历史 `task004-airflow-*`，不能直接打开 Claim。Writer 显式版本合同仍在 Healthcare PR #109 待解决冲突，Self-Runner 验收 Workflow PR #92 已 merged。TASK004 IN PROGRESS / TASK005 ON HOLD。

> **2026-10-13 EDT / 2026-10-14 UTC NEW ONLY v2 第一真批交接（覆盖所有「v2 READY 尚未发布」的历史状态）**：[完整中文新报告](SYNTHEA-NEW-ONLY-FIRST-REAL-V2-S3-READY-AIRFLOW-2026-10-13.zh-CN.md)。Healthcare PR #107 + Self-Runner PR #91 merged，NEW_ONLY 正式 image `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:050a9dcdfb1b95791e2664b85d692152408a473201e2e73a2420f8349167a21f`（45+29 tests PASS）、真正新 Synthea Request `gh-38497355290` 1 Person / 812 Encounter、18 CSV 含 1 个真实 zero-row 辅助，S3+PG Source ID 预审零碰撞后真实 v2 S3 Publish NEW + independent SHA readback + replay REUSE_EXISTING 成功；Manifest `s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/manifest.json` SHA `dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`。真实 Airflow `landing_batch_discovery` DagRun XCom 匹配新 v2 Batch SHA，Claim NO / Spark skipped / PG writes NO。旧 73、70 Person v1 READY 不变；当前真实 2×v1+1×v2 READY。v2 Producer 原合同 SHA `d7118f4bc3306d74911e609b4f0a41b9340ba9a60acaa69174063d5025ad1249` 保持历史未发布 metadata 但不可改动字节，**版本化 `contracts/synthea/new-only/ready-publication-policy-v1.json` 已批准 v2 Reader/Publisher 联动**。下一阶段不要再重复当前特定 Request！通用 `Synthea NEW_ONLY - Run New Independent Request` 仍 pin 老源码/镜像，需正式改为支持 v2 的动态分支并重新验收；动态 Airflow Claim/Spark/PG Writer ROLLBACK/COMMIT 另启安全工作流。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC 最新 Agent Handoff（覆盖所有旧的「Airflow v2 Consumer 尚未部署」NEXT）**：[实际部署与 DagRun Closeout](LANDING-AIRFLOW-V2-READER-REAL-DAGRUN-LIVE-2026-10-13.zh-CN.md)，Healthcare PR #104 merged，Self-Runner PR #89 merged，真实 [Run 38496119114](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38496119114) success；新版 Discovery 官方 digest `ghcr.io/johnzhang-dataforge/healthcare-landing-discovery@sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924` 已在真正运行中的 `landing_batch_discovery` DAG 使用，scheduler GitSync/DagBag 相同 SHA，Claim=NO/Allowlist 空，实际无参数 DagRun scan+claim success / spark all skipped。原 v1 73/70 Person Batch 回归 PASS。**下一轮不要再部署 Reader**：先安全审核 `csv-contract-v2.json` 的 `consumer_compatibility` 版本化发布权限更新（仍默认 `NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY`）；由真实独立 Synthea 小人口 Generator 产生合法 header-only 辅助 CSV，执行真实 source-key PG/S3 防撞、v2 S3 Manifest-last 发布、18 GET 校验、Airflow v2 ReadOnly Scan、Same Request Replay。Writer BatchID 旧前缀和 Existing Target Drift 保留、PG COMMIT 禁止，TASK004 IN PROGRESS / TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC 最新 v2 Publisher Handoff（覆盖所有下文过时 NEXT）**：[正式 Closeout](SYNTHEA-NEW-ONLY-V2-PUBLISHER-STAGED-LIVE-2026-10-13.zh-CN.md) / Healthcare PR #102 / Self-Runner PR #88 / [Run 38492827750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38492827750) SUCCESS，42 tests + Fake S3 v2 Publish/Readback/Replay 全 PASS；新 `apps/synthea/new_only/publish_v2_verified.py` 和 `verify_v2_ready.py` 已归档，image `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:4a456ee4f186bcfdcf5e22c6477ac92ce32941ca4bae9ba685b0b1a2ca3840c5` 已真实 GHCR push，worker01 使用真实 70 Person 11487 Encounter 已冻结数据完整构建 v2 Draft PASS，随后受 `consumer_compatibility=NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY` 拒绝真正 v2 S3 READY PASS。**下一轮先 Airflow 真 Runtime v2 Consumer 和原有 v1 回归验收（Claim NO），才能升级合同并使用真实合法 0 行辅助 Synthea 新 Request 做 v2 不可变 S3 发布。** 旧 v1 Publisher/Writer Batch ID/PG Drift 一律不能变。TASK004 IN PROGRESS/TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC V2 Reader 最新交接（替代历史 NEXT 中的「v2 Reader 尚未开发」）**：[LIVE Closeout](SYNTHEA-NEW-ONLY-V2-CONSUMER-READER-LIVE-2026-10-13.zh-CN.md) / [Run 38491626783](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38491626783) 全 PASS，Healthcare PR #100、Self-Runner PR #87 merged。新版 `apps/task004/validate_new_only_v2_manifest.py` 严格验证 v2 空辅助行合同，`resolve_verified_landing_file.py` 仅 v2 显式 dispatch，保留 v1 严格 >0 行；33 tests、worker01 实际两个 v1 READY Batch 全部 18/18 SHA GET PASS。新 GHCR image digest `sha256:d53a706feba8aff30375836f84c9228d22e61aa35578349b01ddcb1b5d532350`；**此镜像虽包含 v2 Reader，但 Airflow 现行 Consumer 尚未部署新版，没有任何真实 v2 READY Manifest；不能声称 1..100 人任意批都可发布**。下一轮应开发 NEW_ONLY v2 不可变 Publisher、在实际新 Synthea 小人口零辅助表时通过 v2 S3/Discovery/Replay 全循环，并发布经验证的运行中 Airflow Reader；Main 手工 dispatch 原有空表 HOLD 保留；PG Writer 和 Drift Guard 不变。TASK004 IN PROGRESS，TASK005 ON HOLD。


> **2026-10-13 EDT / 2026-10-14 UTC 最新 Agent Handoff：独立 NEW_ONLY 的正式镜像、第二个真正新 Request → READY S3 的真实闭环已完成**，[权威报告](SYNTHEA-NEW-ONLY-DIGEST-RUNTIME-SECOND-READY-LIVE-2026-10-13.zh-CN.md) / Healthcare PR #96 / Self-Runner PR #85。固定独立 image `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:36b69a26f25f9b627da693fc1aa70b8d0a37de0af755bcb7d95d140568efa909`，新 Batch `synthea-new-only-gh-38489944582` Person 70、Encounter 11487、18 CSV 全非空、历史 S3/PG source ID 冲突为 0；新 manifest `s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38489944582/manifest.json` SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`。首次发布 PASS 后独立最新 Digest readback 18/18 / replay `REUSE_EXISTING` + 再回读全部 PASS（Run 38490367050），无 PG DML、无 Airflow Claim。已在 Self-Runner Main 安装 **workflow_dispatch** `Synthea NEW_ONLY - Run New Independent Request`，但尚未从 Main 实际点一次；下一轮可做首次 Dispatch，然后处理 v2 空表 Consumer（否则要 HOLD，不能虚报任意 1～100 人可 READY），后续单独核验 Airflow Claim/Spark→PostgreSQL ROLLBACK/COMMIT；不触碰 UPDATE_ONLY/MIX_DATA，不重建现有 PVC。


> **2026-10-13 EDT / 2026-10-14 UTC 最新交接（覆盖下文旧 NEXT）**：独立 NEW_ONLY 的第一个真实 S3 READY 完整通过：[Closeout](SYNTHEA-NEW-ONLY-FIRST-REAL-S3-READY-2026-10-13.zh-CN.md) / [Self-Runner Run 38488453236](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38488453236)、Healthcare PR #93、Self-Runner PR #83。固定 PVC 请求 `gh-38484300008` → S3 Batch `synthea-new-only-gh-38484300008`，真实 Person=73/Encounter=12159/18 CSV=119147940 bytes；旧 v1 严格 Validator、S3 immutable Manifest 最后发布，v1 Discovery + 18 SHA reread，重放 REUSE_EXISTING SHA 完全相同。**Manifest = `s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38484300008/manifest.json`；SHA = `66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9`**。无需再重新生成/发布该批；NEXT = NEW_ONLY 专用 digest image + 任意新 request 的独立自动生产-发布，零行辅助表独立 v2 Consumer；Airflow 原有 v1 Core 只读 Scanner 能识别，但实际 Airflow 对本批的计划消费/自动处理尚未核验；Writer Plan 新 Batch ID 前缀版本化、真实 Spark→PG ROLLBACK 正例、事务内 Drift/Claim/Reconciliation 完成前 **PG COMMIT 禁用**。


> **2026-10-13 最新用户决定：生产者三个独立命名固定**：`synthea-new-only-`（NEW_ONLY）、`synthea-update-only-`（UPDATE_ONLY，ON HOLD）、`synthea-mix-data-`（MIX_DATA，ON HOLD），[单一版本化命名合同](../../contracts/synthea/producer-batch-identity-v1.json)。旧的 `EXISTING_ONLY`、`MIXED` 仅为历史叫法，今后实施必须使用新名称，不创建旧名字的新入口。Synthea 自身 `synthea-local` Retain 5Gi PVC 已在 worker01 `/data/synthea/` 验证并 Bound，且现有 NEW_ONLY 真实生成和第二 Pod replay PASS，**无需为此再次排查 SeaweedFS PV 或重建卷**；SeaweedFS 仅在 S3 发布时作为服务使用。旧 Writer `task004-airflow-` 限制和 Existing Target Drift Guard 均保留，不能以新前缀跳过。下一步继续固定 73 Person 批次的 v1 Validator → S3 payload readback → 最后 READY Manifest，后两模式与 TASK005 保持暂停。


> **2026-10-13 NEW_ONLY 发布前全局身份审计已真实 PASS，覆盖本交接旧 NEXT：** [LIVE 验收](SYNTHEA-NEW-ONLY-PREPUBLISH-SOURCE-IDENTITY-LIVE-2026-10-13.zh-CN.md) / [Run 38486092750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38486092750)。已持久生成的 `synthea-new-only-gh-38484300008` 73 人/12159 Encounter、18 CSV 全部非空；Source ID S3 14 个历史 CSV 比对及 PG Person 136/Visit 9391 source map 比对均为 0 冲突。新增 `contracts/synthea/new-only/csv-contract-v2.json` 与 streaming `apps/synthea/new_only/prepublish_gate.py`，但**新版本 v2 仅准备、不是当前 v1 Consumer 已支持，也没有 S3 READY**。新的 NEXT：直接选这批全非空 LocalPath 数据跑 v1 Validator → 受控独立 S3 payload immutable 上传/readback → Manifest 最后发布 → v1 Consumer discovery 只读核验；必须在发布前再次做防撞审计，PG Writer Existing Target Drift 不动，动态 PG 正向 ROLLBACK/COMMIT 尚未完成。TASK004 IN PROGRESS、TASK005 ON HOLD。


> **2026-10-13 NEW_ONLY LOCAL 阶段已越过本页旧「尚未部署」NEXT-A/NEW-B：** [正式 LIVE Closeout](SYNTHEA-NEW-ONLY-LOCAL-GENERATOR-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)、[Self-Runner Run 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008)、Healthcare [PR #87](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/87)。已持久创建 `synthea-local` Retain StorageClass、`dw-synthea/synthea-new-only-state` 5Gi PVC / worker01 PV `/data/synthea/`，真实独立 Synthea NEW_ONLY 生成 Person 73、Encounter 12159、18 CSV，全新 Pod 固定 request replay PASS。**注意：只有本地源 ID Registry，PG 历史全局撞车尚未证明；独立镜像最终 Digest 未发布；S3 READY Manifest 未发布，Writer ROLLBACK 正例/COMMIT 仍没有发生。** 下一步 versioned NEW_ONLY Landing/Consumer contract + 全局 ID audit + 独立镜像 S3 最后发布；**禁止用下文旧 NEXT 重新创建 PVC 或将历史 Writer 错认完成**。TASK004 IN PROGRESS / TASK005 ON HOLD。


> **新 Session 2026-10-13 NEW-A 进展补记（覆盖下方旧 NEXT-A 的“尚未审计”措辞）**：worker01 + Contract **READ-ONLY PREFLIGHT 实测 PASS（有阻塞）**，证据：[正式报告](SYNTHEA-NEW-ONLY-READONLY-PREFLIGHT-2026-10-13.zh-CN.md) / [Self-Runner Run 38481854395](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38481854395)。worker01 Ready / `dw-synthea` 存在；NEW_ONLY PVC 0，默认 local-path Delete，专用 host mount/空间未验证；S3 Secret 准确名称未确认；18 CSV 旧合同对每个文件强制非空；v3.3.0 CLI `-o false` 源码静态确认、未真实生成；Writer V1 正确拒绝 `synthea-new-only-`。**下一步先只读核对 host mount/Secret 名称，选定 Retain 存储，随后 NEW-B；没有新生成/新 S3/动态 PG ROLLBACK 正例/COMMIT。TASK004 IN PROGRESS，TASK005 ON HOLD。**


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
