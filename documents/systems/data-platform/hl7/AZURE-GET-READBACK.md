# HL7 V2 — scoped Azure GET-only source readback

**Status: original 42 real Azure HEAD/GET + ephemeral local Delta/dbt Candidate accepted (Run #42488836550, 2026-11-08); formal Canonical Silver/OMOP still OPEN.** This is a non-deploying source adapter governed by [HL7 Consumer Active OpenSpec](../../../../openspec/changes/implement-hl7-local-delta-dbt-canonical/tasks.md), not approval to access existing Blob, OIE, Spark, Fabric or Silver.

## Exact scope and provenance

The user/authorized operator MUST first independently verify the already published immutable Landing Manifest key, its SHA-256 and the frozen original source Manifest SHA-256 from existing publish receipts. Never infer "latest" from Blob LIST or filenames. The exact request ID is bound to:

`clinical/v1/johns-creek-hospital-b/johns-creek-hospital-b-hl7-v2/<request_id>/landing-manifest.json`

All declared object keys must be exactly under that same request's `HL7_V2/hl7/` path. The reader rejects a mismatched object count (expected historical 42, but still independently pin the actual count), foreign keys, changed bytes/SHA/ETag/Version, unexpected publisher metadata, source/clinical profile mismatch and changed Manifest on reread.

## Live GET runtime gate — not executed

Before any cloud network call, confirm current Main SHA, exact already published Batch and original Manifest/receipts, target Storage Account and Container, **explicitly verified approved Azure identity** (Reader preferred in production; previously proven Publisher allowed solely for this single code-operation GET-only pilot), current Agent/Workflow/Runner occupancy, secure private local storage and clean-up policy. Do not rerun historical producer or OIE messages. Read [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md) and [Session Coordination](../../../engineering/development/SESSION-COORDINATION.md). The CLI switch `--approved-get-only` is a fail-closed code gate but **never substitutes for actual user approval**.

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

## 2026-11-08 — authorized GET, blocked at dedicated Reader configuration

The original exact request is `johnscreek-hl7-gh-42410482514`; independently verified original Blob Manifest SHA is `dfb9895554470b0cb31536a041cd38aef5aaedd11ff762f491ce54e6dd1df114` and Source Manifest SHA is `3999e773321a76a5d8421d62af23d24d833261a65812ea24e14e7e828f960a93`, 42 HL7 ADT events. Authorized source SHA for this particular read is Healthcare Main `21648b0270540ae7044d8ded81f6a1fc9870efe2`.

The actual controlled hosted execution is now in [Self-Runner PR #596](https://github.com/JohnZhang-DataForge/Self-Runner/pull/596), merged `ca344067ddab54994ed5224c8ff24ae4ed262249`, `.github/workflows/hl7-azure-exact42-consumer-once.yml`. CI [Run #42467014533](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42467014533) confirmed five offline tests PASS but Reader configuration **MISSING_OR_NOT_ACCESSIBLE**. Neither the one-shot Main marker nor a real Azure GET has been run. The existing Contributor Publisher secret is not an approved substitute; real Azure IAM changes or secrets must be handled through authorized credential administration, not committed to Git. When independently configured, the workflow checks the exact Reader role at the original Azure container by ARM GET before first Blob GET, and then processes bytes through the existing local Delta + dbt Candidate, deletes ephemeral Runner files, never uploads raw records and never touches Silver/OMOP.

**Main verification:** [Self-Runner Run #42467343863](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42467343863) confirmed `HL7_P2_MAIN_READER_CONFIG=MISSING` in the main-branch context and `HL7_P2_NO_REMOTE_AZURE_REQUEST=YES`. This is confirmed unavailable configuration rather than just potential PR Secret masking; user approval of the one-shot GET remains valid but cannot override the credential/RBAC Gate. [PR #597](https://github.com/JohnZhang-DataForge/Self-Runner/pull/597) merged the same workflow's no-cloud Main credential check; there is still **no approved one-shot marker / live GET Run**.


## 2026-11-08 — P2.1 pilot credential-route correction (latest authority)

The current **single-run** original-42 GET-only controller is permitted to use the **already tested Publisher** identity (`AZURE_BLOB_PUBLISHER_CLIENT_ID`, `AZURE_BLOB_PUBLISHER_TENANT_ID`, `AZURE_BLOB_PUBLISHER_CLIENT_SECRET`) from Self-Runner, per the latest owner instruction. P3 [Run #42412009780](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42412009780) used this identity to read back all 42. The absence of newly invented `AZURE_BLOB_READER_*` variables does not demonstrate a permission gap. **Storage Blob Data Contributor is not a Reader-only principal**. The approved pilot is code-operation read-only: obtain Storage OAuth, verify the pinned principal/token and perform exact-key Blob properties/conditional downloads with the verified `AzureGetOnly` adapter, never Blob LIST/PUT/POST/DELETE or OIE POST. Limit the sensitive secret to the exact authentication and read step, keep a one-shot Main commit gate and all source identity/SHA/ETag checks. No additional live authorization exists for shared Silver/OMOP, producer replay, Azure IAM mutation or persistent Processing. Dedicated least-privilege Reader remains the preferred later production option, **not a prerequisite for this already-approved pilot**. Historical Reader-only statements above are superseded only for the one-shot P2.1/P2.2 run. Actual real-source GET remains OPEN until a newly observed successful Run.

## 2026-11-08 real-source original42 P2 completion

[Self-Runner Main Run #42488836550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42488836550) **COMPLETED SUCCESS** with independently inspected Job logs. Main source SHA `c35554cfbafa071fbede7c6b82191158939da7fc`, pinned Healthcare Source SHA `21648b0270540ae7044d8ded81f6a1fc9870efe2`; original request `johnscreek-hl7-gh-42410482514`, original Azure Manifest SHA `dfb9895554470b0cb31536a041cd38aef5aaedd11ff762f491ce54e6dd1df114` and Source SHA `3999e773321a76a5d8421d62af23d24d833261a65812ea24e14e7e828f960a93`.

Exact one-shot gate/parent and original Publisher Storage OAuth `PASS`. Real Azure 42 exact Blob GET + Manifest `PASS`, 42 strict clinical intake rows `PASS`, local physical Delta + safe same-source replay `PASS`, dbt 5 Models+Data Tests `PASS`, independently reopened Patient 18/Encounter 27 Canonical Candidate Delta `PASS`. The controller reported `HL7_P2_APPROVED_SILVER_AND_OMOP=NO` and `HL7_P2_RAW_BYTES_AND_CANDIDATE_REMOVED_WITH_EPHEMERAL_RUNNER=YES`. No external new Processing Cache, storage or Ledger; Producer and original Landing immutable objects untouched. The credential remained write-capable RBAC; only the audited exact-key GET/HEAD methods were called. The obsolete dedicated-Reader-only prerequisite is superseded **only for this bounded pilot**.

Historical first-add marker [Run #42488454417](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42488454417) **skipped** live job due an unreliable push-event `head_commit.added` condition; [PR #614](https://github.com/JohnZhang-DataForge/Self-Runner/pull/614) tightened launch to an exact new Marker path plus full in-script single-file first-add and parent SHA validation, then [PR #615](https://github.com/JohnZhang-DataForge/Self-Runner/pull/615) triggered the single successful run. No retry of completed job, no automatic schedule, and no Silver/Gold authorization.
