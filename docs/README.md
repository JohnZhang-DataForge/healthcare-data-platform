# Healthcare Data Platform — Agent START HERE（当前有效文档）

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
