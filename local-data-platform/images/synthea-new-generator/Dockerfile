# syntax=docker/dockerfile:1
# REQUIRED BASE_IMAGE: verified immutable Synthea v3.3.0 base @sha256 digest.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG PROJECT_GIT_SHA=unknown
LABEL org.opencontainers.image.title="healthcare-synthea-new-generator" \
      org.opencontainers.image.description="Independent parameterized NEW_ONLY CSV/FHIR source generation" \
      org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform" \
      org.opencontainers.image.revision="${PROJECT_GIT_SHA}" \
      io.healthcare-data-platform.synthea.commit="995cf2fd33e67918d4e33110d9f68ad248002221"

# Only the NEW generator; do not copy the legacy NEW_ONLY S3/PG publisher.
COPY --chown=10001:10001 apps/synthea/synthea_new_generator/ \
  /opt/new-generator/apps/synthea/synthea_new_generator/

ENV PYTHONPATH=/opt/new-generator \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SYNTHEA_JAR=/opt/synthea/synthea-with-dependencies.jar

WORKDIR /opt/new-generator
USER 10001:10001
ENTRYPOINT ["python3", "-m", "apps.synthea.synthea_new_generator.entrypoint"]
