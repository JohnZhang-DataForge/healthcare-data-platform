# Fabric Blob Batch Control — CODE map

Scope: `fabric-blob-batch-control-mvp` (OpenSpec). Platform-side source; **SOURCE / CI ONLY** until separately authorized real Azure checks. This component does not run automatically from Fabric, LocalDP or Self-Runner.

| Source / CI | Owner |
| --- | --- |
| [blob_batch_ledger.py](../../../../azure-fabric/blob-control/blob_batch_ledger.py) | Validated StageScope / version digest / Manifest-last source verification; Shared `BatchContext` + `decide_replay`; conditional Claim, bounded owner, finalization, stage Receipt and unknown ACK HOLD |
| [azure_blob_backend.py](../../../../azure-fabric/blob-control/azure_blob_backend.py) | Existing `johnzhang/landing` Container client; SDK conditional create / ETag CAS / short renewable Lease; per-key strict write allowlist only |
| [test_blob_batch_ledger.py](../../../../.github/quality/tests/azure-fabric/blob-control/test_blob_batch_ledger.py) | Synthetic positive/negative/concurrent/partial/unknown-ACK source tests |
| [Offline Workflow](../../../../.github/workflows/fabric-blob-batch-control-offline.yml) | Hosted Python 3.11/3.13 no-OIDC CI only |

## Hard boundary

- `clinical/v1/<hospital>/<feed>/<request>/` immutable manifest-last source remains untouched. No Blob DELETE, COPY, MOVE, prefix scan or container creation.
- Control object: `_control/v1/<hospital>/<feed>/<request>/<stage>/claim.json`. Only CAS on this exact object may mutate, under an active lease; no automatic stale-lease stealing.
- Completion: `processed/v1/<hospital>/<feed>/<request>/<stage>/<version-digest>/receipt.json`. Conditional-create once, exact GET readback. No Patient/Encounter duplication.
- Stage enum: SILVER_APPROVED / CANDIDATE_APPROVED / GOLD_COMMITTED; no cross-stage inference. The source batch uses Shared `BatchContext.source_batch_id`; release digest additionally includes landing-manifest SHA/ETag, processing/Mapper/Wheel/profile versions, publication and stage.
- `TargetProof` is **caller-provided evidence**, not a proof generator. Only an independently authorized Fabric source reader may populate verified evidence after actual target readback. Do not enable public/untrusted invocation; Blob control itself cannot verify Warehouse SQL/Delta transactions. Source CI PASS does not approve actual release.
- `precheck` returns SKIP only on exact immutable receipt *and* COMPLETED same-scope claim, subject to trusted provenance; missing or uncertain control/receipt returns VERIFY_READONLY, not automatic replay.
- Reuses existing Publisher SP credentials when explicitly provided by a runner: `AzureBlobBatchBackend.from_existing_publisher_sp`. Never pass Fabric WorkspaceIdentity Reader credentials as if they were Contributor.
- No runtime import or change of Shared Engine Wheel; new code imports existing pure `healthcare_data_engine.models.batch_context` and `reconciliation.replay`.
- AWS/LocalDP PostgreSQL Ledger remains the runtime owner for Local; G5 P3.19 signed nonce contract remains a separate HOLD.

## Testing and deployment status

Offline CI: `PYTHONPATH=shared-data-engine/src:azure-fabric/blob-control python -m unittest discover -s .github/quality/tests/azure-fabric/blob-control -v`.

Before any live acceptance: observe latest Healthcare/Self-Runner SHA and active HL7/FHIR runs, audit the actual Publisher/SP data-plane read/create/CAS/lease permissions, check for preexisting control prefix collisions, and use a completely new synthetic request through a separately approved Self-Runner workflow. Do not configure this as an automatic Fabric Job or start Capacity. Runtime HTTP/ETag/request-ID evidence remains **NOT_RUN** until explicitly recorded.
