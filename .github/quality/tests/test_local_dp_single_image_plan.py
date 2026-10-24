"""Offline positive/negative checks for manual one-image GHCR build policy."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PLAN_FILE = ROOT / ".github/quality/scripts/local_dp_single_image_plan.py"
MOD_SPEC = importlib.util.spec_from_file_location("local_dp_single_image_plan", PLAN_FILE)
import sys
module = importlib.util.module_from_spec(MOD_SPEC)
sys.modules[MOD_SPEC.name] = module
MOD_SPEC.loader.exec_module(module)


class SelectiveImagePlanTests(unittest.TestCase):
    def test_all_eight_existing_images_selectable_with_exact_dockerfile(self):
        self.assertEqual(len(module.IMAGES), 8)
        for name, spec in module.IMAGES.items():
            with self.subTest(image=name):
                plan = module.build_plan(name, "validate", "refs/heads/test")
                self.assertEqual(plan["package"], module.REGISTRY + "/" + spec.package)
                self.assertEqual(plan["dockerfile"], f"local-data-platform/images/{spec.dockerfile_dir}/Dockerfile")
                self.assertTrue((ROOT / plan["dockerfile"]).is_file())
                self.assertEqual(plan["publish"], "false")
                self.assertEqual(plan["promote"], "false")
                self.assertTrue(plan["smoke"].startswith("test -"))

    def test_exact_parent_mapping_for_three_child_images(self):
        mapping = {
            "synthea-new-only": "healthcare-data-platform-synthea",
            "landing-processing-runtime": "healthcare-data-platform-task004-runtime",
            "new-only-omop-writer": "healthcare-data-platform-task004-cdm-runtime",
        }
        for name, spec in module.IMAGES.items():
            plan = module.build_plan(name, "validate", "refs/heads/main")
            self.assertEqual(plan["parent_repo"],
                             f"{module.REGISTRY}/{mapping[name]}" if name in mapping else "")
            if name in mapping:
                self.assertIn("ARG BASE_IMAGE=" + plan["parent_repo"] + ":latest",
                              (ROOT / plan["dockerfile"]).read_text())

    def test_publish_candidates_only_and_no_build_to_latest_path(self):
        for operation, publish in (("validate", "false"), ("publish", "true")):
            with self.subTest(operation=operation):
                plan = module.build_plan("synthea", operation, "refs/heads/main",
                                         release_tag="portal-v1.0")
                self.assertEqual(plan["publish"], publish)
                self.assertEqual(plan["promote"], "false")
                self.assertEqual(plan["release_tag"], "portal-v1.0")
        for ref in ("refs/heads/feature/foo", "refs/tags/v1", "", "main"):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, "REQUIRES_MAIN"):
                    module.build_plan("synthea", "publish", ref)
        with self.assertRaisesRegex(ValueError, "NOT_ALLOWLISTED"):
            module.build_plan("synthea", "promote-latest", "refs/heads/main")

    def test_candidate_release_tag_validation(self):
        for tag in ("portal-v1.0", "portal-v1.0.1", "synthea-v2.1"):
            self.assertEqual(
                module.build_plan("synthea", "validate", "refs/heads/main", release_tag=tag)["release_tag"],
                tag)
        for tag in ("latest", "portal-v1.0;echo hacked", "Portal-v1.0",
                    "ghcr.io/foo", "portal-v1", "a"*50+"-v1.0",
                    "", "portal-v1.0\\nunsafe", "../portal-v1.0"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "INVALID_RELEASE_TAG"):
                module.build_plan("synthea", "publish", "refs/heads/main", release_tag=tag)

    def test_promotion_requires_exact_candidate_digest_main_and_evidence(self):
        d = "sha256:" + "e"*64
        evidence = "https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40097080983"
        verify = module.promotion_plan("new-only-omop-writer", "verify-candidate",
                                       "refs/heads/main", "portal-v1.0", d)
        self.assertEqual(verify["promote"], "false")
        self.assertEqual(verify["expected_digest"], d)
        promoted = module.promotion_plan("new-only-omop-writer", "promote-tested",
                                         "refs/heads/main", "portal-v1.0", d, evidence)
        self.assertEqual(promoted["promote"], "true")
        self.assertEqual(promoted["acceptance_evidence"], evidence)
        for ref in ("refs/heads/feature/x", "", "main"):
            with self.assertRaisesRegex(ValueError, "REQUIRES_MAIN"):
                module.promotion_plan("synthea", "verify-candidate", ref, "portal-v1.0", d)
        for invalid in ("", "sha256:" + "A"*64, "sha256:" + "e"*63, "latest"):
            with self.assertRaisesRegex(ValueError, "EXPECTED_DIGEST_REQUIRED"):
                module.promotion_plan("synthea", "verify-candidate",
                                      "refs/heads/main", "portal-v1.0", invalid)
        for evidence in ("", "I tested it", "https://evil.example/1",
                         "https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/notvalid"):
            with self.assertRaisesRegex(ValueError, "EVIDENCE"):
                module.promotion_plan("synthea", "promote-tested",
                                      "refs/heads/main", "portal-v1.0", d, evidence)

    def test_promotion_policy_excludes_build_and_latest_on_candidate_job(self):
        candidate = (ROOT / ".github/workflows/local-dp-image-rebuild-single.yml").read_text()
        promotion = (ROOT / ".github/workflows/local-dp-image-promote-tested.yml").read_text()
        self.assertIn("docker build", candidate)
        self.assertIn("portal-v1.0", candidate)
        self.assertNotIn("promote-latest", candidate)
        self.assertNotIn('docker push "${PACKAGE}:latest"', candidate)
        self.assertIn("docker push", promotion)
        self.assertIn('docker tag "$PINNED"', promotion)
        self.assertNotIn("docker build", promotion)
        self.assertIn('mode == \'promote-tested\'', promotion)
        self.assertIn("EXPECTED_DIGEST", promotion)
        self.assertIn("CANDIDATE_CHANGED_AFTER_TEST", promotion)
        self.assertIn("ACCEPTANCE_EVIDENCE", promotion)
        self.assertIn("workflow_dispatch:", promotion)
        self.assertIn("pull_request:", promotion)  # policy-only; no GHCR write
        bulk = (ROOT / ".github/workflows/local-dp-image-rebuild.yml").read_text()
        for text in (candidate, promotion, bulk):
            self.assertIn("group: local-dp-image-ghcr-release", text)

    def test_deny_unknown_component_and_mode(self):
        for image in ("", "all", "synthea;echo hacked", "../synthea", "ghcr.io/evil/image"):
            with self.subTest(image=image):
                with self.assertRaisesRegex(ValueError, "NOT_ALLOWLISTED"):
                    module.build_plan(image, "validate", "refs/heads/main")
        for mode in ("", "force", "push", "publish; ls", "Promote-latest"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "NOT_ALLOWLISTED"):
                    module.build_plan("synthea", mode, "refs/heads/main")

    def test_valid_optional_digest_only_for_child(self):
        d = "sha256:" + "b" * 64
        output = module.build_plan("synthea-new-only", "validate", "refs/heads/a", d)
        self.assertEqual(output["parent_digest"], d)
        for name in ("synthea", "task004-cdm-runtime", "landing-claim-runtime"):
            with self.subTest(image=name), self.assertRaisesRegex(ValueError, "HAS_NO_PARENT"):
                module.build_plan(name, "validate", "refs/heads/main", d)

    def test_invalid_digest_fails_closed(self):
        for digest in ("latest", "sha256:abc", "sha256:" + "A"*64,
                       "sha256:" + "c"*64 + ";echo leak", "sha256:" + "c"*63,
                       "sha256:" + "c"*65, "sha512:" + "d"*64):
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, "INVALID_PARENT_DIGEST"):
                module.build_plan("synthea-new-only", "validate", "refs/heads/main", digest)

    def test_old_bulk_workflow_no_automatic_main_push_or_pr_trigger(self):
        old = (ROOT / ".github/workflows/local-dp-image-rebuild.yml").read_text()
        top = old.split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", top)
        self.assertNotIn("pull_request:", top)
        self.assertNotIn("  push:", top)
        self.assertIn('test "${GITHUB_REF}" = "refs/heads/main"', old)
        self.assertIn("LATEST_PROMOTION=8/8", old)  # manual emergency full rebuild retained

    def test_new_workflow_never_builds_on_pr_and_publishes_single_package(self):
        source = (ROOT / ".github/workflows/local-dp-image-rebuild-single.yml").read_text()
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("pull_request:", source)  # offline policy CI only
        self.assertIn("github.event_name == 'workflow_dispatch'", source)
        self.assertIn("--parent-digest", source)
        self.assertIn("docker build", source)
        self.assertIn("docker push", source)
        self.assertIn('steps.plan.outputs.release_tag', source)
        self.assertNotIn('docker push "${PACKAGE}:latest"', source)
        self.assertIn("GITHUB_RUN_ID", source)
        self.assertNotIn("build_base()", source)
        self.assertNotIn("build_child()", source)


if __name__ == "__main__":
    unittest.main()
