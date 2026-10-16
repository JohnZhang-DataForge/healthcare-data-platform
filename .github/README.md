# GitHub Actions

This directory contains the repository's **GitHub Actions workflows** for checking source code, building container images, and producing test artifacts.

## What's here

- [`workflows/build-synthea-image.yml`](workflows/build-synthea-image.yml) — build the source generator image
- [`workflows/build-new-only-omop-writer.yml`](workflows/build-new-only-omop-writer.yml) — build the OMOP writer image
- [`workflows/build-landing-discovery-image.yml`](workflows/build-landing-discovery-image.yml) and [`workflows/build-landing-claim-image.yml`](workflows/build-landing-claim-image.yml) — package landing services
- [`workflows/portal-a4-spark-static.yml`](workflows/portal-a4-spark-static.yml) — test the standalone Spark/OpenLineage probe without deploying it
- [`workflows/code-component-naming-check.yml`](workflows/code-component-naming-check.yml) — check the names of newly added maintained code paths

Some workflows retain historical Task-based names. Cluster-facing execution and Azure infrastructure workflows are maintained separately in the [Self-Runner repository](https://github.com/JohnZhang-DataForge/Self-Runner).

See the [repository overview](../README.md) and [testing documentation](../documents/development/TESTING-AND-EVIDENCE.md).
