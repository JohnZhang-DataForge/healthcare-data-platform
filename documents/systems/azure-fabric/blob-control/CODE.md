# Fabric Blob Batch Control — CODE map

Scope: `fabric-blob-batch-control-mvp` (OpenSpec). Platform-side source; Azure Claim/CAS/Lease accepted in Tasks 3.1–3.2. **Task 3.3 is now physically accepted for exactly one previously approved G4 `SILVER_APPROVED` target**: one real Azure Completion Receipt + terminal Claim, independent GET, and a second isolated Blob-only SKIP (`Self-Runner` PRs #693/#694; Runs #42707893782/#42708750893). Generic automatic Fabric/Gold/G5 orchestration is still **HOLD**; no component is enabled to auto-run from Fabric, LocalDP or Self-Runner.

| Source / CI | Owner |
| --- | --- |
| [blob_batch_ledger.py](../../../../azure-fabric/blob-control/blob_batch_ledger.py) | Validated StageScope / version digest / Manifest-last source verification; Shared `BatchContext` + `decide_replay`; conditional Claim, bounded owner, stage Receipt and unknown ACK HOLD; completion now requires a trusted injected physical-target readback verifier and a second source verification |
| [azure_blob_backend.py](../../../../azure-fabric/blob-control/azure_blob_backend.py) | Existing `johnzhang/landing` Container client; SDK conditional create / ETag CAS / short renewable Lease; per-key strict write allowlist only |
| [test_blob_g4_identity_bridge.py](../../../../.github/quality/tests/azure-fabric/blob-control/test_blob_g4_identity_bridge.py) | Positive/negative contract for historical G4 Shared source ID vs Publisher upstream/landing Manifest SHA and format; SOURCE-ONLY |\n| [test_blob_batch_ledger.py](../../../../.github/quality/tests/azure-fabric/blob-control/test_blob_batch_ledger.py) | Synthetic positive/negative/concurrent/partial/unknown-ACK source tests |
| [Offline Workflow](../../../../.github/workflows/fabric-blob-batch-control-offline.yml) | Hosted Python 3.11/3.13 no-OIDC CI only |

## Hard boundary

- `clinical/v1/<hospital>/<feed>/<request>/` immutable manifest-last source remains untouched. No Blob DELETE, COPY, MOVE, prefix scan or container creation.
- Control object: `_control/v1/<hospital>/<feed>/<request>/<stage>/claim.json`. Only CAS on this exact object may mutate, under an active lease; no automatic stale-lease stealing.
- Completion: `processed/v1/<hospital>/<feed>/<request>/<stage>/<version-digest>/receipt.json`. Conditional-create once, exact GET readback. No Patient/Encounter duplication.
- Stage enum: SILVER_APPROVED / CANDIDATE_APPROVED / GOLD_COMMITTED; no cross-stage inference. The source batch uses Shared `BatchContext.source_batch_id`; release digest additionally includes landing-manifest SHA/ETag, processing/Mapper/Wheel/profile versions, publication and stage. A historical approved G4 Scope MAY carry an explicit `synthea-fhir` logical source + `FHIR_R4` landing target-format bridge with **different pinned upstream Publisher SHA and delivered Landing SHA**; its original Shared Batch ID is never recalculated with a different source-system string.
- `TargetProof` is **caller-provided evidence**, not a proof generator. Only an independently authorized Fabric source reader may populate verified evidence after actual target readback; `finalize` and unknown-ACK recovery REQUIRE `target_reader.readback(scope)`, with exact proof matching. Never inject unit/Azurite fake readers in production. Do not enable public/untrusted invocation; Blob control itself cannot verify Warehouse SQL/Delta transactions. Source CI PASS does not approve actual release.
- `precheck` returns SKIP only on exact immutable receipt *and* COMPLETED same-scope claim, subject to trusted provenance; missing or uncertain control/receipt returns VERIFY_READONLY, not automatic replay.
- A different Stage (for example CANDIDATE_APPROVED) can correctly return `NEW` in read-only `precheck`, but this is **not authorization** to start that Stage: all separate G5/clinical/Native/HALT gates still apply. A SILVER_APPROVED Receipt grants no cross-stage SKIP or execution right.
- Reuses existing Publisher SP credentials when explicitly provided by a runner: `AzureBlobBatchBackend.from_existing_publisher_sp`. Never pass Fabric WorkspaceIdentity Reader credentials as if they were Contributor.
- No runtime import or change of Shared Engine Wheel; new code imports existing pure `healthcare_data_engine.models.batch_context` and `reconciliation.replay`.
- AWS/LocalDP PostgreSQL Ledger remains the runtime owner for Local; G5 P3.19 signed nonce contract remains a separate HOLD.

## Testing and deployment status

Offline CI: `PYTHONPATH=shared-data-engine/src:azure-fabric/blob-control python -m unittest discover -s .github/quality/tests/azure-fabric/blob-control -v`.

The earlier Task 3.1–3.2 true Azure Claim/CAS/Lease proofs are Self-Runner PR #672/#674 / Runs #42630476797/#42631631148 (HTTP 409/412). The only **real physical** completion under Task 3.3 is the frozen historical G4 Silver P100/E5918/Q0 case: Healthcare Main `c8affd1b`, Self-Runner PR #693 / [Run #42707893782](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42707893782) `PASS_REAL_G4_SILVER_RECEIPT_GET_COMPLETED`, immutable Receipt SHA `835263ebe44496f1f3e3bd8560b8bf654a5b6a15fe6e7fbb98bb49899727f6e6`, target proof SHA `a075ec7cef7653133c62b2ce84fbe2fe110546bf78115506ecdcaed03ece039b`, terminal Claim, no Writer or CU. Separate Self-Runner PR #694 / [Run #42708750893](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42708750893) `PASS_REAL_G4_BLOB_ONLY_SKIP_NO_FABRIC_IDENTITY`, negative drift views fail closed, no Azure mutations. See OpenSpec Tasks for Artifact IDs, SHA pins, 651 + 37 source-modeled Blob request counts, exception and ACK recovery semantics. Actual Azure billed cost is **not verified**.

**Historical registration exception:** Unlike the previously authorized new synthetic empty Batch control tests, this one *existing physically approved historical G4 Silver Stage* was registered with a freshly created control Claim **after independent physical OneLake readback**. This was a narrowly reviewed one-shot recovery/registration: no forged old Claim, no Silver rerun, no backfill of other Stage approvals or generic permission to add Receipts from logs. Original Landing remains immutable. The accepted G4 result does not grant G5 Candidate/Gold, clinical, P1/F1/F2/License or production signer approval. Do not configure automatic Batch submission or start Capacity from this result.

## Task 4.1 step A — Self-Runner pre-capacity Blob-only gate (2026-11-09)

The existing `blob_batch_ledger.precheck()` / Shared `decide_replay` remains the **single** Replay decision owner. Self-Runner [PR #696](https://github.com/JohnZhang-DataForge/Self-Runner/pull/696) adds only a read-only entrypoint:

| Self-Runner path | Purpose |
| --- | --- |
| `src/ci/fabric_blob_batch_precapacity_gate.py` | Pure no-Capacity/no-write decision: only verified exact stage is `SKIP`; `NEW`, `BUSY`, `VERIFY_READONLY`, mismatched or unknown states are `HALT` |
| `scripts/ci/fabric_blob_task41_precapacity_get_only_once.py` | Trusted GET-only G4 historical Stage/Receipt SHA pin and real read-only pre-capacity check; rejects Fabric OIDC and mutable backend exposure |
| `tests/ci/test_fabric_blob_batch_precapacity_gate.py`, `tests/ci/test_fabric_blob_task41_precapacity_get_only_once.py` | Offline source and fail-closed negative contracts; no Azure or Fabric call |
| `.github/workflows/fabric-blob-task41-precapacity-get-only-once.yml` | PR offline-only; one exact reviewed main-push marker can run real Publisher SP Blob HEAD/GET with no Fabric identity/capacity or Blob mutation |

Physical [Run #42715771329](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42715771329) PASS with exact original G4 Silver `SKIP` prior to any compute; its report and request model are recorded in the OpenSpec Tasks. This is **a partial Task 4.1 implementation**, not automatically dispatched by any existing Fabric Pipeline. It cannot reserve OMOP identities, validate or generate production signed authorizations, create Claims/Receipts, issue Notebook jobs, or start Fabric CU. An unprocessed `NEW` Stage stays HALT. Full Task 4.1 and Task 4.2 still require separate authentic stage/writer approvals.


## Task 4.1 step B1 — explicit NEW-stage source inspection (2026-11-09)

Self-Runner `src/ci/fabric_blob_task41_new_batch_admission.py` adds the **read-only** opposite path to the already real-tested G4 receipt SKIP. It uses exactly this Healthcare module's `blob_batch_ledger.precheck` + `verify_source` and the Self-Runner `fabric_pipeline_safety.safe_readonly_pipeline`. A wholly validated new Manifest/payload inventory with SHA/ETag/size and exact hospital/feed/request source returns `HALT`, **not** a Claim or a Capacity permit. A second precheck detects raced Claims; no precheck is a substitute for an atomic conditional Claim. Historical G4 must not create a second retrospective Claim for a different Stage.

[Self-Runner PR #699](https://github.com/JohnZhang-DataForge/Self-Runner/pull/699), Main `5c84c285bd83cc8bd51333b1570c19c388173402`; 12/12 offline tests and real Git Pipeline default-HALT read in [Run #42730498091](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42730498091). This step has **no live Azure test or Fabric access**. The following remain independent: signed Clinical/License review, F1 release, fresh F2 SQL six-table identity evidence, Native signed/durable nonce, approved G5 Writer and independent physical target/Receipt verification. Task 4.1 and 4.2 remain unchecked.


## Task 4.1 B2 — protected authority-to-Claim fence (source-only)

Self-Runner [PR #701](https://github.com/JohnZhang-DataForge/Self-Runner/pull/701) adds `src/ci/fabric_blob_task41_b2_authority_claim_fence.py` and `scripts/ci/fabric_blob_task41_b2_authority_readiness.py`. They compose the real existing B1 `NEW` inspector with the **existing** G5 trusted reviewer module and Healthcare Shared Native `provider_attestation` protected configuration. No new signature/Mapper/Replay/Blob authority is implemented. The strongly typed B2 report cannot set any Claim/Lease/Native nonce/Capacity/Writer grant to True. Source integrity alone cannot issue a writer authorization; old G4 production reviewer scope cannot be replayed to a new FHIR/HL7 Batch.

Review/test source: `tests/ci/test_fabric_blob_task41_b2_authority_claim_fence.py`; existing `.github/workflows/fabric-blob-task41-new-batch-source-offline.yml` now runs both B1 and B2, with **24/24** tests PASS on [Run #42752993144](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42752993144), followed by [Run #42753011249](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42753011249) SUCCESS. No Azure I/O or Fabric Capacity. The default Native `PROVENANCE_ONLY_NO_WRITE`, unonboarded production trust anchors and no Native durable nonce callback remain explicit HOLD; no actual new Blob Claim execution was attempted. Task 4.1/4.2 remain OPEN, pending an independent production stage-specific authority and physically verified target.


## Task 4.1 B3 — Stage execution lifecycle contract, offline only

Self-Runner merged [PR #705](https://github.com/JohnZhang-DataForge/Self-Runner/pull/705) adds:
- `src/ci/fabric_blob_task41_b3_stage_execution_contract.py`: read-only, non-granting B3 plan for exact Stage/Batch/version (Candidate Delta vs Gold Warehouse), composes B2; the production execution API fails closed and registered Writer list is **empty**
- `tests/ci/test_fabric_blob_task41_b3_stage_execution_contract.py`: uses a **synthetic in-memory Blob**, synthetic Writer and separate physical Reader to execute the genuine Healthcare `acquire/finalize/reconcile_unknown_finalize/precheck` methods, including Lease/CAS and failure fencing; never a source of clinical approval or physical Fabric evidence
- `scripts/ci/fabric_blob_task41_b3_lifecycle_readiness.py`: non-sensitive B3 gate audit and zero-production-mutation artifact
- Existing `.github/workflows/fabric-blob-task41-new-batch-source-offline.yml`: **41 tests** B1+B2+B3 passing [Run #42755316754](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42755316754); no Azure credential or Fabric OIDC

Future actual Stage Writer binding must preserve **one existing Healthcare Ledger** and native clinical mapper, verified signed release and independent target readback, renewable Claim Lease heartbeat through compute, receipt-last and zero blind retries on unknown Job/PUT ACK. No new Blob container, account, identity, or G5 Gold permission is created by B3. OpenSpec Task 4.1/4.2 remain OPEN.


## Task 4.1 B4 — Ed25519 Stage-specific release contract (SOURCE/OFFLINE ONLY)

Self-Runner [PR #709](https://github.com/JohnZhang-DataForge/Self-Runner/pull/709) merged Main `d00f60d8bfc6fead7a25dac8209a1ba943d01634`:
- `src/ci/fabric_blob_task41_b4_signed_stage_release.py` — source-level **independent** Ed25519 release verifier for exact StageScope, Batch, Manifest, Clinical/License, F1/F2/Native, version, Writer/Reader/target hashes, short UTC time window and nonce. Reuses the **one Shared Native canonical JSON**. It is not the existing G5 provenance-only attestation, contains **no private signing key or live issuer**, and cannot accept job-supplied production public roots. The production entry remains HALT.
- `tests/ci/test_fabric_blob_task41_b4_signed_stage_release.py` — 18 new positive/negative source-only tests with ephemeral, test-only Ed25519 keypairs. Their positive signature result is NOT a production release or permission for Claim/Capacity/Writer.
- `scripts/ci/fabric_blob_task41_b4_release_readiness.py` — sanitized authority-gap audit (zero native nonce, Blob claims and Fabric jobs); compiled/verified together with B1+B2+B3 through the existing `.github/workflows/fabric-blob-task41-new-batch-source-offline.yml`.
- Actual [Run #42758578858](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42758578858) on ARC `dw-runner-set` SUCCESS: **12+12+17+18 = 59 PASS**. Artifact ID `13736846192`, ZIP SHA256 `7a785d240d06666c4ca22ddd388c6753c71c94a4515d7c7bd0af5903a1e7d9c9`. Hosted retries before this run failed at runner allocation without steps and are not code-test failures or accepted PASS.

The next production work must onboard separate approved Clinical+License human keys, F1/F2 fresh evidence, Native protected signer/durable replay, reviewed stage-specific Writer and independent Target Reader, and continuous Lease renewal. Neither a B4 cryptographic fixture nor a Stage Claim bypasses those gates. Task 4.1 and 4.2 remain OPEN. Do not create a second Blob account/container or attach a production Fabric write identity in this source-only change.
