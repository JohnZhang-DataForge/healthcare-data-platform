# Fabric dbt — official source CODE map

**Scope: P3 local Candidate, not an approved production Publisher.** Project owner: `azure-fabric/dbt/hl7-canonical/` with dbt name `hl7_canonical`. The pre-existing dbt implementation under Local DP remains frozen reference and is the only current executable consumer path until separately tested cutover.

| Source | Responsibility |
| --- | --- |
| [dbt_project.yml](../../../../azure-fabric/dbt/hl7-canonical/dbt_project.yml) | dbt identity; staging/intermediate/canonical materializations |
| [sources.yml](../../../../azure-fabric/dbt/hl7-canonical/models/staging/sources.yml) | Physical local Delta source `hl7_staging.hl7_events` |
| [stg_hl7_events.sql](../../../../azure-fabric/dbt/hl7-canonical/models/staging/stg_hl7_events.sql) | Explicit trusted 23-field HL7 structured source projection |
| [int_hl7_patient_latest.sql](../../../../azure-fabric/dbt/hl7-canonical/models/intermediate/int_hl7_patient_latest.sql) | Deterministic patient ranking |
| [int_hl7_encounter_pairs.sql](../../../../azure-fabric/dbt/hl7-canonical/models/intermediate/int_hl7_encounter_pairs.sql) | Exact A01/A03 source, patient, batch and time pairing |
| [canonical_patient.sql](../../../../azure-fabric/dbt/hl7-canonical/models/canonical/canonical_patient.sql) | Patient v1 18-column Candidate |
| [canonical_encounter.sql](../../../../azure-fabric/dbt/hl7-canonical/models/canonical/canonical_encounter.sql) | Encounter v1 27-column Candidate |
| [canonical_models.yml](../../../../azure-fabric/dbt/hl7-canonical/models/canonical/canonical_models.yml) | Original six dbt non-null tests |
| [tests/](../../../../azure-fabric/dbt/hl7-canonical/tests/) | Native dbt SQL tests for unmatched A03, chronological reversal, identity collisions, duplicate controls/keys, orphan Encounter and missing/invalid facts |
| [profiles.yml](../../../../azure-fabric/dbt/hl7-canonical/profiles/local/profiles.yml) | Credential-free `dbt-fabricspark` local session with isolated `hl7_candidate_p3` schema |

Unused standard `macros/`, `seeds/`, `snapshots/`, `analyses/` are tracked with `.gitkeep`; `packages.yml` is not needed.

## Contracts, runtime and retirement boundaries

- Contract authority stays [Patient v1](../../../../local-data-platform/spark/contracts/canonical/patient-v1.json) (18) / [Encounter v1](../../../../local-data-platform/spark/contracts/canonical/encounter-v1.json) (27); these are **not copied or redefined** in dbt.
- Parser, Intake, physical Delta Staging Writer and frozen legacy SQL/config stay owned by [HL7 CODE](../../data-platform/hl7/CODE.md).
- New [offline hosted P3 acceptance workflow](../../../../.github/workflows/hl7-dbt-canonical-candidate-offline.yml) and [independent candidate readback / isolated negative fixture script](../../../../.github/quality/tests/data-platform/hl7/check_new_dbt_candidate.py) cover the new project separately from the existing [legacy baseline Workflow](../../../../.github/workflows/hl7-local-delta-dbt-offline.yml).
- Business change: [Fabric dbt OpenSpec P3](../../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md). Distinct [HL7 Consumer Change](../../../../openspec/changes/implement-hl7-local-delta-dbt-canonical/tasks.md) owns future real Azure GET, Silver and OMOP integration.
- All CI data is synthetic, local Spark/Delta only. P3 local PASS never means actual Azure 42-object HL7 intake, Fabric Spark, approved Canonical Silver or OMOP Gold.
- Only after independent acceptance should a **separate** consumer cutover PR update the sole formal execution path. A later separately validated cleanup PR removes obsolete old dbt SQL/config/profiles, **not** Python parser/intake/writer or required regression tests.
