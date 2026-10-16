# Spark — PySpark transformations, quality gates and job templates

[← Repository overview](../README.md) · [Airflow orchestration](../airflow/README.md) · [Source contracts](../contracts/README.md)

This directory contains the PySpark business transformation layer and the manifests used to submit workloads through **Spark Operator**. The accepted current batch path processes **Synthea patients and encounters** into Person/Visit-ready data; additional OMOP domains require their own implementation and acceptance.

## Structure

| Path | Contents |
| --- | --- |
| [`apps/person/`](apps/person/) | Synthea Patient adapter, canonical publication, OMOP Person mapping and stage loading |
| [`apps/visit/`](apps/visit/) | Encounter adapter, Visit candidate mapping, processed DQ, publication and safety controls |
| [`apps/task004/reconcile_person_visit.py`](apps/task004/reconcile_person_visit.py) | Historical-name Person/Visit same-batch reconciliation |
| [`apps/publish_canonical_entity.py`](apps/publish_canonical_entity.py) | Shared canonical publication logic |
| [`common/`](common/) | Batch manifest, canonical gate and OMOP helper functions |
| [`contracts/canonical/`](contracts/canonical/) | Versioned Patient/Encounter canonical record agreements |
| [`contracts/omop/`](contracts/omop/) | Person and Visit candidate mapping contracts |
| [`contracts/processed/`](contracts/processed/) | Processed Visit publication, mapping and writer contracts |
| [`manifests/`](manifests/) | SparkApplication templates for Person, Visit, Raw publication and reconciliation |

## Data flow and verification

```text
Immutable Synthea CSV (SeaweedFS landing)
            ↓
PySpark source adapter + type/schema checks
            ↓
Canonical/processed Parquet + run-scoped manifest
            ↓
Person ↔ Visit reconciliation + writer handoff
            ↓
Airflow-gated OMOP Writer (apps/omop_writer/)
            ↓
PostgreSQL cdm.person / cdm.visit_occurrence
```

Actual execution is orchestrated from [`airflow/dags/new_only_omop_consumer.py`](../airflow/dags/new_only_omop_consumer.py). Success of a SparkApplication or creation of a Parquet object **does not** by itself mean data reached PostgreSQL; follow the database proof in [TASK004 final acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md).

**Next domain:** `conditions.csv` → OMOP Condition is planned as [TASK005 STEP00 read-only preflight](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md). Avoid duplicating Person/Visit adapters into new domain implementations without first extracting and testing reusable contracts.

**Operator safety:** `manifests/**/*.yaml.tpl` are parameterized templates. Confirm image digest, namespace, node scheduling and S3 batch prefix before submitting; do not re-run accepted completed batches for convenience.
