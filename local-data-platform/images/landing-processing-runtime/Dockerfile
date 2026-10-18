# syntax=docker/dockerfile:1
# Immutable, additive compatibility layer over the previously accepted TASK004
# Spark control-plane runtime. Original digest is never rebuilt or replaced.
FROM ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime@sha256:8d55a150e7fcd8ea9a1ed8e8c2c64d09bf4d19687822c0ec84857fdf429c05a7

LABEL io.healthcare-data-platform.runtime.role="landing-processing-v2-source-bridge"
LABEL io.healthcare-data-platform.runtime.claim="disabled"
LABEL io.healthcare-data-platform.runtime.postgres-commit="disabled"

# The frozen legacy control image predates NEW_ONLY v2: its Resolver cannot
# import the v2 Validator, and does not contain the pinned CSV contract.
# Package the modern resolver with its explicit v2-only helper and EXACT
# immutable contract. Existing v1 code remains fail-closed and unchanged.
COPY --chown=10001:10001 --chmod=0755 \
  apps/task004/resolve_verified_landing_file.py \
  /data/spark/healthcare-data-platform/apps/task004/resolve_verified_landing_file.py
COPY --chown=10001:10001 --chmod=0644 \
  apps/task004/validate_new_only_v2_manifest.py \
  /data/spark/healthcare-data-platform/apps/task004/validate_new_only_v2_manifest.py
COPY --chown=10001:10001 --chmod=0644 \
  contracts/synthea/new-only/csv-contract-v2.json \
  /data/spark/healthcare-data-platform/apps/task004/csv-contract-v2.json

USER 10001:10001
# Inherit the proven /usr/local/bin/task004-runtime entrypoint.
