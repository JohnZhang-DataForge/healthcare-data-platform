# Dedicated future NEW_ONLY runtime; independent of historical Synthea entrypoint.
# Build/push must be separately validated. Actual smoke initially mounts source
# in a ConfigMap on the pinned underlying image, not yet this unpublished image.
FROM ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d
ARG PROJECT_GIT_SHA=unknown
LABEL org.opencontainers.image.title="healthcare-synthea-new-only"
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"
LABEL org.opencontainers.image.revision="${PROJECT_GIT_SHA}"
COPY --chown=10001:10001 apps/synthea/new_only/generate_new_only.py /opt/synthea-new-only/generate_new_only.py
USER 10001:10001
ENTRYPOINT ["python3", "/opt/synthea-new-only/generate_new_only.py"]
