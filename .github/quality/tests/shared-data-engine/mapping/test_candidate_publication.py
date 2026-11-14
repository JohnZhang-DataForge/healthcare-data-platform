"""P3 pure Candidate publication planning: synthetic first-batch/replay/negative DQ.

There is NO live Delta or Azure call here. Clinical and license approval are
separate runtime gates. The 100/5918 case is synthetic only.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[5] /
                       "shared-data-engine" / "src"))

from healthcare_data_engine.identity.candidate_handoff import (
    CandidatePersonId, CandidateVisitId, PersonVisitCandidateHandoff,
)
from healthcare_data_engine.mapping.omop.candidates import OmopCandidates
from healthcare_data_engine.mapping.omop.candidate_publication import (
    CandidatePublicationHold, CandidatePublicationPlan, FrozenCandidateScope,
    ObservedCandidate, classify_mapping_failure, decide_candidate_publication,
    freeze_candidate_scope,
)

HOSPITAL = "atlanta-hospital-a"
FEED = "atlanta-hospital-a-fhir-r4"
SOURCE = "synthea-fhir:" + HOSPITAL + ":" + FEED
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def fixture(people=2, visits=4, *, person_state="PROVISIONAL"):
    persons = tuple(
        CandidatePersonId(HOSPITAL, SOURCE, "patient-%05d" % i,
                          i + 1, person_state)
        for i in range(people))
    children = tuple(
        CandidateVisitId(
            HOSPITAL, SOURCE, "encounter-%05d" % i,
            "patient-%05d" % (i % people),
            i + 1, (i % people) + 1, "PROVISIONAL", person_state,
        )
        for i in range(visits))
    h = PersonVisitCandidateHandoff(
        person_lookup=persons, batch_persons=persons, batch_visits=children,
        hospital_id=HOSPITAL, source_system=SOURCE,
        source_batch_id="2e110eb1971fcfa3ebb4dda6782c49a7608955855a2de45a3d77ada47fea8adb",
        manifest_sha256=SHA_A, processing_version="fhir-silver-canonical-v1:engine-0.1.1",
        silver_publication_id="silver-synthetic-001", snapshot_fingerprint=SHA_B,
    )
    c = OmopCandidates(
        object(), object(), SHA_C, people, visits,
    )
    return h, c


def scope(people=2, visits=4):
    h, c = fixture(people=people, visits=visits)
    return freeze_candidate_scope(h, c, feed_id=FEED,
                                  request_id="atlanta-fhir-gh-41552666929")


def complete_observed(sc, **changes):
    val = {
        "scope": sc, "person_delta_exists": True, "visit_delta_exists": True,
        "approval_exists": True, "person_count": sc.patient_count,
        "visit_count": sc.encounter_count, "person_content_sha256": SHA_C,
        "visit_content_sha256": SHA_D,
        "approval_status": "CANDIDATE_APPROVED",
        "independently_reopened": True,
        "schema_keys_fk_verified": True,
    }
    return ObservedCandidate(**{**val, **changes})


class CandidatePublicationPlanTests(unittest.TestCase):
    def test_100_5918_g4_compatible_first_batch_is_offline_plan_only(self):
        s = scope(100, 5918)
        p = decide_candidate_publication(s, ())
        self.assertEqual(p.decision, "PLAN_NEW_OFFLINE_ONLY")
        self.assertEqual((s.patient_count, s.encounter_count), (100, 5918))
        self.assertEqual(s.provisional_person_count, 100)
        self.assertEqual(s.provisional_visit_count, 5918)
        self.assertEqual(len(p.ordered_steps), 5)
        self.assertLess(p.ordered_steps.index("DELTA_PERSON_CREATE_ERROR_IF_EXISTS"),
                        p.ordered_steps.index("CANDIDATE_APPROVAL_WRITE_LAST"))
        self.assertLess(p.ordered_steps.index("DELTA_VISIT_CREATE_ERROR_IF_EXISTS"),
                        p.ordered_steps.index("CANDIDATE_APPROVAL_WRITE_LAST"))
        self.assertFalse(p.gold_commit_authorized)
        self.assertTrue(p.source_only_not_clinically_approved)

    def test_same_batch_deterministic_receipt_no_athena_literal(self):
        s1 = scope()
        s2 = scope()
        self.assertEqual(s1, s2)
        self.assertEqual(s1.receipt_key, s2.receipt_key)
        self.assertEqual(len(s1.receipt_key), 64)
        self.assertNotIn("FEB-26", repr(s1))
        self.assertNotIn("LOINC", repr(s1))

    def test_persisted_person_with_provisional_visits_keeps_flags(self):
        h, c = fixture(person_state="PERSISTED")
        result = freeze_candidate_scope(h, c, feed_id=FEED,
                                        request_id="atlanta-fhir-gh-41552666929")
        self.assertEqual(result.provisional_person_count, 0)
        self.assertEqual(result.provisional_visit_count, c.visit_count)
        self.assertFalse(decide_candidate_publication(
            result, ()).gold_commit_authorized)

    def test_replay_skip_requires_independent_readback(self):
        s = scope()
        self.assertEqual(decide_candidate_publication(
            s, (complete_observed(s),),
            expected_person_content_sha256=SHA_C,
            expected_visit_content_sha256=SHA_D).decision,
            "SKIP_VERIFIED_CANDIDATE_ONLY")
        # A readback digest that merely exists cannot authorize SKIP.
        self.assertEqual(decide_candidate_publication(
            s, (complete_observed(s),)).decision, "VERIFY_READONLY")
        for change in (
            {"independently_reopened": False},
            {"schema_keys_fk_verified": False},
            {"person_delta_exists": False},
            {"visit_delta_exists": False},
            {"approval_exists": False},
        ):
            with self.subTest(change=change):
                self.assertEqual(
                    decide_candidate_publication(
                        s, (complete_observed(s, **change),)).decision,
                    "VERIFY_READONLY")

    def test_wrong_hash_missing_hash_count_or_approval_hold(self):
        s = scope()
        for change in (
            {"person_content_sha256": None},
            {"visit_content_sha256": None},
            {"person_count": 0},
            {"visit_count": 1},
            {"approval_status": "HOLD"},
        ):
            with self.subTest(change=change):
                self.assertEqual(
                    decide_candidate_publication(
                        s, (complete_observed(s, **change),),
                        expected_person_content_sha256=SHA_C,
                        expected_visit_content_sha256=SHA_D).decision,
                    "HOLD_READBACK_OR_APPROVAL_CONFLICT")

    def test_expected_digest_mismatch_and_partial_expectation_hold(self):
        s = scope()
        with self.assertRaisesRegex(CandidatePublicationHold,
                                    "DIGEST_PAIR_REQUIRED"):
            decide_candidate_publication(
                s, (complete_observed(s),),
                expected_person_content_sha256=SHA_C)
        self.assertEqual(decide_candidate_publication(
            s, (complete_observed(s),),
            expected_person_content_sha256=SHA_D,
            expected_visit_content_sha256=SHA_D).decision,
            "HOLD_READBACK_OR_APPROVAL_CONFLICT")

    def test_same_request_different_batch_mapping_or_snapshot_holds(self):
        s = scope()
        for change in (
            {"manifest_sha256": SHA_D},
            {"mapping_sha256": SHA_D},
            {"identity_snapshot_fingerprint": SHA_D},
            {"source_batch_id": "other-batch"},
            {"silver_publication_id": "other-publication"},
        ):
            with self.subTest(change=change):
                other = replace(s, **change)
                self.assertEqual(
                    decide_candidate_publication(
                        s, (complete_observed(other),)).decision,
                    "HOLD_VERSION_OR_SOURCE_CONFLICT")

    def test_unrelated_request_is_not_conflict_or_skip(self):
        s = scope()
        other = replace(s, request_id="another-request")
        self.assertEqual(decide_candidate_publication(
            s, (complete_observed(other),)).decision, "PLAN_NEW_OFFLINE_ONLY")

    def test_duplicate_observations_hold_and_unknown_ack_never_retries(self):
        s = scope()
        previous = complete_observed(s)
        self.assertEqual(decide_candidate_publication(
            s, (previous, previous)).decision, "HOLD_DUPLICATE_PUBLICATIONS")
        self.assertEqual(decide_candidate_publication(
            s, (), unknown_write_ack=True).decision, "VERIFY_READONLY")
        self.assertFalse(decide_candidate_publication(
            s, (), unknown_write_ack=True).ordered_steps)

    def test_unknown_codes_can_quarantine_without_implicit_gold(self):
        for reason in (
            "UNMAPPED_SOURCE_CODE", "NO_VALID_STANDARD_CONCEPT",
            "WRONG_CONCEPT_DOMAIN", "EXPIRED_CONCEPT",
            "MISSING_REQUIRED_SOURCE_CODE",
        ):
            self.assertEqual(classify_mapping_failure(reason),
                             "DATA_QUARANTINE_CANDIDATE_HOLD_PUBLICATION")
        # Existing strict Mapper/P1 reason codes (no patient values).
        self.assertEqual(
            classify_mapping_failure("G5_UNKNOWN_MAPPING_CODE:race_code"),
            "DATA_QUARANTINE_CANDIDATE_HOLD_PUBLICATION")
        self.assertEqual(
            classify_mapping_failure("P1_UNMAPPED_SOURCE_CODE:encounter_class"),
            "DATA_QUARANTINE_CANDIDATE_HOLD_PUBLICATION")
        for reason in ("SNAPSHOT_CHANGED", "SILVER_APPROVAL_MISSING",
                       "PROFILE_SHA_DRIFT", "WAREHOUSE_WRITE_UNKNOWN_ACK",
                       "G5_UNKNOWN_MAPPING_CODE:untrusted_field",
                       "P1_CONCEPT_DOMAIN_MISMATCH"):
            self.assertEqual(classify_mapping_failure(reason),
                             "BATCH_HOLD_NO_PUBLICATION")

    def test_missing_parent_and_identity_flag_forgery_hold(self):
        h, c = fixture()
        for altered in (
            replace(h.batch_visits[0], person_id=99999),
            replace(h.batch_visits[0], parent_state="PERSISTED"),
            replace(h.batch_visits[0], state="GOLD_COMMITTED"),
        ):
            broken = replace(h, batch_visits=(altered,) + h.batch_visits[1:])
            with self.subTest(altered=altered), self.assertRaises(
                    CandidatePublicationHold):
                freeze_candidate_scope(broken, c, feed_id=FEED,
                                       request_id="atlanta-fhir-gh-41552666929")

    def test_mapper_count_and_status_forgery_hold(self):
        h, c = fixture()
        with self.assertRaisesRegex(CandidatePublicationHold,
                                    "COUNTS_MISMATCH"):
            freeze_candidate_scope(h, replace(c, visit_count=3), feed_id=FEED,
                                   request_id="atlanta-fhir-gh-41552666929")
        with self.assertRaisesRegex(CandidatePublicationHold,
                                    "UNTRUSTED_SOURCE_HANDOFF"):
            freeze_candidate_scope(h, replace(c, status="GOLD_COMMITTED"),
                                   feed_id=FEED,
                                   request_id="atlanta-fhir-gh-41552666929")

    def test_duplicate_person_visit_ids_hold(self):
        h, c = fixture()
        second = replace(h.batch_persons[1], person_id=h.batch_persons[0].person_id)
        with self.assertRaises(CandidatePublicationHold):
            freeze_candidate_scope(
                replace(h, batch_persons=(h.batch_persons[0], second)),
                c, feed_id=FEED, request_id="atlanta-fhir-gh-41552666929")
        duplicate = replace(h.batch_visits[1],
                            visit_occurrence_id=h.batch_visits[0].visit_occurrence_id)
        with self.assertRaises(CandidatePublicationHold):
            freeze_candidate_scope(
                replace(h, batch_visits=(h.batch_visits[0], duplicate) +
                        h.batch_visits[2:]),
                c, feed_id=FEED, request_id="atlanta-fhir-gh-41552666929")

    def test_cannot_substitute_random_or_row_ordinal_as_persisted_id(self):
        s = scope()
        with self.assertRaisesRegex(CandidatePublicationHold,
                                    "PROVISIONAL_COUNTS_INVALID"):
            replace(s, provisional_person_count=101)
        with self.assertRaisesRegex(CandidatePublicationHold,
                                    "INVALID_MAPPING_SHA256"):
            replace(s, mapping_sha256="untrusted")
        with self.assertRaisesRegex(CandidatePublicationHold,
                                    "SOURCE_NAMESPACE_CONFLICT"):
            replace(s, feed_id="another-feed")

    def test_observation_malformed_values_hold_without_writes(self):
        s = scope()
        for args in (
            {"person_count": -1},
            {"person_content_sha256": "not-sha"},
            {"independently_reopened": "yes"},
            {"approval_status": "GOLD_COMMITTED"},
        ):
            with self.subTest(args=args), self.assertRaises(
                    CandidatePublicationHold):
                complete_observed(s, **args)

    def test_017_package_metadata_and_public_p3_api_are_same_release(self):
        import tomllib
        import healthcare_data_engine as engine
        project = tomllib.loads(
            (Path(__file__).resolve().parents[5] /
             "shared-data-engine/pyproject.toml").read_text())["project"]
        self.assertEqual(project["version"], engine.__version__)
        self.assertEqual(engine.__version__, "0.1.14")
        self.assertIs(engine.FrozenCandidateScope, FrozenCandidateScope)
        self.assertIs(engine.ObservedCandidate, ObservedCandidate)
        self.assertIs(engine.CandidatePublicationPlan, CandidatePublicationPlan)
        self.assertIs(engine.decide_candidate_publication,
                      decide_candidate_publication)
        self.assertIs(engine.freeze_candidate_scope, freeze_candidate_scope)
        self.assertIs(engine.classify_mapping_failure,
                      classify_mapping_failure)
        # Pure planning is source-only: even first-batch has NO Gold grant.
        self.assertFalse(engine.decide_candidate_publication(
            scope(), ()).gold_commit_authorized)

    def test_module_has_no_azure_sql_spark_or_delta_io(self):
        import inspect
        import healthcare_data_engine.mapping.omop.candidate_publication as mod
        source = inspect.getsource(mod)
        for forbidden in ("import pyodbc", "SparkSession", "dbutils", ".write.",
                          "INSERT INTO", "UPDATE cdm.", "requests.get("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
