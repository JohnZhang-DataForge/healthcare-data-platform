# Marquez PostgreSQL manifests

Kubernetes resource definitions for the **PostgreSQL 14 metadata database used by Marquez**.

## Contents

- [`statefulset.yaml`](statefulset.yaml) — database workload
- [`pvc.yaml`](pvc.yaml) and [`storageclass.yaml`](storageclass.yaml) — persistent storage configuration
- [`clusterip-service.yaml`](clusterip-service.yaml) and [`headless-service.yaml`](headless-service.yaml) — database network services

These files describe the lab's Marquez metadata database, **not the separate OMOP clinical-data database**. They are a source snapshot, not a complete reinstall procedure or current live-state report.

See the [Portal overview](../README.md) and [infrastructure notes](../../documents/architecture/INFRASTRUCTURE.md).
