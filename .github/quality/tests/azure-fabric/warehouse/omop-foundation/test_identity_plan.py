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



# F2 physical Warehouse -> Shared IdentitySnapshot boundary. All synthetic,
# exactly the Self-Runner six-table SELECT row layout and SHA encoding.
import hashlib
import json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] /
                       "shared-data-engine/src"))
from silver_identity import bridge_f2_sql_readback_rows
from healthcare_data_engine.identity.preview import (
    bridge_f2_person_visit_allocation, require_preview_snapshot_unchanged,
)
from healthcare_data_engine.mapping.omop.registry import DerivedRowKey

F2_WAREHOUSE = "7a6d08da-278d-4603-8a3b-28640110984c"


def f2_physical_rows():
    return {name: () for name in ("identity_map", "allocator", "person",
                                 "visit", "ledger", "audit")}


def f2_table_digest(rows):
    hashes = {}
    for name, values in rows.items():
        digest = hashlib.sha256()
        for row in values:
            raw = json.dumps(tuple(row), ensure_ascii=False,
                             separators=(",", ":"), default=str).encode("utf-8")
            digest.update(len(raw).to_bytes(4, "big") + raw)
        hashes[name] = digest.hexdigest()
    return hashes


def make_f2_bridge(rows, **changes):
    d = f2_table_digest(rows)
    args = dict(first_table_sha256=d, second_table_sha256=d,
                warehouse_id=F2_WAREHOUSE)
    args.update(changes)
    return bridge_f2_sql_readback_rows(rows, **args)


class F2PhysicalToSharedBridgeTests(unittest.TestCase):
    def test_empty_real_shaped_six_table_snapshot_is_preview_only(self):
        rows = f2_physical_rows()
        a = make_f2_bridge(rows)
        b = make_f2_bridge(rows)
        self.assertEqual(a.physical_snapshot_sha256, b.physical_snapshot_sha256)
        self.assertEqual(a.shared_snapshot_fingerprint, b.shared_snapshot_fingerprint)
        self.assertNotEqual(a.physical_snapshot_sha256, a.shared_snapshot_fingerprint)
        self.assertEqual(a.snapshot.existing, ())
        self.assertEqual(dict(a.snapshot.next_free), {
            "cdm.person": 1, "cdm.visit_occurrence": 1})
        self.assertEqual(a.status, "F2_SQL_ROWS_TO_SHARED_SNAPSHOT_SOURCE_ONLY_NOT_AUTHENTICATED")
        self.assertEqual(len(a.table_sha256), 6)

    def test_shared_bridge_reuses_f2_allocator_and_preserves_existing_int(self):
        rows = f2_physical_rows()
        rows["identity_map"] = (
            ("PERSON", "hospital-a", "fhir:hospital-a:feed1", "p1", 41, "b1", "v1"),
            ("VISIT_OCCURRENCE", "hospital-a", "fhir:hospital-a:feed1", "v1", 90, "b1", "v1"),
        )
        rows["allocator"] = (("PERSON", 42, "v1"),
                             ("VISIT_OCCURRENCE", 91, "v1"))
        rows["person"] = ((41,),)
        rows["visit"] = ((90, 41),)
        rows["ledger"] = (
            ("hospital-a", "fhir:hospital-a:feed1", "b1",
             "a" * 64, "b" * 64, "writer-1", "COMMITTED", 1, 1, 1, 1),
        )
        rows["audit"] = (("b1", "PERSON", 1, 1, "PASS"),)
        source = make_f2_bridge(rows)
        self.assertEqual(len(source.snapshot.persisted()), 2)
        new = IdentityKey("PERSON", "hospital-b", "fhir:hospital-b:feed1", "p1")
        old = IdentityKey("PERSON", "hospital-a", "fhir:hospital-a:feed1", "p1")
        physical_existing = (
            (old, 41),
            (IdentityKey("VISIT_OCCURRENCE", "hospital-a",
                         "fhir:hospital-a:feed1", "v1"), 90),
        )
        plan = plan_ids([old, new], physical_existing,
                        {"PERSON": 42, "VISIT_OCCURRENCE": 91},
                        {"PERSON": (41,), "VISIT_OCCURRENCE": (90,)})
        shared = bridge_f2_person_visit_allocation(plan, source.snapshot)
        self.assertEqual(shared.for_key(DerivedRowKey(
            "cdm.person", "hospital-a", "fhir:hospital-a:feed1",
            "p1")).state, "PERSISTED")
        self.assertEqual(shared.for_key(DerivedRowKey(
            "cdm.person", "hospital-b", "fhir:hospital-b:feed1",
            "p1")).state, "PROVISIONAL")
        self.assertEqual(shared.for_key(DerivedRowKey(
            "cdm.person", "hospital-b", "fhir:hospital-b:feed1",
            "p1")).omop_id, 42)
        require_preview_snapshot_unchanged(shared, source.snapshot)

    def test_modified_digest_or_single_connection_is_not_physical_proof(self):
        rows = f2_physical_rows()
        d = f2_table_digest(rows)
        tampered = dict(d, ledger="f" * 64)
        for change in (
            {"first_table_sha256": tampered},
            {"second_table_sha256": tampered},
            {"first_table_sha256": {}},
            {"warehouse_id": "wrong"},
        ):
            with self.subTest(change=list(change)):
                with self.assertRaises(PlanningHold):
                    make_f2_bridge(rows, **change)

    def test_missing_rowsets_or_unsupported_schema_holds(self):
        rows = f2_physical_rows()
        for broken in (
            dict(rows, extra=()),
            {k: v for k, v in rows.items() if k != "ledger"},
            dict(rows, person=(("wrong", "extra"),)),
            dict(rows, allocator=(("PERSON", 1, "v1"),)),
        ):
            with self.subTest(names=sorted(broken)):
                with self.assertRaises(PlanningHold):
                    make_f2_bridge(broken)

    def test_tampered_rows_do_not_match_previous_independent_sql_sha(self):
        original = f2_physical_rows()
        pinned = f2_table_digest(original)
        mutated = dict(original, person=((999,),))
        with self.assertRaisesRegex(PlanningHold, "TWO_CONNECTION_SHA_MISMATCH"):
            bridge_f2_sql_readback_rows(
                mutated, first_table_sha256=pinned,
                second_table_sha256=pinned, warehouse_id=F2_WAREHOUSE)

    def test_unbounded_physical_readback_is_rejected_before_shared_plan(self):
        rows = dict(f2_physical_rows(), person=((1,),) * 20001)
        with self.assertRaisesRegex(PlanningHold, "ROW_BOUND_OR_TYPE"):
            make_f2_bridge(rows)

    def test_nonempty_without_durable_allocator_does_not_invent_ids(self):
        rows = f2_physical_rows()
        for table, value in (
            ("person", ((1,),)),
            ("ledger", (("h", "s", "b", "a" * 64, "b" * 64, "v", "COMMITTED", 1, 0, 1, 0),)),
            ("audit", (("b", "PERSON", 1, 1, "PASS"),)),
        ):
            with self.subTest(table=table):
                with self.assertRaisesRegex(PlanningHold, "ALLOCATOR_MISSING_WITH_STATE"):
                    make_f2_bridge(dict(rows, **{table: value}))

    def test_map_gold_drift_and_orphan_visit_hold(self):
        rows = f2_physical_rows()
        rows["allocator"] = (("PERSON", 2, "v1"),
                             ("VISIT_OCCURRENCE", 2, "v1"))
        rows["identity_map"] = (("PERSON", "h", "fhir:h:f", "p", 1, "b", "v1"),)
        with self.assertRaisesRegex(PlanningHold, "SHARED_SNAPSHOT_CONFLICT"):
            make_f2_bridge(rows)
        rows["person"] = ((1,),)
        rows["visit"] = ((1, 99),)
        with self.assertRaisesRegex(PlanningHold, "VISIT_PARENT_MISSING"):
            make_f2_bridge(rows)

    def test_snapshot_changes_invalidate_shared_preview(self):
        rows = f2_physical_rows()
        bridge = make_f2_bridge(rows)
        key = IdentityKey("PERSON", "h", "fhir:h:f", "p")
        proposed = plan_ids([key], (), {"PERSON": 1, "VISIT_OCCURRENCE": 1},
                            {"PERSON": (), "VISIT_OCCURRENCE": ()})
        preview = bridge_f2_person_visit_allocation(proposed, bridge.snapshot)
        self.assertEqual(preview.status, "ID_PREVIEW_ONLY_NOT_PERSISTED")
        changed_rows = dict(rows, allocator=(("PERSON", 1, "v1"),
                                            ("VISIT_OCCURRENCE", 1, "v1")))
        changed = make_f2_bridge(changed_rows)
        with self.assertRaisesRegex(Exception, "SNAPSHOT_CHANGED_BEFORE_COMMIT"):
            require_preview_snapshot_unchanged(preview, changed.snapshot)


if __name__=="__main__":
    unittest.main()
