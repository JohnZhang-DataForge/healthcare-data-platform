# Fabric OMOP 5.4 Clinical Domain Expansion — Design Proposal (DRAFT)

Status: **Discussion only — not approved for implementation or merge**. Date: 2026-11-22. Base: main.

## 1. Business purpose and current baseline
Extend the verified FHIR/HL7 → Canonical Silver → Shared Data Engine → OMOP Candidate → Fabric Warehouse Gold path beyond PERSON and VISIT_OCCURRENCE, using synthetic Synthea and controlled HL7 fixtures. Existing Fabric Gold Person/Visit physical readback and replay are baseline evidence, not proof that other domains are supported. Preserve independent local PostgreSQL writer and ATLAS consumer. No new per-source or per-target mapper.

## 2. Scope and domain priority
1. CONDITION_OCCURRENCE: diagnoses, vocabulary normalization, visit/person FK.
2. DRUG_EXPOSURE: medication events, ingredients vs clinical drug concepts, dates and quantities.
3. PROCEDURE_OCCURRENCE: performed procedures; distinguish ordered vs performed.
4. MEASUREMENT: numeric and categorical lab values, units, reference range and abnormality.
5. OBSERVATION: non-measurement observations; no dumping unmatched clinical events here.
Dependent tables to assess: OBSERVATION_PERIOD, DEATH, VISIT_DETAIL, DEVICE_EXPOSURE, SPECIMEN, NOTE, FACT_RELATIONSHIP. Do not claim these are already implemented. OMOP vocabulary and CDM schema are pre-existing foundation; verify physical target DDL and concept validity for each new table.

## 3. Input contracts
FHIR resources: Condition, MedicationRequest/MedicationAdministration/MedicationStatement (separate event semantics), Procedure, Observation. HL7 v2: current ADT A01/A03 supports identity and encounters only; clinical domains require new, explicitly scoped message types such as ORU/ORM/RDE or an approved synthetic adapter. Never fabricate diagnosis/drug/lab fields from ADT. CSV remains adapter-agnostic architecture, not an additional parallel mapper. Record source system, event identifier, provenance, effective time, batch manifest and source schema version.

## 4. Unified architecture
Source adapter → canonical typed clinical event (Silver) → shared vocabulary/identity/FK/DQ/replay engine → domain-specific candidate tables → Fabric Warehouse writer → independent SQL physical readback. Local writer consumes the same canonical and shared mappings. Candidate staging is distinct from published Gold. Shared engine owns OMOP concept resolution, person/visit identity, stable domain primary keys, data quality and idempotency; writers own target-specific physical persistence only.

## 5. Per-table contract
Each table needs: canonical event schema and nullable/required rules; OMOP 5.4 column map; concept mapping and explicit concept_id=0 policy; unit conversion; person_id and visit_occurrence_id FK checks; stable deterministic business key; duplicate/correction/late-arrival policy; target DDL and SQL writer; audit/ledger; replay; independent SQL verification; negative tests. Reject or quarantine unsupported events; never silently insert dummy clinical concepts. Drug exposure must distinguish orders from administration. Measurements must retain value_as_number, value_as_concept_id and unit_concept_id semantics. Condition status and temporal semantics must be defined before mapping.

## 6. Incremental and replay design
Batch key = source + source_batch_id + manifest hash + mapper version. Event identity independent of physical file order. Commit protocol: validate candidate → stage → merge/upsert with deterministic IDs → commit ledger → independent readback; recover from partial failures by reconciling ledger and target. Preserve immutable source provenance, allow corrected versions with explicit supersession policy. Remove historical frozen 100/5918 counts and 10k verifier limitation from the *general* path only after designing scalable chunked physical verification; retain old one-shot guardrails and do not rerun historical commits. Explicitly separate byte limits from row limits.

## 7. DQ and acceptance gates
- Required fields, type/timezone and semantic checks, concept domain and vocabulary membership, person/visit FK integrity.
- No duplicate stable event keys, no orphan rows, no cross-source identity collision, no unexpected destructive updates.
- Per-table 0/1/N cases, nulls, malformed concepts, late arrivals, corrections, replay, partial failure and >10k rows through chunking.
- FHIR first for domains supported by FHIR fixture; HL7 clinical messages only when their parser/dbt canonical route is explicitly specified.
- Warehouse independent SQL reads: row counts, key sets, selected clinical fields, FK counts, ledger, audit and second-run no-op.
- ATLAS local visibility is NOT automatically implied by Fabric Gold success.

## 8. Delivery sequence and evidence
A. Inventory existing DDL, Shared Engine candidates, FHIR fixture, local OMOP mappings, Fabric scripts and one-shot workflows.
B. Approve canonical clinical-event contracts, vocabulary policy, stable IDs and writer transaction strategy.
C. Implement Condition end-to-end and review real physical readback.
D. Add Drug and Procedure independently with domain-specific acceptance.
E. Add Measurement and Observation with units and coded-value checks.
F. Multi-domain same-patient joins, backfill, corrections, idempotent replay, larger-batch verification.
For each domain record commit SHA, synthetic source manifest, notebook run, Warehouse readback query/results, failure-path evidence, and known unsupported mappings.

## 9. Boundaries and cost
Trial Fabric is disposable compute and test data; Git is source of truth for code, contracts, DDL and evidence. No requirement to preserve all synthetic rows when trial expires. Design for external daily sync controller after paid capacity decision; no capacity automation in this scope. Do not add production PHI or assume clinical correctness from synthetics.

## 10. Decisions for review
D1: Is priority Condition → Drug → Procedure → Measurement → Observation accepted, or should Measurement precede Drug for the MLOps use case?
D2: Are FHIR Condition/Procedure/Observation and medication resources available in current Synthea fixtures, or should a new fixture be generated?
D3: Should clinical HL7 expansion start with ORU results, or remain out of first milestone?
D4: Policy for unmapped concept_id=0: quarantine vs accepted with explicit reason, by domain?
D5: Gold correction strategy: MERGE/update vs append+supersession, consistent with Warehouse semantics?
D6: Define first domain acceptance dataset size and evidence threshold; avoid artificial fixed production batch sizes.

**No code, deployment, workflow execution, PR merge or production data changes authorized by this document.**
