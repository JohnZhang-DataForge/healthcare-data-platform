# GitHub Actions — CI, image builds and release evidence

[← Repository overview](../README.md) · [Development rules](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)

This folder holds GitHub Actions workflow definitions, primarily for **building workload images**, validating source contracts and publishing immutable GHCR artifacts. It is not the source of business data or a complete automated deployment system.

## Main entry points

| Workflow | Purpose |
| --- | --- |
| [`build-new-only-omop-writer.yml`](workflows/build-new-only-omop-writer.yml) | Build the NEW_ONLY atomic OMOP Writer image; manual dispatch available; checks the packaged Python modules |
| [`build-landing-discovery-image.yml`](workflows/build-landing-discovery-image.yml) | Build the S3 Landing discovery runtime |
| [`build-landing-claim-image.yml`](workflows/build-landing-claim-image.yml) | Build the claim/ledger runtime |
| [`build-synthea-image.yml`](workflows/build-synthea-image.yml) | Synthea workload image build |
| [`portal-a4-spark-static.yml`](workflows/portal-a4-spark-static.yml) | Static Portal/Spark smoke validation |

The other `task004-*.yml` files preserve earlier milestone-specific build and source checks. Their names are **historical development identifiers**, not the proposed public component names.

## Execution model

1. Make a bounded source change through a PR; run offline and packaging checks.
2. Build/publish an image to GHCR only through the relevant workflow.
3. Record the **immutable image digest**; update the Airflow/Kubernetes consumer pin in a separate reviewed change.
4. Validate the real runtime and durable database state independently before marking an acceptance complete.

Some workflows are manually dispatched; some only trigger on explicitly listed feature branches. **Read each `on:` block before assuming a Main push will launch it.**

Cluster-running acceptance workflows and generic ARC/self-hosted runners live in the companion [Self-Runner repository](https://github.com/JohnZhang-DataForge/Self-Runner). A build SUCCESS is not a PostgreSQL COMMIT acceptance. The verified Person/Visit closeout is [here](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md).

**Safety:** never commit passwords, tokens, kubeconfig or live patient data to workflow YAML or logs; do not replay historical COMMIT workflows.
