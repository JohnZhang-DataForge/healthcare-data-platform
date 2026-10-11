import unittest
from pathlib import Path


ROOT = Path(
    "/data/spark/healthcare-data-platform"
)

DOCKERFILE = (
    ROOT
    / "images/task004-runtime/Dockerfile"
)

ENTRYPOINT = (
    ROOT
    / "images/task004-runtime/entrypoint.sh"
)

WORKFLOW = (
    ROOT
    / ".github/workflows/"
    "build-task004-runtime-image.yml"
)


class UnifiedRuntimeImageSourceTests(
    unittest.TestCase
):

    def test_source_files_exist(self):
        for path in (
            DOCKERFILE,
            ENTRYPOINT,
            WORKFLOW,
        ):
            self.assertTrue(
                path.is_file()
            )


    def test_dockerfile_uses_python_runtime_base(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "FROM python:3.12-slim-bookworm",
            text,
        )


    def test_dockerfile_pins_kubectl_version(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "ARG KUBECTL_VERSION=v1.32.5",
            text,
        )


    def test_dockerfile_verifies_kubectl_checksum(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "kubectl.sha256",
            text,
        )

        self.assertIn(
            "sha256sum -c -",
            text,
        )


    def test_dockerfile_runs_nonroot(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "USER 10001:10001",
            text,
        )


    def test_dockerfile_sets_project_root(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "ENV PROJECT_ROOT=/data/spark/healthcare-data-platform",
            text,
        )


    def test_dockerfile_copies_task004_apps(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        for path in (
            "apps/task004/resolve_verified_landing_file.py",
            "apps/task004/publish_synthea_landing.py",
        ):
            self.assertIn(
                path,
                text,
            )


    def test_dockerfile_copies_control_scripts(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        for path in (
            "04c-run-synthea-generate-publish.sh",
            "05c-resolve-runtime-lineage.sh",
            "05d-run-person-canonical.sh",
            "05e-run-visit-canonical.sh",
        ):
            self.assertIn(
                path,
                text,
            )


    def test_dockerfile_copies_synthea_job_template(self):
        self.assertIn(
            "synthea-generate-publish-job.yaml.tpl",
            DOCKERFILE.read_text(
                encoding="utf-8"
            ),
        )


    def test_dockerfile_copies_person_assets(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        for path in (
            "synthea_patient_adapter.py",
            "batch_manifest.py",
            "patient-v1.json",
            "person-canonical-adapter.yaml.tpl",
        ):
            self.assertIn(
                path,
                text,
            )


    def test_dockerfile_copies_visit_assets(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        for path in (
            "synthea_encounter_adapter.py",
            "encounter-v1.json",
            "encounter-canonical-adapter.yaml.tpl",
        ):
            self.assertIn(
                path,
                text,
            )


    def test_entrypoint_exposes_required_commands(self):
        text = ENTRYPOINT.read_text(
            encoding="utf-8"
        )

        for command in (
            "resolve)",
            "generate-publish)",
            "person)",
            "visit)",
            "version)",
        ):
            self.assertIn(
                command,
                text,
            )


    def test_entrypoint_forces_direct_incluster_lineage(self):
        text = ENTRYPOINT.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "TASK004_RUNTIME_CONTEXT=in-cluster",
            text,
        )

        self.assertIn(
            "05c-resolve-runtime-lineage.sh",
            text,
        )


    def test_control_image_does_not_install_java_or_spark(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn(
            "openjdk",
            text,
        )

        self.assertNotIn(
            "temurin",
            text,
        )

        self.assertNotIn(
            "spark-submit",
            text,
        )


    def test_workflow_uses_task004_ghcr_image(self):
        text = WORKFLOW.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "healthcare-data-platform-task004-runtime",
            text,
        )

        self.assertIn(
            "registry: ghcr.io",
            text,
        )


    def test_workflow_uses_immutable_git_sha_tag(self):
        text = WORKFLOW.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'tag="git-${GITHUB_SHA}"',
            text,
        )

        self.assertNotIn(
            ":latest",
            text,
        )


    def test_workflow_builds_linux_amd64(self):
        self.assertIn(
            "platforms: linux/amd64",
            WORKFLOW.read_text(
                encoding="utf-8"
            ),
        )


    def test_workflow_records_digest(self):
        text = WORKFLOW.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "steps.build.outputs.digest",
            text,
        )

        self.assertIn(
            "TASK004_RUNTIME_IMAGE_BUILD=PASS",
            text,
        )


if __name__ == "__main__":
    unittest.main()
