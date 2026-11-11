"""ATLAS 3 private worker03 deployment contracts; no network or Kubernetes writes."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[5]
K8S = ROOT / "local-data-platform/kubernetes/manifests/atlas"
APP = ROOT / "local-data-platform/atlas"
IMAGE = ROOT / "local-data-platform/images/atlas3-ui/Dockerfile"


class AtlasP2P4StaticTests(unittest.TestCase):
    def read(self, name):
        return (K8S / name).read_text(encoding="utf-8")

    def test_names_and_private_services(self):
        self.assertIn("name: dw-atlas", self.read("namespace.yaml"))
        svc = self.read("services.yaml")
        self.assertEqual(svc.count("type: ClusterIP"), 2)
        self.assertNotIn("NodePort", svc)
        self.assertNotIn("LoadBalancer", svc)
        self.assertIn("name: atlas3-ui", svc)
        self.assertIn("name: webapi3", svc)
        self.assertNotIn("nodePort:", svc)
        network = self.read("webapi3-networkpolicy.yaml")
        self.assertIn("kind: NetworkPolicy", network)
        self.assertIn("name: webapi3-private-ingress", network)
        self.assertIn("app.kubernetes.io/name: atlas3-ui", network)

    def test_host_placement_and_limits(self):
        for f in ("atlas3-ui-deployment.yaml.tpl", "webapi3-deployment.yaml.tpl"):
            t = self.read(f)
            self.assertIn("namespace: dw-atlas", t)
            self.assertIn("kubernetes.io/hostname: worker03", t)
            self.assertIn("workload: compute", t)
            self.assertIn("requests:", t)
            self.assertIn("limits:", t)
            self.assertIn("automountServiceAccountToken: false", t)
            self.assertNotIn("worker01", t)
            self.assertNotIn("worker02", t)

    def test_refuses_unpinned_or_unsafe_credentials(self):
        ui = self.read("atlas3-ui-deployment.yaml.tpl")
        web = self.read("webapi3-deployment.yaml.tpl")
        self.assertIn("ghcr.io/johnzhang-dataforge/healthcare-data-platform-atlas3-ui@sha256:cb18de851c4510908de7272a51b72d992f10c1250f170541be929b43789df3c9", ui)
        self.assertIn("docker.io/ohdsi/webapi@sha256:16a7fb6446775152421831dc319cf72dda274a7af8cb4cae0bf1e0450af5a6ac", web)
        self.assertIn("dw-postgre.dw-postgre.svc.cluster.local", web)
        self.assertIn("secretKeyRef:", web)
        self.assertIn("SECURITY_AUTH_DB_ENABLED", web)
        self.assertIn("SECURITY_PROVIDER, value: AtlasRegularSecurity", web)
        self.assertIn('SECURITY_ADMIN_LOGIN, value: "atlas_admin"', web)
        self.assertIn("SECURITY_ALLOWANONYMOUSACCESS", web)
        self.assertIn("SECURITY_ALLOWANONYMOUSACCESS", web)
        self.assertIn('TREXSQL_ENABLED, value: "false"', web)
        self.assertNotIn("admin/admin", web)
        self.assertNotIn("ohdsi/ohdsi", web)
        self.assertNotIn("mypass", web)

    def test_gateway_same_origin_and_not_public(self):
        g = self.read("frontend-gateway-configmap.yaml")
        self.assertIn("handle /WebAPI/*", g)
        self.assertIn("handle /atlas/*", g)
        self.assertIn("webapi3.dw-atlas.svc.cluster.local:8080", g)
        self.assertNotIn("tls internal", g)
        self.assertNotIn("nodePort:", g)
        self.assertNotIn("lineage.johnzhang-dataforge.site", g)

    def test_schema_plan_cdm_select_only_and_fails_closed(self):
        sql = (APP / "sql/prepare-webapi-schemas.sql").read_text()
        self.assertIn("BEGIN;", sql)
        self.assertIn("COMMIT;", sql)
        self.assertIn("ATLAS_SCHEMA_COLLISION", sql)
        self.assertIn("atlas_migrator", sql)
        self.assertIn("atlas_webapi", sql)
        self.assertIn("GRANT SELECT ON ALL TABLES IN SCHEMA cdm", sql)
        self.assertNotIn("DROP SCHEMA", sql.upper())
        self.assertNotIn("TRUNCATE", sql.upper())
        self.assertNotIn("DELETE FROM cdm", sql)
        self.assertNotIn("INSERT INTO cdm", sql)

    def test_unique_owner_paths_and_contract(self):
        self.assertFalse((ROOT / "local-data-platform/atlas/kubernetes").exists())
        self.assertFalse((ROOT / "local-data-platform/atlas/images").exists())
        self.assertTrue(IMAGE.is_file())
        contract = json.loads((APP / "config/runtime-contract.json").read_text())
        self.assertEqual(contract["target_worker"], "worker03")
        self.assertEqual(contract["target_namespace"], "dw-atlas")
        self.assertEqual(contract["upstream_atlas3_version"], "v3.0.0")
        # Runtime contract was updated by real Self-Runner PG17 / Source evidence.
        self.assertFalse(contract["public_route_enabled"])
        self.assertTrue(contract["public_route_verified"])
        self.assertEqual(contract["pg_migration_status"], "EXECUTED_VERIFIED")
        self.assertEqual(contract["cluster_apply_status"], "EXECUTED_VERIFIED")
        self.assertEqual(contract["local_omop_source_key"], "LOCAL_OMOP")
        self.assertEqual(contract["local_omop_source_id"], 1)
        self.assertEqual(contract["local_omop_source_status"], "REGISTERED_VERIFIED")
        self.assertEqual(contract["vocabulary_sql_search_status"], "PASS_2_REAL_RESULTS")
        self.assertEqual(contract["observation_period_exact_count"], 0)
        self.assertEqual(contract["cohort_results_status"], "SCHEMA_INITIALIZED_VERIFIED")
        self.assertEqual(contract["cohort_results_total_tables"], 26)
        self.assertEqual(contract["cohort_results_new_tables"], 23)
        self.assertEqual(contract["cohort_results_valid_new_indexes"], 2)
        self.assertEqual(contract["cohort_results_disabled_stale_heracles_indexes"], 12)
        self.assertEqual(contract["cohort_results_real_pg_readback_run"], "42984162727")
        self.assertEqual(contract["atlas_research_private_backup_run"], "42982698266")
        self.assertTrue(contract["atlas_research_private_backup_verified"])
        self.assertFalse(contract["atlas_research_full_restore_drill_verified"])
        self.assertEqual(contract["research_cohort_status"], "BLOCKED_OBSERVATION_PERIOD")


if __name__ == "__main__":
    unittest.main()
