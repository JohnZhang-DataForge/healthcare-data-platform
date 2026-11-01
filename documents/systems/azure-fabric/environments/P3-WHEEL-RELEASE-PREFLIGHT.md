# P3 Wheel 0.1.1 — Fabric live preflight and release decision (2026-11-01)

> **Current state: HOLD — Git main is NOT Fabric staging/published state.** This is a read-only evidence and rollout decision document; it neither authorizes `UpdateFromGit` nor `Environment Publish`, Notebook binding, Spark execution or data writes.

## Provenance and versions

| Gate | Evidence | Observed result |
| --- | --- | --- |
| Source and package | Healthcare [PR #585](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/585), [CI #41316184936](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41316184936) | Shared Engine 0.1.1 real Wheel install PASS on Python 3.11 and 3.13; PySpark 3.5.7/4.1.1 regression PASS; repeatable SHA256 `4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3` |
| Git-native Environment | Healthcare [PR #590](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/590), merged main `4d16469349e3ed629a2ed3f4b308bbf29702bec4` | Sole Git CustomLibraries Wheel is 0.1.1; exact byte comparison to rebuild PASS; **no cloud state implied** |
| Trusted cloud metadata preflight | Self-Runner [PR #383](https://github.com/JohnZhang-DataForge/Self-Runner/pull/383), main `424d6313292420156663e407a1bdeeabe1aab3a1`, [live run #41319069996](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41319069996) | All 3 jobs PASS, including **GET-only** Fabric OIDC readback; Git provider credential rebind disabled for automatic main push |
| Cloud Git connection/status | Live `fabric-git-preflight-41319069996` artifact | GitHub `main` remote SHA `4d16469349e3ed629a2ed3f4b308bbf29702bec4`, Fabric synced workspace HEAD `8188cddcd79f0654eff1d95b81fd97ad94604f2d`; `HOLD_UNAPPROVED_CHANGES` |
| Cloud Environment staging | Live `fabric-p2-live-definition-41319069996` artifact | Exactly 1 custom library listed, **0.1.0 legacy=True**, **0.1.1 target=False**; release state `HOLD_LIBRARY_READBACK_UNAVAILABLE` |
| Cloud Environment published | Same live artifact | `GET /libraries?beta=false` HTTP 404, effective published Wheel **UNKNOWN**. Historic `publishDetails.state=Success` / `sparkLibraries.state=Success` is not proof of effective 0.1.1 |
| Notebook binding + runtime | Same live artifact | ipynb metadata `NOT_DECLARED_IN_IPYNB` (not proof of unbound); real Spark binding/import **NOT_VERIFIED**, no Spark session executed |
| Notebook and Pipeline | Live drift artifact `fabric-git-drift-41319069996` | Notebook/Pipeline safe readback PASS but cloud-local representation differs from Git (details below); Notebook runtime code still pins engine 0.1.0 with `run_mode=HALT` |

## Why automatic UpdateFromGit correctly stopped

The trusted Git status at the exact cloud HEAD/remote SHA lists **three** items, no reported `Conflict`:

| Item | Item type in live Git status | Remote change | Workspace change | Action now |
| --- | --- | --- | --- | --- |
| `env_healthcare` | `Environment` | `Modified` | `None` | Candidate incoming Git 0.1.1, **not yet cloud staged** |
| `nb_fhir_ingest` | `SynapseNotebook` | `None` | `Modified` | Preserve cloud-local item and compare serialization before any change |
| `pl_fhir_ingest` | `Pipeline` | `None` | `Modified` | Preserve physical ID references, compare before any change |

The read-only drift tool found Notebook code-cell sequence equal but **parameter metadata not semantically identical** (one end-of-file diff span). For Pipeline, its two reported property differences are physical Notebook/Workspace references in cloud versus Git logical/same-workspace sentinel references; the cloud pipeline still points to the actual notebook and same workspace, and its HALT parameters are preserved. These observations do **not** authorize discarding cloud-local definitions.

**Important limitation:** Fabric's standard Source Control Update operation updates the connected branch to the latest commit; the UI cannot select only one Environment Item for Update. The UpdateFromGit API accepts per-item **options**, but that is not a documented selective item list. It may affect relevant incoming changes according to Git status, and must never be invoked automatically here merely because the remote Env update is the only incoming one. Official references: [Git integration process](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/git-integration-process), [Update From Git REST API](https://learn.microsoft.com/en-us/rest/api/fabric/core/git/update-from-git), [Environment Git staging vs Publish](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline).

## Controlled forward sequence — **all cloud write steps require new explicit authorization**

1. **Read-only re-preflight**: check real Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`, Environment `d85a4218-8da0-46ed-8517-b5eced219dd5`, Notebook `8311ab6b-3484-4e96-8370-badeeb751633`, authenticated Git connection, `workspaceHead`, `remoteCommitHash` and full item status. Halt if new changes, conflicts, unexpected item types, unknown IDs or concurrent update/publish appear.
2. **Resolve the drift preservation plan (no write now)**: review/export a controlled backup of current Notebook/Pipeline definitions using readback, record their hashes and physical references, compare parameter metadata. Existing local-only modifications MUST NOT be silently committed, undone or overwritten. Confirm any update's precise side effects and recovery steps. No assumption of item-specific Git update.
3. **Separately authorized Git UpdateFromGit**: only after reviewing the *whole* branch update scope, approved exact HEAD pair, rollback and credential state. Never use permissive override/conflict resolution defaults to force changes. After the operation, independently GET Git status and Environment staging. Expected staging sole 0.1.1; if still 0.1.0 or API unavailable, HOLD. **Git sync does not Publish.**
4. **Separately authorized Environment Publish**: compare staging and published libraries, check in-flight Publish, Runtime 2.0/Python 3.13 compatibility and session/capacity impact; obtain explicit approval before Publish. Capture LRO/targetVersion and published readback. Published 404 remains UNKNOWN until evidence resolves it.
5. **Coordinated Notebook update and binding**: the existing Notebook explicitly requires engine `0.1.0`. Do not remove that gate as part of step 3. Separately review the 0.1.1 Notebook version pin, Fabric native `env_healthcare` binding, running Session impact and retained `run_mode=HALT`, `write_authorized=False`, `retention_preflight_verified=False`, and `HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED`.
6. **Separately authorized non-writing Spark smoke**: only inside a fresh explicitly approved environment/session, check `importlib.metadata.version('healthcare-data-engine')`, module `__version__` and path; do not read patient data, run the production Notebook or write Delta/OneLake/PG.
7. **Next development change**: only after all gates have evidence, plan the actual FHIR Bronze/Silver data execution in its own reviewed change; no inferred E2E or Silver APPROVED from isolated import.

## Hard stop / rollback

- Without explicit cloud-action authorization: **GET-only, HOLD**. There is **no automatic recovery, overwrite, Publish or Notebook execution**.
- Preserve old 0.1.0 Wheel provenance SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7` for comparison, not automatic re-upload.
- If a read-only endpoint returns an unclassified 404, mark Published UNKNOWN; do not infer that historical Publish Success means the new Wheel is effective.
- Re-run a trusted read-only preflight immediately before any separately approved mutation. Keep logs scrubbed of credentials, raw Notebook source and personal healthcare data.
