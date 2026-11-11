# Tasks — Unified FHIR + HL7 G5 technical admission (coordinating OpenSpec)

> This change is DESIGN/COORDINATION ONLY (skip_specs: true). Checked P0 items denote **verified existing evidence**, not a new runtime acceptance. Implementation and cloud authorization remain under their owning OpenSpec Changes and PRs. Never mark a task complete from an offline or source-only signal alone.

## P0 — Current source/policy baseline, no changes to cloud

- [x] 0.1 Verify both Main branches, active PRs, Shared 0.1.13 source, Native Candidate and Gold technical code paths and source-specific adapters on 2026-11-11. Starting SHAs are in design.md; re-check every session.
- [x] 0.2 Confirm business decision: remove mandatory TWO HUMAN Clinical/License signatures for the synthetic-data G5; retain actual vocabulary use rights, semantic mapping validity, F1/F2, Batch/StageScope, DQ, nonce and physical write/readback.
- [x] 0.3 Confirm existing merged code MUST be reused: Shared v3 and target-concept-v2, FHIR #892/#895/#897, Native Silver #837, HL7 Native #847, Self-Runner HL7 Controller #625, technical-only provider #732 and existing GoldBatch/Candidate technical branches. Do not build replacements.
- [ ] 0.4 Before coding, reconcile current deployed Fabric Notebook/Published Wheel, running Actions, pending F1 #748/#753 and exclusive source ownership. Do not assume current Main has been synced to Fabric.

## P1 — Single F1 technical governance and evidence (Self-Runner)

- [x] 1.1 **SOURCE-ONLY CLOSED:** obsolete mandatory human Clinical/License review-signature blockers removed without removing REAL source, legal-rights or Concept safeguards. Self-Runner [PR #748](https://github.com/JohnZhang-DataForge/Self-Runner/pull/748) merged `4458407766db688e662d37aa7ae85c9deef9ed19`; full offline F1 provenance [Run #43082294111](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43082294111) and Deep DQ [Run #43082294181](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43082294181) SUCCESS on the exact tested PR source. No Fabric/Azure mutation, no true 9/9 audit or license release.
- [x] 1.2 **SOURCE-ONLY CLOSED:** nine pinned Athena Blob conditional GET/full-bytes SHA/ETag double-HEAD verifier and per-file actual verification UTC event metadata, negative tests and Main one-shot marker integrated, without any real nine-GET execution. Self-Runner [PR #753](https://github.com/JohnZhang-DataForge/Self-Runner/pull/753) merged `f3e9aa670178707b3256793d9f23313d146867c0`; final PR [Deep DQ Run #43082823777](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/43082823777) SUCCESS. GitHub-hosted runner had failed before assignment; only same-repository PR source-only tests were routed to the existing ephemeral ARC runner `dw-runner-set`; cloud OIDC remains separate. **F1 physical nine-file SHA and Warehouse audit SQL remain NOT RUN / last-observed 0/9.**
- [ ] 1.3 Explicit separate protected Main one-shot executes the nine exact pinned GET/HEAD reads; independently validate each ETag/version/size/full SHA, no data-raw artifacts or SQL write, no repeated GET when existing exact proof is valid.
- [ ] 1.4 Independently establish authentic original release transaction + rights for in-scope vocabulary and resolve blank versions; no fake Clinical/License reviewer, no invented release IDs. Restricted rights missing => exclude or HOLD.
- [ ] 1.5 Separately authorized single SQL audit transaction and independent F1 nine-row readback, with original provenance and verified UTC event evidence; do not treat raw full-SHA receipt as permission to INSERT.

## P2 — ONE Shared evidence / Stage Controller (Cross-source owner)

- [ ] 2.1 Freeze ONE source-format-neutral expected-StageScope → TrustedTechnicalScope v3 → target-concept-v2 / F2 typed technical evidence contract; preserve exact legacy v1/v2 parsing and replay.
- [ ] 2.2 Wire protected Self-Runner F1/F2/Concept provider to the actual Stage owner with independently pinned source BatchContext, physical Silver Approval, Mapping SHA, F1/rights, fresh F2 logical fingerprint and technical_evidence_sha256. No new Mapper/SQL reader/evidence provider.
- [ ] 2.3 Authenticate service/machine provenance with fixed actual issuer/public key and durable atomic replay nonce; v3 transport remains PROVENANCE_ONLY, stage-specific protected release must be independent, not Notebook/Pipeline Boolean.
- [ ] 2.4 Reuse Native Candidate + Gold technical branches already present. Close G5 2.6 only when trusted call sites, dynamic scope, v2 technical Approval-LAST, cross-version replay HOLD and protected single-writer/Gold release tests really pass; do not reimplement Writers.
- [ ] 2.5 Negative CI for both formats: forged signs/flags or token, untrusted callbacks, source SHA/F2 drift, missing F1/rights, illegal Concept, unknown source, same-batch collision, stage confusion, nonce/replay, unknown ACK and no writes under HALT.

## P3 — Per-source thin integration, independently owned

- [ ] 3.1 FHIR owner: bind real dynamic FHIR approved Silver and new Batch/StageScope to the **same** trusted technical contract; maintain frozen historical 0.1.7 G4 P100/E5918/Q0 and approved processing. Source tests #892/#895/#897 already PASS, not real live release.
- [ ] 3.2 HL7 owner: preserve Parser → local Delta → dbt → canonical Shared DQ; use already merged Silver helper #837, new16 allowlist #847 and controller #625, then prove real Native transfer/Approval-last/readback/replay. No HL7 → FHIR; no second Silver Writer.
- [ ] 3.3 Both sources invoke ONE StageScope/technical evidence Controller + ONE Candidate/Gold Writer interface; run shared contract test matrix and independently scoped source tests. Preserve separate source-specific errors and provenance; no duplicate gate.

## P4 — Controlled runtime and physical business acceptance

- [ ] 4.1 Reproducible Shared 0.1.13 Wheel is CI-built and Python 3.11/3.13 installed compatibility PASS (#897); still require isolated Fabric Environment publish, exact hash/definition double readback and actual runtime import. Do NOT replace current 0.1.7 in place.
- [ ] 4.2 FHIR actual dynamic v3 approved Silver readback + source-specific replay in controlled Fabric runtime, record actual Job UUID/bytes/rows/SHA; no inferred PASS from offline spark.
- [ ] 4.3 HL7 new16 physical approved Silver delivery/Approval-last/readback/replay with exact real Blob provenance, transport cleanup and FHIR historical isolation; reconcile unknown ACK by GET, no blind retry.
- [ ] 4.4 After F1 9/9 and real F2, independently issue trusted Candidate Stage release, actual create-only Delta Person/Visit, complete physical readback and technical Approval-last v2; same Batch Replay SKIP and corrupted/conflicting Approval HOLD. No Gold declaration.
- [ ] 4.5 Separately gated Gold single-writer transaction: fresh F2/identity/rights, exact Candidate Approval, commit of identity + Person/Visit + ledger/audit, independent SQL readback and rollback/conflict evidence. Do not invent successful physical results.
- [ ] 4.6 Confirm both formats E2E in source-specific tests while sharing Controller, Mapper, Candidate/Gold; exact Main SHAs, CI, Fabric Jobs, artifact references and cost bounds; update owning OpenSpecs.

## P5 — Exit criteria

- [ ] 5.1 Remove mandatory two-human-signoff from all **active** FHIR and HL7 technical admission branches; retain legacy versioned historical compatibility with strict isolation, no fake approvals.
- [ ] 5.2 Prove same Stage/evidence/Writer contracts with two different real source formats and independent physical readback, plus F1/rights/F2/cost/replay fences. No source-specific second Mapper/Writer/Controller.
- [ ] 5.3 All intended PRs have real applicable CI success and are merged against latest Main; production Wheel and actual Fabric state independently confirmed. Document remaining blockers, never mark Gold COMPLETED from Candidate/Silver status.
