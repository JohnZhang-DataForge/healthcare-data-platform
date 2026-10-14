"""Read-only next NEW_ONLY Airflow Spark handoff audit guard tests."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[2]
for p in ("apps/omop_writer", "airflow/dags", "apps/landing_claim"):
    sys.path.insert(0, str(ROOT/p))
import audit_second_new_only_ready as app


def plan():
    return {
        "batch_id":app.EXPECTED_BATCH,
        "manifest_sha256":app.EXPECTED_SHA,
        "person_rows":70,
        "visit_rows":11487,
        "plan_sha256":"0"*64,
    }


class NewOnlyRealReaderAuditTests(unittest.TestCase):
    def test_wrong_batch_digest_count_never_fetches_s3(self):
        for change in ({"batch_id":"synthea-new-only-untrusted"},
                       {"manifest_sha256":"f"*64},
                       {"person_rows":69},
                       {"visit_rows":812},
                       {"batch_id":app.COMPLETED_BATCH}):
            with self.subTest(change=change):
                context=plan() | change
                with patch.object(app,"verified_plan",return_value=context), \
                     patch.object(app,"assert_dynamic_handoff"), \
                     patch.object(app,"s3_rows") as s3:
                    with self.assertRaisesRegex(ValueError,"BLOCKED:NOT_VERIFIED_SECOND_READY"):
                        app.audit({"plan":context})
                    s3.assert_not_called()

    def test_requires_structured_real_spark_handoff(self):
        for handoff in (None, {}, {"plan":"bad"}):
            with self.subTest(handoff=handoff), self.assertRaises(ValueError):
                app.audit(handoff)
        with patch.object(app,"verified_plan",return_value=plan()), \
             patch.object(app,"assert_dynamic_handoff",side_effect=ValueError("BLOCKED:DRIFT")), \
             patch.object(app,"s3_rows") as s3:
            with self.assertRaisesRegex(ValueError,"DRIFT"):
                app.audit({"plan":plan()})
            s3.assert_not_called()

    def test_readonly_principal_required(self):
        with patch.object(app,"verified_plan",return_value=plan()), \
             patch.object(app,"assert_dynamic_handoff"), \
             patch.dict(app.os.environ,{"PGUSER":"cdm_writer"}), \
             patch.object(app,"s3_rows") as s3:
            with self.assertRaisesRegex(ValueError,"READONLY_PRINCIPAL"):
                app.audit({"plan":plan()})
            s3.assert_not_called()

    def test_readonly_collision_or_claim_refuses(self):
        base=MagicMock(status="READY_TO_CLAIM",claim_status="ABSENT",
                       existing_person_keys=0,existing_visit_keys=0,
                       historic_ledger_rows=0,commit_authorized=False)
        for field,value in [("status","INVALID"),
                            ("claim_status","PROCESSING"),
                            ("existing_person_keys",1),
                            ("existing_visit_keys",1),
                            ("historic_ledger_rows",1),
                            ("commit_authorized",True)]:
            gate=MagicMock(**{**vars(base),"status":"READY_TO_CLAIM",
                               "claim_status":"ABSENT",
                               "existing_person_keys":0,"existing_visit_keys":0,
                               "historic_ledger_rows":0,"commit_authorized":False})
            setattr(gate,field,value)
            fake=MagicMock()
            fake.__enter__.return_value=fake
            with patch.object(app,"verified_plan",return_value=plan()), \
                 patch.object(app,"assert_dynamic_handoff"), \
                 patch.object(app,"s3_rows",return_value=([{}]*70,[{}]*11487)), \
                 patch.object(app,"connect",return_value=fake), \
                 patch.object(app,"inspect_new_only",return_value=gate), \
                 patch.dict(app.os.environ,{"PGUSER":"cdm_reader"}):
                with self.subTest(field=field), self.assertRaisesRegex(ValueError,"SOURCE_COLLISION"):
                    app.audit({"plan":plan()})

    def test_source_script_has_zero_write_paths(self):
        source=(ROOT/"apps/omop_writer/audit_second_new_only_ready.py").read_text()
        self.assertIn('connect("cdm_reader", readonly=True)',source)
        self.assertIn("inspect_new_only(db, context, people, visits, require_claim=False)",source)
        self.assertIn("s3_rows(context)",source)
        self.assertNotIn("INSERT INTO",source)
        self.assertNotIn("UPDATE etl.",source)
        self.assertNotIn("COMMIT;",source)
        self.assertNotIn("task004-runtime person",source)


if __name__ == "__main__":
    unittest.main()
