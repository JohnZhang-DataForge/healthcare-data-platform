# syntax=docker/dockerfile:1
# Base must be selected by a reviewed builder as python:3.12-slim@sha256:<64hex>.
# Unset BASE_IMAGE intentionally fails; never build/deploy a floating latest.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG PROJECT_GIT_SHA=unknown
LABEL org.opencontainers.image.title="healthcare-azure-blob-publisher" \
      org.opencontainers.image.description="Isolated immutable Azure Blob Publisher" \
      org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform" \
      org.opencontainers.image.revision="${PROJECT_GIT_SHA}"

COPY apps/clinical_producers/requirements-blob-publisher.txt /opt/azure-blob-publisher/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /opt/azure-blob-publisher/requirements.txt
COPY --chown=10001:10001 apps/clinical_producers/ /opt/azure-blob-publisher/apps/clinical_producers/
COPY --chown=10001:10001 apps/synthea/synthea_new_generator/ /opt/azure-blob-publisher/apps/synthea/synthea_new_generator/
# Python recognizes namespace parents under /opt/azure-blob-publisher/apps.
ENV PYTHONPATH=/opt/azure-blob-publisher \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /opt/azure-blob-publisher
USER 10001:10001
ENTRYPOINT ["python3", "-m", "apps.clinical_producers.azure_blob_runtime"]
