"""Static guard for one OIE persistent appdata PVC; never calls Kubernetes."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'kubernetes' / 'manifests' / 'oie' / 'persistent'

class OiePersistentStatic(unittest.TestCase):
    def test_single_dedicated_class_and_pvc(self):
        sc = yaml.safe_load((BASE / 'storageclass.yaml').read_text())
        claim = yaml.safe_load((BASE / 'pvc.yaml').read_text())
        self.assertEqual(sc['kind'],'StorageClass')
        self.assertEqual(sc['metadata']['name'],'oie')
        self.assertEqual(sc['provisioner'],'rancher.io/local-path')
        self.assertEqual(sc['parameters']['nodePath'],'/data/oie')
        self.assertEqual(sc['reclaimPolicy'],'Retain')
        self.assertEqual(sc['volumeBindingMode'],'WaitForFirstConsumer')
        self.assertNotIn('storageclass.kubernetes.io/is-default-class',sc.get('metadata',{}).get('annotations',{}))
        self.assertEqual(claim['kind'],'PersistentVolumeClaim')
        self.assertEqual(claim['metadata']['namespace'],'dw-oie')
        self.assertEqual(claim['metadata']['name'],'oie-state')
        self.assertEqual(claim['spec']['storageClassName'],'oie')
        self.assertEqual(claim['spec']['accessModes'],['ReadWriteOnce'])
        self.assertEqual(claim['spec']['resources']['requests']['storage'],'10Gi')
        self.assertEqual({p.name for p in BASE.glob('*.yaml')},
                         {'storageclass.yaml','pvc.yaml'})
    def test_legacy_debug_is_not_modified_by_new_storage_definitions(self):
        dep=(BASE.parent / 'debug' / 'deployment.yaml.tpl').read_text()
        self.assertIn('kubernetes.io/hostname: worker01',dep)
        self.assertIn('name: debug-appdata',dep)
        self.assertIn('emptyDir:',dep)
        self.assertNotIn('persistentVolumeClaim:',dep)
        self.assertIn('strategy:\n    type: Recreate',dep)
if __name__=='__main__':
    unittest.main()
