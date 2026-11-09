"""Offline-only proof: two pinned HL7 sources share exactly ONE physical Silver writer.

Tests the actual Fabric notebook module. Does NOT run Azure or authorize release.
"""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "azure-fabric/notebook-development"))
import fhir_ingest_notebook as nb


class HL7TwoSourceSingleWriter(unittest.TestCase):
    def test_original42_unchanged_and_new16_exact_source_pins(self):
        old = nb._hl7_source_context()
        ten = nb._hl7_source_context("johnscreek-hl7-gh-42535807666")
        self.assertEqual(old.request_id, "johnscreek-hl7-gh-42410482514")
        self.assertEqual(old.manifest_sha256,
                         "dfb9895554470b0cb31536a041cd38aef5aaedd11ff762f491ce54e6dd1df114")
        self.assertEqual(old.processing_run_id, "hl7-real-get-42410482514")
        self.assertEqual(nb._hl7_approved_scope(old.request_id)["raw_count"], 42)
        self.assertEqual(ten.manifest_sha256,
                         "5c2f506af86861a4bc539159f26db8077dcc10a27ad872738b19da2443832c81")
        self.assertEqual(ten.processing_run_id, "hl7-real-get-42535807666")
        self.assertEqual(nb._hl7_approved_scope(ten.request_id)["source_sha"],
                         "a68c7aa7d9fed1b1dcb6d8bb63162a87a98751dfbcfb187df214824de24a5e2f")
        self.assertEqual(nb._hl7_approved_scope(ten.request_id)["raw_count"], 16)
        self.assertEqual(ten.source_version, old.source_version)
        self.assertEqual(ten.adapter_version, old.adapter_version)
        self.assertNotEqual(ten.source_batch_id, old.source_batch_id)

    def test_new_request_paths_isolate_old_approval_and_immutable_transfer(self):
        old=nb._hl7_source_context()
        ten=nb._hl7_source_context("johnscreek-hl7-gh-42535807666")
        p=nb._hl7_real_paths(old); t=nb._hl7_real_paths(ten)
        self.assertEqual(set(p), set(t))
        self.assertEqual(set(p), {"patient","encounter","approval","quarantine"})
        self.assertFalse(set(p.values()) & set(t.values()))
        self.assertNotEqual(nb._hl7_transfer_root(old), nb._hl7_transfer_root(ten))
        for path in t.values():
            self.assertIn("42535807666",path)
            self.assertNotIn("42410482514",path)

    def test_unknown_request_or_context_collision_fail_closed(self):
        with self.assertRaises(ValueError):
            nb._hl7_source_context("johnscreek-hl7-gh-42410482514-replay")
        with self.assertRaises(ValueError):
            nb._hl7_approved_scope("arbitrary")
        old=nb._hl7_source_context()
        ten=nb._hl7_source_context("johnscreek-hl7-gh-42535807666")
        from dataclasses import replace
        altered=replace(ten, manifest_sha256=old.manifest_sha256)
        with self.assertRaises(ValueError):
            nb._hl7_real_paths(altered)
        with self.assertRaises(ValueError):
            nb._hl7_transfer_root(altered)

    def test_single_shared_writer_and_zero_automatic_writes(self):
        from inspect import getsource
        code=getsource(nb.verify_hl7_real_silver)
        self.assertIn("_write_verified_canonical_silver(",code)
        self.assertIn("_hl7_source_context(request)",code)
        self.assertIn("_hl7_verified_original_raw(",code)
        self.assertIn("HOLD_SILVER_NOT_FOUND",code)
        self.assertIn("SILVER_SKIP_VERIFIED",code)
        self.assertIn("VERIFY_READONLY",code)
        self.assertEqual(code.count("_write_verified_canonical_silver("),1)
        self.assertEqual(nb._HL7_SOURCE_SCOPES.keys(),
                         {nb._HL7_REAL_REQUEST,nb._HL7_TEN_REQUEST})

if __name__=="__main__":
    unittest.main()
