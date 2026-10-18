"""The real new 70-Person request must not be checked as the old 73-Person fixture."""
import inspect
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"apps/synthea/new_only"),str(ROOT/"apps/task004"),str(ROOT/"apps/landing_discovery")]
from verify_v1_ready import verify, ReadyVerificationError


class DynamicReadbackTests(unittest.TestCase):
    def test_counts_are_required_from_frozen_producer_not_first_demo(self):
        sig=inspect.signature(verify)
        self.assertIs(sig.parameters["expected_people"].default,inspect.Parameter.empty)
        self.assertIs(sig.parameters["expected_visits"].default,inspect.Parameter.empty)
        main=inspect.getsource(__import__("verify_v1_ready").main)
        self.assertIn("frozen_request(",main)
        self.assertIn("marker[\"actual_persons\"]",main)
        self.assertIn("marker[\"actual_encounters\"]",main)
        self.assertNotIn("=73",inspect.getsource(verify))
        self.assertNotIn("=12159",inspect.getsource(verify))

    def test_old_and_new_batches_are_distinct(self):
        self.assertNotEqual("synthea-new-only-gh-38484300008",
                            "synthea-new-only-gh-38489944582")
        self.assertNotEqual((73,12159),(70,11487))


if __name__=="__main__":
    unittest.main()
