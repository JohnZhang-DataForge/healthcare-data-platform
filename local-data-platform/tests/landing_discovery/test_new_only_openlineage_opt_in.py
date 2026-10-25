"""Offline contract: opt in only the existing NEW_ONLY DAG to OpenLineage.

No Airflow import, scheduler connection, DAG execution, S3, PG or Kubernetes.
The deployed OpenLineage Provider/transport must be checked separately.
"""
import ast
from pathlib import Path
import unittest


DAGS = Path(__file__).resolve().parents[2] / "airflow" / "dags"
BUSINESS = DAGS / "new_only_omop_consumer.py"
PROBE = DAGS / "platform_portal_openlineage_probe.py"
DISCOVERY = DAGS / "landing_batch_discovery.py"

EXPECTED_TASK_IDS = {
    "scan_ready_manifests",
    "select_verified_new_only_batch",
    "inspect_claim_readonly",
    "route_new_only_status",
    "already_completed_no_replay",
    "unclaimed_batch_hold",
    "spark_patient",
    "spark_encounter",
    "spark_reconcile",
    "prepare_writer_handoff",
    "writer_awaits_live_preflight",
    "route_writer_authorization",
    "execute_new_only_writer",
    "writer_committed_verified",
}


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _lineage_wrapped_dags(tree):
    """Find only DAG constructors directly wrapped in selective enable_lineage."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            wrapper = item.context_expr
            if not isinstance(wrapper, ast.Call) or not isinstance(wrapper.func, ast.Name):
                continue
            if wrapper.func.id != "enable_lineage":
                continue
            if len(wrapper.args) != 1 or not isinstance(wrapper.args[0], ast.Call):
                continue
            dag = wrapper.args[0]
            if isinstance(dag.func, ast.Name) and dag.func.id == "DAG":
                found.append((item, dag))
    return found


def _keyword(call, name):
    matches = [k.value for k in call.keywords if k.arg == name]
    if len(matches) != 1:
        raise AssertionError(f"missing or duplicate DAG keyword: {name}")
    return ast.literal_eval(matches[0])


class BusinessOpenLineageOptInContract(unittest.TestCase):
    def test_business_dag_explicitly_uses_a3_selective_opt_in(self):
        tree = _tree(BUSINESS)
        imports = [
            n for n in tree.body
            if isinstance(n, ast.ImportFrom)
            and n.module == "airflow.providers.openlineage.utils.selective_enable"
        ]
        self.assertEqual(len(imports), 1)
        self.assertEqual([n.name for n in imports[0].names], ["enable_lineage"])
        wrapped = _lineage_wrapped_dags(tree)
        self.assertEqual(len(wrapped), 1)
        item, dag = wrapped[0]
        self.assertIsInstance(item.optional_vars, ast.Name)
        self.assertEqual(item.optional_vars.id, "dag")
        self.assertEqual(_keyword(dag, "dag_id"), "new_only_omop_consumer")
        self.assertIsNone(_keyword(dag, "schedule"))
        self.assertFalse(_keyword(dag, "catchup"))
        self.assertEqual(_keyword(dag, "max_active_runs"), 1)
        self.assertTrue(_keyword(dag, "is_paused_upon_creation"))
        self.assertEqual(_keyword(dag, "default_args"), {"retries": 0})

    def test_existing_business_task_ids_unchanged(self):
        tree = _tree(BUSINESS)
        assigned = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            target_names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            call = node.value
            func = call.func.id if isinstance(call.func, ast.Name) else None
            if func in {"KubernetesPodOperator", "PythonOperator",
                        "BranchPythonOperator", "EmptyOperator"}:
                kw = [k.value for k in call.keywords if k.arg == "task_id"]
                self.assertEqual(len(kw), 1)
                self.assertEqual(len(target_names), 1)
                self.assertEqual(ast.literal_eval(kw[0]), next(iter(target_names)))
                assigned |= target_names
            if func == "make_processing_pod":
                self.assertEqual(len(target_names), 1)
                self.assertEqual(ast.literal_eval(call.args[0]), next(iter(target_names)))
                assigned |= target_names
        self.assertEqual(assigned, EXPECTED_TASK_IDS)

    def test_unrelated_scheduled_dag_stays_outside_opt_in(self):
        tree = _tree(DISCOVERY)
        self.assertFalse(_lineage_wrapped_dags(tree))
        imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertNotIn(
            "airflow.providers.openlineage.utils.selective_enable",
            [n.module for n in imports],
        )
        self.assertIn('dag_id="landing_batch_discovery"',
                      DISCOVERY.read_text(encoding="utf-8"))

    def test_all_shipped_dag_modules_have_exact_selective_opt_in_allowlist(self):
        """Fail if any other shipped DAG/helper enables Lineage silently.

        This inventories source AST only. It does not run Airflow tasks or
        prove the deployed Provider/transport or live negative event behavior.
        """
        approved = {"new_only_omop_consumer.py",
                    "platform_portal_openlineage_probe.py"}
        files = sorted(DAGS.glob("*.py"))
        self.assertGreaterEqual(len(files), 4)
        self.assertTrue(approved.issubset({p.name for p in files}))
        for path in files:
            with self.subTest(path=path.name):
                tree = _tree(path)
                calls = [
                    node for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and (
                        (isinstance(node.func, ast.Name)
                         and node.func.id == "enable_lineage") or
                        (isinstance(node.func, ast.Attribute)
                         and node.func.attr == "enable_lineage"))
                ]
                imported_selective = [
                    node for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom) and
                    node.module == (
                        "airflow.providers.openlineage.utils.selective_enable")
                ]
                wrappers = _lineage_wrapped_dags(tree)
                if path.name in approved:
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(len(imported_selective), 1)
                    self.assertEqual(len(wrappers), 1)
                else:
                    self.assertEqual(calls, [], "unexpected DAG opt-in")
                    self.assertEqual(imported_selective, [],
                                     "unrelated module imports selective opt-in")
                    self.assertEqual(wrappers, [])

    def test_a3_probe_remains_opted_in(self):
        self.assertEqual(len(_lineage_wrapped_dags(_tree(PROBE))), 1)

    def test_xcom_claim_and_writer_guards_are_preserved(self):
        source = BUSINESS.read_text(encoding="utf-8")
        for part in (
            "select_verified_new_only",
            "route_claim_status",
            "route_new_only_writer_commit",
            "prepare_new_only_writer_handoff",
            "do_xcom_push=True",
            "do_xcom_push=False",
            "default_transaction_read_only=on",
            "TASK004_WRITER_DEPLOY_ENABLE",
            "TASK004_WRITER_AIRFLOW_COMMIT_SELECTION",
            'task_id="execute_new_only_writer"',
            "schedule=None",
        ):
            with self.subTest(part=part):
                self.assertIn(part, source)
        self.assertNotIn("AIRFLOW__OPENLINEAGE__SELECTIVE_ENABLE=False", source)
        self.assertNotIn("airflow dags trigger", source)


if __name__ == "__main__":
    unittest.main()
