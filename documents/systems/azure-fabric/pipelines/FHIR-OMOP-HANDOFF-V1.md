# Fabric FHIR → OMOP boundary v1 — two independent workstreams

**This is the normative Stage-1 contract, not a Fabric OMOP write authorization.** The G5 FHIR owner publishes an **Approved Silver snapshot**; the OMOP Foundation F1/F2/F3 owner separately resolves identity, vocabulary and Warehouse Gold transaction. The same Healthcare repository carries both contracts, but neither component may access the other's runtime database.

## Verified current state

| Gate | Observed result | Authoritative evidence |
| --- | --- | --- |
| G4 Bronze/Silver request | 100 Patient / 5,918 Encounter / Q0 | [G5 real Pipeline + independent readback](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41636454542) |
| G5 Pipeline to persisted Silver | Completed + separate Spark readback PASS | Pipeline Job `7069b9d5-0617-442f-a976-833e56189997`; readback Job `3d16895a-d19d-45db-999b-2cad77983399` |
| Fabric OMOP Warehouse schema | Existing `dw-omop-5.4`: 39 empty official CDM 5.4 tables / 432 columns | [F0 real schema readback](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578) |
| F1 Identity Map + official Vocabulary | **NOT DONE** | [OMOP Foundation tasks](../../../../openspec/changes/fabric-omop-foundation/tasks.md) |
| F2 Candidate → Warehouse transaction | **NOT DONE** | Blocked on F1 |
| F3 Gold SQL readback, FK and replay | **NOT DONE** | Blocked on F2 |

## Machine-readable interface

- [Shared handoff contract v1](../../../../shared-data-engine/contracts/fabric-fhir-omop-handoff-v1.json) — producer, consumer physical target IDs, raw SHA of existing Canonical v1 contracts, all required Patient/Encounter columns, snapshot path and Approval fence, stable identity and Concept release obligations.
- [Pure structural validator](../../../../shared-data-engine/src/healthcare_data_engine/models/fabric_omop_handoff.py) — no Spark, Blob, SQL, network, ID allocation or data writes.
- [Fail-closed contract tests](../../../../shared-data-engine/tests/test_fabric_omop_handoff.py) and [no-cloud CI](../../../../.github/workflows/fabric-fhir-omop-handoff-offline.yml).
- [OpenSpec handoff change](../../../../openspec/changes/fabric-fhir-omop-handoff-v1/design.md), [G5 existing Candidate spec](../../../../openspec/changes/fabric-g5-approved-silver-omop-candidate/design.md), [independent OMOP Foundation spec](../../../../openspec/changes/fabric-omop-foundation/design.md).

### Contract boundary

FHIR's producer hands over a **batch envelope**, not direct SQL rows:

```text
Producer Fabric Lakehouse (physical GUID pinned)
  G4 patient Delta + encounter Delta + one SILVER_APPROVED row
    exact request + delivery Manifest SHA + source_batch_id + processing_version
    exact original canonical Patient/Encounter SHA, P/E/Q and publication ID
                           |
                           v
                     Envelope v1
         structural check  !=  physical Delta approval
                           |
          independent Silver physical Delta readback
                           |
                           v
Consumer Fabric OMOP F1 adapter (Warehouse-owned)
  scoped patient/encounter IDs + approved Concept/Vocabulary release
                           |
                           v
            Candidate-only Delta output (G5)
                           |
                           v
     F2 Warehouse single fenced Gold transaction + ledger
                           |
                           v
  F3 independent SQL readback / FK / DQ / replay SKIP
```

Patient key is **(hospital_id, feed_id, raw_source_system, source_record_id)**; Encounter key similarly includes `source_encounter_id`. Canonical `source_system` is already namespaced as `raw_source_system:hospital_id:feed_id`, but a global OMOP `person_id` is provided only by Fabric F1. No Local PostgreSQL ID lookup and no hash/row number as final OMOP IDs. A same `source_record_id` at two hospitals is NOT the same Patient.

The Warehouse owns `visit_occurrence_id`. The existing Candidate mapper currently accepts an injected, narrower `source_system, source_person_id, person_id` lookup; it MUST NOT receive a feed-unscoped lookup. The F1 integration adapter is **blocked pending the real F1 table definition**; do not infer schema or prematurely rename the F1 Agent's columns. Its proposed read-only projection must include explicit namespace, unique source keys, globally unique Warehouse-assigned IDs, one target per source identity, and a versioned immutable map snapshot.

Vocabulary mapping profile and actual official Concept rows must match the same reviewed release. Mapping version, original profile SHA and Vocabulary release metadata are mandatory F2 provenance. Unknown Concept, invalid Concept, 0/default fallbacks without review, source-to-Concept mismatch or an unsupported encounter class => HOLD.

The actual OHDSI 5.4 `cdm.person.person_source_value` and Visit source value columns are `varchar(50)` in the existing Warehouse DDL, so ETL must validate lengths before writing; no silent truncation, no implicit SQL cast assumptions. The canonical source tables retain all original columns but do not supply `visit_occurrence_id`; source E5918 does NOT guarantee E5918 committed Gold Visit rows.

### Validating a handoff envelope

In the future runner, load the contract bytes from a **reviewed immutable Git commit**, independently pin its SHA256 and invoke:
```python
from healthcare_data_engine.models.fabric_omop_handoff import (
    load_handoff_contract, validate_handoff_envelope,
)
contract = load_handoff_contract(reviewed_git_bytes, expected_git_sha256)
outcome = validate_handoff_envelope(contract, handoff_metadata)
assert outcome == "STRUCTURAL_PASS_PHYSICAL_READBACK_REQUIRED"
# STILL REQUIRED: physical Delta Patient/Encounter/Approval readback.
# STILL REQUIRED: Fabric F1 ID Map/Vocabulary validation and F2 Gold gate.
```

This check does **not** query any data. No one may report an actual source approval, Candidate, Gold Commit or replay PASS based on this validation alone. Reference G4 P100/E5918 synthetic batch is illustrative of an accepted physical source but the validator makes no live presence claim.

## Acceptance and handoff to the OMOP Agent

1. F1 Agent publishes a real `etl` scoped Identity Map contract (keys, `person_id` type, allocation/reuse, cross-hospital collision rules, concurrency and snapshot version); separately publishes official Vocabulary release, Concept validity and mapping-profile version.
2. FHIR integration Agent reviews those REAL interfaces, updates existing pure Candidate mapper without runtime dependency on Local DP/PG, validates P100/E5918 source plus cross-hospital/negative fixtures, builds and pins new Wheel. No write until new Fabric Environment Published/Readback PASS.
3. F2/F3 Gold Writer Agent owns Warehouse transaction, ledger/rollback/unknown-ACK semantics, independent SQL readback and replay; expected Gold counts come from actual mapping/DQ, not an assumed 1:1 conversion.
4. Both parties explicitly agree a **new** runnable authorization; no G5 read-only Pipeline gate grants Gold writes.

**Durable decision**: Part 1 is source/contract only. F1 readiness is an external dependency, not a missing parameter to fill with mock IDs. See [handoff OpenSpec tasks](../../../../openspec/changes/fabric-fhir-omop-handoff-v1/tasks.md).
