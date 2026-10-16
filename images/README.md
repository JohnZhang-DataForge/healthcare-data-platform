# Container images — reproducible workload packaging

[← Repository overview](../README.md) · [Image build workflows](../.github/workflows/) · [Airflow CODE](../documents/components/airflow/CODE.md)

Each child directory is a Docker build context specification (typically a `Dockerfile`) for a distinct workload. **Dockerfiles are source recipes, not proof an image is currently deployed.**

| Folder | Intended container workload |
| --- | --- |
| [`synthea/`](synthea/) | Earlier Synthea generator / publisher runtime |
| [`synthea-new-only/`](synthea-new-only/) | Decoupled NEW_ONLY source producer |
| [`landing-discovery-runtime/`](landing-discovery-runtime/) | SeaweedFS immutable READY inventory reader |
| [`landing-claim-runtime/`](landing-claim-runtime/) | Claim and lease/fencing logic |
| [`landing-processing-runtime/`](landing-processing-runtime/) | Landing → Spark processing runtime integration |
| [`new-only-omop-writer/`](new-only-omop-writer/) | **Accepted atomic OMOP Writer container** for Person and Visit |
| [`task004-cdm-runtime/`](task004-cdm-runtime/) | Legacy-named CDM plan/read-only/write support base runtime |
| [`task004-runtime/`](task004-runtime/) | Earlier integrated Synthea/Airflow milestone runtime |

## Important: the Writer image dependency boundary

The tested Writer image explicitly overlays matching versions of:

- `task004_cdm_materialization_plan.py`
- `task004_cdm_dynamic_source.py` and `task004_cdm_dynamic_adapters.py`
- `task004_cdm_dynamic_pg_writer.py`

Earlier image versions inherited stale versions of these modules and failed `BLOCKED=batch_id` in different phases. **Do not remove these COPY lines or assume updating a Python source file automatically updates the base image.**

The accepted image digest and build-run evidence are recorded in the [final TASK004 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md). For new releases: run source tests → build/image smoke → publish immutable digest → update consumer pin → validate actual cluster and durable state. Build success by itself is not a new batch COMMIT.
