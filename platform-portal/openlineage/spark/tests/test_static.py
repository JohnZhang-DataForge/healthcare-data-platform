"""A4 task-1 unit tests. No Spark, S3, GitHub Action, Kubernetes or network."""
import ast
import importlib.util
import io
import re
import sys
import unittest
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portal_a4_render", HERE / "render.py")
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class PortalA4StaticTests(unittest.TestCase):
    def setUp(self):
        self.raw = renderer.render("probe01")
        self.docs = list(yaml.safe_load_all(io.StringIO(self.raw)))
        self.cm, self.app = self.docs
        self.spec = self.app["spec"]

    def test_namespaced_and_names_unique_per_run(self):
        self.assertEqual([d["kind"] for d in self.docs], ["ConfigMap", "SparkApplication"])
        for doc in self.docs:
            self.assertEqual(doc["metadata"]["namespace"], "dw-spark")
        self.assertEqual(self.app["metadata"]["name"], "portal-a4-probe01")
        self.assertEqual(self.cm["metadata"]["name"], "portal-a4-probe01-source")
        self.assertNotIn("portal-a4-probe01", renderer.render("probe02"))

    def test_token_is_strict_and_cannot_inject_yaml(self):
        for bad in ["X", "a", "../etc", "foo\nkind: Pod", "UPPERCASE", "a" * 40, "foo_", "-begin", "end-", "with.dot"]:
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    renderer.render(bad)

    def test_readonly_spark_operator_scope_and_budgets(self):
        self.assertEqual(self.app["apiVersion"], "sparkoperator.k8s.io/v1beta2")
        self.assertEqual(self.spec["type"], "Python")
        self.assertEqual(self.spec["mode"], "cluster")
        self.assertEqual(self.spec["image"], "spark:3.5.7-python3")
        self.assertEqual(self.spec["sparkVersion"], "3.5.7")
        self.assertEqual(self.spec["restartPolicy"]["type"], "Never")
        self.assertEqual(self.spec["executor"]["instances"], 1)
        self.assertEqual(self.spec["driver"]["cores"], 1)
        self.assertEqual(self.spec["executor"]["cores"], 1)
        self.assertEqual(self.spec["driver"]["memory"], "1g")
        self.assertEqual(self.spec["executor"]["memory"], "1g")
        self.assertEqual(self.spec["driver"]["serviceAccount"], "spark-job")
        for role in ("driver", "executor"):
            self.assertEqual(self.spec[role]["nodeSelector"], {"workload": "platform"})
            self.assertEqual(self.spec[role]["volumeMounts"][0]["readOnly"], True)
            self.assertNotIn("envFrom", self.spec[role])

    def test_openlineage_is_per_job_not_global(self):
        c = self.spec["sparkConf"]
        self.assertEqual(self.spec["deps"]["packages"], [
            "io.openlineage:openlineage-spark_2.12:1.47.1"])
        self.assertEqual(c["spark.extraListeners"],
                         "io.openlineage.spark.agent.OpenLineageSparkListener")
        self.assertEqual(c["spark.openlineage.transport.type"], "http")
        self.assertEqual(c["spark.openlineage.transport.url"],
                         "http://marquez.dw-marquez.svc.cluster.local")
        self.assertEqual(c["spark.openlineage.transport.endpoint"], "/api/v1/lineage")
        self.assertEqual(c["spark.openlineage.namespace"],
                         "healthcare-platform-spark-probe")
        self.assertNotIn("parentRunId", " ".join(c))

    def test_only_mounted_fixture_not_s3_or_omop(self):
        self.assertEqual(self.spec["mainApplicationFile"],
                         "local:///opt/spark/portal-a4/probe.py")
        self.assertEqual(self.spec["arguments"],
                         ["--run-token", "probe01", "--input-uri",
                          "file:///opt/spark/portal-a4/input.csv"])
        self.assertEqual(self.spec["volumes"][0]["configMap"]["name"],
                         self.cm["metadata"]["name"])
        self.assertNotIn("Secret", self.raw)
        self.assertNotIn("s3a://", self.raw)
        self.assertNotIn("health-processing", self.raw)
        self.assertNotIn("cdm.", self.raw)
        self.assertNotIn("kubectl", self.raw)
        self.assertEqual(self.cm["data"]["input.csv"].count("\n"), 4)
        compile(self.cm["data"]["probe.py"], "<rendered probe.py>", "exec")
        ast.parse((HERE / "probe.py").read_text())

    def test_python_fails_closed_on_unknown_inputs_without_spark(self):
        spec = importlib.util.spec_from_file_location("portal_a4_probe", HERE / "probe.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(SystemExit):
            module.parse_args(["--run-token", "probe01", "--input-uri", "s3a://data"])
        with self.assertRaises(SystemExit):
            module.parse_args(["--run-token", "invalid/../", "--input-uri",
                               "file:///opt/spark/portal-a4/input.csv"])
        args = module.parse_args(["--run-token", "probe01", "--input-uri",
                                  "file:///opt/spark/portal-a4/input.csv"])
        self.assertEqual(args.run_token, "probe01")


if __name__ == "__main__":
    unittest.main()
