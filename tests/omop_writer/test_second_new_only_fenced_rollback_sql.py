"""70/11487 second READY strict fenced Writer SQL rollback transformation."""
from pathlib import Path
from unittest.mock import patch
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
for p in ("airflow/dags","apps/omop_writer","apps/landing_claim"):
    sys.path.insert(0,str(ROOT/p))
import generate_second_new_only_fenced_rollback as mod


def plan():
    return {"batch_id":mod.EXPECTED_BATCH,
            "manifest_sha256":mod.EXPECTED_SHA,
            "person_rows":70,"visit_rows":11487}


def skeleton():
    return ("\\set ON_ERROR_STOP on\nBEGIN;\n"
      + "SELECT task004_writer_fence.assert_active_claim('synthea','x','x','x','x',1);\n"
      + "DO $reconcile$ BEGIN NULL; END $reconcile$;\n"
      + "SELECT task004_writer_fence.assert_active_claim('synthea','x','x','x','x',1);\n"
      + "DO $complete$ BEGIN NULL; END $complete$;\n"
      + "SELECT task004_writer_fence.assert_active_claim('synthea','x','x','x','x',1);\n"
      + "COMMIT;\n"
      + "SELECT 'ORIGINAL_AFTER_COMMIT_MARKER';\n")


class SecondNewOnlySQLRollback(unittest.TestCase):
    def test_only_rollback_not_single_persistent_commit(self):
        with patch.object(mod,"verified_plan",return_value=plan()), \
             patch.object(mod,"assert_dynamic_handoff"), \
             patch.object(mod,"generate_dynamic_commit_sql",return_value=skeleton()) as render:
            sql=mod.generate_rollback({"plan":plan()},[{}]*70,[{}]*11487,"a"*48)
            render.assert_called_once()
            self.assertEqual([s.strip() for s in sql.splitlines()].count("BEGIN;"),1)
            self.assertEqual([s.strip() for s in sql.splitlines()].count("COMMIT;"),0)
            self.assertEqual([s.strip() for s in sql.splitlines()].count("ROLLBACK;"),1)
            self.assertEqual(sql.count("SELECT task004_writer_fence.assert_active_claim("),3)
            self.assertIn("DO $reconcile$",sql)
            self.assertIn("DO $complete$",sql)
            self.assertIn("SECOND_NEW_ONLY_REAL_FENCED_JOINT_ROLLBACK=PASS",sql)
            self.assertNotIn("ORIGINAL_AFTER_COMMIT_MARKER",sql)
            self.assertLess(sql.index("DO $complete$"),sql.index("\nROLLBACK;"))

    def test_wrong_batch_sha_counts_or_stale_handoff_stops_before_sql(self):
        for change in ({"batch_id":"synthea-new-only-untrusted"},
                       {"manifest_sha256":"f"*64}):
            with self.subTest(change=change), \
                 patch.object(mod,"verified_plan",return_value=plan()|change), \
                 patch.object(mod,"assert_dynamic_handoff"), \
                 patch.object(mod,"generate_dynamic_commit_sql") as render:
                with self.assertRaisesRegex(ValueError,"SECOND_BATCH_ONLY"):
                    mod.generate_rollback({"plan":plan()|change},[{}]*70,[{}]*11487,"a"*48)
                render.assert_not_called()
        with patch.object(mod,"verified_plan",return_value=plan()), \
             patch.object(mod,"assert_dynamic_handoff",side_effect=ValueError("BLOCKED:HANDOFF_DRIFT")), \
             patch.object(mod,"generate_dynamic_commit_sql") as render:
            with self.assertRaisesRegex(ValueError,"HANDOFF_DRIFT"):
                mod.generate_rollback({"plan":plan()},[{}]*70,[{}]*11487,"a"*48)
            render.assert_not_called()

    def test_rejects_inner_boundary_or_missing_fence_and_reconcile(self):
        for bad in (
          skeleton().replace("COMMIT;","COMMIT;\nCOMMIT;"),
          skeleton().replace("COMMIT;","ROLLBACK;"),
          skeleton().replace("DO $reconcile$ BEGIN NULL; END $reconcile$;\n",""),
          skeleton().replace("SELECT task004_writer_fence.assert_active_claim('synthea','x','x','x','x',1);\n","",1),
        ):
            with self.subTest(sql=bad[:25]),patch.object(mod,"verified_plan",return_value=plan()), \
                 patch.object(mod,"assert_dynamic_handoff"), \
                 patch.object(mod,"generate_dynamic_commit_sql",return_value=bad):
                with self.assertRaisesRegex(ValueError,"BLOCKED:SECOND_BATCH"):
                    mod.generate_rollback({"plan":plan()},[{}]*70,[{}]*11487,"a"*48)

    def test_staged_script_has_no_deploy_commit_path(self):
        src=(ROOT/"apps/omop_writer/generate_second_new_only_fenced_rollback.py").read_text()
        self.assertIn('connect("cdm_reader",readonly=True)',src)
        self.assertIn("inspect_new_only(conn,plan,people,visits,require_claim=False)",src)
        self.assertIn("generate_dynamic_commit_sql",src)
        self.assertIn('before+"\\nROLLBACK;\\n',src)
        self.assertNotIn("cur.execute(sql)",src)
        self.assertNotIn("subprocess.run",src)

if __name__=="__main__":
    unittest.main()
