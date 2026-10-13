FROM python:3.12-slim-bookworm
RUN groupadd -g 10001 hdp && useradd -u 10001 -g 10001 -m hdp
WORKDIR /opt/task004
COPY --chown=10001:10001 airflow/dags/task004_cdm_materialization_plan.py /opt/task004/
COPY --chown=10001:10001 apps/task004/cdm_runtime_cli.py /opt/task004/
ENV PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["python","/opt/task004/cdm_runtime_cli.py"]
