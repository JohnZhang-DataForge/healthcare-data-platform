"""TASK004 second new-only single authorized COMMIT guard tests."""
from pathlib import Path
from unittest.mock import patch
import sys,unittest

ROOT=Path(__file__).resolve().parents[2]
for p in ("airflow/dags","apps/omop_writer","apps/landing_claim"):
    sys.path.insert(0,str(ROOT/p))
import commit_second_new_only_once as app


def good_plan():
    return {"batch_id":app.EXPECTED_BATCH,
            "manifest_sha256":app.EXPECTED_SHA,
            "person_rows":70,"visit_rows":11487}


def skeleton():
    return ("\\set ON_ERROR_STOP on\n\\set QUIET 1\nBEGIN;\n"
       + "DO $pre$ BEGIN RAISE EXCEPTION 'BLOCKED:COMMIT_PRECONDITION_NOT_CLEAN'; END $pre$;\n"
       + "SELECT task004_writer_fence.assert_active_claim('x','x','x','x','x',1);\n"
       + "SELECT 'BLOCKED:EXISTING_TARGET_DRIFT';\n"
       + "SELECT task004_writer_fence.assert_active_claim('x','x','x','x','x',1);\n"
       + "DO $reconcile$ BEGIN NULL; END $reconcile$;\n"
       + "SELECT task004_writer_fence.assert_active_claim('x','x','x','x','x',1);\n"
       + "DO $complete$ BEGIN NULL; END $complete$;\n"
       + "COMMIT;\n"
       + "SELECT 'REAL_NEW_ONLY_BUSINESS_COMMIT_AND_COMPLETED=PASS';\n")


class SecondCommitGuard(unittest.TestCase):
    def test_authorized_exact_identity_one_commit_and_fencing(self):
        with (patch.object(app,"verified_plan",return_value=good_plan()),
              patch.object(app,"assert_dynamic_handoff"),
              patch.object(app,"generate_dynamic_commit_sql",return_value=skeleton()) as render):
            sql=app.render_authorized_one_time_commit(
                {"plan":good_plan()},[{}]*70,[{}]*11487,"a"*48)
            render.assert_called_once()
            lines=[x.strip() for x in sql.splitlines()]
            self.assertEqual(lines.count("BEGIN;"),1)
            self.assertEqual(lines.count("COMMIT;"),1)
            self.assertEqual(lines.count("ROLLBACK;"),0)
            self.assertEqual(sql.count("SELECT task004_writer_fence.assert_active_claim("),3)
            self.assertLess(sql.index("DO $reconcile$"),sql.index("DO $complete$"))
            self.assertLess(sql.index("DO $complete$"),sql.index("\nCOMMIT;\n"))

    def test_missing_or_wrong_batch_never_renders_commit(self):
        cases=[{"batch_id":"synthea-new-only-other"},
               {"batch_id":"synthea-new-only-gh-38497355290"},
               {"manifest_sha256":"0"*64}]
        for change in cases:
            plan=good_plan()|change
            with (self.subTest(change=change),
                  patch.object(app,"verified_plan",return_value=plan),
                  patch.object(app,"assert_dynamic_handoff"),
                  patch.object(app,"generate_dynamic_commit_sql") as render):
                with self.assertRaisesRegex(ValueError,"EXACT_IDENTITY"):
                    app.render_authorized_one_time_commit(
                        {"plan":plan},[{}]*70,[{}]*11487,"a"*48)
                render.assert_not_called()
        for ppl,visit in [(69,11487),(70,11486),(70,0)]:
            with (self.subTest(ppl=ppl,visit=visit),
                  patch.object(app,"verified_plan",return_value=good_plan()),
                  patch.object(app,"assert_dynamic_handoff"),
                  patch.object(app,"generate_dynamic_commit_sql") as render):
                with self.assertRaisesRegex(ValueError,"EXACT_IDENTITY"):
                    app.render_authorized_one_time_commit(
                        {"plan":good_plan()},[{}]*ppl,[{}]*visit,"a"*48)
                render.assert_not_called()

    def test_malformed_renderer_refused(self):
        bad_sqls=[
            skeleton().replace("COMMIT;","COMMIT;\nCOMMIT;"),
            skeleton().replace("\nCOMMIT;\n","\nROLLBACK;\n"),
            skeleton().replace("DO $reconcile$","DO $other$"),
            skeleton().replace("DO $complete$","DO $other$"),
            skeleton().replace("BLOCKED:EXISTING_TARGET_DRIFT","SAFETY_ERASED"),
            skeleton().replace("SELECT task004_writer_fence.assert_active_claim('x','x','x','x','x',1);\n","",1),
        ]
        for sql in bad_sqls:
            with (self.subTest(sql=sql[-70:]),
                  patch.object(app,"verified_plan",return_value=good_plan()),
                  patch.object(app,"assert_dynamic_handoff"),
                  patch.object(app,"generate_dynamic_commit_sql",return_value=sql)):
                with self.assertRaisesRegex(ValueError,"UNSAFE_SQL_TRANSACTION"):
                    app.render_authorized_one_time_commit(
                        {"plan":good_plan()},[{}]*70,[{}]*11487,"a"*48)

    def test_script_never_calls_live_dml_or_changes_airflow(self):
        src=(ROOT/"apps/omop_writer/commit_second_new_only_once.py").read_text()
        self.assertIn("proof=audit(handoff)",src)
        self.assertIn("people,visits=s3_rows(ctx)",src)
        self.assertIn("generate_dynamic_commit_sql",src)
        self.assertNotIn("subprocess",src)
        self.assertNotIn("cur.execute(",src)
        self.assertNotIn("CLAIM_ENABLE=YES",src)
        self.assertIn("SECOND_COMMIT_SQL_READY_NOT_YET_EXECUTED=PASS",src)


if __name__=="__main__":
    unittest.main()
