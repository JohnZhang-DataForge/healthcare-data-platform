import importlib.util
from pathlib import Path
import sys
import unittest

file = Path(__file__).resolve().parents[1] / "compatibility.py"
spec = importlib.util.spec_from_file_location("compatibility", file)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class CompatibilityTests(unittest.TestCase):
    def test_cross_builds_not_reused(self):
        a = mod.plan_listener("local", "https://collector.internal.example/lineage")
        b = mod.plan_listener("fabric", "https://collector.internal.example/lineage")
        self.assertIn("_2.12:", a.artifact)
        self.assertIn("_2.13:", b.artifact)
        self.assertEqual("CANDIDATE_NOT_RUNTIME_VERIFIED", b.status)
        self.assertNotEqual(a.properties["spark.openlineage.namespace"], b.properties["spark.openlineage.namespace"])

    def test_reject_unsafe_config(self):
        for url in ("http://example.net", "https://user:pass@example.net", "https://example.net/?token=secret"):
            with self.assertRaises(ValueError):
                mod.plan_listener("fabric", url)
        with self.assertRaises(ValueError):
            mod.plan_listener("fabric", "https://example.net", artifact_version="latest")
        with self.assertRaises(ValueError):
            mod.plan_listener("unknown", "https://example.net")
