---
status: active
scope: fabric-omop-f2-writer-preview-gate
last_verified: 2026-11-08
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

> **P2 文档归属**：由源码文件 `azure-fabric/warehouse/omop-foundation/writer/README.md` 迁入；原证据、ID/事务/FK/Replay/授权边界保留。F0/F1 Schema/Vocabulary 及 F2 Synthetic ROLLBACK 的真实 Run 仅证明各自范围，**不等于 Person/Visit Gold COMMIT**。本 PR 不执行 Warehouse SQL。

# F2 preview-to-commit contract

**Status: SOURCE_ONLY / NOT GOLD_COMMITTED.** This module is a deterministic ID preview, not a Warehouse write or a persistent reservation.

**Input:** Canonical keys must include entity type, hospital ID, source system, and source business key. Patient uses `source_record_id`; Encounter uses `source_encounter_id`. All ID allocations are positive INT within 2,147,483,647 and global per entity across the Warehouse, not per hospital. The planner fails on casefold collisions, duplicates, invalid fields, Map/Gold drift, counter rewind, and overflow.

**Preview:** Read the actual Warehouse Identity Map, Gold rows, allocator and ledger under a verified source batch/manifest/mapping hash. The planner produces proposed ID assignments without saving them. Existing IDs remain stable; new IDs are reproducible regardless of the input ordering.

**Gold gate:** The future Writer must recheck the whole snapshot inside a single-writer Warehouse transaction, resolve the G5 Candidate hospital-scope join, validate real Concept mappings, then atomically write identity map, `cdm.person`, `cdm.visit_occurrence`, the allocator and a COMMITTED ledger. Unknown commit acknowledgement requires independent readback, not blind retry.

**Fabric limits:** Warehouse snapshot isolation does not provide a SERIALIZABLE allocator lock; PK/FK/UNIQUE constraints are not assumed enforced. Use a verified global writer fence, short transactions, explicit conflict detection and safe bounded retries. Current Fabric IDENTITY only supports BIGINT, while official OMOP ID columns are INT.

**Still open:** F2 SQL transaction rehearsal, the real clinical Gold Writer, Patient/Visit commit readback, G4 100/5918 input, G5 hospital join and mapping profile, replay proof and release/license audit. Do not call an offline planner GOLD_COMMITTED.

References:
- https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions
- https://learn.microsoft.com/en-us/fabric/data-warehouse/identity
- https://learn.microsoft.com/en-us/fabric/data-warehouse/ingest-data-tsql

## Real transaction rehearsal — 2026-11-04

- [Self-Runner PR #496](https://github.com/JohnZhang-DataForge/Self-Runner/pull/496): source-controlled synthetic/no-PHI transaction test.
- [Run #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608): real `BEGIN TRANSACTION`; six tables contained exactly the expected synthetic rows within one transaction; explicit `ROLLBACK TRANSACTION`; independent new SQL connection verified all six zero rows. **PASS, NO GOLD COMMIT**.
- The remaining task is an authorized Writer that rechecks verified Candidate inputs and commits stable IDs, clinical rows and Ledger atomically, then reads back for Replay; this rehearsal is not that writer.

## 六表物理 SQL 行集 → Shared IdentitySnapshot 的纯转换边界（F2 SOURCE_ONLY）

已有 Self-Runner `fabric_omop_identity_snapshot_readonly.py` 提供六张表的完整 SQL 行及每表 SHA256（`identity_map`/ `allocator`/ `person`/ `visit`/ `ledger`/ `audit`），通过两条独立 SQL 连接确认，所产生的**物理六表指纹不是** Shared Engine 的 `IdentitySnapshot.fingerprint`。新纯业务入口仍位于唯一 Fabric Writer `silver_identity.py::bridge_f2_sql_readback_rows`，不引入第二套 Mapper/分配器：调用方传入同一个全量有序 SQL 记录集、两连接各自的六 SHA 字典及精确 Warehouse GUID；接口按 Self-Runner 的逐行四字节长度前缀 JSON 编码算法重新算全部六表 SHA，严格匹配双连接指纹，再将 F1 Map/Gold/Allocator/ledger 语义映射到 Shared 的 `PersistedIdentity`/`IdentitySnapshot`，由现有逻辑复核跨医院 INT 唯一、Map/Gold 同步与 counter 不倒退。

只有所有六表皆空的首次预览允许 SOURCE_ONLY 虚拟两个 `next_free=1`，状态依然不是已持久化 ID；已有任何 Ledger/Map/Gold/Audit 而 allocator 为空立即 HOLD。桥接提供不同的 `physical_snapshot_sha256` 和 `shared_snapshot_fingerprint`，后者可直接用于 `bridge_f2_person_visit_allocation` 和 `require_preview_snapshot_unchanged`，前者仅是源行摘要。**调用方自己提供的 SHA/行并不能证明它真的从两条 OIDC/SQL 连接读取；连接认证、物理独立性、短期新鲜度、G4 Silver Approval、正式临床/License 审签、单写入者 Fence 及真候选/Gold 发布必须由可信 Runner/运行控制器独立完成。** 不接受仅有 SHA 而缺少行集的请求，不把 SOURCE_ONLY 桥接结果当临床 Release Gate。

## 2026-11-08 — 实机 F2 与 G4 Silver 双 Planner 一致性边界

Self-Runner [PR #594](https://github.com/JohnZhang-DataForge/Self-Runner/pull/594)、[PR #595](https://github.com/JohnZhang-DataForge/Self-Runner/pull/595) / [Main Run #42466726161](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42466726161) 对现有 `dw-omop-5.4` 完成 Warehouse REST GUID、SQL DB_NAME 和完整六表原始 SQL 行集的两独立新连接比对，再调用固定 Healthcare SHA `21648b0270540ae7044d8ded81f6a1fc9870efe2` 的同一 Shared Bridge。控制器 `b733d1d071096ff0f4e9226fce64af2d9b1637a2`；六表实际全部空；物理 SHA `0e128f1f9f27f4db42084637da2db9baf74daf03657345788cdff10b133c4890`、Shared 语义 SHA `30b218f15d59d11d0105e50d9c42f074536a315b6e6a334f662dcd7e936463ba`；Artifact `fabric-f2-physical-shared-42466726161`（ID `13612340680`）仅含计数/哈希。Run #42466437498 曾在原 F0 SQL 连接 HOLD，诊断增强不绕过门禁，最终复核成功。没有持久化 Source Key/ID、任何 DML、Capacity、Notebook 或 Gold 动作。

新增 `silver_identity.py::plan_silver_identity_with_f2_bridge` 不发明新的算法，而是把同一 `F2SnapshotBridge` 中 Map/Gold/Allocator 传给原 `plan_silver_identity`、唯一 F2 `plan_ids` 与 Shared `bridge_f2_person_visit_allocation`，双向核对每一个 Patient/Visit ID、`PERSISTED/PROVISIONAL` 和 Parent FK；新版四文件 Warehouse 合成测试覆盖 100 Patient / 5918 Encounter、跨医院 Replay、空表起点与错误 Approval/HASH。调用方声明的 `physical_silver_readback_verified=True` **不能独立证明真实 G4 Silver 被物理核验**；本轮只对 F2 Warehouse 做了真实 SQL，不是 G4 真实数据的物理读回、临床/License 审批、Candidate Delta 或 Gold Release。原 F1/F2/P3/P4 Gate 继续生效。


## 2026-11-08 — G4 实机 100/5918/0 → F2 Shared Preview PASS（未发布）

Self-Runner [PR #619](https://github.com/JohnZhang-DataForge/Self-Runner/pull/619) 合并 Main `7733b2dce97498a21f6932d6b7032f1819762c42`，真实可信 [Run #42490347923](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42490347923) **SUCCESS**。独立读取聚合证据 Artifact `fabric-f2-g4-silver-readonly-42490347923`（ID `13620899472`）：`G4_REAL_DELTA_KEYS_TO_F2_REAL_SQL_SHARED_PREVIEW_PASS_NOT_RELEASED`。

在冻结的 G4 FHIR Request/Manifest/Lakehouse/Processing 路径下，本次只读程序严格通过原始 Delta V0 及同版本 CRC、确切审定的 Delta Reader v3 / Writer v7 声明，逐 AddFile 验证文件名、字节长度和无实际 Deletion Vector/Remove；从活跃已提交 Parquet 中读取 **100 Patient、5,918 Encounter 的 Canonical v1 身份及来源字段**、一条 `SILVER_APPROVED` Approval，批次/Manifest/Person FK 验证及当前 Processing 的 Quarantine=0 均 PASS。只解码身份与必要溯源列，**不宣称在本轮重复验证全部临床字段内容**；原历史 G4 Spark 全内容验收为独立证据。

OneLake 原始 PathList 带虚拟目录前缀，其他 Processing 的 quarantine 不属于本次审批数据。Approval 目录另有 **1 个未被任何活跃 Delta AddFile 引用的 Parquet**：源码仅记录汇总计数，**没有 GET、解码、计入正式表或日志输出其文件名**；Patient、Encounter 各有 0 个此类额外文件。批准数据完整 Parquet 字节流聚合 SHA256 `a768a3315420f0da5dd34a1c7af3054118721cb5dc438a505a4e6ec363ac8dc6`，读取的 Delta JSON 日志聚合 SHA256 `6c2ffef57d360c2448911a24639bd9fa196b6a8ae1f39472c8c196c2b268dd36`。

同次执行真正开启两条新的 Warehouse OIDC/SQL 连接，六表 `identity_map/allocator/person/visit/ledger/audit` 均 0，物理 SQL 指纹 `0e128f1f9f27f4db42084637da2db9baf74daf03657345788cdff10b133c4890`，调用固定 Healthcare SHA `79f194d1d7bc6b412e82dc96f6c72b479fc9c395` 的**原唯一** Shared Engine 以真实 Silver Person/Visit 业务键进行 Preview，全 6,018 条身份逻辑快照指纹 `30b218f15d59d11d0105e50d9c42f074536a315b6e6a334f662dcd7e936463ba`。所有 ID 仅为 `PROVISIONAL_OR_EXISTING_PREVIEW_ONLY`，无 Map/Allocator/Gold 持久化；没有源业务键/PHI 日志/Artifact，也没有 SQL/Delta DML、Spark、Capacity 改动或 Candidate/Gold COMMIT。

**门禁仍 OPEN**：F1 来源/License/CPT4 治理、正式临床 Concept Mapping Profile 审签、P3 Candidate Delta 发布、P4 Gold 的独立单写者事务及 P5 完整 E2E。此处真实只读验收 PASS **不授予**任何这些写入权限。

## 2026-11-08 — 早期真实 G4 OneLake 路径 HOLD（已由后续物理证据纠偏）

在原 [G5 Pipeline 与独立 Spark Silver 读回 Run #41636454542](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41636454542) 已验收 P100/E5918/Q0 之后，OMOP Foundation 另建 **GET-only** OneLake Storage-audience Delta V0 Reader，在 [Self-Runner PR #598](https://github.com/JohnZhang-DataForge/Self-Runner/pull/598) 开发固定请求/Manifest/GUID/Approval、准入边界与现有 F2 SQL 双连接→唯一 Shared Preview 连接。所有源业务键只驻留工作进程，不写入日志/Artifact，且未执行 Notebook/Delta/SQL DML。PR #599（GUID-only URI）、#600（PathList 可空分页）、#601（GET 网络单次重试）、#602（隔离路径类型不下载内容的安全诊断）均通过离线 CI 并合并。

真实 [Run #42480741491](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42480741491) 及 [#42481082624](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42481082624) 保持 Fabric Warehouse REST/DB_NAME/六表 SELECT 双连接 PASS；OneLake 目录读取现在可成功，但分别触发 `G4_QUARANTINE_PRESENT_HOLD` 和 `G4_FOREIGN_DELTA_CONTENT_HOLD`。**这两种结果仅表明当前物理目录不满足 Reader 的完整三表文件归属检查，不等于已经确认隔离数据行数，也不能断定旧审批失效。** 旧 Spark Q0 不可直接覆盖新目录异常。下一步在固定 G4 路径只读识别额外文件的结构与 Delta Log，而不抓取 Patient/Encounter/Quarantine 正文，确定是否无关文件/历史残留或实质隔离提交。未证实当前 G4 全量 Silver 行集时绝不触发 F2 实际 Preview，也不放行临床 Concept Profile、Candidate Delta、Gold Writer 或 License。

**精确后续观察：** Self-Runner [PR #603](https://github.com/JohnZhang-DataForge/Self-Runner/pull/603) / [Main Run #42481611612](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42481611612)（控制器 `abad92cc1cbe740875d04afdaaf80a4b5d2e629e`）在 F0 REST 和六表 SQL 全部 PASS 之后，将外来文件树归类为 `G4_FOREIGN_NESTED_QUARANTINE_HOLD`，即当前固定 Silver Root 存在非标准**嵌套** `quarantine/` 路径。该类别来自 OneLake LIST 的目录结构，不包含内容/行数与实际 Q0 差异证明。本轮不下载异常文件或放行 Patient/Encounter；原 Spark G4 P100/E5918/Q0 和新的目录结构事实必须先经过来源/Delta 提交元数据审核才可协调，不得自行删改或跳过文件。


## Canonical G4 Silver → F2 Identity preview bridge (source-only)

`silver_identity.py` consumes only independently verified canonical Silver Person/Encounter source key columns, exact hospital/source/batch namespace, physical Silver approval and zero-quarantine confirmation. It validates Visit-to-Patient FK, then calls the unchanged global `identity_plan.plan_ids` against a trusted complete Warehouse Map/Gold/Allocator snapshot. Output proposes both `person_id` and `visit_occurrence_id` with each Visit's linked Person INT.

Synthetic tests include 100 Patient / 5,918 Encounter, deterministic ordering, exact replay, cross-hospital same business keys, duplicate/casefold collision, foreign FK, approval drift, Map/Gold drift and allocator rewind.

**Do not mistake preview for allocation or Gold.** This helper neither connects to Fabric nor persists an Identity Map, Candidate Delta, Person/Visit, audit or Ledger. The existing published 0.1.3 Candidate Wheel still needs integration of verified Visit IDs and the formal Concept Mapping Profile. A future single-writer SQL transaction must independently reload all Warehouse state and commit everything atomically, followed by independent SQL/DQ/readback and Replay SKIP verification.

## P4 Gold transaction adapter — source-only (2026-11-07)

[Gold transaction adapter](../../../../azure-fabric/warehouse/omop-foundation/writer/gold_transaction.py) is a Warehouse DB-API DML implementation beside the existing F2 planner, **not** a new Mapper, clinical Concept Profile or identity allocator. It strictly validates complete Person/Visit mapping, preserves candidate `PROVISIONAL` IDs until transactionally persisted, compares them to a fresh full Warehouse Map/Gold/Allocator snapshot under an externally held single-writer fence, rejects cross-hospital batch-ID reuse, inserts Map/Allocator/clinical tables/Ledger/Audit together, reconciles clinical rows before committing, and handles failures with rollback. If COMMIT ACK is uncertain, **no retry or rollback assumption is made**: independently reconnect and GET. An acknowledged COMMIT still returns **VERIFY_REQUIRED**, never Gold PASS.

The writer accepts a `release_gate` callback only from a trusted execution controller; user-supplied booleans or SHA strings are **not** legal release approvals. Clinical mapping reviewer/license signoff, persisted F2 snapshot/lease identity, Candidate Approval physical readback, and exact Warehouse connection identity must be verified by that controller before ever calling the writer. The current source does **not** connect the formal Native Pipeline to Warehouse DML and cannot run without an explicit trusted caller. Synthetic SQLite six-table tests test transaction behavior but are **not** an equivalent Fabric DB transaction acceptance. Genuine OIDC/Fabric SQL COMMIT, new-connection readback, Replay SKIP and P5 remain OPEN.
