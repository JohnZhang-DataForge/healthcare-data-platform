#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

DOCKERFILE="${ROOT}/images/task004-runtime/Dockerfile"
ENTRYPOINT="${ROOT}/images/task004-runtime/entrypoint.sh"
WORKFLOW="${ROOT}/.github/workflows/build-task004-runtime-image.yml"
TEST="${ROOT}/tests/task004/test_unified_runtime_image_source.py"

mkdir -p \
  "$(dirname "$DOCKERFILE")" \
  "$(dirname "$WORKFLOW")" \
  "$(dirname "$TEST")"

cat > "$DOCKERFILE" <<'DOCKERFILE_EOF'
# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

ARG PROJECT_GIT_SHA=unknown
ARG KUBECTL_VERSION=v1.32.5

LABEL org.opencontainers.image.title="healthcare-data-platform-task004-runtime"
LABEL org.opencontainers.image.description="TASK004 control-plane runtime for Healthcare Data Platform"
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"
LABEL org.opencontainers.image.revision="${PROJECT_GIT_SHA}"
LABEL io.healthcare-data-platform.runtime.role="task004-control-plane"
LABEL io.healthcare-data-platform.kubectl.version="${KUBECTL_VERSION}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       coreutils \
       curl \
       findutils \
       gawk \
       grep \
       sed \
    && rm -rf /var/lib/apt/lists/*

RUN curl \
      --fail \
      --location \
      --silent \
      --show-error \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
      -o /usr/local/bin/kubectl \
    && curl \
      --fail \
      --location \
      --silent \
      --show-error \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256" \
      -o /tmp/kubectl.sha256 \
    && echo "$(cat /tmp/kubectl.sha256)  /usr/local/bin/kubectl" \
      | sha256sum -c - \
    && chmod 0755 /usr/local/bin/kubectl \
    && rm -f /tmp/kubectl.sha256 \
    && kubectl version --client=true

RUN groupadd \
      --gid 10001 \
      hdp \
    && useradd \
      --uid 10001 \
      --gid 10001 \
      --create-home \
      --home-dir /home/hdp \
      --shell /bin/bash \
      hdp \
    && mkdir -p \
      /data/spark/healthcare-data-platform/runtime/reports/task004 \
    && chown -R \
      10001:10001 \
      /data/spark/healthcare-data-platform

COPY --chown=10001:10001 --chmod=0755 \
  apps/task004/resolve_verified_landing_file.py \
  /data/spark/healthcare-data-platform/apps/task004/resolve_verified_landing_file.py

COPY --chown=10001:10001 --chmod=0755 \
  apps/task004/publish_synthea_landing.py \
  /data/spark/healthcare-data-platform/apps/task004/publish_synthea_landing.py

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/04c-run-synthea-generate-publish.sh \
  /data/spark/healthcare-data-platform/scripts/task004/04c-run-synthea-generate-publish.sh

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05c-resolve-runtime-lineage.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05c-resolve-runtime-lineage.sh

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05d-run-person-canonical.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05d-run-person-canonical.sh

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05e-run-visit-canonical.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05e-run-visit-canonical.sh

COPY --chown=10001:10001 --chmod=0644 \
  kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl \
  /data/spark/healthcare-data-platform/kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl

COPY --chown=10001:10001 --chmod=0755 \
  spark/apps/person/synthea_patient_adapter.py \
  /data/spark/healthcare-data-platform/spark/apps/person/synthea_patient_adapter.py

COPY --chown=10001:10001 --chmod=0644 \
  spark/common/batch_manifest.py \
  /data/spark/healthcare-data-platform/spark/common/batch_manifest.py

COPY --chown=10001:10001 --chmod=0644 \
  spark/contracts/canonical/patient-v1.json \
  /data/spark/healthcare-data-platform/spark/contracts/canonical/patient-v1.json

COPY --chown=10001:10001 --chmod=0644 \
  spark/manifests/task002/person-canonical-adapter.yaml.tpl \
  /data/spark/healthcare-data-platform/spark/manifests/task002/person-canonical-adapter.yaml.tpl

COPY --chown=10001:10001 --chmod=0755 \
  spark/apps/visit/synthea_encounter_adapter.py \
  /data/spark/healthcare-data-platform/spark/apps/visit/synthea_encounter_adapter.py

COPY --chown=10001:10001 --chmod=0644 \
  spark/contracts/canonical/encounter-v1.json \
  /data/spark/healthcare-data-platform/spark/contracts/canonical/encounter-v1.json

COPY --chown=10001:10001 --chmod=0644 \
  spark/manifests/task003/encounter-canonical-adapter.yaml.tpl \
  /data/spark/healthcare-data-platform/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl

# Docker COPY --chmod applies the supplied mode to destination
# path components it creates. Read-only assets copied with 0644
# can therefore leave newly-created parent directories without
# the execute/traverse bit for the non-root runtime user.
#
# Normalize every runtime source directory to 0755 after all
# source COPY operations. Individual file modes remain unchanged.
RUN find /data/spark/healthcare-data-platform \
      -type d \
      -exec chmod 0755 {} + \
    && test "$(stat -c '%a' /data/spark/healthcare-data-platform/kubernetes)" = "755" \
    && test "$(stat -c '%a' /data/spark/healthcare-data-platform/kubernetes/manifests)" = "755" \
    && test "$(stat -c '%a' /data/spark/healthcare-data-platform/spark/common)" = "755" \
    && test "$(stat -c '%a' /data/spark/healthcare-data-platform/spark/contracts)" = "755" \
    && test "$(stat -c '%a' /data/spark/healthcare-data-platform/spark/manifests)" = "755"

COPY --chown=10001:10001 --chmod=0755 \
  images/task004-runtime/entrypoint.sh \
  /usr/local/bin/task004-runtime

ENV PROJECT_ROOT=/data/spark/healthcare-data-platform
ENV TASK004_RUNTIME_CONTEXT=in-cluster
ENV PROJECT_GIT_SHA=${PROJECT_GIT_SHA}
ENV KUBECTL_VERSION=${KUBECTL_VERSION}

WORKDIR /data/spark/healthcare-data-platform

USER 10001:10001

ENTRYPOINT ["/usr/local/bin/task004-runtime"]
DOCKERFILE_EOF

cat > "$ENTRYPOINT" <<'ENTRYPOINT_EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
export PROJECT_ROOT

usage() {
  cat <<'HELP'
Healthcare Data Platform TASK004 Control Runtime

Commands:
  version
  resolve <dataset>
  generate-publish [runner args]
  person [--render-only]
  visit [--render-only]

Runtime contract:
  TASK004_RUNTIME_CONTEXT=in-cluster
  PROJECT_ROOT=/data/spark/healthcare-data-platform

The runtime image is a control-plane image.
It does not contain Synthea, Java, Spark or Airflow.
HELP
}

command_name="${1:-help}"

case "$command_name" in

  help|-h|--help)
    usage
    ;;

  version)
    echo "TASK004_RUNTIME_IMAGE=YES"
    echo "PROJECT_GIT_SHA=${PROJECT_GIT_SHA:-unknown}"
    echo "KUBECTL_VERSION=${KUBECTL_VERSION:-unknown}"
    echo "PROJECT_ROOT=${PROJECT_ROOT}"
    ;;

  resolve)
    shift

    [[ "$#" -eq 1 ]] || {
      echo "ERROR=resolve requires exactly one dataset" >&2
      exit 2
    }

    export TASK004_RUNTIME_CONTEXT=in-cluster

    exec \
      "${PROJECT_ROOT}/scripts/task004/05c-resolve-runtime-lineage.sh" \
      "$1"
    ;;

  generate-publish)
    shift

    exec \
      "${PROJECT_ROOT}/scripts/task004/04c-run-synthea-generate-publish.sh" \
      "$@"
    ;;

  person)
    shift

    export TASK004_RUNTIME_CONTEXT=in-cluster

    exec \
      "${PROJECT_ROOT}/scripts/task004/05d-run-person-canonical.sh" \
      "$@"
    ;;

  visit)
    shift

    export TASK004_RUNTIME_CONTEXT=in-cluster

    exec \
      "${PROJECT_ROOT}/scripts/task004/05e-run-visit-canonical.sh" \
      "$@"
    ;;

  *)
    echo "ERROR=unsupported command: ${command_name}" >&2
    usage >&2
    exit 2
    ;;

esac
ENTRYPOINT_EOF

cat > "$WORKFLOW" <<'WORKFLOW_EOF'
name: Build TASK004 Runtime Image

on:
  workflow_dispatch:

  push:
    branches:
      - main
    paths:
      - ".github/workflows/build-task004-runtime-image.yml"
      - "images/task004-runtime/**"
      - "apps/task004/resolve_verified_landing_file.py"
      - "apps/task004/publish_synthea_landing.py"
      - "scripts/task004/04c-run-synthea-generate-publish.sh"
      - "scripts/task004/05b-prepare-person-visit-runtime-interface.sh"
      - "scripts/task004/05c-resolve-runtime-lineage.sh"
      - "scripts/task004/05d-run-person-canonical.sh"
      - "scripts/task004/05e-run-visit-canonical.sh"
      - "scripts/task004/06a-prepare-unified-runtime-image.sh"
      - "kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl"
      - "spark/apps/person/synthea_patient_adapter.py"
      - "spark/common/batch_manifest.py"
      - "spark/contracts/canonical/patient-v1.json"
      - "spark/manifests/task002/person-canonical-adapter.yaml.tpl"
      - "spark/apps/visit/synthea_encounter_adapter.py"
      - "spark/contracts/canonical/encounter-v1.json"
      - "spark/manifests/task003/encounter-canonical-adapter.yaml.tpl"
      - "tests/task004/test_person_visit_runtime_interface.py"
      - "tests/task004/test_unified_runtime_image_source.py"

permissions:
  contents: read
  packages: write

concurrency:
  group: task004-runtime-image-${{ github.ref }}
  cancel-in-progress: false

jobs:
  build-and-push:
    name: Build and push TASK004 runtime
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Resolve immutable image identity
        id: image
        shell: bash
        run: |
          set -Eeuo pipefail

          owner_lc="${GITHUB_REPOSITORY_OWNER,,}"

          image="ghcr.io/${owner_lc}/healthcare-data-platform-task004-runtime"
          tag="git-${GITHUB_SHA}"

          echo "image=${image}" >> "${GITHUB_OUTPUT}"
          echo "tag=${tag}" >> "${GITHUB_OUTPUT}"
          echo "ref=${image}:${tag}" >> "${GITHUB_OUTPUT}"

          echo "IMAGE=${image}"
          echo "TAG=${tag}"
          echo "REF=${image}:${tag}"

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push linux/amd64 runtime image
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./images/task004-runtime/Dockerfile
          platforms: linux/amd64
          push: true
          pull: true
          provenance: true
          sbom: true
          tags: ${{ steps.image.outputs.ref }}
          build-args: |
            PROJECT_GIT_SHA=${{ github.sha }}
            KUBECTL_VERSION=v1.32.5

      - name: Record immutable runtime image evidence
        shell: bash
        env:
          IMAGE_REF: ${{ steps.image.outputs.ref }}
          IMAGE_DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          set -Eeuo pipefail

          [[ -n "${IMAGE_REF}" ]]
          [[ "${IMAGE_DIGEST}" =~ ^sha256:[0-9a-f]{64}$ ]]

          {
            echo "## TASK004 control runtime image"
            echo
            echo "- Git commit: \`${GITHUB_SHA}\`"
            echo "- Image tag: \`${IMAGE_REF}\`"
            echo "- Image digest: \`${IMAGE_DIGEST}\`"
            echo "- Platform: \`linux/amd64\`"
            echo "- kubectl: \`v1.32.5\`"
          } >> "${GITHUB_STEP_SUMMARY}"

          echo "TASK004_RUNTIME_IMAGE_BUILD=PASS"
          echo "IMAGE_REF=${IMAGE_REF}"
          echo "IMAGE_DIGEST=${IMAGE_DIGEST}"
WORKFLOW_EOF

cat > "$TEST" <<'TEST_EOF'
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


    def test_dockerfile_normalizes_runtime_directories(self):
        text = DOCKERFILE.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "find /data/spark/healthcare-data-platform",
            text,
        )

        self.assertIn(
            "-type d",
            text,
        )

        self.assertIn(
            "-exec chmod 0755 {} +",
            text,
        )

        for directory in (
            "/data/spark/healthcare-data-platform/kubernetes",
            "/data/spark/healthcare-data-platform/kubernetes/manifests",
            "/data/spark/healthcare-data-platform/spark/common",
            "/data/spark/healthcare-data-platform/spark/contracts",
            "/data/spark/healthcare-data-platform/spark/manifests",
        ):
            self.assertIn(
                directory,
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
TEST_EOF

chmod 0755 \
  "$ENTRYPOINT"

echo "UNIFIED_RUNTIME_IMAGE_SOURCE_RECONSTRUCTED=YES"
