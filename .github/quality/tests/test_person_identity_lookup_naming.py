"""Source-only, dependency-light Person mapping lookup compatibility regression.

This test imports source code (not any historically pinned Fabric GA Wheel).
No Spark, Azure, Warehouse, Fabric or database operations are invoked.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "shared-data-engine" / "src"
sys.path.insert(0, str(SOURCE))

from healthcare_data_engine.identity.candidate_handoff import (
    CandidatePersonId, PersonVisitCandidateHandoff,
)


class PersonIdentityLookupNamingTests(unittest.TestCase):
    def test_new_business_method_matches_old_lookup_api(self):
        person = CandidatePersonId(
            hospital_id="synthetic-hospital", source_system="synthetic:synthetic-hospital:fhir",
            source_business_key="person-synthetic", person_id=147, state="PROVISIONAL",
        )
        expected = ("PERSON", "synthetic-hospital",
                    "synthetic:synthetic-hospital:fhir", "person-synthetic",
                    147, "PROVISIONAL")
        self.assertEqual(person.person_identity_lookup_row(), expected)
        self.assertEqual(person.f1_lookup(), expected)
        self.assertEqual(
            CandidatePersonId.f1_lookup(person),
            CandidatePersonId.person_identity_lookup_row(person),
        )

    def test_handoff_uses_semantic_method_and_retains_state(self):
        person = CandidatePersonId(
            "synthetic-hospital", "synthetic:synthetic-hospital:fhir",
            "synthetic-person", 11, "PERSISTED",
        )
        handoff = PersonVisitCandidateHandoff(
            person_lookup=(person,), batch_persons=(person,), batch_visits=(),
            hospital_id="synthetic-hospital",
            source_system="synthetic:synthetic-hospital:fhir",
            source_batch_id="synthetic-batch",
            manifest_sha256="a" * 64,
            processing_version="test-only",
            silver_publication_id="synthetic-publication",
            snapshot_fingerprint="b" * 64,
        )
        self.assertEqual(handoff.person_lookup_rows(), (
            person.person_identity_lookup_row(),
        ))
        self.assertEqual(handoff.person_lookup_rows()[0][-1], "PERSISTED")
        self.assertEqual(handoff.status, "G5_CANDIDATE_ID_HANDOFF_ONLY_NOT_PERSISTED")


if __name__ == "__main__":
    unittest.main()
