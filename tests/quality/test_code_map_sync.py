"""Offline tests for component CODE.md source synchronization and ownership."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[2] / "scripts/quality/check_component_code_map.py"
SPEC = importlib.util.spec_from_file_location("code_map_sync", PATH)
assert SPEC and SPEC.loader
policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(policy)


class CodeMapSyncTests(unittest.TestCase):
    def test_guard_source_files_only(self):
        self.assertTrue(policy.is_guarded_source("airflow/dags/condition_consumer.py"))
        self.assertTrue(policy.is_guarded_source("airflow/dags/a.yaml"))
        self.assertFalse(policy.is_guarded_source("airflow/README.md"))
        self.assertFalse(policy.is_guarded_source("spark/apps/condition/code.py"))

    def test_all_dags_must_be_linked(self):
        text = "[one](../../../airflow/dags/one.py)\n[two](../../../airflow/dags/two.py)\n"
        missing, obsolete = policy.validate_dag_file_map(
            text, {"airflow/dags/one.py", "airflow/dags/three.py"})
        self.assertEqual(missing, ["airflow/dags/three.py"])
        self.assertEqual(obsolete, ["airflow/dags/two.py"])

    def test_exact_complete_links_pass(self):
        paths = {"airflow/dags/one.py", "airflow/dags/two.py"}
        content = "\n".join(f"[source](../../../{p})" for p in sorted(paths))
        self.assertEqual(policy.validate_dag_file_map(content, paths), ([], []))



    def test_apps_source_filter(self):
        self.assertTrue(policy.is_app_source("apps/synthea/new_only/added.py"))
        self.assertTrue(policy.is_app_source("apps/landing_discovery/file.yml"))
        self.assertFalse(policy.is_app_source("apps/README.md"))
        self.assertFalse(policy.is_app_source("airflow/dags/file.py"))

    def test_app_catalog_missing_stale_and_duplicate(self):
        docs = {
            policy.APP_MAP_PATHS[0]: "[a](../../../apps/synthea/a.py)",
            policy.APP_MAP_PATHS[1]: "[b](../../../apps/landing_claim/b.py)\n[dup](../../../apps/synthea/a.py)",
            policy.APP_MAP_PATHS[2]: "[stale](../../../apps/omop_writer/old.py)",
            policy.APP_MAP_PATHS[3]: "",
        }
        missing, stale, duplicated = policy.validate_app_code_maps(
            docs, {"apps/synthea/a.py", "apps/landing_claim/b.py", "apps/new.py"}
        )
        self.assertEqual(missing, ["apps/new.py"])
        self.assertEqual(stale, ["apps/omop_writer/old.py"])
        self.assertEqual(duplicated, ["apps/synthea/a.py"])

    def test_apps_same_pr_owner_updates_for_add_delete(self):
        s, l, o, a = policy.APP_MAP_PATHS
        old = {s: "[old](../../../apps/synthea/old.py)", l: "", o: "", a: ""}
        new = {s: "", l: "", o: "[new](../../../apps/omop_writer/new.py)", a: ""}
        required = policy.required_app_updates(
            {"apps/synthea/old.py", "apps/omop_writer/new.py"}, old, new
        )
        self.assertEqual(required, {s, o})
        self.assertEqual(policy.required_app_updates(set(), old, new), set())


    def test_spark_source_filter(self):
        self.assertTrue(policy.is_spark_source("spark/apps/condition/main.py"))
        self.assertTrue(policy.is_spark_source("spark/contracts/canonical/patient.json"))
        self.assertTrue(policy.is_spark_source("spark/manifests/condition/job.yaml.tpl"))
        self.assertFalse(policy.is_spark_source("spark/README.md"))
        self.assertFalse(policy.is_spark_source("apps/omop_writer/main.py"))

    def test_spark_map_missing_stale_and_duplicate(self):
        content = "\n".join([
            "[one](../../../spark/apps/visit/a.py)",
            "[again](../../../spark/apps/visit/a.py)",
            "[old](../../../spark/contracts/canonical/old.json)",
        ])
        missing, stale, dup = policy.validate_spark_code_map(
            content, {"spark/apps/visit/a.py", "spark/manifests/common/new.yaml.tpl"}
        )
        self.assertEqual(missing, ["spark/manifests/common/new.yaml.tpl"])
        self.assertEqual(stale, ["spark/contracts/canonical/old.json"])
        self.assertEqual(dup, ["spark/apps/visit/a.py"])

    def test_spark_map_complete_sources(self):
        paths = {"spark/apps/visit/main.py", "spark/contracts/omop/visit.json",
                 "spark/manifests/common/job.yaml.tpl"}
        text = "\n".join(f"[source](../../../{p})" for p in sorted(paths))
        self.assertEqual(policy.validate_spark_code_map(text, paths), ([], [], []))


    def test_contract_sql_source_filter(self):
        self.assertTrue(policy.is_contract_sql_source("contracts/synthea/identity.json"))
        self.assertTrue(policy.is_contract_sql_source("sql/landing_claim/new.sql"))
        self.assertFalse(policy.is_contract_sql_source("sql/README.md"))
        self.assertFalse(policy.is_contract_sql_source("spark/contracts/patient.json"))

    def test_contract_sql_ownership_missing_stale_duplicates(self):
        syn, landing, omop = policy.CONTRACT_SQL_MAP_PATHS
        data = {
            syn: "| [a](../../../contracts/synthea/a.json) | version |",
            landing: ("| [dup](../../../contracts/synthea/a.json) | dup |"
                      "\n| [old](../../../sql/landing_claim/old.sql) | old |"),
            omop: ("[cross](../../../contracts/synthea/a.json)\n"
                   "| [writer](../../../sql/task002/person.sql) | owner |"),
        }
        missing, stale, duplicate = policy.validate_contract_sql_maps(
            data, {"contracts/synthea/a.json", "sql/task002/person.sql",
                   "sql/landing_claim/new.sql"}
        )
        self.assertEqual(missing, ["sql/landing_claim/new.sql"])
        self.assertEqual(stale, ["sql/landing_claim/old.sql"])
        self.assertEqual(duplicate, ["contracts/synthea/a.json"])

    def test_contract_sql_ownership_ignores_narrative_crossrefs(self):
        contents = (
            "[cross](../../../contracts/synthea/a.json)\n"
            "| [owned](../../../contracts/synthea/a.json) | source |"
        )
        self.assertEqual(
            policy.contract_sql_owned_links(contents), {"contracts/synthea/a.json"}
        )

    def test_contract_sql_move_requires_old_and_new_owner_updates(self):
        syn, landing, omop = policy.CONTRACT_SQL_MAP_PATHS
        old = {syn: "| [old](../../../contracts/synthea/old.json) | owner |",
               landing: "", omop: ""}
        new = {syn: "", landing: "",
               omop: "| [new](../../../contracts/omop-writer/new.json) | owner |"}
        self.assertEqual(
            policy.required_contract_sql_updates(
                {"contracts/synthea/old.json", "contracts/omop-writer/new.json"},
                old, new,
            ),
            {syn, omop},
        )
        self.assertEqual(policy.required_contract_sql_updates(set(), old, new), set())

if __name__ == "__main__":
    unittest.main()
