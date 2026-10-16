# Kubernetes manifests

This directory holds **Kubernetes YAML manifests and workload templates** used by parts of the Healthcare Data Platform lab.

## Contents

- [`manifests/synthea/new-only/`](manifests/synthea/new-only/) — independent Synthea generator jobs, storage, and publication templates
- [`manifests/task004/`](manifests/task004/) — older ingestion/control runtime manifests retained for existing integrations

The repository does not contain a complete backup of the running cluster. Some services, namespaces, volumes, and secrets are managed outside these source files.

See the [infrastructure overview](../documents/architecture/INFRASTRUCTURE.md), [container images](../images/README.md), and [operations](../documents/operations/README.md).
