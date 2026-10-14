# syntax=docker/dockerfile:1
# Independent NEW_ONLY image; pinned and previously proven Synthea v3.3.0 base.
# No multi-mode generator and no Airflow / PostgreSQL client code in this image.
FROM ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d

ARG PROJECT_GIT_SHA=unknown
LABEL org.opencontainers.image.title="healthcare-synthea-new-only"
LABEL org.opencontainers.image.description="Independent NEW_ONLY Synthea generator, strict-v1 S3 publisher and immutable readback"
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"
LABEL org.opencontainers.image.revision="${PROJECT_GIT_SHA}"
LABEL io.healthcare-data-platform.synthea.commit="995cf2fd33e67918d4e33110d9f68ad248002221"

COPY --chown=10001:10001 apps/synthea/new_only/entrypoint.py /opt/synthea-new-only/entrypoint.py
COPY --chown=10001:10001 apps/synthea/new_only/generate_new_only.py /opt/synthea-new-only/generate_new_only.py
COPY --chown=10001:10001 apps/synthea/new_only/prepublish_gate.py /opt/synthea-new-only/prepublish_gate.py
COPY --chown=10001:10001 apps/synthea/new_only/publish_v1_verified.py /opt/synthea-new-only/publish_v1_verified.py
COPY --chown=10001:10001 apps/synthea/new_only/publish_v2_verified.py /opt/synthea-new-only/publish_v2_verified.py
COPY --chown=10001:10001 apps/synthea/new_only/verify_v2_ready.py /opt/synthea-new-only/verify_v2_ready.py
COPY --chown=10001:10001 apps/synthea/new_only/verify_v1_ready.py /opt/synthea-new-only/verify_v1_ready.py
COPY --chown=10001:10001 apps/task004/publish_synthea_landing.py /opt/synthea-new-only/publish_synthea_landing.py
COPY --chown=10001:10001 apps/task004/validate_generated_synthea_batch.py /opt/synthea-new-only/validate_generated_synthea_batch.py
COPY --chown=10001:10001 apps/task004/resolve_verified_landing_file.py /opt/synthea-new-only/resolve_verified_landing_file.py
COPY --chown=10001:10001 apps/task004/validate_new_only_v2_manifest.py /opt/synthea-new-only/validate_new_only_v2_manifest.py
COPY --chown=10001:10001 apps/landing_discovery/scan_ready_batches.py /opt/synthea-new-only/scan_ready_batches.py
COPY --chown=10001:10001 contracts/synthea/v3.3.0/csv-contract.json /opt/synthea-new-only/csv-contract-v1.json
COPY --chown=10001:10001 contracts/synthea/new-only/csv-contract-v2.json /opt/synthea-new-only/csv-contract-v2.json
COPY --chown=10001:10001 contracts/synthea/producer-batch-identity-v1.json /opt/synthea-new-only/batch-identity.json

ENV SYNTHEA_STATE_ROOT=/synthea-state \
    SYNTHEA_JAR=/opt/synthea/synthea-with-dependencies.jar \
    SYNTHEA_CSV_CONTRACT=/opt/synthea-new-only/csv-contract-v1.json \
    SYNTHEA_S3_CLIENT_DIR=/opt/synthea-new-only \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001:10001
WORKDIR /opt/synthea-new-only
ENTRYPOINT ["python3", "/opt/synthea-new-only/entrypoint.py"]
