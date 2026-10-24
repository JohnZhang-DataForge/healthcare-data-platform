"""Offline contracts for authentic Airflow Task -> Spark application parent IDs."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = (Path(__file__).resolve().parents[2] / "spark/common/openlineage_parent_context.py")
SPEC = importlib.util.spec_from_file_location("openlineage_parent_context", MODULE)
parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parent)
BASE = """kind: SparkApplication
spec:
  sparkConf:
    spark.openlineage.namespace: healthcare-platform-spark-business
    spark.openlineage.transport.url: http://marquez.dw-marquez.svc.cluster.local
    spark.openlineage.appName: task004_person_20261024t192638z_9
    spark.hadoop.fs.s3a.endpoint: http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333
"""
RUN = "01a16f63-7aa4-7a60-9ad9-46d8c4064617"


def context(task="spark_patient", run=RUN):
    return {
        "OPENLINEAGE_PARENT_REQUIRED": "YES",
        "OPENLINEAGE_PARENT_NAMESPACE": "healthcare-platform-airflow",
        "OPENLINEAGE_PARENT_JOB": "new_only_omop_consumer." + task,
        "OPENLINEAGE_PARENT_RUN_ID": run,
    }


class ParentInjectionTests(unittest.TestCase):
    def test_injects_exact_airflow_uuid_with_other_spark_conf_unchanged(self):
        for task in sorted(parent.ALLOWED_TASKS):
            with self.subTest(task=task):
                out, status = parent.render(BASE, task_id=task, env=context(task))
                self.assertEqual(status, "REAL_AIRFLOW_PARENT_INJECTED")
                self.assertIn("spark.openlineage.parentJobNamespace: healthcare-platform-airflow", out)
                self.assertIn("spark.openlineage.parentJobName: new_only_omop_consumer."+task, out)
                self.assertIn("spark.openlineage.parentRunId: "+RUN, out)
                self.assertEqual(out.count("spark.openlineage.parentRunId:"), 1)
                self.assertIn("spark.hadoop.fs.s3a.endpoint:", out)
                self.assertEqual(out.split("    spark.hadoop.fs.s3a.endpoint:")[1],
                                 BASE.split("    spark.hadoop.fs.s3a.endpoint:")[1])

    def test_legacy_without_optin_never_changes_manifest(self):
        out, status = parent.render(BASE, task_id="spark_patient", env={})
        self.assertEqual(out, BASE)
        self.assertEqual(status, "LEGACY_UNCHANGED")

    def test_partial_optin_always_fails_closed(self):
        for fields in (
            {"OPENLINEAGE_PARENT_REQUIRED": "YES"},
            {"OPENLINEAGE_PARENT_JOB": "new_only_omop_consumer.spark_patient"},
            {**context(), "OPENLINEAGE_PARENT_REQUIRED": ""},
        ):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError, "INCOMPLETE_PARENT"):
                    parent.render(BASE, task_id="spark_patient", env=fields)

    def test_forged_dag_namespace_task_and_runid_rejected(self):
        for changes, pattern in (
            ({"OPENLINEAGE_PARENT_NAMESPACE": "evil"}, "UNTRUSTED_PARENT"),
            ({"OPENLINEAGE_PARENT_JOB": "other_dag.spark_patient"}, "UNTRUSTED_PARENT"),
            ({"OPENLINEAGE_PARENT_JOB": "new_only_omop_consumer.spark_encounter"}, "UNTRUSTED_PARENT"),
            ({"OPENLINEAGE_PARENT_RUN_ID": "manual__2026-10-24"}, "INVALID_PARENT"),
            ({"OPENLINEAGE_PARENT_RUN_ID": RUN.upper()}, "NONCANONICAL_PARENT"),
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, pattern):
                    parent.render(BASE, task_id="spark_patient", env={**context(), **changes})

    def test_untrusted_task_endpoint_and_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_AIRFLOW_TASK"):
            parent.render(BASE, task_id="execute_new_only_writer", env=context())
        for candidate, pattern in (
            (BASE.replace("healthcare-platform-spark-business","other"), "SPARK_NAMESPACE"),
            (BASE.replace("http://marquez.dw-marquez.svc.cluster.local",
                          "http://evil.invalid"), "MARQUEZ_ENDPOINT"),
            (BASE+"    spark.openlineage.parentRunId: "+RUN+"\n", "PARENT_ALREADY"),
            (BASE.replace("    spark.openlineage.appName:",
                          "    spark.openlineage.wrong:"), "APP_NAME_ANCHOR"),
        ):
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(ValueError, pattern):
                    parent.render(candidate, task_id="spark_patient", env=context())

    def test_cli_writes_only_valid_rendered_yaml_and_preserves_failed_input(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sparkapplication.yaml"
            source.write_text(BASE)
            with patch.dict(parent.os.environ, context(), clear=True):
                self.assertEqual(parent.main([str(source), "spark_patient"]), 0)
            self.assertIn("parentRunId: "+RUN, source.read_text())
            source.write_text(BASE)
            with patch.dict(parent.os.environ,
                            {**context(), "OPENLINEAGE_PARENT_RUN_ID": "bad"},
                            clear=True):
                self.assertEqual(parent.main([str(source), "spark_patient"]), 2)
            self.assertEqual(source.read_text(), BASE)


if __name__ == "__main__":
    unittest.main()
