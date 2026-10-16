# TASK004 STEP04F — CDM Runtime Kubernetes Read-only S3 Verification

**Status: SUCCESS / CLOSED for read-only in-cluster S3 validation. No CDM PostgreSQL writes.**

- Self-Runner run: https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38408512776 — SUCCESS.
- Published digest pinned for each ephemeral Kubernetes Job:
  `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:a7ad7007d3751fd4e778635c3b5fbf4bfca3ebdc9aea1ec9c344b75f5eecd25f`.
- Namespace `dw-spark`, node `worker02`. Existing `dw-spark-s3-secret` injected through Kubernetes Secret references (no secret printed to logs), read-only plan ConfigMap, non-root UID/GID 10001, read-only container root filesystem, privilege escalation disabled.
- Used the **previously committed historical batch** `task004-airflow-task004-step03e-38324111846`; validated immutable Manifest SHA and exact real Parquet datasets from the SeaweedFS S3 endpoint.
- Person Job: `DYNAMIC_SOURCE_VALIDATED=PASS`, `ROW_COUNT=23`, `K8S_person_READONLY=PASS`.
- Visit Job: `DYNAMIC_SOURCE_VALIDATED=PASS`, `ROW_COUNT=3592`, `K8S_visit_READONLY=PASS`.
- Both successfully checked dynamic batch/Manifest/Processing lineage and performed Python OMOP row transformations in the real container; `CDM_K8S_READONLY_SMOKE=PASS`.
- Cleanup trap requested deletion of both transient Jobs and the plan ConfigMap. No new Synthea generation, no Airflow trigger, no DB connection, no CDM insert/update/delete. Existing SQL writer is packaged but not executed.
- First full-smoke run 38408371011 verified Person 23 PASS but failed because of a shell variable name typo in an echo command; fixed and reran both Jobs successfully. Initial lightweight prerequisite run 38408003073 failed because kubectl wasn't preinstalled, then passed on 38408115226 after bootstrap.

**Next bounded task:** independently design/validate PostgreSQL credential scope and CDM runtime command/execution boundary before considering Airflow integration and new-batch COMMIT. TASK005 ON HOLD.
