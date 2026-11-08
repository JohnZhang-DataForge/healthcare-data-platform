---
status: active
scope: fabric-omop-f2-writer-preview-gate
last_verified: 2026-11-04
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

## Canonical G4 Silver → F2 Identity preview bridge (source-only)

`silver_identity.py` consumes only independently verified canonical Silver Person/Encounter source key columns, exact hospital/source/batch namespace, physical Silver approval and zero-quarantine confirmation. It validates Visit-to-Patient FK, then calls the unchanged global `identity_plan.plan_ids` against a trusted complete Warehouse Map/Gold/Allocator snapshot. Output proposes both `person_id` and `visit_occurrence_id` with each Visit's linked Person INT.

Synthetic tests include 100 Patient / 5,918 Encounter, deterministic ordering, exact replay, cross-hospital same business keys, duplicate/casefold collision, foreign FK, approval drift, Map/Gold drift and allocator rewind.

**Do not mistake preview for allocation or Gold.** This helper neither connects to Fabric nor persists an Identity Map, Candidate Delta, Person/Visit, audit or Ledger. The existing published 0.1.3 Candidate Wheel still needs integration of verified Visit IDs and the formal Concept Mapping Profile. A future single-writer SQL transaction must independently reload all Warehouse state and commit everything atomically, followed by independent SQL/DQ/readback and Replay SKIP verification.

## P4 Gold transaction adapter — source-only (2026-11-07)

[Gold transaction adapter](../../../../azure-fabric/warehouse/omop-foundation/writer/gold_transaction.py) is a Warehouse DB-API DML implementation beside the existing F2 planner, **not** a new Mapper, clinical Concept Profile or identity allocator. It strictly validates complete Person/Visit mapping, preserves candidate `PROVISIONAL` IDs until transactionally persisted, compares them to a fresh full Warehouse Map/Gold/Allocator snapshot under an externally held single-writer fence, rejects cross-hospital batch-ID reuse, inserts Map/Allocator/clinical tables/Ledger/Audit together, reconciles clinical rows before committing, and handles failures with rollback. If COMMIT ACK is uncertain, **no retry or rollback assumption is made**: independently reconnect and GET. An acknowledged COMMIT still returns **VERIFY_REQUIRED**, never Gold PASS.

The writer accepts a `release_gate` callback only from a trusted execution controller; user-supplied booleans or SHA strings are **not** legal release approvals. Clinical mapping reviewer/license signoff, persisted F2 snapshot/lease identity, Candidate Approval physical readback, and exact Warehouse connection identity must be verified by that controller before ever calling the writer. The current source does **not** connect the formal Native Pipeline to Warehouse DML and cannot run without an explicit trusted caller. Synthetic SQLite six-table tests test transaction behavior but are **not** an equivalent Fabric DB transaction acceptance. Genuine OIDC/Fabric SQL COMMIT, new-connection readback, Replay SKIP and P5 remain OPEN.
