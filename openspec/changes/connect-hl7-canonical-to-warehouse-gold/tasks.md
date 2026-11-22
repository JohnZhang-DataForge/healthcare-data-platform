# HL7 Canonical Silver → existing Warehouse Gold

- [x] 1.1 Implement the HL7 source-bound Silver readback and Candidate/Gold handoff using the existing 0.1.17 Shared Engine and Warehouse writer; no new Mapper or SQL writer.
- [x] 1.2 Add synthetic DQ/source/FK/approval/replay/offline tests and a self-hosted GitHub Actions workflow.
- [x] 1.3 Validate required PR CI, naming gates, and merge the business path into `Self-Runner/main` and `healthcare-data-platform/main`. Real final run 45047792510.
- [ ] 1.4 Resolve Fabric Git Environment identity safely without overwriting local Workspace resources, and confirm real Notebook and published Wheel readiness.
- [x] 1.5 Run HL7 source → real Canonical Silver → shared Candidate → Warehouse Gold with independent SQL readback and idempotent replay; exact real PASS: Self-Runner run 45047792510.

- [x] 1.6 Pin the reviewed HL7 ADT source-code → OMOP Standard Concept mapping as immutable, source-namespaced data. Add offline namespace/tamper tests. Real Warehouse Concept SQL validation remains required before Candidate publication.

- [x] 1.7 Independently re-read real HL7 4/8 Silver approval and both full Warehouse SQL identity snapshots with Shared Engine 0.1.17, read-only evidence: Self-Runner run 45035617569. This is not Candidate or Gold publication.

- [x] 1.8 Retire the never-published HL7 profile v1, which incorrectly used FHIR male/female labels; pin v2 to Parser's actual HL7 M/F values and enforce parser-to-profile tests before real Standard Concept SQL validation.

## Real Azure Fabric physical evidence — 2026-11-22

This change is now **business E2E verified** for the source-bound, synthetic, frozen new16 HL7 ADT batch (8 A01 + 8 A03; 4 Patient / 8 Encounter), not merely offline-interface complete. This does **not** represent an arbitrary hospital production-data rollout.

- Original raw Azure Blob GET and SHA verification recovered after Azure subscription restoration: [Run 45027630986](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/45027630986).
- Original HL7 16-message real Fabric **Canonical Silver** physical 4/8 write, readback, replay: [Run 45029344814](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/45029344814).
- All nine source-namespaced HL7 v2 Standard Concepts (including unobserved profile mappings) verified by two real Warehouse SQL queries, current existing Shared Identity bridge and immutable Silver physical approval: [Run 45044524800](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/45044524800).
- Actual isolated Fabric Spark **Shared Engine 0.1.17** Mapper (in-memory 4/8) passed with zero Candidate/Gold writes: [Run 45045868395](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/45045868395).
- Physical **Candidate Person 4 / Visit 8 / Approval-last** created using original Native Delta writer: [Run 45046372776](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/45046372776). That *overall* run ended HOLD during a subsequent Silver recheck **before** Warehouse SQL, and must not be rerun or mistaken for Gold success.
- Existing Candidate independently double-read and verified, original Gold Silver gate double GET passed, FHIR-only Warehouse 4P/4V + Identity Map 8 + Ledger 1 confirmed unchanged (no HL7 Gold at that point): [Run 45047240141](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/45047240141).
- **Final real Warehouse Gold COMMIT + independent SQL readback + verified replay SKIP PASS** from the **existing** Candidate without repeating Spark / Candidate publication: [Run 45047792510](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/45047792510), Self-Runner commit `bb2450a1649ce3f9b94effe892f14bf2ccc4212b`.
- Gold SQL row counts **before → after**: `cdm.person 4→8`, `cdm.visit_occurrence 4→12`, `etl.identity_map 8→20`, `etl.batch_ledger 1→2`, `etl.audit 2→4`, `etl.id_allocator 2→2` (unchanged cardinality). Same-batch replay verified SKIP with **no second SQL DML**.

### Safety and remaining environment issue

- CSV/FHIR and HL7 use **one** Shared OMOP Mapper/identity planner and existing Native Delta/SQL Gold writers; no G5 shadow Mapper, no HL7-to-FHIR detour, no default Concept=0, no fabricated Vocabulary or signed clinical/license bypass.
- No GA `env_healthcare` edit was necessary: the **isolated, published v0.1.17 environment** supported this HL7 Fabric Spark proof. Task **1.4 remains open** only for the independent historical Fabric Git / GA Environment identity reconciliation; it is **not** a blocker for the completed frozen synthetic HL7 business E2E.
- Do not rerun the historical Gold-v2 Candidate-publisher workflow: persisted Candidate and Gold now exist. Any future batch must use a new source manifest/request and new reviewed admission scope; replay the current batch only through audited independent readback.
