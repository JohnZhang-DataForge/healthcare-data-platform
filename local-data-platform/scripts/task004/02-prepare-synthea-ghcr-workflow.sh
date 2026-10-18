#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

SOURCE="${BASH_SOURCE[0]:-}"
STAGE=''

echo '#### TASK004 STEP04B GHCR SOURCE INSTALL OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  if [[ -n "$STAGE" ]]; then
    rm -rf -- "$STAGE"
  fi

  echo "INSTALL_EXIT_CODE=${rc}"
  echo '#### TASK004 STEP04B GHCR SOURCE INSTALL OUTPUT END ####'
  exit "$rc"
}

trap finish EXIT

[[ -n "$SOURCE" && -f "$SOURCE" ]] || {
  echo 'ERROR: generator must run from a saved Bash file'
  exit 2
}

cd "$ROOT"

STAGE="$(
  mktemp -d \
    /data/spark/temp_shell/task004-step04b.XXXXXXXX
)"

mkdir -p \
  "$STAGE/.github/workflows" \
  "$STAGE/tests/task004"

# ============================================================
# A. GitHub Actions workflow
# ============================================================

cat > \
  "$STAGE/.github/workflows/build-synthea-image.yml" \
  <<'WORKFLOW'
name: Build Synthea Generator Image

on:
  workflow_dispatch:

  push:
    branches:
      - main
    paths:
      - ".github/workflows/build-synthea-image.yml"
      - "images/synthea/**"
      - "apps/task004/validate_generated_synthea_batch.py"
      - "contracts/synthea/v3.3.0/csv-contract.json"
      - "scripts/task004/01-prepare-synthea-generator-image-source.sh"
      - "tests/task004/test_synthea_generator_image_source.py"

permissions:
  contents: read
  packages: write

concurrency:
  group: synthea-image-${{ github.ref }}
  cancel-in-progress: false

jobs:
  build-and-push:
    name: Build and push Synthea image
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
          image="ghcr.io/${owner_lc}/healthcare-data-platform-synthea"
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

      - name: Build and push linux/amd64 image
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./images/synthea/Dockerfile
          platforms: linux/amd64
          push: true
          pull: true
          provenance: true
          sbom: true
          tags: ${{ steps.image.outputs.ref }}
          build-args: |
            PROJECT_GIT_SHA=${{ github.sha }}
            SYNTHEA_VERSION=v3.3.0
            SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221

      - name: Record immutable image evidence
        shell: bash
        env:
          IMAGE_REF: ${{ steps.image.outputs.ref }}
          IMAGE_DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          set -Eeuo pipefail

          [[ -n "${IMAGE_REF}" ]]
          [[ "${IMAGE_DIGEST}" =~ ^sha256:[0-9a-f]{64}$ ]]

          {
            echo "## TASK004 Synthea image"
            echo
            echo "- Git commit: \`${GITHUB_SHA}\`"
            echo "- Image tag: \`${IMAGE_REF}\`"
            echo "- Image digest: \`${IMAGE_DIGEST}\`"
            echo "- Platform: \`linux/amd64\`"
            echo "- Synthea version: \`v3.3.0\`"
            echo "- Synthea commit: \`995cf2fd33e67918d4e33110d9f68ad248002221\`"
          } >> "${GITHUB_STEP_SUMMARY}"

          echo "IMAGE_BUILD=PASS"
          echo "IMAGE_REF=${IMAGE_REF}"
          echo "IMAGE_DIGEST=${IMAGE_DIGEST}"
WORKFLOW

# ============================================================
# B. Static tests
# ============================================================

cat > \
  "$STAGE/tests/task004/test_synthea_ghcr_workflow.py" \
  <<'PY_TEST'
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
PY_TEST

# ============================================================
# C. Install
# ============================================================

mkdir -p \
  "$ROOT/.github/workflows" \
  "$ROOT/tests/task004"

install \
  -m 0644 \
  "$STAGE/.github/workflows/build-synthea-image.yml" \
  "$ROOT/.github/workflows/build-synthea-image.yml"

install \
  -m 0644 \
  "$STAGE/tests/task004/test_synthea_ghcr_workflow.py" \
  "$ROOT/tests/task004/test_synthea_ghcr_workflow.py"

echo "GHCR_WORKFLOW_SOURCE_INSTALLED=YES"
