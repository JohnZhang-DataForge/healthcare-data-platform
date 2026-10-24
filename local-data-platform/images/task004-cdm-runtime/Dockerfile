FROM python:3.12-slim-bookworm
# Read-only source validation image. The existing dynamic PG SQL renderer is
# packaged for offline compatibility tests but cannot execute SQL in this image.
RUN groupadd -g 10001 hdp && useradd -u 10001 -g 10001 -m hdp
RUN python -m pip install --no-cache-dir "boto3==1.40.40" "pyarrow==21.0.0" "psycopg[binary]==3.2.10"
WORKDIR /opt/task004
COPY --chown=10001:10001 airflow/dags/task004_cdm_materialization_plan.py /opt/task004/
COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_adapters.py /opt/task004/
COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_source.py /opt/task004/
COPY --chown=10001:10001 airflow/dags/task004_cdm_dynamic_pg_writer.py /opt/task004/
COPY --chown=10001:10001 airflow/dags/task004_cdm_postgres_readonly.py /opt/task004/
COPY --chown=10001:10001 airflow/dags/task004_cdm_postgres_rollback_executor.py /opt/task004/
COPY --chown=10001:10001 apps/task004/cdm_runtime_cli.py /opt/task004/
ENV PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["python","/opt/task004/cdm_runtime_cli.py"]
