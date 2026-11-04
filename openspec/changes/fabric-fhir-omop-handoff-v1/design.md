# Design — FHIR → OMOP integration boundary, v1

## Real verified baselines (read-only facts)

- G4 approved request `atlanta-fhir-gh-41552666929`, delivered Manifest SHA `425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1`, input P100/E5918/Q0, rejected G4.c request P99/E5893/Q26 is **not** approved.
- G5 actual Fabric Pipeline Job `7069b9d5-0617-442f-a976-833e56189997` + independent Silver readback Job `3d16895a-d19d-45db-999b-2cad77983399`; Self-Runner run [41636454542](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41636454542) `FHIR_G5_EXISTING_PIPELINE_COMPLETED_SILVER_INDEPENDENT_READBACK_PASS`.
- OMOP Foundation F0 Warehouse `dw-omop-5.4` existing item `7a6d08da-278d-4603-8a3b-28640110984c`; full OHDSI 5.4 empty schema 39 tables/432 columns real readback PASS [run 41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578). **F1 ID Map and real Vocabulary not yet accepted.**

## Producer: Approved Silver only

Source Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`, Lakehouse `e67c42ee-5ab2-4bc8-a013-7bdf9741ef68`. The Fabric-owned canonical files are request scoped:
`Files/silver/fhir_r4/<hospital_id>/<feed_id>/<request_id>/processing=<sha256(processing_version)>/{canonical_patient,canonical_encounter,silver_approval}`.

Actual `_g4_paths` currently uses fixed trusted Atlanta namespace and a request-id allowlist. **Do not turn this into unvalidated path concatenation.** A later multi-hospital rollout needs a separately reviewed manifest-derived namespace resolver and permissions.

The source batch ID equals SHA256 of compact JSON encoding `[hospital_id,feed_id,raw_source_system,request_id,manifest_sha256]` (Python BatchContext semantics, ASCII JSON separators `,:`). Canonical `source_system` column is `raw_source_system:hospital_id:feed_id`; this is a source-namespace string, **not** an OMOP person ID. Both Silver tables must have the same exact `source_batch_id` and namespace, unique source PK, Encounter→Patient FK and date/DQ checks. One persisted `silver_approval` row must match batch/Manifest/processing/publication, original Patient/Encounter contracts' pinned SHA, P/E counts, source-preservation strategy `DELTA_RAW_SNAPSHOT_V1`, zero Quarantine and literal `SILVER_APPROVED`.

An independent Spark/Delta **physical readback** of BOTH canonical tables + Approval is mandatory each execution. A passed Python metadata envelope validator, one Pipeline Completed, or a copy of a known PASS string is **not** physical evidence.

## Consumer: Fabric OMOP Foundation

The separate Agent owns F1 Warehouse `etl.identity_map` (or an independently versioned read-only adapter with exactly the equivalent semantics), official `cdm.concept` Vocabulary release/validity, `etl` transaction ledger and `audit` reconciliation. The source-person identity key is the composite `(hospital_id, feed_id, raw_source_system, source_record_id)`; source-encounter identity uses the same namespace plus `source_encounter_id`. Identity allocation is **Warehouse-owned, persistent, concurrency-safe and deterministic on replay**; no Local PostgreSQL ID maps, row_number, hash-derived final IDs, display name/DOB fuzzy matching or unscoped join.

The current `candidates.py` accepts an injected `source_system,source_person_id,person_id` DataFrame and checks int32/unique. That DataFrame MUST be materialized from a fully verified F1 namespace-preserving allocation snapshot; **do not pass unscoped source IDs or claim this mapper independently prevents cross-hospital collisions**. Record F1 adapter contract as a separate blocking dependency and fix/verify target namespace joins in the future integration PR.

Mapping uses a pinned, fully reviewed Concept profile with signed/digested lookup evidence, compatible official Vocabulary release, standard-concept and validity checks, and explicit source-code fallbacks. No arbitrary Concept IDs or invented clinical dates. Official Warehouse 5.4 Person/Visit types are int and source-value columns have bounded lengths; validate before SQL to avoid truncation. `visit_occurrence_id` is not allocated by Silver nor by a Candidate-only transform; Gold writer must allocate it in the Warehouse with stable source-visit mapping.

## Handoff envelope and safe replay

Machine contract: `shared-data-engine/contracts/fabric-fhir-omop-handoff-v1.json`.
Pure validator: `healthcare_data_engine.models.fabric_omop_handoff`.

The handoff envelope contains only batch metadata, exact physical path coordinates and an independently persisted Approval row. It MUST verify exact key set/types, stable source-batch SHA, canonical source namespace, processing digest, physical workspace/Lakehouse/Warehouse pins, original canonical contracts' SHA, Approval/manifest/processing/row counts. Its result is always `STRUCTURAL_PASS_PHYSICAL_READBACK_REQUIRED`, **never approved or committed**. It must reject unapproved/quarantined/duplicate/missing/mismatched batches and tampered paths.

Replay key for later integration: `(hospital_id, feed_id, raw_source_system, request_id, manifest_sha256, processing_version, publication_id, mapping_profile_sha256, identity_snapshot_version, vocabulary_release_id)`. A same-request changed manifest/contract/mapping is a **new reviewed version or HOLD**, not silent re-use. Unknown ack => GET-ledger/readback and HOLD until reconciled; no blind retry. Candidate-only Delta approval LAST; Gold is separately fenced Warehouse transaction and readback; no Part-1 write.

## Sequencing / acceptance

**Stage 1 in this PR**: OpenSpec, machine contract, envelope validator, negative tests, offline CI and CODE map — no runtime writes. **Stage 2 blocked on F1**: agree exact Warehouse ID snapshot + Vocabulary adapter/profile, deploy new Wheel + Spark integration, independently verify actual Candidate Delta. **Stage 3 blocked on Stage 2 and F2**: Warehouse Gold COMMIT, independent SQL readback, FK/DQ and replay SKIP. Only real run IDs count as completion.
