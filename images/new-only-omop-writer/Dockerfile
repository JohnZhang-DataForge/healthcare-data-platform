# Digest-pinned proven read-only CDM runtime; add only the Task004
# NEW_ONLY atomic Writer modules and a narrowly scoped entrypoint.
FROM ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e
USER root
WORKDIR /opt/task004
COPY --chown=10001:10001 airflow/dags/new_only_omop_writer_handoff.py airflow/dags/new_only_omop_routing.py /opt/task004/
# Supply the current NEW_ONLY-aware plan validator; inherited CDM runtime
# carries a legacy-only validator that rejects synthea-new-only-* batch IDs.
COPY --chown=10001:10001 airflow/dags/task004_cdm_materialization_plan.py /opt/task004/
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
