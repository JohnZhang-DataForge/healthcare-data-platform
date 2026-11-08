---
status: active
scope: fabric-omop-cdm54-schema-vocabulary
last_verified: 2026-11-06
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

> **P2 文档归属**：由源码文件 `azure-fabric/deployment/warehouse/omop-cdm-5.4/README.md` 迁入；原证据、ID/事务/FK/Replay/授权边界保留。F0/F1 Schema/Vocabulary 及 F2 Synthetic ROLLBACK 的真实 Run 仅证明各自范围，**不等于 Person/Visit Gold COMMIT**。本 PR 不执行 Warehouse SQL。

# OMOP CDM 5.4 — Fabric Warehouse schema source

**Status: SOURCE_FILES_VERSIONED; LIVE CDM SCHEMA AND NINE VOCABULARY TABLES VERIFIED.** Source for the already existing Fabric Warehouse `healthcare-omop/dw-omop-5.4`; no Terraform creation.

- Canonical upstream: [OHDSI/CommonDataModel `b90ae944...`](https://github.com/OHDSI/CommonDataModel/blob/b90ae94430e9a266891890a549ac188137fd7f00/inst/ddl/5.4/sql_server/OMOPCDM_sql_server_5.4_ddl.sql), exact blob SHA-1 `a77fcad931eef37fe113a79fc266f09cb13e9ed0`, locally retained byte-for-byte in `upstream/`.
- All **39 base tables / 432 fields** are emitted as one declarative SQL file per table under `tables/`. This is a **base DDL schema**, not populated Vocabulary or a complete OMOP compliant deployment.
- Explicit Fabric-compatible column adaptations: case-insensitive `integer` → `int` (same T-SQL type) and unsupported SQL Server `datetime` → Fabric Warehouse `datetime2(6)`. Source column names, order and `NULL / NOT NULL` remain unchanged. Upstream `varchar(MAX)` is supported by Fabric Warehouse.
- Original official SQL Server constraints/PK/index scripts are not part of the base DDL. Fabric Warehouse PK/FK/UNIQUE can be `NOT ENFORCED`; the eventual Writer will implement explicit uniqueness/FK/DQ gates.
- SQL files deliberately omit `CREATE SCHEMA`, migration fences, destructive `DROP`, and any runtime execution. A **separate** trusted Self-Runner migration workflow must validate Warehouse GUID, schema state, deployment SHA and readback before first real DDL apply.
- Offline CI validates upstream blob SHA, table inventory, columns and exact transformed SQL, without making Fabric API/SQL calls.

Official datatype guidance: https://learn.microsoft.com/en-us/fabric/data-warehouse/data-types

Source OpenSpec: [Fabric OMOP Foundation](../../../../openspec/changes/fabric-omop-foundation).

## Real Fabric deployment evidence

- Existing user-created Warehouse `dw-omop-5.4`, item ID `7a6d08da-278d-4603-8a3b-28640110984c`. [F0 real schema CREATE/readback Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578): 39 official base tables, 432 columns, PASS.
- [F1 nine Vocabulary table COPY/readback Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994): private Blob source, 9/9 SHA256-verified files, 9/9 physical table row reconciliation, **28,703,753 rows** PASS; Concept ID/date and Vocabulary ID checks PASS.
- **Current F1 metadata status (2026-11-06):** Actual [Self-Runner SQL SELECT-only Run #42219030641](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42219030641) PASS, independently verified 47 Vocabulary rows, 28 blank `vocabulary_version` metadata rows, 0 rows in `audit.vocabulary_source_file`. Nine CDM tables still reconcile to **28,703,753** rows and 11 referential checks show zero missing links. The exact 28 blank-version vocabulary IDs are retained in the archived `fabric-p1-f1-metadata-42219030641/report.json`, SHA256 `d822605d00fb7e741b3d7ab7ccf8135f539f499f51fdff73a3343b44662ebb97`. Empty version fields may be valid for some internal Vocabulary categories and must be reviewed, not made up. Source files already imported and hash-checked, but the nine corresponding SQL audit rows have **not** been recorded.
- **Not complete:** clinical Concept profile review and approval, Vocabulary release/version/license/CPT4 legal evidence, Source File audit Manifest recording, real OMOP Person/Visit identity allocation/Gold COMMIT, complete E2E. Do not infer clinical authorization from physical Vocabulary readback.


## F1 来源审计记录设计与 Release/License 审核清单（SOURCE_ONLY；不授权 SQL 写入）

**唯一审计实现入口复用 Self-Runner：**
[`fabric_p1_release_provenance_preflight.py`](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/src/ci/fabric_p1_release_provenance_preflight.py)
以及现有九文件 Blob pin / deep DQ。不要在 Healthcare/Shared 另写一套 F1 审计或临床 Mapper。已完成的离线负向测试 [Self-Runner PR #527 / CI #42212808029](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42212808029) 为 16/16 PASS；受控 [Run #42219030641](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42219030641) 为真实 **PHYSICAL SQL READBACK ONLY**，均**不是**数据库来源审计记录写入成功。

### 现有表结构与待补齐的 9 条记录

目标仅限**现有** `dw-omop-5.4.audit.vocabulary_source_file`；不创建新表、不更改已载入 `cdm` 表。其已发布 DDL 的六列依次为：
`vocabulary_release_key`、`blob_file_name`、`sha256_hex`、`source_bytes`、`source_rows`、`verified_at_utc`。记录按冻结的九份源文件，每文件恰好一行：`CONCEPT.csv`、`CONCEPT_ANCESTOR.csv`、`CONCEPT_CLASS.csv`、`CONCEPT_RELATIONSHIP.csv`、`CONCEPT_SYNONYM.csv`、`DOMAIN.csv`、`DRUG_STRENGTH.csv`、`RELATIONSHIP.csv`、`VOCABULARY.csv`。**当前物理审计行数为 0，不得将九份文件历史导入事实当作九条 Audit INSERT。**

从单一已有 `Self-Runner/src/ci/fabric_omop_vocabulary_preflight.py` 的 `FILES/BLOBS` 获取**固定 SHA256 和字节数**、从 `fabric_omop_vocabulary_deep_dq.py` 的 `EXPECTED_COUNTS` 获取**预期每文件行数**。`vocabulary_release_key` 必须来自能追溯到原 Athena Vocabulary 下载的**同一份真实 release manifest / 文件元数据 / 文件 SHA 绑定证据**，不得使用执行日期、文件名、`cdm.vocabulary.vocabulary_version` 的部分值或临时标识冒充 release。若无法证明本批全部九个文件同版，应标记 `RELEASE_ID_UNVERIFIED` **HOLD**。每个 `verified_at_utc` 应来自真实独立校验的审计事件（记录其控制器 SHA/Run/UTC 观测时间），不能凭 Git 源码推定已校验。

**写前仅准备非可执行 Manifest/Review Receipt（未签字的草案不可入库）：** 输入九文件原始路径、Blob 已校验 SHA/Size/ETag、预期行数和真实 Warehouse SQL COUNT /目标 GUID；精确匹配全部九份 pin，拒绝缺失、额外、重复、大小写重名、混合 release、已存在但值冲突的审计行及未知身份来源。审查记录另行绑定 Athena release 证据、使用权限/CPT4 限制、审阅人及其决策凭据 SHA、G4 临床 Profile；注意当前六列 Audit 表**没有许可审批字段**，因此即使九行成功写入也只能证明**来源追溯**，绝不能单凭审计行数将 License 或 Clinical Mapping 标记 APPROVED。

**独立受控写入门禁（本 PR 不执行）：** 后续另外审核精确 SQL INSERT 计划、真实 SQL GUID/DB/Principal、实时共享占用、唯一写入者以及可审计回滚；用户明确授权该次持久写入后，先只读读取现有 Audit 行。仅在已证实 0 行且九份相同 release 原始来源经独立核实时可提交九条审计记录；未知 ACK 时首先以**新 SQL 连接只读核验**，不得盲重试。写后新连接完整读回 9/9 SHA、bytes、row counts、release、timestamps 与 Warehouse 来源表计数，严格判定 `SOURCE_MANIFEST_PHYSICAL_READBACK`，而非 Gold/Clinical/License PASS。所有修改仍须单独 OpenSpec/PR/CI/安全授权与真实 Run 证据。

### 28 个未填写 Vocabulary Version 的真实审核队列

Run #42219030641 Artifact `report.json` 原始 SHA256 `d822605d00fb7e741b3d7ab7ccf8135f539f499f51fdff73a3343b44662ebb97`，列出的 28 个 `vocabulary_id` 为：

`Cohort Type`, `Concept Class`, `Condition Status`, `Condition Type`, `Cost`, `Cost Type`, `Death Type`, `Device Type`, `Domain`, `Drug Type`, `Gender`, `Korean Revenue Code`, `Meas Type`, `Metadata`, `Note Type`, `Obs Period Type`, `Observation Type`, `Plan`, `Plan Stop Reason`, `Procedure Type`, `Relationship`, `Sponsor`, `UB04 Point of Origin`, `UB04 Pri Typ of Adm`, `UB04 Pt dis status`, `UB04 Typ bill`, `Visit Type`, `Vocabulary`.

每个条目保留原始 NULL/空值；人工将其分类为「确实允许空的内部分类」或「缺少外部来源版本证据」，并记录真实 Athena release、来源许可证和 reviewer 决策的可验证来源。不允许批量填同一个日期或伪造 Vocabulary Version。临床 `gender/race/ethnicity/visit class/source_code` 需独立核查标准 Concept/Domain/有效性与来源规则；既有证据显示部分 Ethnicity 的词法命中属于 Measurement Domain，不能作为正式 `ethnicity_concept_id`。`UNK`、`virtual`、`home` 在批准真实 Profile 前继续 HOLD。

### F1 Governance Closure 第一轮：实际审核工作清单已落地（SOURCE_ONLY）

在已有 F1 1.4 设计和真实文件/SQL 历史审计基础上，统一复用 Self-Runner [PR #591](https://github.com/JohnZhang-DataForge/Self-Runner/pull/591) `fabric_p1_release_provenance_preflight.py` 的纯函数 `inspect_f1_governance_worklist`，不是第二套 Manifest、不重新导入九表。真实 [离线 CI #42440786876](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42440786876) **SUCCESS**，Artifact `fabric-f1-governance-review-42440786876` 是由已归档实机 SQL #42219030641、`VOCABULARY.csv` 文件对账 #42322067991 和近期九源 Blob HEAD #42313042119 生成的**历史证据离线审核清单，不是新一轮 SQL SELECT/Blob GET**。报告 `F1_GOVERNANCE_REVIEW_ONLY_HOLD`：源版本空字段 28/47、缺失 SQL Audit 记录 9/9，`vocabulary_release_key`、License、临床签审仍缺；`sql_write_authorized=false`、`license_approved=false`、`clinical_mapping_approved=false`。

28 个原始空 Version 中，**仅作工作路由而非法律结论**：`Korean Revenue Code` 与四个 `UB04` 词表优先进行外部来源版本/使用权限核实，其余 23 个列入“可能为内部/Type 分类”的合法空值审核队列，**不能自动判定合法**。`CPT4` 自带 `2025 Release` 元数据也不等于取得使用/分发许可。报告明确将最近**一份完整 `VOCABULARY.csv` SHA 重验**和其余八份最近 HEAD 长度/ETag 观察分开；这不否认历史九文件加载时的 SHA 验收，但不能冒充本轮重新下载了九份完整内容。下一阶段仍需真实同一 Athena Release/下载证据、正式 License 与 Reviewer 审签、精确受控九行审计补写与独立 SQL 读回。 **该审核清单只反映归档报告的历史观测时点；在受控物理 SQL 重新核验前，不得将 0/9 的历史计数当作永远不变的实时状态。**

**验收定义：** 本节为 `SOURCE_ONLY / REVIEW WORKLIST IMPLEMENTED`；现有 16 项离线审计负向测试及真实 SELECT 只读证据照旧成立，但九条 Audit 行的数据库持久化、正式 Athena Release 授权、CPT4 许可、临床 Reviewer Signoff、G5 Candidate Delta 和 F2 Gold 均为 **NOT_DONE**。
