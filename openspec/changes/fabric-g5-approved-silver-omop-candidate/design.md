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
