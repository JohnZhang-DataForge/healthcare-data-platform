# HL7 V2 — scoped Azure GET-only source readback

**Status: CODED + OFFLINE SYNTHETIC TEST ACCEPTED (Run #42449129041); real Azure GET still NOT AUTHORIZED/NOT EXECUTED.** This is a non-deploying source adapter governed by [HL7 Consumer Active OpenSpec](../../../../openspec/changes/implement-hl7-local-delta-dbt-canonical/tasks.md), not approval to access existing Blob, OIE, Spark, Fabric or Silver.

## Exact scope and provenance

The user/authorized operator MUST first independently verify the already published immutable Landing Manifest key, its SHA-256 and the frozen original source Manifest SHA-256 from existing publish receipts. Never infer "latest" from Blob LIST or filenames. The exact request ID is bound to:

`clinical/v1/johns-creek-hospital-b/johns-creek-hospital-b-hl7-v2/<request_id>/landing-manifest.json`

All declared object keys must be exactly under that same request's `HL7_V2/hl7/` path. The reader rejects a mismatched object count (expected historical 42, but still independently pin the actual count), foreign keys, changed bytes/SHA/ETag/Version, unexpected publisher metadata, source/clinical profile mismatch and changed Manifest on reread.

## Live GET runtime gate — not executed

Before any cloud network call, confirm current Main SHA, exact already published Batch and original Manifest/receipts, target Storage Account and Container, **least-privilege Storage Blob Data Reader** role, current Agent/Workflow/Runner occupancy, secure private local storage and clean-up policy. Do not rerun historical producer or OIE messages. Read [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md) and [Session Coordination](../../../engineering/development/SESSION-COORDINATION.md). The CLI switch `--approved-get-only` is a fail-closed code gate but **never substitutes for actual user approval**.

Only on that **separately approved runtime**, install the optional `local-data-platform/spark/apps/hl7/requirements-azure-readback.txt`. It references the existing version-pinned Parser/Spark/Delta requirements and Azure publisher SDK pins. Runtime credential env variables are `AZURE_BLOB_ACCOUNT_URL`, `AZURE_BLOB_CONTAINER`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`. Never print/commit/share credentials or raw patient HL7; account URL must be public HTTPS Azure Blob and contain no SAS/query.

**Future invocation template, NOT executed by this PR:**

~~~text
python local-data-platform/spark/apps/hl7/azure_blob_readback.py \
  --request-id <independently pinned request ID> \
  --manifest-key <exact approved Blob key> \
  --manifest-sha256 <verified 64-hex SHA> \
  --source-sha256 <verified original source Manifest SHA> \
  --expected-objects <verified exact count> \
  --output-root <new private absolute local path> \
  --ingest-date <YYYY-MM-DD> \
  --processing-run-id <approved run identifier> \
  --processed-at <YYYY-MM-DD HH:MM:SS> \
  --approved-get-only
~~~

The adapter reads exact Azure keys only and then stages validated bytes to a newly created restricted local directory (`landing-manifest.json` and `staged-local-blob-keys/`). Reprocessing the **same local validated staging** returns `ALREADY_MATCHING_LOCAL_REPLAY_SKIP` without a new remote GET, and a conflict is HOLD. Source validation reuses existing `landing_intake.py` and `parse_oie_v2.py`; a subsequent **separate** controlled step may supply these files to `write_staging_delta.py` and the sole governed dbt project. This adapter does not do that step, approve Canonical Silver or write OMOP Gold.

## Test-only evidence

Centralized `.github/quality/tests/data-platform/hl7/test_azure_blob_readback.py` builds fresh synthetic OIE V2 A01/A03, uses a fake read-only backend (no Azure SDK or credentials), and checks manifest-first, allowed exact keys, local replay, source/clinical facts, SHA, count, ETag, version, metadata, safe paths and changed-manifest rejection. CI success is **source offline test only**, not GET of historical real Azure 42 objects.

## Actual synthetic acceptance (not remote)

[PR #824](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/824), source SHA `08b5f58718ae10df82130fd2aa1850ad4560265d`, [Run #42449129041](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42449129041): 28/28 Parser/Intake and exact GET fake-backend unit tests; actual local staging CREATED/replay SKIP; dbt models 5/5 and tests 15/15; independent physical local Delta Patient 18/Encounter 27 contract readback. No Azure identity loaded and no remote Blob GET, OIE, Fabric CU, Silver or Gold operation.
