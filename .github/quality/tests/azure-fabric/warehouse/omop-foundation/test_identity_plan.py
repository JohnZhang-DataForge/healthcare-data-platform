"""F2 pure planner + negative replay/namespace/allocator cases."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "azure-fabric/warehouse/omop-foundation/writer"))
from identity_plan import (MAX_ID, IdentityKey, BatchFence, Receipt, PlanningHold, plan_ids, replay)

def person(h="hospital-A", key="patient-1"):
    return IdentityKey("PERSON", h, "fhir_r4", key)

def visit(h="hospital-A", key="encounter-1"):
    return IdentityKey("VISIT_OCCURRENCE", h, "fhir_r4", key)

def plan(keys, old=(), nextid=None, gold=None):
    if nextid is None: nextid={"PERSON":1, "VISIT_OCCURRENCE":1}
    if gold is None: gold={"PERSON":[], "VISIT_OCCURRENCE":[]}
    return plan_ids(keys, old, nextid, gold)

def batch(sha="a"*64):
    return BatchFence("hospital-A","fhir_r4","G4-request-100",sha,"b"*64,"f2-v1",100,5918)

class F2PlannerTest(unittest.TestCase):
    def test_cross_hospital_distinct_and_repeatable(self):
        keys=[person("hospital-B"), visit(), person()]
        a=plan(keys)
        self.assertEqual(a,plan(list(reversed(keys))))
        got=dict(a.assigned)
        self.assertEqual(got[person()],1)
        self.assertEqual(got[person("hospital-B")],2)
        self.assertEqual(got[visit()],1)
        self.assertEqual(dict(a.next_free),{"PERSON":3,"VISIT_OCCURRENCE":2})

    def test_existing_source_id_never_changes(self):
        k=person()
        result=plan([k,person("hospital-B")],[(k,123)],
                    nextid={"PERSON":124,"VISIT_OCCURRENCE":1},
                    gold={"PERSON":[123],"VISIT_OCCURRENCE":[]})
        self.assertEqual(dict(result.assigned)[k],123)
        self.assertEqual(dict(result.assigned)[person("hospital-B")],124)
        self.assertEqual(len(result.inserted),1)

    def test_duplicate_and_collation_key_hold(self):
        with self.assertRaisesRegex(PlanningHold,"DUPLICATE_SOURCE"):
            plan([person(),person()])
        with self.assertRaisesRegex(PlanningHold,"SOURCE_COLLATION_COLLISION"):
            plan([person(key="UPPER"),person(key="upper")])
        with self.assertRaises(PlanningHold):
            plan([person()],old=[(person(key="UPPER"),1),(person(key="upper"),2)],
                 nextid={"PERSON":3,"VISIT_OCCURRENCE":1},
                 gold={"PERSON":[1,2],"VISIT_OCCURRENCE":[]})

    def test_new_source_key_casefold_collides_with_persisted(self):
        with self.assertRaisesRegex(PlanningHold,"SOURCE_PERSISTED_COLLATION_COLLISION"):
            plan([person(key="patient")],
                 old=[(person(key="PATIENT"),1)],
                 nextid={"PERSON":2,"VISIT_OCCURRENCE":1},
                 gold={"PERSON":[1],"VISIT_OCCURRENCE":[]})

    def test_missing_keys_and_incorrect_entity(self):
        for value in ("", " key ", "bad\nkey", "x"*257):
            with self.assertRaises(PlanningHold):
                person(key=value)
        with self.assertRaises(PlanningHold):
            IdentityKey("UNKNOWN","h","fhir_r4","id")

    def test_identity_collision_partial_gold_or_allocator_rewind_hold(self):
        a=person()
        b=person("hospital-B")
        for old,physical,n in [
            ([(a,1),(b,1)],[1],3),
            ([(a,1)],[2],3),
            ([(a,1)],[],3),
            ([(a,1)],[1],1),
        ]:
            with self.assertRaises(PlanningHold):
                plan([b],old,nextid={"PERSON":n,"VISIT_OCCURRENCE":1},
                     gold={"PERSON":physical,"VISIT_OCCURRENCE":[]})

    def test_int_limit_and_invalid_counter(self):
        with self.assertRaisesRegex(PlanningHold,"INT_OVERFLOW"):
            plan([person(),person("hospital-B")],
                 nextid={"PERSON":MAX_ID,"VISIT_OCCURRENCE":1})
        self.assertEqual(dict(plan([person()],
            nextid={"PERSON":MAX_ID,"VISIT_OCCURRENCE":1}).next_free)["PERSON"],MAX_ID+1)
        for bad in (0,True,MAX_ID+2):
            with self.assertRaises(PlanningHold):
                plan([person()],nextid={"PERSON":bad,"VISIT_OCCURRENCE":1})

    def test_exact_ledger_replay(self):
        f=batch()
        self.assertEqual(replay(f,[],independently_verified=False),"NEW")
        receipt=Receipt(f,"COMMITTED",100,5918)
        self.assertEqual(replay(f,[receipt],independently_verified=True),"VERIFIED_SKIP")
        with self.assertRaisesRegex(PlanningHold,"GOLD_READBACK_REQUIRED"):
            replay(f,[receipt],independently_verified=False)
        with self.assertRaisesRegex(PlanningHold,"CONFLICTING_BATCH_HASH_OR_COUNTS"):
            replay(f,[Receipt(batch(sha="c"*64),"COMMITTED",100,5918)],
                   independently_verified=True)
        for rows in ([Receipt(f,"STARTED",None,None)],
                     [Receipt(f,"COMMITTED",100,5917)],
                     [receipt,receipt]):
            with self.assertRaises(PlanningHold):
                replay(f,rows,independently_verified=True)

    def test_unknown_hash_and_fake_count(self):
        with self.assertRaises(PlanningHold):
            batch(sha="not-a-sha")
        with self.assertRaises(PlanningHold):
            BatchFence("h","fhir_r4","b","a"*64,"b"*64,"v1",True,0)



class F2GoldTransactionTest(unittest.TestCase):
    """SQLite exercises SQL atomicity offline; never a Fabric COMMIT claim."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.files = {name: pathlib.Path(self.tmp.name) / (name + ".db")
                      for name in ("main", "etl", "cdm", "audit")}
        con = self._open()
        for sql in (
            "CREATE TABLE etl.identity_map (entity_type text, hospital_id text, "
            "source_system text, source_business_key text, omop_id int, "
            "first_batch_id text, mapping_version text, created_at_utc text)",
            "CREATE TABLE etl.id_allocator (entity_type text, next_omop_id int, "
            "mapping_version text, updated_at_utc text)",
            "CREATE TABLE etl.batch_ledger (hospital_id text, source_system text, "
            "batch_id text, source_manifest_sha256 text, mapping_profile_sha256 text, "
            "writer_version text, batch_status text, expected_person_count int, "
            "expected_visit_count int, committed_person_count int, "
            "committed_visit_count int, committed_at_utc text)",
            "CREATE TABLE audit.omop_commit_check (batch_id text, check_name text, "
            "expected_count int, observed_count int, check_status text, checked_at_utc text)",
            "CREATE TABLE cdm.person (person_id int, gender_concept_id int, "
            "year_of_birth int, race_concept_id int, ethnicity_concept_id int, "
            "person_source_value text)",
            "CREATE TABLE cdm.visit_occurrence (visit_occurrence_id int, person_id int, "
            "visit_concept_id int, visit_type_concept_id int, visit_start_date text, "
            "visit_end_date text)",
        ):
            con.execute(sql)
        con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def _open(self):
        import sqlite3
        con = sqlite3.connect(str(self.files["main"]), isolation_level=None)
        for name in ("etl", "cdm", "audit"):
            con.execute(f"ATTACH DATABASE '{self.files[name]}' AS {name}")
        return con

    def _batch(self):
        from gold_transaction import GoldBatch
        fence = BatchFence("hospital-A", "fhir_r4", "batch-1",
                           "a"*64, "b"*64, "f2-v1", 1, 1)
        return GoldBatch(
            fence=fence,
            identities=((person(key="p1"), 1), (visit(key="v1"), 1)),
            persons=({"person_id": 1, "person_source_value": "p1",
                      "gender_concept_id": 8507, "race_concept_id": 8527,
                      "ethnicity_concept_id": 38003564, "year_of_birth": 2000,
                      "identity_state": "PROVISIONAL"},),
            visits=({"visit_occurrence_id": 1, "person_id": 1,
                     "visit_concept_id": 9201, "visit_type_concept_id": 44818517,
                     "visit_start_date": "2026-01-01", "visit_end_date": "2026-01-02",
                     "source_encounter_id": "v1", "source_person_id": "p1",
                     "source_system": "fhir_r4", "identity_state": "PROVISIONAL",
                     "parent_identity_state": "PROVISIONAL"},),
            mapping_version="f2-v1", clinical_review_sha256="c"*64,
            license_review_sha256="d"*64, candidate_approval_sha256="e"*64)

    def _execute(self, batch=None, connection=None):
        from gold_transaction import execute_gold_transaction
        con = connection or self._open()
        try:
            return execute_gold_transaction(
                con, batch or self._batch(),
                single_writer_fence=lambda: True,
                release_gate=lambda value: True)
        finally:
            con.close()

    def _counts(self):
        con = self._open()
        try:
            return tuple(con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                         for table in ("etl.identity_map", "etl.id_allocator",
                                       "cdm.person", "cdm.visit_occurrence",
                                       "etl.batch_ledger", "audit.omop_commit_check"))
        finally:
            con.close()

    def test_atomic_commit_and_separate_connection_readback(self):
        from gold_transaction import independent_gold_readback
        self.assertEqual(
            self._execute(),
            "GOLD_COMMIT_ACK_VERIFY_INDEPENDENT_SQL_NOT_ACCEPTED")
        self.assertEqual(self._counts(), (2, 2, 1, 1, 1, 2))
        self.assertTrue(independent_gold_readback(self._open, self._batch()))

    def test_replay_never_blindly_inserts_again(self):
        from gold_transaction import independent_gold_readback
        self._execute()
        with self.assertRaises(PlanningHold):
            self._execute()
        self.assertEqual(self._counts(), (2, 2, 1, 1, 1, 2))
        self.assertTrue(independent_gold_readback(self._open, self._batch()))

    def test_unapproved_fence_and_fake_concept_hold_before_dml(self):
        from gold_transaction import GoldBatch, execute_gold_transaction, GoldHold
        good = self._batch()
        bad_person = {**good.persons[0], "race_concept_id": 0}
        bad = GoldBatch(good.fence, good.identities, (bad_person,),
                        good.visits, good.mapping_version,
                        good.clinical_review_sha256, good.license_review_sha256,
                        good.candidate_approval_sha256)
        with self.assertRaisesRegex(GoldHold, "GOLD_PERSON_MAP_OR_PROFILE"):
            self._execute(bad)
        con = self._open()
        try:
            with self.assertRaisesRegex(GoldHold, "GOLD_RELEASE_OR_SINGLE_WRITER_HOLD"):
                execute_gold_transaction(con, good,
                    single_writer_fence=lambda: False,
                    release_gate=lambda value: True)
        finally:
            con.close()
        self.assertEqual(self._counts(), (0, 0, 0, 0, 0, 0))

    def test_failure_before_commit_rolls_back_all_six_tables(self):
        class FailureCursor:
            def __init__(self, inner):
                self.inner = inner
            def execute(self, sql, params=()):
                if sql.startswith("INSERT INTO cdm.visit_occurrence"):
                    raise RuntimeError("injected DML failure")
                self.inner.execute(sql, params)
                return self
            def fetchall(self):
                return self.inner.fetchall()
            @property
            def rowcount(self):
                return self.inner.rowcount
        class FailureConnection:
            def __init__(self, inner):
                self.inner = inner
            def cursor(self):
                return FailureCursor(self.inner.cursor())
            def rollback(self):
                return self.inner.rollback()
            def close(self):
                return self.inner.close()
        with self.assertRaisesRegex(RuntimeError, "injected DML"):
            self._execute(connection=FailureConnection(self._open()))
        self.assertEqual(self._counts(), (0, 0, 0, 0, 0, 0))

    def test_commit_ack_unknown_does_not_retry_and_requires_get(self):
        from gold_transaction import independent_gold_readback
        class AckCursor:
            def __init__(self, inner):
                self.inner = inner
            def execute(self, sql, params=()):
                self.inner.execute(sql, params)
                if sql == "COMMIT TRANSACTION":
                    raise OSError("simulated connection lost after commit")
                return self
            def fetchall(self):
                return self.inner.fetchall()
            @property
            def rowcount(self):
                return self.inner.rowcount
        class AckConnection:
            def __init__(self, inner):
                self.inner = inner
            def cursor(self):
                return AckCursor(self.inner.cursor())
            def rollback(self):
                raise AssertionError("do not rollback unknown commit")
            def close(self):
                self.inner.close()
        self.assertEqual(
            self._execute(connection=AckConnection(self._open())),
            "GOLD_UNKNOWN_COMMIT_ACK_VERIFY_READONLY")
        self.assertEqual(self._counts(), (2, 2, 1, 1, 1, 2))
        self.assertTrue(independent_gold_readback(self._open, self._batch()))

if __name__=="__main__":
    unittest.main()
