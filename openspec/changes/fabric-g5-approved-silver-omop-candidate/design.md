# Design — G5 approved Silver → OMOP Candidate / Pipeline

## Frozen starting point

Healthcare main `57a0e6be93ab1a957fbc4f9129cb3de0a6a5a202`; Self-Runner main `efcfa3eaae192be22099aac83e962c0dccf4c9c1` (read on 2026-11-03). These are change-start baselines; actual latest main wins before merge. Cloud Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`; Lakehouse `e67c42ee-5ab2-4bc8-a013-7bdf9741ef68`. Never treat Git logicalId as physical Item GUID.

## Separation of ownership and execution

1. **Silver Input fence:** derive existing request-scoped path through G4 `_g4_paths(request)`; require exact source-batch identity, delivered Manifest SHA, G4 processing version, one `SILVER_APPROVED` Approval row, P=100/E=5918/Q=0 for the currently verified request; independently reopen both Delta tables. Recompute/source check may invoke the existing G4 readback. No fallback from rejected Quarantine.
2. **Pure Shared Engine:** mapping is a deterministic DataFrame transform; no Azure, SparkSession creation, filesystem, SQL or writer. Local contracts remain authoritative: `canonical/patient-v1.json`, `canonical/encounter-v1.json`, `omop/person-v5.4.json`, `omop/visit-candidate-v1.json`, `omop/visit-class-v1.json`. Pin raw bytes/hash and mapping-version provenance. Person stable IDs MUST be supplied by a separate verified identity mapping; no hash-as-OMOP-ID, row_number, name/DOB matching or implicit auto-allocation. Validate uniqueness, unmapped concepts, FK, dates and exact mapping profile before publication.
3. **Candidate only, not Gold:** `Files/omop_candidate/fhir_r4/<hospital>/<feed>/<request>/mapping=<profile-sha>/` contains `person_candidate`, `visit_candidate`, `candidate_approval` as one request/version scoped immutable-mode output, approval LAST after independent two-dataframe readback. This is not a Warehouse transaction and never `GOLD_COMMITTED`.
4. **Pipeline:** current Native `pl_fhir_ingest` owns orchestration. No schedule, retry=0, run_mode default HALT. Read-only verification must not authorize writes. Pipeline must explicitly reject `HOLD_*`, `VERIFY_READONLY`, `DQ_*` and capacity-failed-before-session instead of interpreting Notebook infrastructure completion as business approval.
5. **Live runtime gates:** Git-first Reviewed PR → remote Native source readback → new Wheel fixed hash and Published Environment verified → single authorized run → independent Spark/physical Delta readback → same-request Replay SKIP; pipeline execution only after comparing local/remote Pipeline definition and explicit parameter guard. Unknown POST ACK must be reconciled by GET before retry; conflicts/parallel session cause HOLD.

## Implementation slices

- **A. Contract-first:** OpenSpec + pure Shared candidate planning, explicit stable-ID source requirement, contract/negative/replay unit tests and CODE ownership.
- **B. Fabric candidate:** guarded `SILVER_APPROVED_READONLY` first; then pinned identity/concepts and Candidate-only writes, with independent readback.
- **C. Pipeline:** parameterized read-only preflight, exact Notebook success marker gate, no schedule/auto retry, then a separately reviewed end-to-end plan. Preserve default HALT and the Native metadata separators.
- **D. Gold separate:** Warehouse within-one-Warehouse transaction remains G6; no Gold COMMITTED until target-specific writer + independent receipt; Azure strict WORM / Blob tamper / genuine network ACK separate.

## Testing and evidence

Normal 100/5918; 99/5893/26 rejected; missing approval, mismatched SHA/processing, 2 approvals, cross-hospital identity, duplicate/missing PersonID, unknown visit class, missing/invalid OMOP Concept, invalid Patient FK, replay equality and partial candidate output; source/persisted table independent compare. CI syntax/OpenSpec/CodeMap+Shared boundary/Notebook offline tests. Record each actual GitHub workflow URL and Fabric job ID only when observed. Offline success is not Fabric PASS.

## Data protection

Existing G4 normal and rejected request Delta folders are read-only to G5. Do not change existing Azure Blob policy, Local PG, Terraform, Capacity or Wheel 0.1.1 until a reviewed release; Candidate namespace is new. All live operations follow SAFE-OPERATIONS and SESSION-COORDINATION.

## 2026-11-04 controlled preflight implementation slice

- The first native Notebook G5 run mode is `G5_CANDIDATE_SOURCE_READONLY`, not `G5_CANDIDATE_WRITE`. It consumes **only** the existing accepted G4 request, delivered SHA and exact unmodified Local v1 Canonical contracts; default HALT and both write flags false. `_G4_PROCESSING = ...engine-0.1.1` must remain unchanged because it is the physical namespace of already approved G4 source data, even though the executing Notebook/Published Environment uses engine 0.1.3.
- Physical source verification must reuse `verify_fhir_g4_silver(mode=SILVER_READBACK_ONLY)` which independently checks manifest bytes, Bronze receipts, source regeneration, both Delta tables and single persisted Approval row. Then reopen the persisted Patient/Encounter/Approval for G5-specific P100/E5918/Q0, consistent namespace/batch and anti-join FK. G4 DQ-rejected requests, incomplete approvals, Spark exceptions and any strange override MUST HOLD, never emit success markers.
- Source-only exit `FHIR_G5_CANDIDATE_SOURCE_READONLY_P100_E5918_Q0_APPROVAL_DELTA_PASS_20261104` means **Silver physical read-only verification only**. It is not OMOP Candidate, F1 Concept approval, durable ID assignment, Warehouse Gold COMMIT or F3 E2E. No OMOP ID Map/Concept queries or writes are performed in this change.
- The existing `pl_fhir_ingest` read-only one-activity Pipeline remains default HALT, no schedule or retry, no writer parameters. Later F1/F2 integration must be a separately reviewed PR, pinned real Warehouse snapshots, approved Concept Mapping Profile and Candidate staging with error-if-exists + independent readback/approval-last.

## First-batch candidate preview ID handoff (source-only)

此前设计中「Candidate 必须先有已持久化 Identity Map」与首次 Gold COMMIT 需要从空 Map 开始存在循环依赖。现明确分为**完整已提交 Map/Gold/Allocator/Ledger 的只读快照**与 **F2 的确定性新 ID Proposal**。二者输入独立校验，再将批准 G4 Silver 的 Person/Visit Keys 对照为 `G5_CANDIDATE_ID_HANDOFF_ONLY_NOT_PERSISTED`，每一条 ID 携带 `PERSISTED` 或 `PROVISIONAL` 状态以及 Snapshot Fingerprint。G5 Candidate 后续独立 Delta Readback/Approval-last 才是 Candidate 物理验收，Warehouse Writer 只能在受保护 single-writer 事务内重新完整读取并确认 Map/Allocator/Gold/Ledger 快照后，原子 COMMIT Map/Allocator/Person/Visit/Ledger/Audit。任何快照漂移、无正式临床 Concept Profile、未知 ACK 必须 HOLD。

公共纯桥接实现在 Shared Wheel `identity/candidate_handoff.py`，现有 Fabric `identity_plan.plan_ids` 为 Person/Visit 当前唯一分配器；不向 F1 SQL 写入临时 Map、不改变冻结 G4，也不把 Source-only Handoff 当作实际 Candidate/Gold。后续的多 Entity 目标仍按 `extend-shared-omop-multi-entity` 独立扩充。


## 2026-11-08 P3.17 — Proposed semantic target evidence isolation

The authorized humans, not the mapper or F1 SQL, decide whether the existing proposed mappings `2076-8` (race), `home`, and `virtual` (visit) are clinically appropriate. Before review, gather *target-side facts only*: reconstruct the unchanged G4 P100/E5918 unsigned Profile from the precise pinned Healthcare LocalDP/Shared source and freeze its original eight-field byte SHA; take the three positive proposed IDs directly from its review rows rather than duplicating constants. The F0 trusted, exact-marker Main one-shot does two independent SQL connections to the already approved Warehouse GUID and executes only bounded, parameterized `cdm.concept` SELECT for these three IDs. Require complete eight-column Concept rows, exact ID and Race/Visit Domain, Standard `S`, no invalid_reason, effective as-of UTC date and cross-connection row equality. Capture non-PHI target names, vocabularies and SHA for the clinical reviewer, with all approval and DML flags false. Do not rerun the previously verified 8657 query or collect raw FHIR records. Offline and physical evidence are separate: no target record may be called PASS before a distinct real workflow Run and readback. F1 Source Audit 9/9, blank versions, rights and all independent signoffs remain outside this read-only task.

The clinical reviewer must see the actual target Concept names and vocabulary provenance, not only the three numeric proposed IDs. A physical SELECT PASS remains a review-only fact: a separate approval must explicitly resolve both clinical equivalence and the two `UNK` NullFlavor rows before any release capability is considered.

## P3.18 — Source-only signed provider attestation architecture (not a release capability)

Use **one platform-neutral attestation contract** in the existing Shared Engine. Provider evidence and Native controller may both use its exact canonical byte parser and verifier after a separately reviewed Wheel release; do not duplicate a second Mapper or drift the proof schema. The signed payload binds immutable source batch/request/Manifest/Mapping Profile SHA; Warehouse + Workspace GUID, verified F1 release metadata digest and F2 logical snapshot fingerprint, clinical/license *receipt digests*, issuer, intended native audience, approved controller source SHA, short UTC expiry (at most 5 minutes), and a 128-bit nonce. Receipts and hashes only identify evidence; they DO NOT certify clinical or license authority, F1 9/9 audit or durable IDs. The verifier strictly rejects extra/duplicate fields, unknown issuer/key, signature substitution, wrong audience, expired/future attestation, wrong pinned scope/controller, and missing replay protection. Keys come only from a separately reviewed Native trusted configuration, **never signed JSON, job inputs or Notebook parameters**. Nonce claim must be externally durable and atomic with TTL at least through expiry; an in-memory test implementation is not production evidence. Nonce is consumed only *after* signature and scope verification. Unknown ACK requires checking the durable claim/readback rather than blind replay. Source-only verifier yields only a typed VERIFIED_TRANSPORT_ONLY_NOT_RELEASE_AUTHORITY receipt; it never creates a writer capability or invokes Fabric Notebook, Spark, Delta, Gold, Warehouse DML or long-lived ID reservation.

The only native execute path remains HALT until actual clinical & license role-separated human approval, F1 full provenance audit / blank-version decisions, pinned reviewed signer public key onboarding, genuine Native transport integration, and a single-writer fresh F2 SQL transaction barrier. P3.18a is safe without any production signer and must ship with empty production trusted key set and no approved release artifacts. P3.18b is a separate future reviewed step.
