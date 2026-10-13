# TASK004 — Person / Visit OMOP 入库与 Airflow 批次幂等闭环实施计划 v1.0

> **CURRENT / AUTHORITATIVE IMPLEMENTATION PLAN — 2026-10-12 America/New_York（2026-10-13 UTC）**
> **TASK004 overall = IN PROGRESS / EXTENDED ACCEPTANCE NOT YET PASS。**
> 用户明确要求 TASK004 最终交付是 **一个受 Airflow 编排、可对同一批次安全重放且 Person + Visit 真正写入 PostgreSQL OMOP 并完成数据库对账的完整流程**。
> 现有 STEP03E Processing-first MVP 已真实通过并冻结，原 2026-10-12 的 TASK-004-FINAL-CLOSEOUT.md 是**原限定 MVP 范围的历史 Closeout**，不是本次扩展范围的终验文档；其证据和结论不得涂改，也不能声称数据库曾在 STEP03E 被写入。
> **本 PR 仅批准实施计划、当前优先顺序和下一步只读调查；不自动授权任何 PostgreSQL / S3 / K8s mutation，也不触发历史或新的 Airflow DAG Run。**

## 0. Agent START HERE：立即执行的唯一下一步

1. 读取 docs/README.md → docs/tasks/TASK-STATUS.md → **本文** → docs/tasks/TASK-004-AIRFLOW-STEP03E-END-TO-END-CLOSEOUT.md → docs/tasks/TASK-004-FINAL-CLOSEOUT.md（历史 MVP）→ docs/tasks/TASK-003-FINAL-CLOSEOUT.md → docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md → docs/skill/SKILL-cn.md。
2. 读取两个 GitHub 仓库当前 main SHA；**不可把本文编写时 Healthcare main c3b59725139800d1e773e63fb1d836595b9d4e54 当成未来 main**。Healthcare 是业务源码 canonical repo；Self-Runner 是 Workflow/Request/Policy/Artifact 控制 repo。不要使用 runner01 上旧 clone 作为源代码权威。
3. 开始 **TASK004 STEP04A：READ-ONLY DATABASE & SOURCE PREFLIGHT**；只读核实当前真实 PostgreSQL Schema、mapping、存量、权限、目标同批次 Manifest/Processing 的可读取性以及历史逻辑的重用条件。用 GitHub feature PR 加入报告脚本/测试/文档，通过 fixed-SHA Self-Runner 只读验证后合并。**不要直接进入写库**。
4. STEP04A 若发现结构/外键/映射/源批次问题，明确记录 BLOCKED、阻断原因和所需决策；不要猜测生产库结构或执行自动修复。
5. 在 TASK004 完成 Person + Visit 的**同批次 PostgreSQL 入库 + 真实 DAG + replay / retry / failure recovery 数据库级验收**之前，TASK005 Condition 为 **ON HOLD / DESIGN ONLY**，不得推进任何 Condition ETL/数据库写入。当前 NEXT 唯一 = TASK004 STEP04A。
6. 每次只做一个有界 STEP：Healthcare source + tests → PR HEAD 完整 SHA → Self-Runner request/policy/workflow（必要时）→ ARC real evidence → Merge → post-merge 证据/Checkpoint。禁止一次性生成全套巨型 Shell 或跳过验证关口。

## 1. 当前已验证事实（不可替换为“已入库”）

| 已有能力 | 真实状态 | 说明 |
|---|---|---|
| Synthea Job → 18 CSV → SeaweedFS health-landing → verified Manifest | PASS / FROZEN | worker01 / dw-synthea；S3 服务实际在 dw-seaweedfs |
| TASK004 Airflow task004_processing_pipeline | PASS / FROZEN BASELINE | generate_publish >> [person, visit] >> reconcile；worker02 / dw-airflow + dw-spark |
| Airflow 历史 Run task004-step03e-38324111846 | DAG + 四 Task success | 产出 Person **23** + Visit **3592**，属于 SeaweedFS Processing 数据 |
| 当前运行影像 / DAG GitSync | 审计 PASS | 2026-10-13 UTC DAG SHA 与 GitHub main 一致，S3 四 Pod 1/1，成功 Job 已清理 |
| Self-Runner STEP03E 独立历史只读核验 | PASS | PR #38/#39，read-only Run 38329852476 SUCCESS；原 GitHub mutating Run 38324111846 仍为 FAILURE（DAG 成功后 XCom 后置取证故障） |
| PostgreSQL omop 的历史 CDM 数据 | **已存在，不等于当前批次写入** | 2026-10-13 只读盘点：cdm.person=113，cdm.visit_occurrence=5799，cdm.condition_occurrence=0；etl.person_id_map / etl.visit_occurrence_id_map 存在 |
| STEP03E 自动写 PostgreSQL | **NOT IMPLEMENTED / NOT VERIFIED** | 现有 DAG 没有 CDM Person / Visit Load |
| 同批次重复触发/重放后的 CDM 不变性 | **NOT VERIFIED** | 目前只有部分 Landing 冲突保护和 Processing 独立 run 路径；**不得称整条 DAG 幂等** |
| 修复后的 mutating STEP03E Live 新 batch 回归 | **NOT RUN** | 与新阶段 End-to-End CDM 回归是不同的待测试事项 |

**重要：**旧任务 TASK002/TASK003 已在过去做过独立 Person/Visit CDM 写入，不能把其 113 / 5799 行充当 Airflow 当前 23 / 3592 行的入库证据；数据库总行数增加量也不等于批次行数，因为同一 source ID 可能已存在。

## 2. 目标架构 / 强制数据流

~~~text
Airflow (同一 batch_id / source SHA / ingest_date)
    |
    v
Synthea Generate → verified immutable Landing manifest
    |
    +--> Person Canonical/Processing  ------+
    |                                      |
    +--> Visit Canonical/Processing -------+--> Processing Reconcile (已验收)
                                                |
                                                v
                                      Batch-scoped CDM Preflight
                                                |
                                                v
                                      Stable Person ID Mapping
                                                |
                                                v
                                      OMOP Person Map/Stage/Commit
                                                |
                                                v
                                      Person DB readback gate
                                                |
                                                v
                                      Stable Visit ID Mapping
                                                |
                                                v
                                      OMOP Visit candidate/Stage/Commit
                                                |
                                                v
                                      Final DB reconciliation
                                                |
                                                v
                                      Airflow SUCCESS / verified evidence
~~~

- Person 必须先于 Visit 真实提交成功；Visit 依赖同批次 Person 已落库及有效稳定的 person_id FK。
- 调用者不能假设现有 TASK004 Processing Patient/Encounter 是 17 列 OMOP Payload：须通过已验证 Mapping 和当前 Contract 明确从 Canonical/Processing 到 CDM 的转换；不要直接将原 CSV insert 到 cdm。
- 推荐把 **STEP03E 已验收 DAG 原样保留**，优先新增**明确选择/显式触发**的 TASK004 CDM DAG 或有版本号的扩展入口；待新路径 PASS 再决定替换正式入口。禁止提前修改冻结行为或自动调度写库。
- 可在控制层继续复用既有 Runtime/Spark Operator，也可逐步采用受控 Airflow Operators；**优先保证可追溯与幂等性**，不能为了消灭 Shell 而重做已验收业务链。

## 3. 关键概念：幂等边界（不可只凭 upsert 宣称 PASS）

### 3.1 三类运行必须区分

| 场景 | 输入、标识和期望 |
|---|---|
| **NEW BATCH**：新的 Airflow manual trigger | 生成新的唯一 batch_id / 可信 manifest identity，运行处理、必要的 ID 映射与数据库写入。**新 Run 不是全系统 NO-OP** |
| **REPLAY EXISTING BATCH**：对已成功 batch 重新执行 | **固定同一 batch_id + manifest URI + manifest SHA256 + source fingerprint**；复用已确认的 Landing 和稳定业务键；CDM 内容、映射数量、主键/FK 不变，数据库写入计划为 NO-OP / SKIP / VERIFIED |
| **RETRY FAILED / AMBIGUOUS COMMIT**：中断后恢复 | 先只读查询 batch ledger、mapping、CDM 实况，按状态继续；不能盲目重建新 batch、清空 stage、重分配 ID 或重跑不安全脚本 |

- **业务幂等 ≠ 物理任务恰好执行一次**：Spark/Pods 可能多次执行；要求的是在相同输入身份下 CDM 的逻辑最终状态一致，且证据可验证。
- Airflow 原 DAG 中 batch_id 由 run_id 派生；Person/Visit Processing 路径还包含每次生成的本地 run_id 并采用 errorifexists。它们能够隔离运行，但**本身不实现 CDM 幂等**。Airflow task clear / retry 可能重新触发 Synthea，必须制定 checkpoint/已有 Manifest reuse/skip 规则并做失败恢复验证，不能默认生产安全。
- 相同 source_system/source_person_id 或 source_system/source_encounter_id 跨批次出现时，稳定 mapping 应重用相同 person_id / visit_occurrence_id。**不能以 batch_id 参与 OMOP surrogate ID 的唯一性键而制造重复患者/就诊**。是否允许同业务键字段变化的更新必须有显式策略；不明确时 FAIL CLOSED。
- 同一 batch_id + 不同 manifest SHA / 不同内容 fingerprint = **CONFLICT / FAIL CLOSED**，不得覆盖旧 Landing、Processed、ID map、历史 CDM 或 ledger。
- 不允许直接执行历史 TASK003 的“空目标一次性写入”脚本作为多批次 loader；它的 frozen 5799 / SHA / 预期主键为一次性历史验收合同，不具有新批次通用性。
- 必须定义 source event/row fingerprint（业务字段稳定排序与规范化，不用随机或时间戳）；使用 manifest checksum 锁定批次身份，并区分数据内容差异与执行时生成的元数据。

### 3.2 PostgreSQL 存储、锁、事务、映射的强约束

1. 核查实际表结构、PK/FK/Unique/Index、identity/sequence、source business keys、concept 映射、数据库帐号读写范围，**任何 schema 想象都不算事实**。
2. ETL stage 必须**按 batch/run 严格隔离**（批次键及唯一约束或可审计的 per-run 隔离表），与 mapping 的主键、唯一约束形成闭环。当前 spark/apps/person/load_omop_person_stage.py 使用 JDBC append 写入可指定 stage_table，历史 sql/task002/person-upsert.sql 则从共享 etl.person_stage 取**全量**：**禁止把二者原样顺序拼到新 DAG**。
3. 与历史库兼容：etl.person_id_map 需校验 source_system + source_person_id 一对一；etl.visit_occurrence_id_map 已有 UNIQUE(source_system, source_encounter_id)；保持历史映射及 cdm 原有行不变，不允许重置 identity/sequence、TRUNCATE 或大范围 DELETE。对新增主键的分配需持久化，唯一约束 + 并发序列化/冲突处理；PostgreSQL sequence 允许不可避免的 gap，不用连续 ID 作为 PASS 条件。
4. Person commit 使用可靠 transaction；Visit 在 Person readback PASS 后才开始事务性 materialization；**不能跨两个独立提交伪称数据库全局原子性**，如 Visit 失败则保留已提交 Person，并通过 ledger/checkpoint 恢复。可按任务实现 commit ledger（运行状态、batch_id、manifest_sha、scope、input/output fingerprint、schema version、commit result）。表名、DDL 与权限须在 STEP04A 实际确认后定案。
5. Stage 写入与最终 merge/upsert 应在明确隔离边界内。JDBC 写 stage 与 SQL CDM upsert 不是同一事务时，必须有持久的 stage 批次唯一约束、校验、锁与失败后可安全重试策略，且预防两个 DAG Runs 并发冲突。
6. 幂等 Upsert 策略：已存在相同 business key + 相同业务字段 → NO-OP；全新 business key → INSERT + 稳定映射；字段不同 → 按事先批准、经过测试的变更规则 UPDATE，否则 BLOCK（特别防止跨批次相同 Synthea seed 或生成日期导致 silent overwrite）。
7. 映射时要检查 OMOP 必填字段/类型/Concept ID 与外键；禁止用 Synthea 源 Code 冒充 OMOP concept_id，不允许任意设固定 concept_id 使数据“看似”成功。
8. 提交边界使用数据库独立 readback 判定：零孤儿 FK、零重复业务键、稳定主键、目标逐 key 字段一致、无非目标行修改。**不允许只用全表 count、Spark 成功日志或 COMMIT 文本作为成功证明**。
9. 凭据从 Kubernetes Secret 提供；输出日志不得包含 Secret / PG 密码、Patient 原始 CSV 全文、敏感连接信息；操作前显式说明受影响数据库、表、batch、预计插入/更新数量。所有 mutation 限定到批准的 batch，失败保留证据而非清空。

## 4. 现有资产与实际局限（Agent 须先读源码）

| 路径 | 可复用内容 | 本次风险/必须改造 |
|---|---|---|
| airflow/dags/task004_processing_pipeline.py | 四 Task baseline、KubernetesPodOperator、XCom 同批次参数、max_active_runs=1 | **没有 DB load**；batch_id 基于 run_id；默认不是完整 retry/replay 契约；现有 Runtime digest pinned |
| images/task004-runtime/entrypoint.sh、images/task004-runtime/Dockerfile | 现有 control Pod 与命令入口 | 新增 CDM 命令会要求新镜像构建、digest 固定、RBAC/Secret 与回归；不能只改 Git 仓库就假设 Pod 使用最新文件 |
| scripts/task004/04c-run-synthea-generate-publish.sh | Synthea Job 启动、校验、清理 | 相同 batch 的 Job 会被删除重建；不得作为失败重试时的默认上游重跑策略 |
| apps/task004/publish_synthea_landing.py | 18-file digest/readback、same-content reuse、conflict fail-closed、immutable manifest | 已验收 Landing 层不是整条 DAG 的 exactly-once/CDM 保证 |
| apps/task004/resolve_verified_landing_file.py、scripts/task004/05c-resolve-runtime-lineage.sh | Manifest 来源锁定、文件选择 | 引入 CDM 时必须保持同一 manifest URI/SHA 和 batch ID |
| scripts/task004/05d-run-person-canonical.sh、05e-run-visit-canonical.sh | 以 SparkApplication 创建独立 Processing run_id/path，readback 和清理 | 不是 OMOP Person/Visit CDM payload/loader；需要显式转换与入库步骤 |
| scripts/task004/05f-reconcile-person-visit.sh、spark/apps/task004/reconcile_person_visit.py | Processing 相同批次的行数、FK 对账 | 不能证明数据库已写入；须新增独立 DB Reconciliation |
| spark/apps/person/map_canonical_patient_to_omop.py | 历史 Person OMOP Mapping，JDBC 读取 etl.person_id_map / vocabulary | 依赖已有稳定映射；需在新批次确保缺失 ID 能安全分配，不能假设 23 条已有映射 |
| spark/apps/person/load_omop_person_stage.py | JDBC Person Stage append + readback | 默认 append 到 stage_table；要解决新批次 stage isolation 和安全 replay |
| sql/task002/person-upsert.sql | Person PK upsert/只更新变化字段、advisory transaction lock | 读取共享 etl.person_stage；历史 SQL 全量对账，需要批次级重构和差异保护 |
| spark/apps/visit/map_encounter_to_visit_candidate.py | Visit 业务字段转换、Person 引用 | 调用方必须验证 Person map 和数据库 FK；它自身不启动 Spark/不写数据 |
| sql/task003/visit-id-map-foundation.sql | 现有 Visit 稳定 business key UNIQUE 和已确认 ID map 契约 | 属于已冻结的 bootstrap；已有 5799 行时绝对不能盲目建表、重置分配 |
| apps/task003/candidate_to_cdm_preflight.py、apps/task003/verify_committed_cdm_visit_materialization.py 等 | 历史 17 列 OMOP Visit 结构和验证经验 | 部分程序将 5799 行、旧 mapping SHA 固定为历史验收值，不可直接运行于动态新批次 |
| docs/tasks/TASK-003-FINAL-CLOSEOUT.md | 真实旧库 5799 Visit、ID 分配、事务不确定状态恢复经验 | 第 20 节明确**不能重放旧的一次性数据库写入步骤** |
| spark/contracts/omop/*、spark/contracts/processed/*、tests/task002/、tests/task003/、tests/task004/ | 可参考契约、安全负例、静态回归 | 新阶段需要新的 dynamic batch-specific tests，不能修改旧已验收基线来迎合新测试 |

## 5. 实施步骤、PR 范围和强制验收关口

**每次只开展一行 STEP，不得顺带修改下一阶段；STEP04B 之后的编号是计划，不代表功能已实现。**

| STEP | 动作 / 交付物 | 副作用级别 | Gate（通过才进入下一步） |
|---|---|---|---|
| **04A：read-only preflight** | 盘点真实 PG DDL/keys/index/constraints/sequences/rows、etl stage/map、已有 source IDs 交叉、目标历史 verified batch/Manifest、实际 Processing Schema 和 source keys；生成机器可读报告 + 风险清单 + contract 草案 | **READ ONLY**（唯一当前可开始） | 来源 pinned，真实表结构与历史冻结边界可见，缺失条件与更新策略已列明；PR exact SHA 只读验证 |
| **04B：mapping + replay contract** | 明确 batch ledger、稳定 business keys、collision/update 规则、事务边界、重试/恢复、Stage schema/DDL 方案；实现纯逻辑/模拟测试和失败用例 | CODE / TEST ONLY | 对同 batch、跨 batch 相同 key、冲突内容、并发和未知 COMMIT 有可测试定义；无 PG 写 |
| **04C：Person CDM load** | 实现可重入 Person ID map、batch-scoped Stage、映射校验、事务 merge 与 readback；先有契约/权限/目标范围审批 | **CONTROLLED DB MUTATION — 另行明确授权** | 一次提交成功；同输入二次运行 Insert=0、Update=0、Map delta=0、target fingerprint 不变；旧 113 行按业务键保护 |
| **04D：Visit CDM load** | 从同 batch Encounter Candidate 取 Person FK；稳定 Visit ID map；17 列 OMOP 物化、事务和 readback | **CONTROLLED DB MUTATION — 另行明确授权** | Person 先验证；Visit 无 orphan、重复键、无关数据改动；replay ZERO logical changes；旧 5799 行保持历史相容 |
| **04E：DB reconciliation + recovery** | 新增独立只读（验收器）查询：源 Manifest/Processing、stage/map/CDM 的 key-level 双向差异、schema/值哈希、漏数、重复、外键；对未知 COMMIT/失败恢复测试 | VERIFY READ ONLY；**故障注入写入需要独立批准** | 任一 mismatch 必须 DAG FAIL；已提交 Person + 未提交 Visit 能恢复；证据保留 |
| **04F：Airflow optional CDM DAG integration** | 新建或版本化 DAG，将 Processing 成功门槛 → Person DB → Person readback → Visit DB → final DB reconcile 串联；参数、Secret、稳定 image digest 与权限检查；避免触碰历史 STEP03E 入口 | DEPLOY + MUTATION，需要分段批准 | source parse/contract/PR exact-SHA/Runtime policy PASS；再通过真实完整 DAG 运行并关联 evidence |
| **04G：end-to-end idempotency acceptance** | 在批准的可控新 batch 进行首跑、相同 batch replay、task retry、部分失败恢复、冲突负例，最终数据库独立 readback；形成 append-only evidence | **MUTATING E2E TEST — 单独授权** | 下述验收矩阵全部 PASS；历史数据未受损，新的成功 Pod/Job 自动清理 |
| **04H：final closeout + handoff** | 固定最终 DAG/image/Contract/DB schema/report SHA、GitHub PR/Runner Run/Artifacts；正式更新 TASK-STATUS/README/Skill；TASK005 解锁 | DOCS | 仅在真实 STEP04G 完成后标记 TASK004 COMPLETE/CLOSED/FROZEN；未验收处不得写 PASS |

**命名注意：**STEP03E 是已经验收的 Processing MVP，不是本次未完成阶段的“失败回滚”；STEP04A–04H 是经用户重新明确终态后新增的扩展验收工作，保留既有工作资产，不重命名旧 STEP。

## 6. 必须执行的验收矩阵（推荐分 STEP 落地）

| 编号 | 验收场景 | 必须检查的数据库事实 |
|---|---|---|
| A1 | 已授权全新 batch，完整 Airflow → CDM | DagRun 全成功；锁定 batch manifest SHA；Person/Visit **该 batch 应有的每个 business key** 对应正确 CDM 记录、concept/FK 有效、零丢失 |
| A2 | **同一 batch 同一 Manifest 重放** | business-key → surrogate-ID 映射未变；Person/Visit target 业务字段 fingerprint 不变；insert/update=0；零重复行 |
| A3 | 同 batch 重试单个 Person/Visit 操作 | 没有新 PK、重复 stage 导致双计数或不相关行写入；重试只修复缺失阶段 |
| A4 | Person commit 成功、Visit 失败，然后恢复 | Person 不能重复增加；Visit 最终完整，FK 正确；ledger 从 partial 到 verified；无需删库/清空 |
| A5 | commit 返回不确定 / Runner 断线 | 先数据库只读确认实际提交状态；不能仅依据 GitHub failure 再无脑重复写；运行可恢复 |
| A6 | 同 batch_id + 不同 SHA/源内容 | FAIL CLOSED，**零新数据或历史数据的非预期变更** |
| A7 | 新 batch 重用旧 source ID 且内容相同 | 映射重用、既有实体无重复；不能假定 CDM 总行数每次都增加 Processing 行数 |
| A8 | 新 batch 重用旧 source ID 但内容有冲突 | 显式的更新策略/变更证据；若未批准，FAIL CLOSED、不 silent UPDATE |
| A9 | 并行或同时提交同一键 | DB UNIQUE + ledger/锁防止双主键和重复 mapping；不得仅依赖 max_active_runs=1 |
| A10 | 历史旧数据保护 | 原先冻结的映射和 CDM 业务内容未被覆盖或删减；数据库增长与本批次差异可解释 |
| A11 | 最终数据库级双向对账 | 从本批次稳定业务键出发检查源减目标/目标减源、重复、FK/Concept、内容 checksum；不以全表总数相等替代 |

若发现对应源实体 ID 未在 PostgreSQL 已有 mapping 中，必须走受控 ID allocation；**不能**直接把 Synthea 字符串 ID 塞进 OMOP integer ID，不能以当前数据库总数猜测哪些 source ID 已存在。

## 7. STEP04A 的具体 Agent 实施任务（现在可直接开始）

### 7.1 首次 PR 只需要做以下事情

- 新增 docs/tasks/TASK-004-STEP04A-READONLY-PREFLIGHT.md（真实事实报告，不能空写 PASS）；建议新增 tests/task004/test_task004_cdm_preflight.py 与 apps/task004/inspect_omop_cdm_preflight.py 或功能等价的小型只读程序。
- 在 read-only PostgreSQL transaction 中检查 current_database、current_user、cdm.person、cdm.visit_occurrence、etl.person_stage、etl.person_id_map、etl.visit_occurrence_id_map 的**实际**列、主键、唯一约束、索引、Identity/Sequence、外键、触发器及相关权限；检查冻结表是否仍符合历史 baseline，敏感信息不入证据。
- 只读检查 source_system='synthea' ID 映射业务键唯一性、CDM Person/Visit 对应的原始 key 和 FK；检查既有 ledger 或 batch 标识（若有），不要猜测缺失字段。
- 固定一个经验证可重复读取的 **source batch_id + Landing manifest_uri + sha256**，检查 PERSON / VISIT Processing 已发布数据的 schema、行数、唯一 source keys、重复、源 person/encounter 引用。历史 accepted batch 仅可用作只读输入调查，不代表未来会直接对该 batch 写库。
- 输出预计 NEW/EXISTING/CONFLICT 的**只读预估**（不把个人敏感字段和凭据写入日志）；同时明确哪些旧代码 hardcode 5799、哪些写全表 stage、哪些构建镜像需修订。
- 如需要对 S3/PG 进行容器化查询，Self-Runner 必须通过新 read-only 固定 Request + exact Healthcare PR SHA；无自动 random DAG trigger、无 kubectl apply/delete、无 database DDL/DML。
- STEP04A 结束仅可更新状态：STEP04A PASS 或 BLOCKED + 证据链接；**TASK004 overall 仍 IN PROGRESS、TASK005 仍 ON HOLD**。不得擅自进入 STEP04C 数据库写入。

### 7.2 STEP04A 输出字段最低要求

~~~text
TASK=TASK004
STEP=04A
MODE=READ_ONLY
HEALTHCARE_SOURCE_SHA=<40-char-exact-commit>
SELF_RUNNER_SOURCE_SHA=<40-char-exact-commit>
DATABASE=omop
SOURCE_BATCH_ID=<verified-batch>
MANIFEST_URI=<redacted-if-needed>
MANIFEST_SHA256=<64-hex>
DB_PERSON_DDL_GATE=PASS|BLOCKED
DB_VISIT_DDL_GATE=PASS|BLOCKED
PERSON_ID_MAPPING_GATE=PASS|BLOCKED
VISIT_ID_MAPPING_GATE=PASS|BLOCKED
STAGE_BATCH_ISOLATION_GATE=PASS|BLOCKED
PERSON_PROCESSING_SCHEMA_GATE=PASS|BLOCKED
VISIT_PROCESSING_SCHEMA_GATE=PASS|BLOCKED
HISTORICAL_DATA_PROTECTION_GATE=PASS|BLOCKED
KNOWN_GAPS=<list>
POSTGRESQL_MUTATION=NO
LANDING_MUTATION=NO
AIRFLOW_TRIGGER=NO
RESULT=PASS|BLOCKED
~~~

每项 PASS/ BLOCKED 必须有具体观察值；不要复制模板当作结果。只读事实清单用真实查询结果填充，缺少权限即 BLOCKED 并说明最小权限需求。

## 8. 代码落点建议（仅供下一 STEP 实施，不强制一次创建）

- apps/task004/cdm/：Batch-scoped preflight、状态 ledger、源与库身份对账、readback 独立验收器；若分层明显可拆小模块。
- spark/apps/person/ 和 spark/apps/visit/：可复用 mapping 到 OMOP payload 的逻辑，新增动态 source/batch contract。不要让历史固定 SHA 验证函数直接用于新运行。
- sql/task004/：分批次 stage/map/upsert、事务读回 SQL；DDL/迁移一定须先在 STEP04A 读真实库并审核后再确定。
- spark/contracts/、tests/task004/：新增批次 idempotency/recovery 合同和负例测试。
- airflow/dags/：新增 opt-in CDM DAG 或版本化升级；安全地读取已存在 verified batch checkpoint。
- kubernetes/manifests/task004/、images/task004-runtime/：根据明确角色调整 RBAC、Secret、镜像；使用固定 digest。
- Self-Runner .github/workflows/、config/targets/healthcare/steps/、scripts/ci/：放 request-scoped 有界验证执行入口，不把业务转换代码复制进 Runner；数据库 mutation 使用独立启用的 workflow，不能由普通 push 触发。
- docs/tasks/：每一步的真实 Report/Checkpoint、最终 DB Closeout 和状态索引；历史的 TASK-004-FINAL-CLOSEOUT.md 仅记 2026-10-12 MVP 范围。

## 9. Definition of Done：只有满足以下条件才能正式关闭 TASK004

1. Airflow 通过 approved input 自动完成：Synthea/verified Landing → Person/Visit Processing → Person CDM → Visit CDM → independent DB Reconciliation；每一阶段的相同 batch_id 与 source fingerprints 可以串联验证。
2. PostgreSQL 中不仅有历史 113/5799 行，而且**明确证明此次 Airflow batch** 的 Person/Visit 数据已经按照 OMOP 结构和 FK 正确提交，源与目标对账零差异。
3. 同一 batch 重新处理与不确定状态重试不新增重复 Patient/Visit、不会重分配既有 surrogate IDs，不静默覆写历史数据。
4. 一次真正的集群 DAG 成功 + 独立数据库只读验证、一次同 batch replay NO-OP、一次部分提交恢复、至少一个源冲突 FAIL CLOSED 负例均真实通过；必要的 mutation 均在单独授权的受控窗口执行。
5. PR HEAD → exact-SHA Runner evidence → merge → 必要 post-merge 验证，通过后冻结源码与最终 evidence；所有未运行用例明确 NOT RUN，不能冒充 PASS。
6. 最终更新 docs/tasks/TASK-STATUS.md、docs/README.md、Operations/Skill 的 **TASK004 overall = COMPLETE / CLOSED / FROZEN**；完成后才将 **TASK005 Condition STEP00** 设为 CURRENT NEXT。

~~~text
TASK004_PROCESSING_MVP=COMPLETE_CLOSED_FROZEN
TASK004_OMOP_PERSON_VISIT_DB_LOOP=NOT_IMPLEMENTED
TASK004_IDEMPOTENT_BATCH_REPLAY=NOT_VERIFIED
TASK004_OVERALL=IN_PROGRESS
CURRENT_NEXT=TASK004_STEP04A_READ_ONLY_PREFLIGHT
TASK005_CONDITION=ON_HOLD_DESIGN_ONLY
NEW_DATA_MUTATION_AUTHORIZED=NO
~~~

**最高优先级：先让 Person → Visit 的数据库闭环可复现、可重放，再开始依赖它们的 Condition。**
