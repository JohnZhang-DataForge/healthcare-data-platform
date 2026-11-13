# Design — Compatibility-first semantic source naming

## Verified starting point (2026-11-13 ET)

Healthcare Main `b74211f3af9ca13992d9bc11fff32bc8d40da884`. Self-Runner Main `0bfe78f2eb49b6f127ad9ac1b3654200550a15b8`; Self-Runner PR #795 remains open and its naming CI is not verified PASS. Re-check both Main and PRs before each implementation. Main code and prior CI are not cloud deployment evidence.

## Tier A — private helpers (first business-code PR)

In `azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py`:
| Original name | Semantic target |
| --- | --- |
| `_g3_receipt_path` | `_bronze_source_receipt_path` |
| `_g3_expected_receipts` | `_expected_bronze_source_receipts` |
| `_g3_delta_exists` | `_delta_snapshot_exists` |
| `_g3_independent_receipt_readback` | `_verify_bronze_receipt_readback` |
| `_g4_paths` | `_silver_publication_paths` |
| `_g4_approval_row` | `_silver_approval_row` |
| `_g4_snapshot_source_objects` | `_snapshot_silver_source_objects` |
| `_g4_validate_full_delta` | `_validate_silver_delta_contents` |
| `_g4_independent_silver_readback` | `_verify_silver_publication_readback` |
| `_g5_candidate_content` | `_candidate_delta_content` |
| `_g5_candidate_validate_rows` | `_validate_candidate_rows` |
| `_g5_candidate_verify_mapper_payload` | `_verify_candidate_mapper_payload` |

These are underscore-prefixed Notebook helpers. Check all Python references and source-introspection tests, and preserve behavior and byte-for-byte output; no changes to path values, request IDs, statuses, schemas or writer gates. No old-alias creation without a verified external consumer. Anything called through external dynamic lookup must be promoted to Tier B.

## Tier B — callable/runtime-facing interfaces

Examples: `verify_fhir_g3_bronze`, `verify_fhir_g4_silver`, `verify_fhir_g5_dynamic_silver_source_readonly`, `plan_and_write_g5_candidate_delta`, `execute_g5_person_visit_business`, Self-Runner `fabric_g5_p2_trusted_source_readonly_controller.py`. Inventory all `runpy.run_path`, `getattr`, imports, CLI inputs, Job arguments, Workflow references and installed wheel versions, then provide semantic entrypoints preserving legacy consumers. Do not rename verified external entrypoints in place.

## Tier C — immutable or signed contracts

Keep old `fabric-g5-technical-evidence-transport-v3`, `G5_CANDIDATE_WRITE`, old `G5_...` errors/statuses, old `f1_release_metadata_sha256`/`f2_identity_snapshot_fingerprint` transport keys, issuer/audience, digest and old receipts as-is pending independently accepted protocol migration. An old signed envelope must validate only against its old schema and original canonical bytes; a new semantic protocol version must have new explicit schema, issuer/audience checks, replay isolation and atomic nonce scope. Never silently translate signed bytes.

## Validation

1. Exact Main SHA, PR inventory and read-only symbol reference inspection.
2. Diff of normalized executable code for Tier A: unchanged control/data logic except helper names and related test references; no mode/schema/error/path/authorization change.
3. Notebook offline Bronze/Silver/Candidate/HL7 contract tests, Shared Engine tests and source/structure/semantic naming checks.
4. Confirm no production Fabric or Azure writes occurred. For Tier B, separately verify cross-repo imports and source-only runtime. For Tier C, separate versioned compatibility tests and authorized E2E before release.

## Rollback

Revert the bounded rename PR if source-only tests, diff invariants or consumers fail. Do not replay frozen batches, overwrite Delta receipts, rotate signer, or rename historical artifacts.
