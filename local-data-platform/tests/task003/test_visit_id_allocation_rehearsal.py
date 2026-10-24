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
    / "apps/task003/verify_visit_id_allocation_rehearsal.py"
)

spec = importlib.util.spec_from_file_location(
    "verify_visit_id_allocation_rehearsal",
    MODULE,
)

module = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    module
)


class VisitIDAllocationRehearsalTests(
    unittest.TestCase
):

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

    def test_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "x"
            path.write_bytes(
                b"abc"
            )

            self.assertEqual(
                module.sha(path),
                hashlib.sha256(
                    b"abc"
                ).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
