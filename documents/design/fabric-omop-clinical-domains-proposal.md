# Fabric OMOP 5.4 Clinical Domain Expansion — Approved Design Baseline v1.0

**Approved by project owner:** 2026-11-22 (D1–D8). **Branch:** `design/fabric-omop-clinical-domains-20261122`. **Status:** Design baseline APPROVED; implementation NOT yet completed; no merge to main authorized. **MLOps design remains on its separate branch.**

## 1. Purpose and actual baseline

Expand the proven FHIR/HL7 → Canonical Silver → Shared Data Engine → OMOP Candidate → Fabric Warehouse Gold pipeline beyond PERSON and VISIT_OCCURRENCE. Existing Person/Visit Fabric physical readback and same-batch replay are baseline evidence for **insert and replay only**, not evidence of Update, Delete, mixed batches or new clinical domains. Use controlled synthetic FHIR/HL7 fixtures; never treat synthetic results as clinical validation. Existing OMOP DDL and Vocabulary ingestion do not imply complete clinical ETL.

**Definition of done for each business table:** Insert, Update, Mixed Upsert, Delete/Retraction (as applicable), Idempotent Replay, out-of-order protection, partial-failure recovery, DQ/FK verification and independent physical readback. Any unsupported source event must be explicitly classified rather than silently accepted.

## 2. Approved decisions D1–D8

- **D1 — Scope:** First make PERSON and VISIT_OCCURRENCE support the complete change lifecycle, then implement CONDITION_OCCURRENCE, MEASUREMENT, DRUG_EXPOSURE, PROCEDURE_OCCURRENCE, OBSERVATION. Do not build daily ETL for all 39 CDM DDL tables. Vocabulary is a separately versioned foundation, not a daily clinical feed.
- **D2 — Operations:** Insert, Update, Mixed Upsert, Delete/Retraction, Replay, out-of-order delivery and partial-failure recovery are required acceptance scenarios. **Implementation decomposition remains a design detail under discussion**; see §5. Do not mark D2 completed merely because the scope was approved.
- **D3 — Updates/history:** Maintain stable OMOP IDs for the same business entity. Gold represents current valid state; independent ETL audit/provenance records source versions, change decisions and fingerprints. Do not append duplicate Gold rows for corrections.
- **D4 — Delete/retraction:** Separate source deletion, clinical cancellation/correction and governance/privacy erasure. Keep OMOP 5.4 schema standard (no ad hoc `is_deleted` columns); maintain ETL tombstones to prevent deleted facts reappearing on replay. Patient/Visit deletion requires dependency analysis; privacy erasure follows its own controlled policy, including audit retention limits.
- **D5 — Sources:** FHIR Condition, Observation, Procedure and medication resources with explicit semantic distinction. Existing HL7 ADT A01/A03 remain baseline; expand A08/A11/A12/A13 for relevant patient/visit changes. A23 and ORU or other clinical messages require explicitly scoped adapters, fixtures and business rules; do not derive diagnoses or laboratory results from ADT alone.
- **D6 — Portability:** Canonical and Shared Engine must be runnable outside Fabric. Prioritize Fabric Writer physical verification; keep local PostgreSQL Writer interface compatible and perform at least one representative local end-to-end verification. Fabric Notebook, OneLake and Warehouse dependencies must stay in adapters/execution/writer layers.
- **D7 — Cadence:** Clinical facts run daily incremental batches, with manual replay/backfill. Vocabulary updates on version change, not every batch. Observation Period, Era and other dependent tables are recomputed when their inputs change, using appropriate incremental or batch policy.
- **D8 — Evidence/branches:** Physical independent readback, key stability, versions, mixed operations, delete, replay, recovery and conflicts are mandatory evidence. Work only in clinical design branch pending implementation authorization; **do not merge main** without explicit approval. Keep `design/fabric-mlops-portable-20261122` independent and unchanged.

## 3. Canonical typed business contracts

Shared envelope (exact field names may evolve through contract tests): `source_system`, `source_resource_type`, `source_resource_id`, `source_version`, `patient_source_id`, `encounter_source_id`, `effective_datetime`, `ingestion_batch_id`, `canonical_schema_version`, `source_event_time`, `source_operation`, `source_provenance`, `content_fingerprint`.

Typed contracts must remain separate for Condition, Measurement, Drug, Procedure and Observation. Canonical preserves raw source code/system, clinical status, provenance, values and units; Shared Engine resolves OMOP concepts, target domains, stable identities, temporal semantics, person/visit FKs, DQ and change decisions. No per-source or per-target duplicate Mapper. Multiple FHIR Observation components require stable component-level event identities. Distinguish medication order, administration, statement and actual exposure; distinguish ordered from performed procedures. Never silently convert unmapped facts into generic OBSERVATION.

**Source operation is an intent, not a SQL verb.** FHIR resource DELETE differs from FHIR clinical status correction; HL7 A11 cancels admission, A13 cancels discharge, and neither necessarily deletes Person/Visit. HL7 MSH message ID supports transport deduplication, not business identity. No inferred delete from an absent row in an incremental batch.

## 4. Change semantics and safety invariants

1. **Business key:** source-system scoped stable event/entity key, independent of batch, file order and version. Use Identity Map to preserve target OMOP ID across updates. Define domain-specific subevent keys.
2. **Version ordering:** prefer reliable source version/sequence; compare effective and ingestion timestamps only under explicit source policy. Older arrivals cannot overwrite newer state. Unresolvable conflicts are quarantined with evidence.
3. **Fingerprint:** compare normalized meaningful fields to distinguish UPDATE from NO-OP; repeated identical content must not cause churn.
4. **Tombstone:** retain sufficient scoped identity/version evidence to prevent stale re-inserts after DELETE/RETRACT; do not retain erased sensitive payload contrary to governance requirements.
5. **Dependencies:** clinical fact deletion may invalidate derived Era/Observation Period outputs; Visit/Person removal requires referential impact analysis and a controlled operation plan.
6. **Commit:** candidate validation → staging → transactional or recoverably idempotent target-specific apply → ledger/audit reconciliation → independent readback. Writer implementations must document actual Fabric Warehouse and PostgreSQL transaction semantics; do not assume identical SQL MERGE guarantees.
7. **Mixed batch:** classify all records using one shared engine; apply inserts, updates, deletes and no-ops consistently, including duplicate events, conflicting versions and rollback/retry. A mixed batch is a composition scenario, **not** a second clinical mapper.

## 5. D2 implementation approach — recommended, pending final technical sign-off

**Recommendation:** shared **Change Planner** with typed actions `INSERT`, `UPDATE`, `DELETE/RETRACT`, `NO_OP`, `CONFLICT`; target-specific **Change Executor/Writer**. Expose reusable action handlers, but let the Writer apply grouped operations in a safe batch/transaction protocol. Avoid both (a) separate duplicate domain logic for Insert/Update/Delete and (b) a naive row-by-row Mixed Upsert orchestrator with no atomicity or recovery.

**Incremental delivery gates (do not split architecture):**
- **Gate A:** PERSON/VISIT stable business identity, INSERT/UPDATE/NO_OP, corrected version and replay, independent readback.
- **Gate B:** Mixed batches using the same planner/handlers; same-key multiple changes, out-of-order arrivals, conflicting updates, partial failure and retry.
- **Gate C:** DELETE/RETRACT and tombstone, dependency checks, A11/A13 cancellation semantics, stale replay suppression; separately define governance erasure.
- **Gate D:** Reuse the same planner and writer interface across five clinical domains, with full CRUD+Replay acceptance per table and cross-domain dependencies.

**Open implementation detail requiring review:** whether to use a single batched planner/executor API with action-specific handlers (recommended) versus independent externally callable Insert/Update/Delete services. The D2 business acceptance scope itself is approved and does not depend on this choice. No code implementation of this detail is authorized merely by this document.

## 6. Domain-specific scope and source coverage

| Target OMOP | Initial source | Key acceptance concern |
| --- | --- | --- |
| PERSON | FHIR Patient; HL7 ADT patient segments | stable identity, demographics updates, controlled delete |
| VISIT_OCCURRENCE | FHIR Encounter; HL7 A01/A03 then A11/A13 | stable visit ID, admit/discharge correction/cancellation |
| CONDITION_OCCURRENCE | FHIR Condition | condition status, coding, corrected/retracted diagnosis |
| MEASUREMENT | FHIR Observation (laboratory/vitals) | numeric/coded value, unit concept, component identity |
| DRUG_EXPOSURE | FHIR Medication* with validated exposure semantics | order vs administration vs actual exposure |
| PROCEDURE_OCCURRENCE | FHIR Procedure | performed vs ordered, date and concept |
| OBSERVATION | selected FHIR Observation | domain routing, avoid catch-all dumping |

HL7 ADT A08/A12 can be added with source-specific fixtures and canonical semantics; A23 deletion of patient records and ORU^R01/OBX results are explicitly assessed for later source coverage, not assumed already supported. Additional DEATH, DEVICE_EXPOSURE, SPECIMEN and NOTE depend on actual source data and a separate scope decision.

## 7. Vocabulary, derived tables and cadence

OMOP Vocabulary tables (nine existing imported files) are initialized and updated on vocabulary release/version change, with validation and lineage. No daily bulk reimport for routine clinical batches. Derived OBSERVATION_PERIOD, CONDITION_ERA, DRUG_ERA and related tables are downstream calculations, not independent FHIR/HL7 sync feeds. Other dimensions and metadata are maintained only when justified by their dependencies. A source-code mapping policy must specify when concept_id=0 is permitted with explicit reason versus quarantined; do not invent a concept.

## 8. Verification and operational evidence

Per table and operation: 0/1/N, Insert, Update, mixed new+changed+unchanged, explicit delete/cancel, duplicate transport event, same-batch replay, cross-batch replay, stale older update after newer update, stale reinsert after tombstone, version conflict, partial failure/recovery, FK and concept DQ. Validate **both row counts and field values**, stable target IDs, no orphan rows, correct audit/ledger state and absence of unintended changes. Include >10k fixture verification via chunked independent SQL readback; remove legacy 100/5918 and 10k general-path caps only after safe replacement, without rerunning one-shot historical workflows.

Evidence per gate: code SHA, source fixture and manifest, shared engine version, Notebook/workflow run, Warehouse physical SQL readback and selected values, audit/ledger/tombstone, replay results, negative cases and limitations. At least one representative end-to-end run on local Spark/SeaweedFS/PostgreSQL must demonstrate Fabric-independent business code; local ATLAS visibility is **not** implied by Fabric Gold.

## 9. Execution boundaries and cost

Fabric trial data are disposable synthetic data; Git remains source of truth for code/contracts/evidence. Avoid production PHI. No Fabric capacity pause/resume automation until a separate paid capacity decision. No workflow execution, deployment, main merge, or MLOps branch changes authorized by this design approval. Implementation should be separately initiated after D2 decomposition is finalized.

## 10. Remaining engineering choices (not reopening D1–D8)

- Exact Change Planner / Executor public API and transaction boundaries for mixed batches.
- Domain-by-domain concept_id=0 / quarantine policy and clinical source fixture coverage.
- Source-specific event ordering, FHIR deletion visibility, HL7 cancellation and A23 semantics.
- First representative local acceptance fixture and cross-target equivalence criteria.

**Approval record:** Owner explicitly approved D1–D8 on 2026-11-22; raised the D2 decomposition question for further discussion. This document captures that distinction without treating unimplemented features as complete.
