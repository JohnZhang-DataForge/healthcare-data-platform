"""Structural regression: the sole maintained HL7 dbt Core project is azure-fabric/dbt.

This check is local source inspection only, with no GitHub/Azure/K8s access or I/O.
It protects the caller path while legacy dbt SQL/config stays frozen in Git.
"""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[5]
PROJECT = ROOT / "azure-fabric/dbt/hl7-canonical"
LEGACY = ROOT / "local-data-platform/spark/apps/hl7"
WORKFLOWS = (
    ".github/workflows/hl7-local-delta-dbt-offline.yml",
    ".github/workflows/hl7-dbt-canonical-candidate-offline.yml",
)


class GovernedHL7DbtConsumer(unittest.TestCase):
    def test_one_governed_project_and_compatible_candidate_schema(self):
        self.assertIn("name: hl7_canonical\n", (PROJECT / "dbt_project.yml").read_text())
        profile = (PROJECT / "profiles/local/profiles.yml").read_text()
        self.assertIn("schema: hl7_candidate\n", profile)
        self.assertIn("lakehouse: hl7_candidate\n", profile)
        self.assertNotIn("hl7_candidate_p3", profile)
        self.assertIn('CANDIDATE = "hl7_candidate"', (
            ROOT / ".github/quality/tests/data-platform/hl7/check_new_dbt_candidate.py"
        ).read_text())
        self.assertFalse((LEGACY / "dbt_project.yml").exists())  # retired from live tree
        self.assertFalse((LEGACY / "models").exists())
        self.assertFalse((LEGACY / "profiles").exists())

    def test_all_active_hl7_dbt_workflows_use_new_project(self):
        for name in WORKFLOWS:
            with self.subTest(workflow=name):
                text = (ROOT / name).read_text()
                self.assertIn("working-directory: azure-fabric/dbt/hl7-canonical", text)
                self.assertIn('export DBT_PROFILES_DIR="$PWD/profiles/local"', text)
                self.assertIn("dbt compile", text)
                self.assertIn("dbt run", text)
                self.assertIn("dbt test", text)
                self.assertNotIn(
                    "working-directory: local-data-platform/spark/apps/hl7", text)
                self.assertNotIn("hl7_canonical_candidate", text)

    def test_legacy_parser_and_delta_writer_remain_authoritative(self):
        old_workflow = (ROOT / WORKFLOWS[0]).read_text()
        self.assertIn('local-data-platform/spark/apps/hl7/write_staging_delta.py',
                      old_workflow)
        self.assertIn('azure-fabric/dbt/hl7-canonical/requirements-local.txt',
                      old_workflow)
        self.assertIn("check_local_candidate.py", old_workflow)
        for name in ("parse_oie_v2.py", "landing_intake.py", "write_staging_delta.py"):
            self.assertTrue((LEGACY / name).is_file())

    def test_requirements_are_split_without_duplication(self):
        local_pins = (LEGACY / "requirements-local.txt").read_text()
        governed = (PROJECT / "requirements-local.txt").read_text()
        self.assertIn("hl7apy==1.3.5", local_pins)
        self.assertIn("pyspark==3.5.5", local_pins)
        self.assertIn("delta-spark==3.3.2", local_pins)
        self.assertNotIn("dbt-fabricspark", local_pins)
        self.assertIn(
            "-r ../../../local-data-platform/spark/apps/hl7/requirements-local.txt",
            governed)
        self.assertIn("dbt-fabricspark[spark]==1.13.2", governed)

    def test_patient_encounter_contracts_not_copied(self):
        for entity, count in (("patient", 18), ("encounter", 27)):
            file = ROOT / f"local-data-platform/spark/contracts/canonical/{entity}-v1.json"
            self.assertEqual(len(json.loads(file.read_text())["fields"]), count)
        self.assertFalse(list(PROJECT.rglob("*patient-v1.json")))
        self.assertFalse(list(PROJECT.rglob("*encounter-v1.json")))


if __name__ == "__main__":
    unittest.main()
