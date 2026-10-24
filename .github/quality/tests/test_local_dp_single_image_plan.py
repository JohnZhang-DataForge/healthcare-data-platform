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

    def test_publishing_allowed_only_when_explicit_on_main(self):
        for operation, publish, promote in (
            ("validate", "false", "false"),
            ("publish", "true", "false"),
            ("promote-latest", "true", "true"),
        ):
            with self.subTest(operation=operation):
                plan = module.build_plan("synthea", operation, "refs/heads/main")
                self.assertEqual(plan["publish"], publish)
                self.assertEqual(plan["promote"], promote)

        for ref in ("refs/heads/feature/foo", "refs/tags/v1", "", "main"):
            for operation in ("publish", "promote-latest"):
                with self.subTest(ref=ref, operation=operation):
                    with self.assertRaisesRegex(ValueError, "REQUIRES_MAIN"):
                        module.build_plan("synthea", operation, ref)

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
        self.assertIn('steps.plan.outputs.promote', source)
        self.assertIn("GITHUB_RUN_ID", source)
        self.assertNotIn("build_base()", source)
        self.assertNotIn("build_child()", source)


if __name__ == "__main__":
    unittest.main()
