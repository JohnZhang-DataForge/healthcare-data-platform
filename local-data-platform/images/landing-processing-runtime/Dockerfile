# syntax=docker/dockerfile:1
# V2 compatibility layer over this release's TASK004 control runtime.
ARG BASE_IMAGE=ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-runtime:latest
FROM ${BASE_IMAGE}

LABEL io.healthcare-data-platform.runtime.role="landing-processing-v2-source-bridge"
LABEL io.healthcare-data-platform.runtime.claim="disabled"
LABEL io.healthcare-data-platform.runtime.postgres-commit="disabled"

# The TASK004 control image may contain a v1-only Resolver that cannot
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


# P4 overlays ONLY the three NEW_ONLY SparkApplication configs onto the
# existing parent. No TASK004 Spark business Python or legacy parent release
# is changed; all three jobs use the original control scripts and Airflow DAG.
COPY --chown=10001:10001 --chmod=0644 \
  spark/manifests/task002/person-canonical-adapter.yaml.tpl \
  /data/spark/healthcare-data-platform/spark/manifests/task002/person-canonical-adapter.yaml.tpl
COPY --chown=10001:10001 --chmod=0644 \
  spark/manifests/task003/encounter-canonical-adapter.yaml.tpl \
  /data/spark/healthcare-data-platform/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl
COPY --chown=10001:10001 --chmod=0644 \
  spark/manifests/task004/person-visit-reconciliation.yaml.tpl \
  /data/spark/healthcare-data-platform/spark/manifests/task004/person-visit-reconciliation.yaml.tpl

# P4 Airflow-to-Spark parent identity propagation. Change ONLY the V2 child:
# these existing control scripts inject provider-produced job/run context after
# rendering and before SparkApplication dry-run/apply. Parent base stays intact.
COPY --chown=10001:10001 --chmod=0644 \
  spark/common/openlineage_parent_context.py \
  /data/spark/healthcare-data-platform/spark/common/openlineage_parent_context.py
COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05d-run-person-canonical.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05d-run-person-canonical.sh
COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05e-run-visit-canonical.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05e-run-visit-canonical.sh
COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05f-reconcile-person-visit.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05f-reconcile-person-visit.sh

USER 10001:10001
# Inherit the proven /usr/local/bin/task004-runtime entrypoint.
