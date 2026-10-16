# TASK004 STEP04F — CDM Runtime GHCR Image Publication

**Status: GHCR PUBLISHED / PASS. No Kubernetes deployment, no Airflow DAG trigger, no database writes.**

## Verified delivery

- GitHub Actions run: https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38407086310 — SUCCESS.
- Source commit used for image build: `f1a0d109745e45f1bd63c12516ebae4b92466bfe` (feature branch; source files based on Healthcare main `897cc15c514f635eedcb3cd7edc0c9765aafb757`).
- Tag: `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime:git-f1a0d109745e45f1bd63c12516ebae4b92466bfe`
- **Immutable digest / Kubernetes candidate:** `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:a7ad7007d3751fd4e778635c3b5fbf4bfca3ebdc9aea1ec9c344b75f5eecd25f`
- Image type: linux/amd64 non-root read-only CDM source validation image; includes boto3, pyarrow, dynamic Person/Visit adapters and SQL renderer module; existing CLI exposes **no COMMIT executor**.
- Build workflow tested packaging contracts before `docker/build-push-action@v6` pushed to GHCR using repository-scoped `GITHUB_TOKEN`, and independently confirmed a valid build output digest.

## Scope / next step

This checkpoint is **publication only**. No Job or Deployment created, no image rollout, no Secret read, no actual S3 request, no database write and no DAG Run. Next task is scoped read-only Kubernetes Job smoke test using immutable digest, then separate PostgreSQL credential and Airflow integration. TASK005 ON HOLD.
