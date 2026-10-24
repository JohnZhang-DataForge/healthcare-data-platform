"""P4 offline, negative and release-scope contracts; never import Spark or call K8s."""
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[3]
MANIFESTS = {
    "person": ROOT / "local-data-platform/spark/manifests/task002/person-canonical-adapter.yaml.tpl",
    "visit": ROOT / "local-data-platform/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl",
    "reconcile": ROOT / "local-data-platform/spark/manifests/task004/person-visit-reconciliation.yaml.tpl",
}
NAMESPACE = "healthcare-platform-spark-business"
LISTENER = "io.openlineage.spark.agent.OpenLineageSparkListener"
PACKAGE = "io.openlineage:openlineage-spark_2.12:1.47.1"
ENDPOINT = "http://marquez.dw-marquez.svc.cluster.local"
IMAGE_DOCKERFILE = ROOT / "local-data-platform/images/landing-processing-runtime/Dockerfile"


def assert_listener_contract(data, role):
    if data["kind"] != "SparkApplication":
        raise ValueError("P4_WRONG_KIND")
    spec = data["spec"]
    if spec["mainApplicationFile"] != {
        "person": "local:///opt/spark/app/synthea_patient_adapter.py",
        "visit": "local:///opt/spark/app/synthea_encounter_adapter.py",
        "reconcile": "local:///opt/spark/app/reconcile_person_visit.py",
    }[role]:
        raise ValueError("P4_SPARK_ALGORITHM_PATH_CHANGED")
    if spec["image"] != "spark:3.5.7-python3":
        raise ValueError("P4_SPARK_IMAGE_CHANGED")
    if spec["restartPolicy"] != {"type": "Never"}:
        raise ValueError("P4_RESTART_CONTRACT_CHANGED")
    if spec["deps"]["packages"].count(PACKAGE) != 1:
        raise ValueError("P4_LISTENER_PACKAGE")
    config = spec["sparkConf"]
    expected = {
        "spark.extraListeners": LISTENER,
        "spark.openlineage.transport.type": "http",
        "spark.openlineage.transport.url": ENDPOINT,
        "spark.openlineage.transport.endpoint": "/api/v1/lineage",
        "spark.openlineage.transport.timeoutInMillis": "5000",
        "spark.openlineage.namespace": NAMESPACE,
        "spark.openlineage.appName": "__APP_NAME__",
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError("P4_LISTENER_CONFIG_" + key)
    if set(k for k in config if k.startswith("spark.openlineage.")) != (
        set(expected) - {"spark.extraListeners"}
    ):
        raise ValueError("P4_UNREVIEWED_LISTENER_CONFIGURATION")
    if spec["driver"]["serviceAccount"] != "spark-job":
        raise ValueError("P4_SA_CHANGED")
    if spec["driver"]["volumeMounts"] != spec["executor"]["volumeMounts"]:
        raise ValueError("P4_SOURCE_MOUNTS_CHANGED")
    if spec["volumes"][0]["configMap"]["name"] != "__CONFIGMAP_NAME__":
        raise ValueError("P4_CONFIGMAP_SOURCE_CHANGED")
    if role == "person":
        if "org.apache.hadoop:hadoop-aws:3.3.4" not in spec["deps"]["packages"]:
            raise ValueError("P4_PERSON_HADOOP_AWS_REMOVED")
    else:
        if not any("hadoop-aws-3.3.4.jar" in v for v in spec["deps"]["jars"]):
            raise ValueError("P4_LEGACY_HADOOP_JARS_REMOVED")
    args = spec["arguments"]
    if role == "person" and not (
        "--processing-data-uri" in args and "--manifest-uri" in args
    ):
        raise ValueError("P4_PERSON_IO_CONTRACT")
    if role == "visit" and not (
        "--input-uri" in args and "--output-data-uri" in args
    ):
        raise ValueError("P4_VISIT_IO_CONTRACT")
    if role == "reconcile" and not (
        "--patient-uri" in args and "--encounter-uri" in args and
        not any("output" in k for k in args)
    ):
        raise ValueError("P4_RECONCILE_ONLY_READS")
    return spec


class PortalP4BusinessListenerTests(unittest.TestCase):
    def test_all_three_business_spark_jobs_have_real_listener(self):
        for role, path in MANIFESTS.items():
            with self.subTest(role=role):
                spec = assert_listener_contract(yaml.safe_load(path.read_text()), role)
                self.assertEqual(spec["sparkVersion"], "3.5.7")
                self.assertEqual(spec["imagePullPolicy"], "IfNotPresent")
                self.assertTrue(spec["driver"]["envFrom"])
                self.assertTrue(spec["executor"]["envFrom"])
                self.assertEqual(spec["sparkConf"]["spark.hadoop.fs.s3a.endpoint"],
                                 "http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333")

    def test_fail_closed_if_observability_is_removed_or_redirected(self):
        for role, path in MANIFESTS.items():
            original = yaml.safe_load(path.read_text())
            for field, value in (
                ("spark.extraListeners", "other.Listener"),
                ("spark.openlineage.transport.url", "http://untrusted.invalid"),
                ("spark.openlineage.namespace", "default"),
                ("spark.openlineage.appName", "unknown"),
            ):
                import copy
                malformed = copy.deepcopy(original)
                malformed["spec"]["sparkConf"][field] = value
                with self.subTest(role=role, field=field):
                    with self.assertRaisesRegex(ValueError, "P4_LISTENER_CONFIG_"):
                        assert_listener_contract(malformed, role)
            original["spec"]["deps"]["packages"].remove(PACKAGE)
            with self.subTest(role=role, field="missing-package"):
                with self.assertRaisesRegex(ValueError, "P4_LISTENER_PACKAGE"):
                    assert_listener_contract(original, role)

    def test_only_v2_child_overlay_needs_rebuild(self):
        content = IMAGE_DOCKERFILE.read_text()
        for path in MANIFESTS.values():
            self.assertIn(path.name, content)
            # A copied relative source must be a real Docker context file.
            relative = path.relative_to(ROOT / "local-data-platform").as_posix()
            self.assertIn(relative, content)
        self.assertIn("ARG BASE_IMAGE=ghcr.io/", content)
        self.assertIn("USER 10001:10001", content)
        dag = (ROOT / "local-data-platform/airflow/dags/new_only_omop_consumer.py").read_text()
        factory = (ROOT / "local-data-platform/airflow/dags/landing_spark_processing.py").read_text()
        self.assertIn("image_override=NEW_ONLY_PROCESSING_IMAGE", dag)
        self.assertIn(":latest", factory)
        self.assertIn('image_pull_policy="Always"', factory)
        self.assertIn('"spark_reconcile"', dag)
        self.assertIn("writer_commit", dag)
        smoke = (ROOT / ".github/quality/scripts/local_dp_single_image_plan.py").read_text()
        self.assertIn("healthcare-platform-spark-business", smoke)
        self.assertIn("spark.extraListeners: io.openlineage", smoke)

    def test_no_fake_business_completion_criteria_in_templates(self):
        for path in MANIFESTS.values():
            raw = path.read_text()
            for bad in ("parentRunId", "WRITER_COMMITTED", "PG_READBACK_VERIFIED",
                        "TASK004_WRITER_DEPLOY_ENABLE", "POSTGRESQL_COMMIT"):
                with self.subTest(path=path.name, bad=bad):
                    self.assertNotIn(bad, raw)


if __name__ == "__main__":
    unittest.main()
