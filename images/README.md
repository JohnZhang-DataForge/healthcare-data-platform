# Container images

Each subdirectory defines a **Docker build context** for one of the platform's workloads.

| Build context | Workload |
| --- | --- |
| [`synthea-new-only/`](synthea-new-only/) | Independent Synthea batch generator |
| [`synthea/`](synthea/) | Earlier source generator runtime |
| [`landing-discovery-runtime/`](landing-discovery-runtime/) | Landing inventory and discovery |
| [`landing-claim-runtime/`](landing-claim-runtime/) | Batch claim and fencing |
| [`landing-processing-runtime/`](landing-processing-runtime/) | Landing and processing integration |
| [`new-only-omop-writer/`](new-only-omop-writer/) | Transactional OMOP Person/Visit writer |
| [`task004-runtime/`](task004-runtime/), [`task004-cdm-runtime/`](task004-cdm-runtime/) | Historical runtime images retained for compatibility |

These folders define how images are built; they are **not a list of currently running containers**. Image build workflows are under [`.github/workflows/`](../.github/README.md).

[Back to project overview](../README.md).
