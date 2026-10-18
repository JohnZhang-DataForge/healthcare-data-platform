import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

WORKFLOW = (
    ROOT
    / ".github"
    / "workflows"
    / "build-synthea-image.yml"
)

DOCKERFILE = (
    ROOT
    / "images"
    / "synthea"
    / "Dockerfile"
)

EXPECTED_SYNTHEA_COMMIT = (
    "995cf2fd33e67918d4e33110d9f68ad248002221"
)


class SyntheaGhcrWorkflowTests(unittest.TestCase):

    def test_workflow_exists(self):
        self.assertTrue(WORKFLOW.is_file())

    def test_workflow_has_required_permissions(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "permissions:\n"
            "  contents: read\n"
            "  packages: write\n",
            text,
        )

    def test_workflow_uses_ghcr(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            'image="ghcr.io/${owner_lc}/'
            'healthcare-data-platform-synthea"',
            text,
        )

        self.assertIn(
            "registry: ghcr.io",
            text,
        )

        self.assertIn(
            "password: ${{ secrets.GITHUB_TOKEN }}",
            text,
        )

    def test_workflow_uses_immutable_git_tag(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            'tag="git-${GITHUB_SHA}"',
            text,
        )

        self.assertNotIn(
            ":latest",
            text,
        )

    def test_workflow_builds_only_amd64(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "platforms: linux/amd64",
            text,
        )

    def test_workflow_uses_repo_root_context(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "context: .",
            text,
        )

        self.assertIn(
            "file: ./images/synthea/Dockerfile",
            text,
        )

    def test_workflow_pins_synthea_provenance(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "SYNTHEA_VERSION=v3.3.0",
            text,
        )

        self.assertIn(
            f"SYNTHEA_COMMIT={EXPECTED_SYNTHEA_COMMIT}",
            text,
        )

    def test_workflow_records_digest(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "steps.build.outputs.digest",
            text,
        )

        self.assertRegex(
            text,
            re.compile(
                r"sha256:\[0-9a-f\]\{64\}"
            ),
        )

        self.assertIn(
            "IMAGE_BUILD=PASS",
            text,
        )

    def test_workflow_can_be_manually_retried(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "workflow_dispatch:",
            text,
        )

    def test_workflow_trigger_is_narrow(self):
        text = WORKFLOW.read_text(encoding="utf-8")

        required_paths = [
            '".github/workflows/build-synthea-image.yml"',
            '"images/synthea/**"',
            '"apps/task004/validate_generated_synthea_batch.py"',
            '"contracts/synthea/v3.3.0/csv-contract.json"',
        ]

        for item in required_paths:
            self.assertIn(item, text)

    def test_dockerfile_accepts_project_git_sha(self):
        text = DOCKERFILE.read_text(encoding="utf-8")

        self.assertIn(
            "ARG PROJECT_GIT_SHA=unknown",
            text,
        )

        self.assertIn(
            'org.opencontainers.image.revision="${PROJECT_GIT_SHA}"',
            text,
        )


if __name__ == "__main__":
    unittest.main()
