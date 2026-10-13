# TASK005 — Condition Pipeline 开发与验收计划 v1.0

> **状态：DESIGN BASELINE / IMPLEMENTATION NOT STARTED（2026-10-12）**
> 下一业务目标：Synthea `conditions.csv` → Canonical Condition → immutable Raw → Processing Condition candidate → 经单独授权后 OMOP `cdm.condition_occurrence` → Airflow 集成。
> 本文仅批准任务拆分和受控开发准备；**不批准新的业务数据 mutation，不代表 Condition 已 VERIFIED/PASS**。具体每一个 STEP 仍须真实证据和相应 PR。
> 当前权威入口：`docs/README.md` / `docs/tasks/TASK-STATUS.md`；安全/开发流程：Operations、Skill、TASK003 Reference Blueprint。

## 1. 依据、基线、依赖

设计时的 Healthcare main：`459f907e6646ea5f9f2211b8aff4e39d5af63628`；Agent 开工时必须重新查询实时 main HEAD。
TASK001–TASK003 task-level frozen；TASK004 Synthea/Landing/Resolver/Person/Visit/Reconciliation/STEP03E End-to-End 已验收的范围为 baseline，不得因 TASK005 擅自改写。

### 已有可复用实现（**存在**不等于对 Condition 已验收）
- `contracts/synthea/v3.3.0/csv-contract.json`：`conditions.csv` 的七列表头，18 个文件同一 Landing batch。
- `apps/task004/resolve_verified_landing_file.py`：对固定 manifest URI + SHA256 + batch ID 做验证，解析 `conditions` dataset 的候选入口；须针对它补 Condition 正/负测试。
- `spark/apps/person/synthea_patient_adapter.py` 和 `spark/apps/visit/synthea_encounter_adapter.py`：现有 Source → Canonical/Processing 模式；不直接复制大段 Shell。
- `spark/apps/publish_canonical_entity.py`、`spark/common/batch_manifest.py`、`spark/common/canonical_gate.py`：共享代码候选。必须先盘点实际接口、保证向后兼容，不能推断已支持 Condition。
- `spark/apps/task004/reconcile_person_visit.py` 与 `airflow/dags/task004_processing_pipeline.py`：已验收的 Person/Visit 同 batch lineage 和 Airflow 四 Task DAG；TASK005 不在未复验的情况下修改原已验收链。
- `docs/architecture/TASK-003-REFERENCE-BLUEPRINT.md`：Raw、Processed、ID allocation、CDM、独立 readback 五段工程模式；作为设计蓝图，不把历史巨大 Generator 复制成 Condition 新实现。
- `sql/task003/visit-id-map-foundation.sql` 与 `sql/task002/person-upsert.sql`：数据库 ID 和 materialization 的历史参考，**不意味着**新批次已写入 PostgreSQL 对应 Person/Visit。

原 STEP03E 业务验收固定源码为 `d0731df6ce09953e45e0458cd7bd85f0ce4fb60c`；Airflow Run `task004-step03e-38324111846` SUCCESS；23 Person、3592 Visit 仅代表该运行所证明的 Processing 数据，**不是** PostgreSQL 本批次入库证据。Self-Runner 历史只读取证可以复验该固定 run；不得自动触发新 batch。

## 2. 输入、契约和关键设计风险

### 2.1 Source 与 Lineage

固定 Source = Synthea v3.3.0 `conditions.csv`，严格遵守仓库注册表头顺序：

`START, STOP, PATIENT, ENCOUNTER, SYSTEM, CODE, DESCRIPTION`

- `START` 必需且日期有效；`STOP` 可以为空，但非空时必须有效且不早于 `START`。
- `PATIENT`、`ENCOUNTER`、`SYSTEM`、`CODE` 必须非空，`DESCRIPTION` 的可空及清洗政策在 STEP00 依据真实数据与 contract 明确。
- `SYSTEM` 通常是 SNOMED 体系，**不得假设所有行永远都相同**。先只读统计实际系统分布，任何未允许 system 必须显式 reject/quarantine。
- 通过 `manifest_uri + manifest_sha256 + batch_id` 从 verified Landing 取得 `conditions` 文件路径、源文件 SHA、大小、行数；禁止依赖宿主机 report、临时 Pod 或历史目录猜路径。
- 所有下游包含 `source_system/source_version/source_batch_id/source_ingest_date/source_file_sha256`、`processing_run_id`、contract 版本、Git commit 与镜像 digest。

### 2.2 条件事件标识（STEP00 必须冻结）

`conditions.csv` **没有 Id 列**，不能假造天然唯一主键或用 Patient+CODE 直接去重（同一人可多次记录相同疾病）。
推荐的 **待预检确认** occurrence key 方案：

```text
normalized(PATIENT, ENCOUNTER, START, STOP, SYSTEM, CODE, DESCRIPTION)
+ duplicate_occurrence_index (1..N, preserving exact-duplicate multiplicity)
→ condition_source_occurrence_key (deterministic digest)
```

- 同一批输入重读、不同 Spark partition/order，结果 key 集合必须一致；完全相同原始记录出现 N 次，必须保留 N 条并生成 N 个不同 key。
- 不得使用 `monotonically_increasing_id()`、无排序 `row_number()`、CSV 物理分区序号或单纯 CODE 作为跨运行的业务 ID。
- 在持久化映射前，对跨 batch 重复、修订同一记录和重复事件的身份策略单独做正/负例；若逻辑字段不足以稳定辨别事件，先固定 immutable 文件中可复现的 logical record ordinal 作为显式补充，并在 contract 中披露其稳定性边界。
- `condition_source_occurrence_key` 与 OMOP 整数 `condition_occurrence_id` **是不同身份**；后者只在受控映射/分配 STEP 中生成，不从 digest 截断假造整数。

### 2.3 Person、Visit、Vocabulary 依赖

- Source 的 `PATIENT` 引用 Synthea Patients Id；`ENCOUNTER` 引用 Encounters Id。首先针对**同 batch 已验证的 Canonical/Processing Person/Visit** 做 left-anti join，要求 0 orphan、相同 batch/version/ingest date。
- 只有切入 OMOP materialization 时，才要求通过真实已提交的 Person/Visit ID mapping 获取 `person_id` 和 `visit_occurrence_id`；**不能把 Synthea UUID 当作 OMOP 整数外键**，也不能以 Raw/Processing rowcount 证明 DB 外键存在。
- `cdm.condition_occurrence` 的最低必需字段为 `condition_occurrence_id`、`person_id`、`condition_concept_id`、`condition_start_date`、`condition_type_concept_id`；其他字段（例如时间、结束日期、visit、源代码、状态、provider）按 CDM v5.4 实际 schema 和 source 能力映射。STEP00 只读核对当前 PostgreSQL DDL、nullable/约束、真实映射表和 vocabulary 数据；不能以文档猜实际库状态。
- `SYSTEM/CODE` → 源 Vocabulary Concept → 合法 Standard Condition Concept：使用实际 `concept` / `concept_relationship` 映射，检查 `standard_concept`、`domain_id`、有效期与失效标记。不得把 SNOMED 数值 CODE 直接当 `concept_id`，不得伪造 type/status concept。缺失映射要报告 unresolved 及覆盖率；仅在合规约定和明确批准后允许 0 unknown concept，不能无声标记为已完整映射。
- `condition_type_concept_id` 应选择实际存在且语义正确的 provenance Type Concept；`condition_source_value` 保留原始代码。Source `STOP` 缺失时 end date 可以留空，不擅自制造治疗终点。
- 参考规范：[OHDSI OMOP CDM v5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html)（Condition Occurrence）；最终以本集群已部署的 OMOP/CDM 与 vocabulary 版本复验。

## 3. 推荐实施顺序（每次只处理一个 bounded STEP）

| STEP | 实施内容 | Mutation 范围 | 完成条件 |
|---|---|---|---|
| **00 — Read-only contract & dependency preflight** | 解析 verified `conditions` manifest，统计真实行数、NULL/重复、code system、日期；只读确认 Person/Visit batch 对应、DB schema、vocab 和映射；确定 occurrence key/映射政策 | **NONE** | 源契约、业务 key、0 orphan 基线、Vocabulary 策略及未满足前置条件有报告；单测通过 |
| **01 — Canonical / immutable Raw** | `spark/contracts/canonical/condition-v1.json`、Adapter、独立负例测试、最小 Raw manifest/readback 复用；必要时抽取已有通用组件（不改旧行为） | 新 `entity=condition` 的受控对象写入，仅新 run/prefix | 源行数保留、唯一 occurrence key、合同匹配、Raw readback/sha/lineage PASS |
| **02 — Processed Condition candidate** | 确认同 batch Person/Visit、source FK join；构造 typed candidate、DQ、write-intent/permit、immutable Processed publication、独立 readback | 新 `entity=condition` Processing prefix；**不写 PostgreSQL** | 行数/重复策略准确，0 orphan、dates、lineage、manifest/hash、replay/idempotency 和 DQ PASS |
| **03 — Reuse / Framework extraction** | 将已证明通用的 manifest/evidence/readback/guard 能力提取为小模块，Condition 用新模块；旧 Person/Visit 行为保持不变 | 新源码/测试，无业务写入 | TASK004 原测试与 Condition 静态/契约测试 PASS，冻结文件 diff=0，避免庞大 Shell 复制 |
| **04A — CDM/Vocabulary/ID mapping preflight** | 只读核实目标 `cdm.condition_occurrence`、Person/Visit integer FK、Vocabulary mapping coverage、数据库中已有 Condition 与 ID mapping；产出确定性 staging + mutation proposal | **NONE** | FK/Concept/Type/DQ 和重复运行政策明确，SQL/DDL/范围与备份/回滚条件冻结 |
| **04B — Controlled OMOP materialization（单独授权）** | 经审批执行一次 scoped ID allocation 与 PostgreSQL `condition_occurrence` 装载，独立 SQL 回读对账 | **仅明确授权的 Condition 映射与目标表** | 精确计数、PK/FK/Concept、单批 lineage、0 意外 mutation、重试幂等和数据库读回 PASS |
| **05 — Airflow opt-in integration** | 基于已验收 DAG 新建独立、显式 opt-in Condition 集成 DAG 或隔离版本；Person + Visit → Condition → 三实体 Reconcile；准备 rollback | 默认只读/静态；任何新的 Synthea 或 Processing live run 单独批准 | DAG parse/contract、KPO RBAC、XCom 动态 lineage、受控 live、三实体 reconcile 和资源清理各自真实 PASS |
| **06 — Acceptance/Docs closeout** | PR Head → exact SHA Self-Runner → PASS → merge → post-merge（适用时）→ Checkpoint/README/TASK-STATUS | 文档/代码合并 | 每项完成/未完成范围、运行日志、Git SHA、Artifact、冻结边界可供新 Agent 独立接手 |

**顺序守则：**STEP00 不通过不得跳到 STEP01；STEP02 PASS 不能升级为 `cdm.condition_occurrence` materialization PASS；STEP04B 与 STEP05 Live 必须单独获得明确 mutation 授权。TASK005 不是强制一次跑完整张清单，可以逐 STEP 决策。

## 4. 测试、验收与失败保护

每个实施 PR 至少有：正例、负例、固定 manifest/contract、Exact Healthcare commit、GitHub-hosted Policy、ARC checkout SHA、运行结果与 artifact（按 STEP 是否要求真实工作负载）。

**必须 fail closed 的场景：**错误 manifest SHA/URI/batch、Condition header 漂移、STOP<START、空 PATIENT/ENCOUNTER/CODE、未知 SYSTEM、重复 key 冲突、同一 Source 条件行被意外折叠、Person/Visit source FK orphan、不同 batch 误 join、无标准 Condition Domain 的 concept、未授权 PostgreSQL mutation、现存目标覆盖写、重复分配 ID、writer permit 不合法、失败临时资源误清理。

**读回 evidence（需按 STEP 适用性输出）：** `SOURCE_ROWS`、`SOURCE_EVENT_KEYS_UNIQUE`、`SOURCE_DUPLICATE_GROUPS`、`CANONICAL_ROWS`、`RAW_READBACK`、`PROCESSING_ROWS`、`PROCESSING_READBACK`、`PERSON_ORPHANS`、`VISIT_ORPHANS`、`VOCAB_SOURCE_MATCH`、`VOCAB_STANDARD_CONDITION_MATCH`、`VOCAB_UNRESOLVED`、`POSTGRESQL_MUTATION`、`RESULT=PASS/FAIL`。这些是**拟定义的验收 marker**，非已有 CI 的 PASS 声明；任何精确预期行数从运行时可信 manifest 取得，不直接写死 20/23/3592。

**独立验证：**对 Source/Canonical/Raw/Processing 用重新读取的真实 persisted prefix 核验；对于 ID/CDM，使用独立连接/SQL 再核对 committed rows 与 FK、概念及唯一性；写入可控异常后应验证失败资源保留与恢复办法。对 immutable run 重新执行不得悄悄覆盖同名 prefix。

## 5. 目录与代码策略（计划路径，尚未创建）

```text
contracts/synthea/v3.3.0/csv-contract.json      # reuse, no changes
spark/contracts/canonical/condition-v1.json    # new
spark/contracts/processed/condition-*.json     # new as required
spark/apps/condition/                           # adapter / mapping / DQ
spark/common/                                   # reuse, additions only after tests
tests/task005/                                  # contract, key, FK, vocab, replay
scripts/task005/                                # small controlled execution scripts
airflow/dags/                                   # new opt-in integration after standalone PASS
docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md
```

业务源码在 Healthcare；Self-Runner 只放 Workflow/Policy/Request、读写授权与 Artifact。由 Agent 使用连接的 GitHub 工具直接提交 PR，不要求用户手工复制 Shell；若必须触达集群，则优先通过受控 Runner。

## 6. 当前确认的设计决策与待核实项

| 决策 | 当前结论 |
|---|---|
| Phase E 的第一实体 | **Condition，TASK005** |
| 本轮范围 | **仅设计、计划与 docs 入库**；实施步骤一律 NOT STARTED |
| STEP00 首个具体任务 | **只读契约、源行数/重复、FK 与 Vocabulary/DB inventory** |
| Source-of-truth | Verified Synthea `conditions` Landing manifest + immutable batch |
| Condition source 自身有 Id? | **NO**；需要显式 occurrence-key contract |
| Processing vs PostgreSQL | **分为不同授权/验收阶段**；不混同 |
| Framework extraction | 从 STEP01–03 验证过的接口小步抽取；旧任务冻结 |
| Airflow | STEP05 再扩展 opt-in 流，不直接改写 STEP03E 已验收 DAG |
| 跨 batch Condition event identity | **STEP00 待测试后冻结** |
| Vocabulary 具体 concept/type ID 与 coverage threshold | **STEP00/04A 待读库和正式决定** |
| PostgreSQL `cdm.condition_occurrence` 写入 | **NOT AUTHORIZED** |
| Condition 业务数据 ETL | **NOT STARTED** |

## 7. 下一位 Agent 的唯一开工指令

1. 读取 `docs/README.md`、`docs/tasks/TASK-STATUS.md`、本方案、Operations、Skill、TASK003 Reference Blueprint 与 STEP03E Closeout。
2. 核实 Healthcare/Self-Runner 当下 main SHA 和冻结范围；不要把本文件设计时 SHA 冒充新的 main。
3. 先开展 **TASK005 STEP00（只读 preflight）**：固定 verified `conditions.csv` manifest/sha、检查逻辑 occurrence key 重复策略、Person/Visit 的同 batch 依赖，以及真实 OMOP vocabulary/ID mapping 现状；输出设计风险清单和可测试 contract。
4. 只为 STEP00 创建 bounded feature PR，必要的 Self-Runner workflow 必须 read-only；通过验收后再决定 STEP01。不假设已有 Condition 处理能力，也不重跑 STEP03E 的已冻结 batch。
5. 若已验证数据不足，记录 `BLOCKED` 并请求新的已授权数据输入，**不要自行执行 mutating Synthea generate**。

该方案是下一阶段唯一的**任务设计基线**，并非 Condition 完成/验收报告。
