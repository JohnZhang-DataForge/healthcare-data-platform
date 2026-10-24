"""Offline regression for actual Marquez API response shapes; never POST events."""
import importlib.util
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "business_lineage", Path(__file__).with_name("verify_business_lineage.py")
)
lineage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lineage)
BATCH = "synthea-new-only-gh-39625216978"


def ds(namespace, name, version):
    return {"datasetVersionId": {
        "namespace": namespace, "name": name, "version": version
    }}


def entry(job, run, state, inputs=(), outputs=(), facets=None):
    return {"job": job, "id": run, "state": state,
            "detail": {"state": state, "facets": facets or {},
                       "inputDatasetVersions": list(inputs),
                       "outputDatasetVersions": list(outputs)}}


def fixture():
    prefix = "source=synthea/source_version=v3.3.0/ingest_date=2026-10-21/batch_id=" + BATCH
    patient_source = ds("s3://health-landing", prefix + "/payload/csv/patients.csv", "src-p")
    visit_source = ds("s3://health-landing", prefix + "/payload/csv/encounters.csv", "src-v")
    patient = ds("s3://health-processing",
                 prefix + "/entity=patient/run_id=person/work/normalized/data", "out-p")
    visit = ds("s3://health-processing",
               prefix + "/entity=encounter/run_id=visit/work/normalized/data", "out-v")
    data = {"roles": {
        "person": [
            entry("person-app", "p-app", "COMPLETED"),
            entry("person-app.20", "p-generic", "RUNNING"),
            entry("person-app.adaptive_spark_plan.normalized_data", "p-out",
                  "COMPLETED", [patient_source], [patient]),
        ],
        "encounter": [
            entry("visit-app", "v-app", "COMPLETED"),
            entry("visit-app.adaptive_spark_plan.normalized_data", "v-out",
                  "COMPLETED", [visit_source], [visit]),
        ],
        "reconcile": [
            entry("reconcile-app", "r-app", "COMPLETED"),
            entry("reconcile-app.map_partitions_parallel_collection", "r-p",
                  "RUNNING", [patient]),
            entry("reconcile-app.map_partitions_parallel_collection", "r-v",
                  "RUNNING", [visit]),
        ],
    }, "airflow": {
        "person": [{"id": "af-p", "state": "COMPLETED"}],
        "encounter": [{"id": "af-v", "state": "COMPLETED"}],
        "reconcile": [{"id": "af-r", "state": "COMPLETED"}],
    }}
    return data


class BusinessLineageTests(TestCase):
    def test_real_case_is_incomplete_despite_application_completed(self):
        report = lineage.evaluate(fixture(), BATCH)
        self.assertTrue(report["person_read_write"])
        self.assertTrue(report["encounter_read_write"])
        self.assertTrue(report["reconcile_has_exact_two_produced_versions"])
        self.assertFalse(report["reconcile_input_runs_terminal"])
        self.assertEqual(report["business_dataset_gate"], "INCOMPLETE")
        self.assertEqual(len(report["reconcile_input_run_states"]), 2)
        self.assertEqual(report["airflow_spark_direct_parent"], "UNPROVEN")

    def test_terminal_child_events_pass_without_output_from_reconcile(self):
        data = fixture()
        for row in data["roles"]["reconcile"]:
            row["state"] = row["detail"]["state"] = "COMPLETED"
        report = lineage.evaluate(data, BATCH)
        self.assertEqual(report["business_dataset_gate"], "PASS")
        self.assertTrue(report["reconcile_input_runs_terminal"])

    def test_different_batch_output_fails_closed(self):
        report = lineage.evaluate(fixture(), "synthea-new-only-gh-OTHER")
        self.assertEqual(report["business_dataset_gate"], "INCOMPLETE")
        self.assertFalse(report["person_read_write"])

    def test_no_data_from_top_level_job_is_not_a_failure(self):
        data = fixture()
        self.assertEqual(data["roles"]["person"][0]["detail"]["inputDatasetVersions"], [])
        self.assertTrue(lineage.evaluate(data, BATCH)["person_read_write"])

    def test_partial_reconcile_input_fails(self):
        data = fixture()
        data["roles"]["reconcile"].pop()
        report = lineage.evaluate(data, BATCH)
        self.assertFalse(report["reconcile_has_exact_two_produced_versions"])

    def test_dataset_version_mismatch_fails(self):
        data = fixture()
        data["roles"]["reconcile"][1]["detail"]["inputDatasetVersions"][0][
            "datasetVersionId"]["version"] = "wrong-version"
        self.assertFalse(lineage.evaluate(data, BATCH)[
            "reconcile_has_exact_two_produced_versions"])

    def test_only_matching_real_airflow_run_proves_direct_parent(self):
        data = fixture()
        parent = {"parent": {
            "job": {"namespace": lineage.AIRFLOW_NS,
                    "name": "new_only_omop_consumer.spark_patient"},
            "run": {"runId": "af-p"}}}
        data["roles"]["person"][2]["detail"]["facets"] = parent
        self.assertEqual(lineage.evaluate(data, BATCH)[
            "airflow_spark_direct_parent"], "VERIFIED")
        data["roles"]["person"][2]["detail"]["facets"]["parent"][
            "run"]["runId"] = "not-the-real-run"
        self.assertEqual(lineage.evaluate(data, BATCH)[
            "airflow_spark_direct_parent"], "UNPROVEN")

    def test_no_cross_host_http_or_non_get(self):
        with patch.object(lineage.urllib.request, "urlopen") as call:
            with self.assertRaisesRegex(ValueError, "OFF_HOST"):
                lineage.get_json("https://example.invalid/api/v1/jobs")
            with self.assertRaisesRegex(ValueError, "NON_API"):
                lineage.get_json("/admin/reset")
            call.assert_not_called()

    def test_exact_batch_identity(self):
        patient = lineage.select_writes(
            fixture()["roles"]["person"], BATCH, "patient", "patients.csv")
        self.assertIsNotNone(patient)
        self.assertIn("entity=patient", patient[1])


if __name__ == "__main__":
    main()
