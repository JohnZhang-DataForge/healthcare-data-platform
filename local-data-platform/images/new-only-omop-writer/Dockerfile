# Rebuilt CDM parent runtime; add only the Task004
# NEW_ONLY atomic Writer modules and a narrowly scoped entrypoint.
ARG BASE_IMAGE=ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime:latest
FROM ${BASE_IMAGE}
USER root
WORKDIR /opt/task004
COPY --chown=10001:10001 airflow/dags/new_only_omop_writer_handoff.py airflow/dags/new_only_omop_routing.py /opt/task004/
# Supply the current NEW_ONLY-aware plan validator; inherited CDM runtime
# carries a legacy-only validator that rejects synthea-new-only-* batch IDs.
COPY --chown=10001:10001 airflow/dags/task004_cdm_materialization_plan.py /opt/task004/
# NEW_ONLY reader and adapters must match the materialization-plan contract.
# The inherited legacy image has an older transform() that drops writer_identity_version.
COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_adapters.py /opt/task004/
COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_source.py /opt/task004/
# The inherited PG render() omits writer_identity_version and falsely blocks
# synthea-new-only-* batches. Use the matched NEW_ONLY-aware renderer.
COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_pg_writer.py /opt/task004/
COPY --chown=10001:10001 airflow/dags/task004_cdm_preflight_contract.py /opt/task004/
COPY --chown=10001:10001 apps/omop_writer/build_s3_rollback_plan.py /opt/task004/
COPY --chown=10001:10001 apps/omop_writer/precommit_gate.py /opt/task004/
COPY --chown=10001:10001 apps/omop_writer/joint_s3_rollback.py /opt/task004/
COPY --chown=10001:10001 apps/omop_writer/commit_new_only_batch_once.py /opt/task004/
COPY --chown=10001:10001 apps/omop_writer/dynamic_new_only_commit.py /opt/task004/
COPY --chown=10001:10001 apps/omop_writer/new_only_airflow_writer.py /opt/task004/
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/opt/task004
USER 10001:10001
ENTRYPOINT ["python","/opt/task004/new_only_airflow_writer.py"]
