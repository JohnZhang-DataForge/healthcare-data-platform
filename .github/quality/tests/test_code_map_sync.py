"""Offline tests for source map ownership across workload build, deployment and data code."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[3] / ".github/quality/scripts/check_component_code_map.py"
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
        text = "[one](../../../../airflow/dags/one.py)\n[two](../../../../airflow/dags/two.py)\n"
        missing, obsolete = policy.validate_dag_file_map(
            text, {"airflow/dags/one.py", "airflow/dags/three.py"})
        self.assertEqual(missing, ["airflow/dags/three.py"])
        self.assertEqual(obsolete, ["airflow/dags/two.py"])

    def test_exact_complete_links_pass(self):
        paths = {"airflow/dags/one.py", "airflow/dags/two.py"}
        content = "\n".join(f"[source](../../../../{p})" for p in sorted(paths))
        self.assertEqual(policy.validate_dag_file_map(content, paths), ([], []))



    def test_apps_source_filter(self):
        self.assertTrue(policy.is_app_source("apps/synthea/new_only/added.py"))
        self.assertTrue(policy.is_app_source("apps/landing_discovery/file.yml"))
        self.assertFalse(policy.is_app_source("apps/README.md"))
        self.assertFalse(policy.is_app_source("airflow/dags/file.py"))

    def test_app_catalog_missing_stale_and_duplicate(self):
        docs = {
            policy.APP_MAP_PATHS[0]: "[a](../../../../apps/synthea/a.py)",
            policy.APP_MAP_PATHS[1]: "[b](../../../../apps/landing_claim/b.py)\n[dup](../../../../apps/synthea/a.py)",
            policy.APP_MAP_PATHS[2]: "[stale](../../../../apps/omop_writer/old.py)",
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
        old = {s: "[old](../../../../apps/synthea/old.py)", l: "", o: "", a: ""}
        new = {s: "", l: "", o: "[new](../../../../apps/omop_writer/new.py)", a: ""}
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
            "[one](../../../../spark/apps/visit/a.py)",
            "[again](../../../../spark/apps/visit/a.py)",
            "[old](../../../../spark/contracts/canonical/old.json)",
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
        text = "\n".join(f"[source](../../../../{p})" for p in sorted(paths))
        self.assertEqual(policy.validate_spark_code_map(text, paths), ([], [], []))


    def test_contract_sql_source_filter(self):
        self.assertTrue(policy.is_contract_sql_source("contracts/synthea/identity.json"))
        self.assertTrue(policy.is_contract_sql_source("sql/landing_claim/new.sql"))
        self.assertFalse(policy.is_contract_sql_source("sql/README.md"))
        self.assertFalse(policy.is_contract_sql_source("spark/contracts/patient.json"))

    def test_contract_sql_ownership_missing_stale_duplicates(self):
        syn, landing, omop = policy.CONTRACT_SQL_MAP_PATHS
        data = {
            syn: "| [a](../../../../contracts/synthea/a.json) | version |",
            landing: ("| [dup](../../../../contracts/synthea/a.json) | dup |"
                      "\n| [old](../../../../sql/landing_claim/old.sql) | old |"),
            omop: ("[cross](../../../../contracts/synthea/a.json)\n"
                   "| [writer](../../../../sql/task002/person.sql) | owner |"),
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
            "[cross](../../../../contracts/synthea/a.json)\n"
            "| [owned](../../../../contracts/synthea/a.json) | source |"
        )
        self.assertEqual(
            policy.contract_sql_owned_links(contents), {"contracts/synthea/a.json"}
        )

    def test_contract_sql_move_requires_old_and_new_owner_updates(self):
        syn, landing, omop = policy.CONTRACT_SQL_MAP_PATHS
        old = {syn: "| [old](../../../../contracts/synthea/old.json) | owner |",
               landing: "", omop: ""}
        new = {syn: "", landing: "",
               omop: "| [new](../../../../contracts/omop-writer/new.json) | owner |"}
        self.assertEqual(
            policy.required_contract_sql_updates(
                {"contracts/synthea/old.json", "contracts/omop-writer/new.json"},
                old, new,
            ),
            {syn, omop},
        )
        self.assertEqual(policy.required_contract_sql_updates(set(), old, new), set())


    def test_image_k8s_source_filter(self):
        self.assertTrue(policy.is_image_k8s_source("images/landing-claim/Dockerfile"))
        self.assertTrue(policy.is_image_k8s_source("images/synthea/entrypoint.sh"))
        self.assertTrue(policy.is_image_k8s_source("kubernetes/manifests/claim/job.yaml.tpl"))
        self.assertTrue(policy.is_image_k8s_source("kubernetes/manifests/synthea/pvc.yaml"))
        self.assertFalse(policy.is_image_k8s_source("images/README.md"))
        self.assertFalse(policy.is_image_k8s_source("spark/manifests/visit/job.yaml.tpl"))

    def test_image_k8s_missing_stale_duplicate_owners(self):
        syn, landing, omop, airflow = policy.IMAGE_K8S_MAP_PATHS
        docs = {
            syn: "| [gen](../../../../images/synthea/Dockerfile) | generator |",
            landing: "| [dup](../../../../images/synthea/Dockerfile) | overlapping |",
            omop: "| [old](../../../../images/omop/old.sh) | historical |",
            airflow: "[ref](../../../../images/synthea/Dockerfile)",
        }
        missing, stale, duplicate = policy.validate_image_k8s_maps(
            docs,
            {"images/synthea/Dockerfile", "kubernetes/manifests/task004/rbac.yaml"},
        )
        self.assertEqual(missing, ["kubernetes/manifests/task004/rbac.yaml"])
        self.assertEqual(stale, ["images/omop/old.sh"])
        self.assertEqual(duplicate, ["images/synthea/Dockerfile"])

    def test_image_k8s_prose_reference_is_not_a_second_owner(self):
        text = (
            "[cross](../../../../images/synthea/Dockerfile)\n"
            "| [owned](../../../../images/synthea/Dockerfile) | build recipe |"
        )
        self.assertEqual(
            policy.image_k8s_owned_links(text), {"images/synthea/Dockerfile"}
        )

    def test_image_k8s_moves_require_both_owner_maps(self):
        syn, landing, omop, airflow = policy.IMAGE_K8S_MAP_PATHS
        before = {
            syn: "| [old](../../../../images/synthea/old.Dockerfile) | old |",
            landing: "", omop: "", airflow: "",
        }
        after = {
            syn: "", landing: "",
            omop: "| [new](../../../../images/new-only-omop-writer/Dockerfile) | new |",
            airflow: "",
        }
        changed = {
            "images/synthea/old.Dockerfile",
            "images/new-only-omop-writer/Dockerfile",
        }
        self.assertEqual(
            policy.required_image_k8s_updates(changed, before, after), {syn, omop}
        )
        self.assertEqual(policy.required_image_k8s_updates(set(), before, after), set())


    def test_scripts_config_sources(self):
        self.assertTrue(policy.is_script_config_source(".github/quality/scripts/check_component_code_map.py"))
        self.assertEqual(policy.script_config_owned_links("| [check](../../../.github/quality/scripts/check_component_code_map.py) | tool |"), {".github/quality/scripts/check_component_code_map.py"})
        self.assertTrue(policy.is_script_config_source("scripts/omop/verify.sh"))
        self.assertTrue(policy.is_script_config_source("config/local.env.example"))
        self.assertFalse(policy.is_script_config_source("scripts/README.md"))
        self.assertFalse(policy.is_script_config_source("kubernetes/manifests/job.yaml.tpl"))

    def test_scripts_config_ownership_missing_stale_duplicate(self):
        syn, landing, spark, omop, airflow, dev = policy.SCRIPT_CONFIG_MAP_PATHS
        docs = {
            syn: "| [a](../../../../scripts/task004/a.sh) | historic |",
            landing: "| [again](../../../../scripts/task004/a.sh) | duplicate |",
            spark: "", omop: "", airflow: "",
            dev: ("[incidental](../../../scripts/task004/a.sh)\n"
                  "| [example](../../../config/local.env.example) | config |"
                  "\n| [stale](../../../scripts/quality/removed.py) | old |"),
        }
        missing, stale, duplicate = policy.validate_script_config_maps(
            docs,
            {"scripts/task004/a.sh", "config/local.env.example",
             "scripts/task002/new.sh"},
        )
        self.assertEqual(missing, ["scripts/task002/new.sh"])
        self.assertEqual(stale, ["scripts/quality/removed.py"])
        self.assertEqual(duplicate, ["scripts/task004/a.sh"])

    def test_scripts_config_cross_owner_move_requires_both_maps(self):
        syn, landing, spark, omop, airflow, dev = policy.SCRIPT_CONFIG_MAP_PATHS
        old = {p: "" for p in policy.SCRIPT_CONFIG_MAP_PATHS}
        new = dict(old)
        old[syn] = "| [old](../../../../scripts/synthea/old.sh) | old |"
        new[landing] = "| [new](../../../../scripts/landing/new.sh) | new |"
        needed = policy.required_script_config_updates(
            {"scripts/synthea/old.sh", "scripts/landing/new.sh"}, old, new
        )
        self.assertEqual(needed, {syn, landing})
        self.assertEqual(policy.required_script_config_updates(set(), old, new), set())


    def test_fabric_native_source_filter(self):
        self.assertTrue(policy.is_fabric_native_source(
            "azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/omop.Notebook/.platform"
        ))
        self.assertTrue(policy.is_fabric_native_source(
            "azure-fabric/workspaces/healthcare-omop/pipelines/run.DataPipeline/pipeline-content.json"
        ))
        self.assertFalse(policy.is_fabric_native_source(
            "azure-fabric/workspaces/healthcare-omop/pipelines/.gitkeep"
        ))
        self.assertFalse(policy.is_fabric_native_source(
            "azure-fabric/workspaces/healthcare-omop/notebooks/README.md"
        ))
        self.assertFalse(policy.is_fabric_native_source(
            "azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py"
        ))

    def test_fabric_native_map_missing_stale_duplicate_wrong_owner(self):
        notebooks, pipelines = policy.FABRIC_NATIVE_MAP_PATHS
        notebook = "azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/omop.Notebook/notebook-content.py"
        pipeline = "azure-fabric/workspaces/healthcare-omop/pipelines/load.DataPipeline/pipeline-content.json"
        old = "azure-fabric/workspaces/healthcare-omop/notebooks/old.Notebook/.platform"
        docs = {
            notebooks: f"| [notebook](../../../../{notebook}) | source |\n| [old](../../../../{old}) | stale |",
            pipelines: f"| [wrong](../../../../{notebook}) | duplicate and wrong owner |",
        }
        missing, stale, duplicate, wrong = policy.validate_fabric_native_maps(
            docs, {notebook, pipeline}
        )
        self.assertEqual(missing, [pipeline])
        self.assertEqual(stale, [old])
        self.assertEqual(duplicate, [notebook])
        self.assertEqual(wrong, [notebook])

    def test_fabric_native_same_pr_sync_across_owner_move(self):
        notebooks, pipelines = policy.FABRIC_NATIVE_MAP_PATHS
        old_path = "azure-fabric/workspaces/healthcare-omop/notebooks/old.Notebook/.platform"
        new_path = "azure-fabric/workspaces/healthcare-omop/pipelines/new.DataPipeline/.platform"
        before = {notebooks: f"| [old](../../../../{old_path}) | metadata |", pipelines: ""}
        after = {notebooks: "", pipelines: f"| [new](../../../../{new_path}) | metadata |"}
        self.assertEqual(
            policy.required_fabric_native_updates({old_path, new_path}, before, after),
            {notebooks, pipelines}
        )
        self.assertEqual(policy.required_fabric_native_updates(set(), before, after), set())



    def test_future_data_platform_uses_existing_code_map_ownership(self):
        self.assertTrue(policy.is_guarded_source("data-platform/airflow/dags/main.py"))
        self.assertTrue(policy.is_app_source("data-platform/apps/synthea/producer.py"))
        self.assertTrue(policy.is_spark_source("data-platform/spark/apps/visit/main.py"))
        self.assertTrue(policy.is_contract_sql_source("data-platform/sql/omop/visit.sql"))
        self.assertTrue(policy.is_image_k8s_source("data-platform/images/synthea/Dockerfile"))
        self.assertTrue(policy.is_script_config_source("data-platform/scripts/omop/verify.sh"))
        self.assertFalse(policy.is_app_source("data-platform/apps/README.md"))
        self.assertEqual(policy.validate_dag_file_map(
            "[dag](../../../../data-platform/airflow/dags/main.py)",
            {"data-platform/airflow/dags/main.py"}), ([], []))
        self.assertEqual(policy.validate_spark_code_map(
            "[spark](../../../../data-platform/spark/apps/visit/main.py)",
            {"data-platform/spark/apps/visit/main.py"}), ([], [], []))
        self.assertEqual(policy.app_links(
            "[app](../../../../data-platform/apps/synthea/producer.py)"),
            {"data-platform/apps/synthea/producer.py"})
        self.assertEqual(policy.contract_sql_owned_links(
            "| [sql](../../../../data-platform/sql/omop/visit.sql) | owner |"),
            {"data-platform/sql/omop/visit.sql"})
        self.assertEqual(policy.image_k8s_owned_links(
            "| [img](../../../../data-platform/images/synthea/Dockerfile) | owner |"),
            {"data-platform/images/synthea/Dockerfile"})
        self.assertEqual(policy.script_config_owned_links(
            "| [script](../../../../data-platform/scripts/omop/verify.sh) | owner |"),
            {"data-platform/scripts/omop/verify.sh"})

    def test_future_source_missing_owner_is_rejected(self):
        missing, stale, dup = policy.validate_app_code_maps(
            {name: "" for name in policy.APP_MAP_PATHS},
            {"data-platform/apps/omop_writer/writer.py"})
        self.assertEqual(missing, ["data-platform/apps/omop_writer/writer.py"])
        self.assertEqual(stale, [])
        self.assertEqual(dup, [])

    def test_local_data_platform_moved_paths_are_validated(self):
        prefix = "local-data-platform/"
        self.assertEqual(policy.local_source(prefix + "airflow/dags/main.py"), "airflow/dags/main.py")
        self.assertTrue(policy.is_guarded_source(prefix + "airflow/dags/main.py"))
        self.assertTrue(policy.is_app_source(prefix + "apps/landing_claim/ledger.py"))
        self.assertTrue(policy.is_spark_source(prefix + "spark/apps/visit/reader.py"))
        self.assertTrue(policy.is_contract_sql_source(prefix + "contracts/synthea/identity.json"))
        self.assertTrue(policy.is_contract_sql_source(prefix + "sql/omop/write.sql"))
        self.assertTrue(policy.is_image_k8s_source(prefix + "images/omop/Dockerfile"))
        self.assertTrue(policy.is_image_k8s_source(prefix + "kubernetes/manifests/omop/job.yaml"))
        self.assertTrue(policy.is_script_config_source(prefix + "scripts/omop/run.sh"))
        self.assertTrue(policy.is_script_config_source(prefix + "config/local.env.example"))
        self.assertFalse(policy.is_app_source(prefix + "apps/README.md"))

        dag = prefix + "airflow/dags/main.py"
        self.assertEqual(policy.validate_dag_file_map(
            "[dag](../../../../" + dag + ")", {dag}), ([], []))
        self.assertEqual(policy.validate_dag_file_map(
            "[dag](../../../../" + dag + ")", {dag, prefix + "airflow/dags/missing.py"})[0],
            [prefix + "airflow/dags/missing.py"])
        app = prefix + "apps/landing_claim/ledger.py"
        self.assertEqual(policy.app_links("[app](../../../../" + app + ")"), {app})
        spark = prefix + "spark/apps/visit/reader.py"
        self.assertEqual(policy.validate_spark_code_map(
            "[spark](../../../../" + spark + ")", {spark}), ([], [], []))
        sql = prefix + "sql/omop/write.sql"
        self.assertEqual(policy.contract_sql_owned_links(
            "| [sql](../../../../" + sql + ") | owner |"), {sql})
        img = prefix + "images/omop/Dockerfile"
        self.assertEqual(policy.image_k8s_owned_links(
            "| [img](../../../../" + img + ") | owner |"), {img})
        shell = prefix + "scripts/omop/run.sh"
        self.assertEqual(policy.script_config_owned_links(
            "| [script](../../../../" + shell + ") | owner |"), {shell})



if __name__ == "__main__":
    unittest.main()
