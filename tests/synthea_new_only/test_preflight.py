"""Safety-focused offline tests for NEW_ONLY read-only preflight."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps/synthea/new_only"))
from preflight import audit


def fixture(ready=True, namespace=True):
    node = {
        "metadata": {"name": "worker01"},
        "spec": {"unschedulable": False},
        "status": {"conditions": [{"type": "Ready", "status": "True" if ready else "False"}],
                   "capacity": {"ephemeral-storage": "100Gi"}},
    }
    return {
        "node": node,
        "namespaces": {"items": [{"metadata": {"name": "dw-synthea"}}] if namespace else []},
        "storageclasses": {"items": [{"metadata": {"name": "local-path"},
                                     "provisioner": "rancher.io/local-path",
                                     "reclaimPolicy": "Delete",
                                     "volumeBindingMode": "WaitForFirstConsumer"}]},
        "pvs": {"items": [{"metadata": {"name": "seaweed-pv"},
                          "spec": {"claimRef": {"namespace": "dw-seaweedfs", "name": "volume-0"},
                                   "hostPath": {"path": "/data/local-path/seaweed"},
                                   "persistentVolumeReclaimPolicy": "Retain"}}]},
        "pvcs": {"items": []},
        "pods": {"items": []},
        "localpath_config": {"data": {"config.json": '{"nodePathMap":[{"node":"DEFAULT_PATH_FOR_NON_LISTED_NODES","paths":["/data/local-path"]}]}' }},
        "kubelet_summary": {},
        "synthea_s3_secret": "ABSENT",
    }


class NewOnlyPreflightTests(unittest.TestCase):
    def test_default_blocks_dedicated_storage_and_writer(self):
        result = audit(fixture(), ROOT)
        self.assertTrue(result["worker01"]["ready"])
        self.assertTrue(result["namespace"]["dw_synthea_exists"])
        self.assertFalse(result["storage"]["worker01_dedicated_physical_mount_verified"])
        self.assertEqual(result["storage"]["local_path_class"]["reclaim_policy"], "Delete")
        self.assertTrue(result["writer_batch_id"]["new_only_rejected_by_legacy_plan"])
        self.assertEqual(result["csv_contract"]["expected_files"], 18)
        self.assertTrue(result["csv_contract"]["nonempty_required_for_every_file"])
        self.assertFalse(result["generator_ready_to_deploy"])
        self.assertFalse(result["database_mutation"])

    def test_missing_namespace_and_unready_node_not_misreported(self):
        result = audit(fixture(ready=False, namespace=False), ROOT)
        self.assertFalse(result["worker01"]["ready"])
        self.assertFalse(result["namespace"]["dw_synthea_exists"])

    def test_existing_seaweed_pv_does_not_count_as_synthea_volume(self):
        result = audit(fixture(), ROOT)
        self.assertEqual(result["storage"]["dedicated_synthea_pvcs"], [])
        self.assertEqual(result["storage"]["relevant_existing_pvs"][0]["claim_namespace"], "dw-seaweedfs")
        self.assertFalse(result["storage"]["physical_disk_capacity_verified"])


if __name__ == "__main__":
    unittest.main()
