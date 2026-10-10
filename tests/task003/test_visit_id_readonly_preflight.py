#!/usr/bin/env python3

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "apps/task003/verify_visit_id_readonly_preflight.py"


spec = importlib.util.spec_from_file_location(
    "verify_visit_id_readonly_preflight",
    MODULE,
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class VisitIDReadonlyPreflightTests(unittest.TestCase):

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"
            path.write_bytes(b"abc")

            self.assertEqual(
                mod.sha256_file(path),
                hashlib.sha256(b"abc").hexdigest(),
            )

    def test_require(self):
        mod.require(True, "ok")

        with self.assertRaises(RuntimeError):
            mod.require(False, "expected")


if __name__ == "__main__":
    unittest.main()
