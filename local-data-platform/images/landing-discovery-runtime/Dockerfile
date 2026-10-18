FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="healthcare-landing-discovery"
LABEL org.opencontainers.image.description="Read-only SeaweedFS Landing discovery for Airflow"
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"

RUN groupadd --gid 10001 hdp \
    && useradd --uid 10001 --gid 10001 --no-create-home hdp \
    && python -m pip install --no-cache-dir "boto3==1.40.40"

WORKDIR /opt/healthcare
COPY --chown=10001:10001 apps/landing_discovery/scan_ready_batches.py /opt/healthcare/landing_discovery/
COPY --chown=10001:10001 apps/landing_discovery/run_airflow_scan.py /opt/healthcare/landing_discovery/
COPY --chown=10001:10001 apps/task004/resolve_verified_landing_file.py /opt/healthcare/task004/
COPY --chown=10001:10001 apps/task004/validate_new_only_v2_manifest.py /opt/healthcare/task004/
COPY --chown=10001:10001 contracts/synthea/new-only/csv-contract-v2.json /opt/healthcare/task004/csv-contract-v2.json
RUN find /opt/healthcare -type d -exec chmod 0755 {} +
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AWS_EC2_METADATA_DISABLED=true
USER 10001:10001
ENTRYPOINT ["python","/opt/healthcare/landing_discovery/run_airflow_scan.py"]
