# Design — One FHIR/HL7 G5 Technical Admission, Two Source Adapters

## 1. As-verified baseline (2026-11-11 ET)

- Healthcare Main at design start: c1a53765b0c7bbde1d9b31eeff79a11f8f2d465d. Self-Runner Main: b37e6b5a73939f73058f55e0f9af7ae0cb03d31a. These SHAs are **snapshots**, not permanent latest-state pins. Before each PR/release: re-check Main, active branches/Actions, merged file diffs and concurrent Atlas/HL7/Fabric work.
- Shared Engine 0.1.13 source supports source-neutral FHIR_R4 / HL7_V2 TrustedTechnicalScope and fabric-g5-technical-evidence-transport-v3; target-concept-v2 no longer has mandatory Clinical/License SHA. Real isolated installed-wheel Python 3.11 and 3.13 Native FHIR v3 offline CI passed: Healthcare #897 / Run #43019312496. **No published 0.1.13 Environment or live v3 Fabric runtime evidence**.
- Healthcare #837 merged ONE guarded internal _write_verified_canonical_silver physical primitive for Patient, Encounter, independent readback and Approval-LAST. Healthcare #847 merged bounded HL7 new16 source admission; Self-Runner #625 merged prior one-shot HL7 controller. These are code contributions; do not claim all newer real HL7 Fabric Silver jobs have passed from the merge alone.
- HL7 source adapter owns OIE Raw -> Python parser -> local physical Delta -> dbt -> existing Canonical/Shared DQ, provenance and candidate transport; local physical readback/negative tests have passed. Final new16 official Fabric Silver WRITE/READBACK/replay remains unchecked in existing HL7 OpenSpec. **Do not** run HL7 through a FHIR mapper.
- FHIR #892 / #895 merged source-only dynamic Batch/StageScope plan and independent recompute/readback contract. Existing earlier G4 P100/E5918/Q0 physical Silver remains frozen; the new v3 dynamic test did not launch Fabric.
- Native plan_and_write_g5_candidate_delta / execute_g5_person_visit_business already contain technical_evidence_sha256 + trusted_technical_release_gate; GoldBatch / gold_transaction already accept technical evidence with a separate release_gate and single_writer_fence. Legacy reviewer parameters remain backward-compatibility alternatives, not current policy. **Implementation of a protected live Stage controller and real released batches is missing**, so G5 task 2.6 stays open until integrated acceptance.
- F1 **UPDATED actual 2026-11-11 run (supersedes prior code-only state)**: #748 / #753 merged F1 no-human-quorum and the source-only nine full SHA reader; #767 isolated the GET-only marker on existing ephemeral ARC; exact Main commit `a24cc2505f16e128a5ae84e26f3ef4e136c59d58` from #768 launched [real Run #43093876076](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43093876076), Job `130777725637`, and produced **FULL_BYTES_SHA256 9/9, 1,304,555,334 bytes** with ETag double-HEAD/UTC event integrity and no raw CSV artifacts. [Artifact #13890392224](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43093876076/artifacts/13890392224) was independently downloaded and metadata-checked. Private Self-Runner #770 merged `700c9171eb99af58a064fba39be8854b12a35f4e` preserving the real source-only receipt and regression proving no SQL insert plan from nine SHA events alone. The original Athena acquisition/release transaction, restricted code-set usage rights, missing version reconciliation and actual Warehouse SQL source audit 9/9 are **NOT VERIFIED**; last measured SQL audit still 0/9, not re-queried in this Run. No Clinical/License human signatures are required as a quorum, but true rights and mapping validity remain mandatory.
- **Task interpretation**: G5 2.6 is not an instruction to rewrite the existing technical Candidate/Gold branches; it stays unchecked for authenticated live Controller wiring, F1/F2 evidence, version-isolated runtime and physical release/readback. This coordinating OpenSpec does not supersede the source owners' executable task ledgers.

## P2.1 SOURCE-ONLY bridge accepted (2026-11-11 ET, after initial plan)

Self-Runner [PR #762](https://github.com/JohnZhang-DataForge/Self-Runner/pull/762) merged Main `18dd107fd035ca384ec7703bbe3ab1bb7efadb9c` after [Run #43085053262](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43085053262) SUCCESS. A single pure `fabric_g5_v3_source_only_stage_binding.preview_v3_scope_only` consumes existing typed NewBatchReviewInputs (already parsed BatchContext/StageScope/Shared Mapper profile) and existing technical F1/F2 witness report, strictly checks FHIR/HL7 batch, Manifest, Mapping SHA, StageScope version, F1/F2 and technical witness digest, and verifies the Shared v3 `TrustedTechnicalScope` field/schema **only in local memory**. It returns a non-authoritative digest with `G5_V3_EXPECTED_SCOPE_SOURCE_ONLY_HOLD_NO_STAGE_RELEASE`, no trusted scope object, release callback, signed transport, Controller or Writer capability. Synthetic positive and negative tests for both formats, GOLD-vs-CANDIDATE, fake dual signer, false rights/Silver proof, missing F1, F2 drift and no network/write calls passed. Uses exact reviewed Healthcare Shared source SHA `c02da9e1` for offline CI and existing ephemeral ARC same-repository PR runner. This is not physically authenticated Silver, real F1/rights, actual signed transport, durable nonce or release. **P2.2–P2.5 and all production gates remain open**.

## P2.2.1 read-only controller composition (2026-11-11 ET)

Self-Runner [PR #763](https://github.com/JohnZhang-DataForge/Self-Runner/pull/763) merged Main `b3174e1309c8032143f1091160c6ee8509c468a6` after [offline CI #43090128320](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43090128320) SUCCESS. The new `fabric_g5_p2_trusted_source_readonly_controller.verify_trusted_source_readonly_once(env)` composes existing code in the strict order: **Main first-attempt/OIDC context guard → fixed trusted-source bundle → existing real physical F1/F2 six-table/Concept SQL Provider → SOURCE-ONLY FHIR/HL7 Shared v3 scope parity**. No caller-provided SQL reader, arbitrary evidence dictionary, proof file, override key, stage grant, or Writer callback is accepted at the entrypoint. The tests use synthetic/mocked physical evidence, and verify the protected order, missing source, F1=0, drifted F2, scope confusion and forged release/rights/Silver claims fail closed.

This is a **source-only integration seam**, not a production trusted Controller: the protected technical-source fixture has not been independently commissioned; no actual new P2.2 F1/F2 Azure SQL call was made in this PR; there is no independent physical approved-Silver authentication, vocabulary usage-rights authorization, service signing key, durable nonce/Blob Claim, Native Stage release or Candidate/Gold Writer invocation. The controller's receipt always sets `source_silver_physically_verified=False`, `vocabulary_rights_verified=False`, `provider_service_signature_issued=False`, `durable_nonce_claimed=False`, `stage_release_authorized=False`, and both write/commit flags False. The real F1 nine-file source audit remains last-observed 0/9. **Full P2.2, P2.3 and P2.4 remain OPEN.**

## 2. Authoritative data / trust boundaries

Source-specific, **owned separately**:

- FHIR_R4: immutable Landing Manifest and raw objects -> Fabric Bronze -> canonical FHIR adapter -> approved Silver. Existing G4 request/time/processing fences and prior 0.1.7 runtime remain immutable.
- HL7_V2: OIE A01/A03 -> immutable Raw Blob and actual ACK -> strict HL7 parser -> local Delta/dbt -> canonical HL7 handoff -> approved Silver. Its BatchContext must come from **verified** request, source manifest and content, not caller claims; do not regenerate OIE messages or invent a conversion via FHIR.

Shared, **owned exactly once**:

- Canonical v1 Person/Encounter Contracts, source-scoped BatchContext, reconciliation/PK/FK/DQ/quarantine and the existing internal guarded Silver physical Writer. An Approved Silver envelope is a **physical Patient/Encounter/Approval-LAST readback**, not a status string, Spark completion or self-supplied SHA.
- The same Shared Engine target-concept-v2 mapping rules, per-code coverage and Concept validation, F2 IdentitySnapshot bridge, Candidate identity planner, source-neutral v3 TrustedTechnicalScope and service attestation transport. Review on semantic mapping is a data correctness decision, never a second mandatory person's signature. Unknown/unmapped/UNK or clinically unsupported values must remain rejected/quarantined; no concept 0 fallback.
- The **one protected Stage Controller** independently builds trusted, typed scope from physical source + approved Silver + F1 + F2 + Concepts; validates service issuer/signature, fixed audience, short TTL and durable atomic nonce claim. Signed transport proves authentic evidence exchange but is NOT itself Stage release.
- A separate, stage-specific release decision (scoped to CANDIDATE vs GOLD, request/batch/source, profile SHA, F1/F2 snapshot and writer fence) must be authenticated by the protected Controller, not by Notebook/Pipeline booleans or hashes. Silver-Approved != Candidate-Approved != Gold-Committed.
- Candidate uses existing lower-level Native Writer and its create-only Delta, independent full readback, v2 technical Approval-LAST + exact cross-version replay HOLD. Gold uses existing transaction Writer, fresh F2 single-writer transaction fence, actual Candidate approval and rights to use restricted code sets, commit/readback/audit/ledger. No alternate HL7 writer.

In words:

FHIR adapter ----> |
                   |--> Canonical v1 / approved Silver --> ONE G5 trusted Controller + Shared evidence --> SAME Candidate Writer --> SAME Gold Writer
HL7 Delta / dbt -> |

The physical Silver Writer is a shared *primitive*, not an automatically open endpoint. Both source adapters must separately authenticate their source/batch before calling it.

## 3. Technology gates replacing mandatory human quorum

1. **Immutable provenance**: original source bytes and Manifest SHA, object size/ETag/version, received events and independent source-specific source/BatchContext correctness.
2. **Canonical & approved Silver**: one set of DQ, PK/FK, nonempty, quarantine, source-specific validity, exact two-table persisted Delta and Approval-last independent readback; replay conflict HOLD.
3. **F1 vocabulary**: actual nine pinned Blob content full SHA plus authenticated original release / source transaction evidence, real audit.vocabulary_source_file 9/9 SQL and independent verification, verified valid standard target Concepts, restricted vocabulary rights. Source-only #753 metadata does NOT grant legal rights, SQL insert authority, or release.
4. **F2 identity**: six actual Warehouse datasets queried by independent connections, exact full rows and Shared logical snapshot fingerprint; provisional IDs do not become durable until Gold transaction.
5. **StageScope + evidence**: single target-concept-v2, technical_evidence_sha256 bound to immutable verified input, one v3 service provenance signature, independent expected TrustedTechnicalScope; nonce/claim and replay protections required. No fake Clinical/License signer or 'approved=True'.
6. **Protected release + physical readback**: Stage release authenticated independently, exclusive writer lease/Claim/CAS, no unsafe retries after unknown ACK; Candidate approval LAST; Gold atomic transaction and independent real target readback.

The user removed the requirement for two **people** to sign. They did not waive independent data evidence, applicable vocabulary licensing, clinical semantic correctness or protected service authentication.

## 4. Source-to-runtime plan; do not duplicate existing implementations

A. **F1 legacy policy / facts (as of real Run #43093876076)**: Nine full-source SHA/size/ETag and event UTC are now **physically VERIFIED 9/9 from existing immutable Azure Blob**; event receipts are stored in private Self-Runner #770. **Do not repeat the 1.30 GB GET without an explicit evidence drift reason.** This validates current Blob bytes only, NOT authenticated original Athena download transaction, licensing/rights, version/Concept decisions, or SQL `audit.vocabulary_source_file` rows. Keep P1.4/P1.5 OPEN until independently authentic source release/rights and separately controlled SQL audit write/readback. Never use Blob Last-Modified or the 2026-11-11 SHA verification timestamp as a fabricated original Athena acquisition date. Hold/exclude restricted vocabulary without legitimate use rights. No fake reviewer, approval, source transaction or SQL backfill.

B. **One Controller / Shared contract**: freeze schema version and stage/format matrix, build controller from the existing Self-Runner F1/F2 provider and Shared v3 validator. Require trusted independent pins for physical BatchContext, Silver Approval, F1/F2/Concept snapshot, signer identity and release policy; no second Mapper, SQL reader or verifier. Keep the present technical Candidate/Gold Writer branches, replace only missing trusted caller integration, provenance and dynamic batch/source handling. Guard legacy v1/v2 historical replay without secretly weakening their old exact pins.

C. **Per-source thin adapters**: FHIR source controller constructs exact FHIR v3 scope and independently proves dynamic Silver; HL7 source controller proves local Delta/dbt source, original OIE/Blob bytes, package transport and exact real Silver. They call the SAME shared contract, release Controller and Writer, with source_format-specific validators. Shared Native Notebook is single-owner: source agents must not concurrently modify it.

D. **Package and controlled live rollout**: build pinned reproducible 0.1.13 wheel and install into an **isolated or separately guarded** Fabric runtime. In-place replacement of Published 0.1.7 breaks historical G4 pins and is disallowed. GET-only verify Environment Published vs Staging wheel and actual Notebook Git definition; test both source formats against installed runtime before any eligible Candidate writes. Start Capacity only under bounded approved window; default run_mode HALT, write flags false, retry 0, no schedule.

E. **Real acceptance, independent by Stage**: first FHIR and HL7 live source-specific Silver source/replay/readback; then ONE shared Controller with F1/F2 evidence; then actual Candidate-only write/readback/Approval-last/same-batch Replay SKIP/unknown-ACK HOLD; finally Gold release single SQL transaction, rollback/commit proof and independent readback. Record exact SHA, Job Run, verified physical row counts, object paths and held failures. Never count source tests or cloud job SUCCESS as Gold COMMITTED.

## 5. Non-overlapping code ownership (parallel-session contract)

- **Integration owner, Healthcare**: shared-data-engine/**, Native nb_fhir_ingest.Notebook/**, Gold transaction Writer, shared G5 OpenSpec, unified negative tests. One person/session owns Notebook edits at a time.
- **Technical Controller and F1 owner, Self-Runner**: src/ci/fabric_p1_*, fabric_g5_technical_evidence_readonly, trusted provider/one-shot/OIDC, Source Audit, Stage Claim/Release and actual orchestrator. Coordinate F1 #748/#753 with separate open PRs.
- **FHIR owner**: FHIR-only source adapter / source-specific tests and documents; NO shared Controller, Gold, Shared Mapper or Notebook core edits until integration owner coordinates.
- **HL7 owner**: local-data-platform/spark/apps/hl7/**, azure-fabric/dbt/hl7-canonical/** and HL7-only tests/transport; NO shared Controller, Gold, Shared Mapper or Notebook core edits until coordinated.
- **ATLAS/LocalDP parallel work**: outside this admission change. No fabricated dataset or unrelated schema migrations.

## 6. Conflict and rollout rules

- Use this OpenSpec as the cross-source coordination map; the **existing owning OpenSpecs** remain the authoritative evidence and executable task ledgers:
  - fabric-g5-approved-silver-omop-candidate (Shared/Native Candidate);
  - implement-hl7-local-delta-dbt-canonical (HL7 source/Silver);
  - fabric-fhir-omop-unified-e2e (FHIR/Gold);
  - Self-Runner PR #748/#753 (F1 technical governance and physical-source evidence).
- Every implementation PR re-reads current Main and concurrent PRs; no blind branch rebases or duplicate Writer/Mapper. Documentation history describing 'human signoff required' is retained as **historical** and explicitly superseded by the 2026-11-10 business decision.
- CI for both formats must include technical happy-path only in SOURCE-ONLY harness, wrong Stage/format/tenant/batch SHA, F1 incomplete 0/9, missing vocabulary rights, wrong/expired Concept, F2 drift, fake human-signatures, replay nonce reuse, unknown ACK, untrusted callback, cross-version Approval, no-remote-write, and legacy G4 0.1.7 regression.
- No runtime mutation, Fabric Capacity launch, F1 SQL DML or Gold commit is authorized by this design. Each real release requires separate scoped controller, validated CI/PR/Main, physical proof and cost-aware execution boundary.
