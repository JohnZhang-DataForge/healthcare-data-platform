# HL7 Canonical Silver to OMOP Gold integration

The production runner will supply fresh authenticated OneLake Delta readers for
canonical_patient, canonical_encounter and silver_approval. It must independently
validate original HL7 Raw/Manifest, Azure resource identity and real Vocabulary
and Warehouse snapshots before invoking the adapter.

The HL7 adapter enforces the canonical source namespace
`johns-creek-hl7:johns-creek-hospital-b:johns-creek-hospital-b-hl7-v2`,
the immutable BatchContext and FrozenCandidateScope, approved Silver publication
identity, pinned Patient/Encounter contracts, zero quarantine, full-row parity
across two physical readbacks, unique business keys and parent visit FK.

After these checks it calls the existing Candidate -> Warehouse Gold function
without duplicating the Shared OMOP mapper, allocation, transaction or replay.
The existing Gold writer remains responsible for independently reading persisted
Candidate Delta twice, comparing the Warehouse identity snapshot, honoring the
single-writer fence and release gate, committing to SQL once and independently
verifying replay. Unknown SQL acknowledgements must remain read-only HOLD.

This change is offline/testable and is not a live-completion claim. The Fabric
Git Environment identity mismatch must be resolved without overwriting local
Warehouse/Lakehouse/Environment state before normal production deployment.
