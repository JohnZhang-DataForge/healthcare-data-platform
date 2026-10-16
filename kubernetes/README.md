# Kubernetes manifests — runtime deployment and workload templates

[← Repository overview](../README.md) · [Workload images](../images/README.md) · [Deployment guide](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)

This directory keeps **YAML resources and parameterized templates** for selected application workloads; it is not a complete exported cluster configuration or a one-command installation package.

## Layout

| Path | Contents |
| --- | --- |
| [`manifests/synthea/new-only/`](manifests/synthea/new-only/) | Independent NEW_ONLY generator Job templates, READY publication templates, PersistentVolumeClaim and StorageClass |
| [`manifests/task004/`](manifests/task004/) | Earlier Synthea generation/publish Job templates and Airflow/control-runtime RBAC definitions |

## Lab placement and namespaces

| Workload | Namespace / placement |
| --- | --- |
| Independent Synthea producer | `dw-synthea` on `worker01` |
| SeaweedFS object storage | `dw-seaweedfs` on `worker01` |
| Airflow scheduler and control | `dw-airflow` on `worker02` |
| Spark Operator jobs and atomic Writer | `dw-spark` (batch work on `worker02`) |
| OMOP PostgreSQL | `dw-postgre` on `worker03` |
| Marquez lineage pilot | `dw-marquez` + separate PostgreSQL 14 namespace `dw-postgre14` |

These are verified lab conventions, not necessarily the right placements for other clusters.

**Safety:** templates such as `*.yaml.tpl` require reviewed parameter rendering; blindly applying them will not create a complete valid deployment. Existing PV/PVCs, namespace secrets, service accounts and RBAC can affect durable data. Never delete a volume, rerun an already completed writer, or apply an old namespace-scoped secret based solely on an example manifest. Check the live cluster and [current task guidance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/README.md) first.

For Portal deployment resources, see [`platform-portal/`](../platform-portal/README.md).
