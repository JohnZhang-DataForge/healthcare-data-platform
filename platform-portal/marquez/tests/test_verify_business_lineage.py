"""Offline regression for actual Marquez API response shapes; never POST events."""
import importlib.util
import copy
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
        data["roles"]["reconcile"][1]["detail"]["inputDatasetVersions"] = copy.deepcopy(
            data["roles"]["reconcile"][1]["detail"]["inputDatasetVersions"]
        )
        data["roles"]["reconcile"][1]["detail"]["inputDatasetVersions"][0][
            "datasetVersionId"]["version"] = "wrong-version"
        self.assertFalse(lineage.evaluate(data, BATCH)[
            "reconcile_has_exact_two_produced_versions"])

    def test_only_all_matching_airflow_task_runs_prove_direct_parent(self):
        data = fixture()
        for role, task, run in (
            ("person", "spark_patient", "af-p"),
            ("encounter", "spark_encounter", "af-v"),
            ("reconcile", "spark_reconcile", "af-r"),
        ):
            data["roles"][role][0]["detail"]["facets"] = {"parent": {
                "job": {"namespace": lineage.AIRFLOW_NS,
                        "name": "new_only_omop_consumer." + task},
                "run": {"runId": run},
            }}
        self.assertEqual(lineage.evaluate(data, BATCH)[
            "airflow_spark_direct_parent"], "VERIFIED")
        data["roles"]["person"][0]["detail"]["facets"]["parent"][
            "run"]["runId"] = "not-the-real-run"
        self.assertEqual(lineage.evaluate(data, BATCH)[
            "airflow_spark_direct_parent"], "UNPROVEN")

    def test_child_parent_spark_does_not_impersonate_airflow_parent(self):
        data = fixture()
        app_runs = {"person": "p-app", "encounter": "v-app",
                    "reconcile": "r-app"}
        for role, app in (("person", "person-app"),
                          ("encounter", "visit-app"),
                          ("reconcile", "reconcile-app")):
            for row in data["roles"][role]:
                if row["job"] == app:
                    continue
                if (row["detail"]["inputDatasetVersions"]
                        or row["detail"]["outputDatasetVersions"]):
                    row["detail"]["facets"] = {"parent": {
                        "job": {"namespace": lineage.SPARK_NS, "name": app},
                        "run": {"runId": app_runs[role]},
                    }}
        report = lineage.evaluate(data, BATCH)
        for role in lineage.ROLES:
            self.assertEqual(report["spark_hierarchy"][role][
                "spark_action_application_parent"], "VERIFIED")
        self.assertEqual(report["airflow_spark_direct_parent"], "UNPROVEN")
        self.assertEqual(report["spark_hierarchy"]["reconcile"][
            "running_children_after_application_completed"], 2)
        self.assertEqual(report["spark_hierarchy"]["reconcile"][
            "action_terminal_gap"], "OBSERVED")

    def test_wrong_spark_application_parent_is_not_verified(self):
        data = fixture()
        for e in data["roles"]["person"]:
            if e["detail"]["inputDatasetVersions"]:
                e["detail"]["facets"] = {"parent": {
                    "job": {"namespace": lineage.SPARK_NS,
                            "name": "other-application"},
                    "run": {"runId": "p-app"},
                }}
        report = lineage.evaluate(data, BATCH)
        self.assertEqual(report["spark_hierarchy"]["person"][
            "spark_action_application_parent"], "UNPROVEN")

    def test_completed_child_without_completed_application_is_not_full_pass(self):
        data = fixture()
        for row in data["roles"]["reconcile"]:
            row["state"] = row["detail"]["state"] = "COMPLETED"
        data["roles"]["person"][0]["state"] = "RUNNING"
        data["roles"]["person"][0]["detail"]["state"] = "RUNNING"
        report = lineage.evaluate(data, BATCH)
        self.assertEqual(report["business_dataset_gate"], "INCOMPLETE")
        self.assertFalse(report["spark_hierarchy"]["person"][
            "application_completed"])

    def test_actual_marquez_qualified_application_is_not_bare_running_placeholder(self):
        data = fixture()
        apps = {"person": "person-app", "encounter": "visit-app",
                "reconcile": "reconcile-app"}
        for role, app in apps.items():
            rows = data["roles"][role]
            rows[0]["job"] = lineage.qualified_application_job(role, app)
            rows[0]["detail"]["facets"] = {"parent": {
                "job": {"namespace": lineage.AIRFLOW_NS,
                        "name": "new_only_omop_consumer." + lineage.AIRFLOW_TASK[role]},
                "run": {"runId": data["airflow"][role][0]["id"]},
            }}
            rows.append(entry(app, "bare-" + role, "RUNNING"))
            for item in rows:
                if item["job"].startswith(app + "."):
                    item["detail"]["facets"] = {"parent": {
                        "job": {"namespace": lineage.SPARK_NS, "name": app},
                        "run": {"runId": rows[0]["id"]},
                    }}
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["airflow_spark_direct_parent"], "VERIFIED")
        self.assertTrue(all(report["spark_hierarchy"][role]["application_completed"]
                            for role in lineage.ROLES))
        self.assertTrue(all(report["spark_hierarchy"][role][
            "spark_action_application_parent"] == "VERIFIED"
            for role in lineage.ROLES))
        self.assertFalse(report["reconcile_input_runs_terminal"])
        self.assertEqual(report["business_dataset_gate"], "INCOMPLETE")
        # Design A accepts real business versions and both parent links
        # while exposing the unsolved physical RDD Action lifecycle.
        self.assertEqual(report["business_edges_gate"], "PASS")
        self.assertEqual(report["p4_design_a_gate"],
                         "PASS_WITH_KNOWN_RDD_LIMITATION")
        self.assertEqual(report["rdd_action_lifecycle"], "START_ONLY_OBSERVED")

    def test_bare_completed_cannot_substitute_missing_qualified_application(self):
        data = fixture()
        apps = {"person": "person-app", "encounter": "visit-app",
                "reconcile": "reconcile-app"}
        # The bare job can be COMPLETED and still is NOT the qualified
        # application Run that carries the Airflow ParentRunFacet.
        for role, app in apps.items():
            data["roles"][role][0]["detail"]["facets"] = {"parent": {
                "job": {"namespace": lineage.AIRFLOW_NS,
                        "name": "new_only_omop_consumer." + lineage.AIRFLOW_TASK[role]},
                "run": {"runId": data["airflow"][role][0]["id"]},
            }}
        report = lineage.evaluate(data, BATCH, apps)
        self.assertFalse(any(report["spark_hierarchy"][role]["application_completed"]
                             for role in lineage.ROLES))
        self.assertEqual(report["airflow_spark_direct_parent"], "UNPROVEN")
        self.assertEqual(report["business_dataset_gate"], "INCOMPLETE")

    def verified_live(self):
        """Build a realistic qualified, fully parent-verified Marquez fixture."""
        data = fixture()
        apps = {"person": "person-app", "encounter": "visit-app",
                "reconcile": "reconcile-app"}
        for role, app in apps.items():
            rows = data["roles"][role]
            app_run = rows[0]
            app_run["job"] = lineage.qualified_application_job(role, app)
            app_run["detail"]["facets"] = {"parent": {
                "job": {"namespace": lineage.AIRFLOW_NS,
                        "name": "new_only_omop_consumer." + lineage.AIRFLOW_TASK[role]},
                "run": {"runId": data["airflow"][role][0]["id"]},
            }}
            for child in rows[1:]:
                child["detail"]["facets"] = {"parent": {
                    "job": {"namespace": lineage.SPARK_NS, "name": app},
                    "run": {"runId": app_run["id"]},
                }}
        return data, apps

    def test_design_a_pass_with_real_versions_and_start_only_children(self):
        data, apps = self.verified_live()
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "PASS")
        self.assertEqual(report["business_dataset_gate"], "INCOMPLETE")
        self.assertEqual(report["p4_design_a_gate"],
                         "PASS_WITH_KNOWN_RDD_LIMITATION")
        self.assertEqual(report["rdd_action_lifecycle"], "START_ONLY_OBSERVED")
        self.assertEqual(report["writer_commit"], "NOT_CHECKED")

    def test_design_a_rejects_wrong_airflow_run_even_if_versions_match(self):
        data, apps = self.verified_live()
        data["roles"]["person"][0]["detail"]["facets"]["parent"]["run"][
            "runId"] = "wrong-airflow-task"
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "INCOMPLETE")
        self.assertEqual(report["p4_design_a_gate"], "INCOMPLETE")

    def test_design_a_rejects_wrong_spark_action_parent(self):
        data, apps = self.verified_live()
        data["roles"]["reconcile"][1]["detail"]["facets"]["parent"]["run"][
            "runId"] = "different-spark-application"
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "INCOMPLETE")

    def test_design_a_rejects_wrong_dataset_version(self):
        data, apps = self.verified_live()
        data["roles"]["reconcile"][1]["detail"]["inputDatasetVersions"][0][
            "datasetVersionId"]["version"] = "stale"
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "INCOMPLETE")
        self.assertFalse(report["reconcile_has_exact_two_produced_versions"])

    def test_design_a_rejects_extra_stale_dataset_version(self):
        data, apps = self.verified_live()
        extra = copy.deepcopy(
            data["roles"]["reconcile"][1]["detail"]["inputDatasetVersions"][0]
        )
        extra["datasetVersionId"]["version"] = "older-version"
        data["roles"]["reconcile"][1]["detail"]["inputDatasetVersions"].append(extra)
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "INCOMPLETE")
        self.assertFalse(report["reconcile_has_exact_two_produced_versions"])

    def test_design_a_rejects_absent_exact_qualified_application(self):
        data, apps = self.verified_live()
        data["roles"]["person"][0]["job"] = "person-app"
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "INCOMPLETE")

    def test_design_a_distinguishes_all_terminal_from_known_limitation(self):
        data, apps = self.verified_live()
        for role in lineage.ROLES:
            for item in data["roles"][role][1:]:
                item["state"] = item["detail"]["state"] = "COMPLETED"
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "PASS")
        self.assertEqual(report["business_dataset_gate"], "PASS")
        self.assertEqual(report["rdd_action_lifecycle"],
                         "NO_START_ONLY_OBSERVED_IN_SNAPSHOT")
        self.assertEqual(report["p4_design_a_gate"], "PASS")

    def test_design_a_rejects_incomplete_application_even_if_child_versions_match(self):
        data, apps = self.verified_live()
        data["roles"]["person"][0]["state"] = "RUNNING"
        report = lineage.evaluate(data, BATCH, apps)
        self.assertEqual(report["business_edges_gate"], "INCOMPLETE")

    def test_cli_uses_business_edges_without_erasing_strict_incomplete(self):
        data, apps = self.verified_live()
        argv = ["--batch-id", BATCH, "--person-app", apps["person"],
                "--encounter-app", apps["encounter"],
                "--reconcile-app", apps["reconcile"]]
        printed = []
        with patch.object(lineage, "snapshot", return_value=data), patch.object(
            lineage, "print", create=True, side_effect=printed.append
        ):
            self.assertEqual(lineage.main(argv), 0)
        import json
        report = json.loads(printed[0])
        self.assertEqual(report["business_edges_gate"], "PASS")
        self.assertEqual(report["business_dataset_gate"], "INCOMPLETE")
        self.assertEqual(report["p4_design_a_gate"],
                         "PASS_WITH_KNOWN_RDD_LIMITATION")
        self.assertEqual(report["pg17_independent_readback"], "NOT_CHECKED")

    def test_cli_does_not_pass_without_real_parent(self):
        data, apps = self.verified_live()
        data["roles"]["reconcile"][0]["detail"]["facets"]["parent"][
            "run"]["runId"] = "fabricated"
        argv = ["--batch-id", BATCH, "--person-app", apps["person"],
                "--encounter-app", apps["encounter"],
                "--reconcile-app", apps["reconcile"]]
        with patch.object(lineage, "snapshot", return_value=data), patch.object(
            lineage, "print", create=True
        ):
            self.assertEqual(lineage.main(argv), 1)

    def test_snapshot_fetches_exact_qualified_application_without_prefix_spoof(self):
        apps = {"person": "person-app", "encounter": "visit-app",
                "reconcile": "reconcile-app"}
        job_names = []
        for role, app in apps.items():
            job_names.extend((app, app + ".write",
                              lineage.qualified_application_job(role, app)))
        job_names.append("other_dag.spark_patient.person-app")
        calls = []
        def fake_runs(ns, name, limit=35):
            calls.append((ns, name))
            return []
        with patch.object(lineage, "list_jobs", return_value=[
                {"name": name} for name in job_names
        ]), patch.object(lineage, "get_runs", side_effect=fake_runs):
            data = lineage.snapshot(apps)
        self.assertEqual(set(data["roles"]), set(lineage.ROLES))
        for role, app in apps.items():
            self.assertIn((lineage.SPARK_NS,
                           lineage.qualified_application_job(role, app)), calls)
        self.assertNotIn((lineage.SPARK_NS,
                          "other_dag.spark_patient.person-app"), calls)

    def test_p5_has_explicit_unverified_durable_writes(self):
        report = lineage.evaluate(fixture(), BATCH)
        self.assertEqual(report["writer_commit"], "NOT_CHECKED")
        self.assertEqual(report["pg17_independent_readback"], "NOT_CHECKED")
        self.assertEqual(report["same_batch_skip"], "NOT_CHECKED")

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
