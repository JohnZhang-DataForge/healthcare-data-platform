#!/usr/bin/env python3

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(
    __file__
).resolve().parents[2]

MODULE = (
    ROOT
    / "apps/task003/verify_visit_id_pre_mutation_gate.py"
)

spec = importlib.util.spec_from_file_location(
    "verify_visit_id_pre_mutation_gate",
    MODULE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


class VisitIDPreMutationGateTests(
    unittest.TestCase
):

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"
            path.write_bytes(b"abc")

            self.assertEqual(
                module.sha256_file(
                    path
                ),
                hashlib.sha256(
                    b"abc"
                ).hexdigest(),
            )

    def test_require(self):
        module.require(
            True,
            "ok",
        )

        with self.assertRaises(
            RuntimeError
        ):
            module.require(
                False,
                "expected",
            )


if __name__ == "__main__":
    unittest.main()
