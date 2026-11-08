# Design — Local HL7 Delta staging + dbt Candidate

## 已决定的方案（不再重复后端实验）
```text
Azure Blob immutable Raw HL7 + manifest (P3 actual PASS)
  → [单独获批的 GET-only 才能取得真实原始字节]
  → hl7apy Python HL7 Source parser / Manifest SHA + identity Gate
  → structured typed rows in LOCAL physical Delta: hl7_staging.hl7_events
  → dbt Core + dbt-fabricspark method=session (local Spark)
  → LOCAL Delta Candidate: hl7_candidate.canonical_patient, canonical_encounter
  → [待实现] shared Contract / DQ / Approval / single Silver Publisher
  → ONE Approved Canonical Silver Delta → ONE OMOP Identity/Mapping/Gold pipeline
```

HL7 **不**转换为 FHIR。Parser 输出结构化记录；历史 `dbt seed` CSV 是临时测试数据导入方式，本地 Spark 可以直接写 Delta 供 dbt 使用。上述计算可在 GitHub-hosted/self-runner 本地完成而不用 Fabric Spark CU；远端 Silver 发布则依然有正式共享 Writer/CU 和单写入者约束。

## 接口及数据边界
- Input: Caller 已合法取得的本地 Raw HL7 和原始 Manifest、独立来源 Manifest SHA、实际 Manifest SHA、Request/Feed/Hospital。
- Parser: `hl7apy==1.3.5`；目前只支持已审核 Johns Creek Hospital B `JOHNSCREEKB` 源 Profile，接受 OMB CDCREC 5 种 Race/2 种 Ethnicity、真实 DOB/Gender、MSH-9/10/12、PID/PV1/EVN 时间；绝不造缺失临床事实。
- Manifest 验证全部 Raw 字节 SHA、大小、Message Control ID、跨消息 Person/Visit 身份和 A01/A03 配对；所有对象预检成功**之后**才创建本地 Delta。
- Stage: Spark 3.5.5 / Delta 3.3.2 的 `hl7_staging.hl7_events`，每个字段保留 raw pointer/provenance，类型化 date/timestamp/bigint；同内容重跑 SKIP，不同内容 HOLD，不覆盖/append。
- Transform: dbt-fabricspark 1.13.2 `method=session`，两个 Source-specific SQL Model 输出 Patient 18 / Encounter 27 字段候选；dbt test 通过不等于 Silver APPROVED。
- Owner: 真实业务源 `local-data-platform/spark/apps/hl7/`，唯一地图 `documents/systems/data-platform/hl7/CODE.md`；Self-Runner POC 仅历史基线；避免复制后续 OMOP Mapper 和单 Writer。

## 测试、成本、回滚
GitHub-hosted workflow 使用冻结源源码 `adt_events_v2.js` 生成新的 synthetic FHIR→HL7，经过严格本地 Manifest/Parser→Delta/_delta_log→dbt run/test→独立 Spark 合同读回，并检验 A01/A03/篡改/重跑冲突。没有云凭据或共享服务访问，不消耗 Fabric Capacity；本地 Spark JVM 开销较 DuckDB 大但其真实物理 Delta 路径已有 POC 实证。CI 通过后记录精确 PR/Run/SHA；任何错误不绕过 Gate，需修复后再合并。清理临时数据仅限 Github-hosted 临时作业；原 Azure P3 不触碰。

## Scoped Azure GET-only intake adapter (runtime separately authorized)

An exact-key GET-only HL7 source reader (under the existing Local HL7 Source Owner) verifies an externally pinned committed Blob Manifest, each object's ETag/Version/metadata/SHA and the existing `landing_intake.verified_seed_rows` clinical/profile Gate before making private local staging visible. It is **not** a second Parser/Mapper, does no Azure List/PUT or OIE POST, and does not call the Delta/Canon/Silver Writer. An authorized caller subsequently passes the files to the existing local Delta/dbt Candidate path; real Azure 42 objects and unified Silver/Gold remain separately gated.


## 2026-11-08 — one-shot real-source credential correction (no business architecture change)

The P2.1 pilot is a **single exact-source GET/HEAD read**, not a durable production Consumer. The approved user direction is to reuse the **previously verified Azure Publisher service principal** (Storage Blob Data Contributor, app ID `29b25de8-2e1a-46cf-8d6c-c5e40f3d8d97`) rather than require an unconfigured `AZURE_BLOB_READER_*` service principal for this one run. Existing P3 [Run #42412009780](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42412009780) used `AZURE_BLOB_PUBLISHER_*` to independently GET/HEAD all 42 objects; this is historical evidence, **not a new live Azure check**. The credential has write-capable RBAC; do **not** claim identity-level read-only. The P2 controller shall allow *only* Storage OAuth and exact Blob properties/conditional download via the already-reviewed `AzureGetOnly` adapter, with no Blob LIST, PUT, POST, MOVE or DELETE, and no OIE/Fabric/PG/Silver/Gold operations. Limit secret exposure to the authentication and exact-read steps, fail closed on wrong principal/token, verify the pinned Manifest and every object, and remove ephemeral local staging after validation. No new processing persistence, cache or ledger; Local Delta/dbt Candidate remains ephemeral, and real Silver publication stays independent P2.3.

For a long-lived scheduled consumer, prefer a separate least-privilege Reader identity and an independently authorized persistent processing/publication design; this one-shot correction does **not** establish such a deployment.

## P2.3 first implementation slice — HL7 Candidate → shared Canonical DQ handoff (no Silver write)

- **Owner:** `local-data-platform/spark/apps/hl7/silver_handoff.py` is the thin HL7 source-specific integration adapter; the **one shared authority** remains `healthcare_data_engine.canonical.validation` for pinned Patient/Encounter v1 schema and `healthcare_data_engine.reconciliation.patient_encounter` for PK/FK/batch validation. This does not duplicate FHIR parsing, shared OMOP mapping, or Fabric writer code. The governed dbt project remains the only SQL Candidate generator.
- **API:** `prepare_hl7_canonical_handoff(patients, encounters, *, context, patient_contract, encounter_contract)` takes **already independently verified** local dbt Candidate records, immutable caller-supplied `BatchContext`, and both authoritative pinned v1 Contracts; returns a pure DQ handoff result/metrics, never an Approval record or Writer call. All patient/encounter identities remain stable and no clinical values are invented.
- **Source identity bridge:** current audited HL7 v1 Candidate carries `source_system=johns-creek-hl7` and `source_batch_id=<raw request_id>` while the unified Shared Contract uses `context.namespaced_source_system` and `context.source_batch_id` (SHA256 of Hospital+Feed+Source+Request+Manifest SHA). Validate the legacy row's source/hospital/feed scope, provenance, processing version, clinical types and FK first, and *only then* replace those two metadata fields on the in-memory handoff row. A different raw request/source namespace or unexpected shared-format input MUST HOLD, not silently normalize.
- **DQ/Quarantine:** reuse pinned `load_pinned_contract`/`validate_row`, and `reconcile_patient_encounter`. Rows incompatible with Canonical v1 are classified `QUARANTINED`; PK/FK violations `REJECTED`; **any** quarantined/rejected row or empty Patient/Encounter set fails the first-stage handoff (`HOLD_DQ`), never allows a partial silent Silver publication. Normal status is `CANDIDATE_DQ_PASS_NOT_SILVER_APPROVED` only. The caller must independently verify physical Candidate Delta and separately gain Silver Single Writer/Approval authorization; this code cannot approve Silver or publish Gold.
- **Runtime:** only synthetic unit and transient hosted local Delta/dbt CI, no new persisted Processing, Cache, Ledger, Blob GET/POST, K8s/PG, Fabric CU or shared Silver/Gold mutation. First implement pure scoped handoff and unit/readback tests; separately review Publisher protocol and Fabric work scheduling before any authorized shared Silver publication. No re-GET of already accepted original 42 HL7 events.


### Follow-on Silver Publisher boundary — existing Fabric G4 is FHIR-scoped

Source audit at current Main confirmed `azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py` G4 functions `_g4_paths` and `verify_fhir_g4_silver` are specifically bound to `Files/silver/fhir_r4`, FHIR hospital/feed/request and FHIR G3 Bronze snapshots. These **are not** a general-purpose callable HL7 Silver writer; calling them with HL7 source records would be incorrect.

P2.3.3 should review a **single source-neutral Silver publication boundary** with the Fabric writer owner, reusing existing approved semantics: independently pinned source + processing identity, output namespace, strict DQ/Quarantine, create-only Delta writes, two-table independent readback, approval-LAST and same-version Replay SKIP / unknown-ACK HOLD. Do not copy FHIR-specific paths or Source Parser into HL7; do not modify the live FHIR G4 writer or execute shared Fabric mutations in this first P2.3.1/2.3.2 PR. Native Notebook/Pipeline/Environment changes and capacity are separate reviewed, authorized integration steps.

## P2.3.3-A/B offline integration source boundary (candidate PR; no cloud release)

The **only maintained physical Silver Writer** remains the real Git-native `nb_fhir_ingest.Notebook/notebook-content.py`. The existing FHIR G4 source-specific request/profile/G3 Bronze/Manifest checks and its recovery/replay semantics remain authoritative and unchanged. FHIR delegates **Patient, Encounter, independent readback, Approval-LAST** to internal `_write_verified_canonical_silver`, rather than retaining a second inline write sequence. A source-neutral Approval payload builder retains exactly the historical G4 `DELTA_RAW_SNAPSHOT_V1` envelope. The helper validates pinned Contracts and BatchContext identity, rejects nonempty DQ findings, empty tables, unknown paths, existing Delta and missing independent readback before approval; it never exposes a new Notebook `run_mode`, bypasses G4 guards or authorizes a Fabric write.

The **HL7 offline hosted harness** independently reopens physical local dbt Candidate and Shared DQ handoff first, then constructs transient local-only Delta Patient/Encounter from the already accepted records and calls the **same** physical writer with explicit `VERIFIED_HL7_CANDIDATE_V1` evidence semantics. It reopens the written Delta and revalidates Contracts/PK/FK, confirms Approval is written last, rejects direct repeated write and DQ HOLD. All transient files are inside the ephemeral hosted Runner warehouse; the harness is **not** a deployed HL7 Fabric source adapter, retained Processing storage or permission to publish official Silver. G4 source-only regression must pass on the same PR head.

The source-neutral helper is internal to the existing physical owner, not a publicly callable source admission API. HL7 still lacks a separate approved Fabric source/Candidate transport, a source-pinned replay/unknown-ACK recovery coordinator and an exclusive live Fabric window. Those must be reviewed and implemented before any native HL7 cloud entrypoint or real Approval can exist. Git Native Notebook main changes can dispatch guarded Fabric Git sync; PR CI is offline only and merging requires checking the deployment coordination gate.

## P2.3.3c increment — Candidate transport integrity (OFFLINE only)

HL7 source code **local-data-platform/spark/apps/hl7/candidate_transport.py** owns only pure in-memory Candidate serialization. The three canonical JSON byte parts carry source-scoped v1 Patient/Encounter values (including UTC timestamps, optional Decimal fields and original HL7 row provenance) plus a manifest-last envelope with exact original source Manifest SHA, hashed Shared Batch Identity, processing version, pinned v1 Contract SHA, per-entity SHA/size/count and deterministic publication fingerprint. No second Canonical Mapper/Writer or new persistent Processing/Cache/Ledger.

The only existing physical Fabric Writer owner, the Git Native Notebook, has a guarded bytes-to-PreparedBatch admission helper, **prepare_hl7_candidate_bundle_for_silver**. It requires an *independently trusted* expected bundle Manifest SHA and source preflight evidence provided by a future authorized controller. It enforces exact audited Johns Creek HL7 source/version, field-level provenance, pinned Contract/BatchContext, payload hashes and Shared PK/FK before generating any Spark DataFrame for writing. Any mismatch HOLDs before Delta. Offline CI builds/sends these bytes in-memory and exercises transient local Delta readback/Approval-last; real Fabric route is still HALT.

**Trust boundary:** SHA catches tampering only if its expected value is independently pinned by a trusted controller. The bundle does not cryptographically sign itself, authenticate its producer, or independently re-prove original Raw bytes. Prior Azure 42-object GET evidence cannot be substituted for a new bundle SHA or a live source-retention gate. Fabric cannot consume the ephemeral local bytes until an independently approved remote transport mechanism, source proof, TTL/cleanup, exclusive Writer and replay/unknown-ACK plan exist. This slice performs no actual Files/Blob writes, network transfer, persistent Processing, or real Silver/Gold.
