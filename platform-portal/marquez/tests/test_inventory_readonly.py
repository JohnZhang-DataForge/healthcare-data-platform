"""Offline unit checks for Portal GET-only inventory, no Kubernetes access."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
import json

PATH = Path(__file__).with_name("inventory_readonly.py")
SPEC = importlib.util.spec_from_file_location("portal_inventory_readonly", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def item(name, *, status=None, spec=None):
    return {"metadata": {"name": name}, "status": status or {}, "spec": spec or {}}


def listing(*elements):
    return {"kind": "List", "items": list(elements)}


def endpoint():
    return listing({"endpoints": [{"conditions": {"ready": True}}]})


def fixture():
    return {
        "namespaces": listing(
            item("dw-marquez", status={"phase": "Active"}),
            item("dw-postgre14", status={"phase": "Active"})),
        "marquez_deployments": listing(
            item("marquez", spec={"replicas": 1}, status={"readyReplicas": 1}),
            item("marquez-web", spec={"replicas": 1}, status={"readyReplicas": 1})),
        "marquez_services": listing(
            item("marquez", spec={"type": "ClusterIP"}),
            item("marquez-web", spec={"type": "ClusterIP"}),
            item("marquez-web-lan", spec={"type": "NodePort", "ports": [{"nodePort": 30999}]})),
        "api_endpoints": endpoint(),
        "web_endpoints": endpoint(),
        "lan_endpoints": endpoint(),
        "postgres_pod": item("dw-postgre14-database-0", status={"phase": "Running"}),
        "postgres_pvc": item("dw-postgre14-data", status={"phase": "Bound"}),
        "postgres_service": item("dw-postgre14", spec={"type": "ClusterIP"}),
    }


class InventoryTests(unittest.TestCase):
    def test_exact_kubectl_get_only_commands(self):
        self.assertEqual(len(module.QUERIES), 9)
        for query in module.QUERIES:
            c = module.command_for(query)
            self.assertEqual(c[:3], ["kubectl", "--request-timeout=12s", "get"])
            self.assertEqual(c[-2:], ["-o", "json"])
            self.assertFalse(set(c) & {"apply", "delete", "exec", "patch", "replace",
                                        "rollout", "port-forward", "create", "secret"})

    def test_all_resources_pass_when_healthy(self):
        values = module.evaluate(fixture())
        self.assertEqual(len(values), 10)
        self.assertTrue(all(values.values()), values)

    def test_missing_endpoint_fails_even_if_deployment_ready(self):
        f = fixture()
        f["api_endpoints"] = listing()
        self.assertFalse(module.evaluate(f)["api_endpoint_ready"])

    def test_api_service_must_not_be_nodeport(self):
        f = fixture()
        f["marquez_services"]["items"][0]["spec"]["type"] = "NodePort"
        self.assertFalse(module.evaluate(f)["api_web_clusterip"])

    def test_wrong_context_blocks_before_get(self):
        with patch.object(module, "run_stdout", return_value="other-context") as run:
            with self.assertRaisesRegex(ValueError, "KUBE_CONTEXT_MISMATCH"):
                module.fetch_inventory("approved-context")
            run.assert_called_once()

    def test_query_error_is_not_echoed(self):
        with patch.object(module, "run_stdout") as run:
            run.side_effect = ["approved-context",
                               subprocess.CalledProcessError(1, ["kubectl"],
                                                             stderr="potential-sensitive-detail")]
            with self.assertRaisesRegex(ValueError, "GET_ONLY_QUERY_FAILED:namespaces") as result:
                module.fetch_inventory("approved-context")
            self.assertNotIn("potential-sensitive-detail", str(result.exception))


if __name__ == "__main__":
    unittest.main()
