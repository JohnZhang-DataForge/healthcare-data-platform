# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

ARG PROJECT_GIT_SHA=unknown
ARG KUBECTL_VERSION=v1.32.5

LABEL org.opencontainers.image.title="healthcare-data-platform-task004-runtime"
LABEL org.opencontainers.image.description="TASK004 control-plane runtime for Healthcare Data Platform"
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"
LABEL org.opencontainers.image.revision="${PROJECT_GIT_SHA}"
LABEL io.healthcare-data-platform.runtime.role="task004-control-plane"
LABEL io.healthcare-data-platform.kubectl.version="${KUBECTL_VERSION}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash \
       ca-certificates \
       coreutils \
       curl \
       findutils \
       gawk \
       grep \
       sed \
    && rm -rf /var/lib/apt/lists/*

RUN curl \
      --fail \
      --location \
      --silent \
      --show-error \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
      -o /usr/local/bin/kubectl \
    && curl \
      --fail \
      --location \
      --silent \
      --show-error \
      "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256" \
      -o /tmp/kubectl.sha256 \
    && echo "$(cat /tmp/kubectl.sha256)  /usr/local/bin/kubectl" \
      | sha256sum -c - \
    && chmod 0755 /usr/local/bin/kubectl \
    && rm -f /tmp/kubectl.sha256 \
    && kubectl version --client=true

RUN groupadd \
      --gid 10001 \
      hdp \
    && useradd \
      --uid 10001 \
      --gid 10001 \
      --create-home \
      --home-dir /home/hdp \
      --shell /bin/bash \
      hdp \
    && mkdir -p \
      /data/spark/healthcare-data-platform/runtime/reports/task004 \
    && chown -R \
      10001:10001 \
      /data/spark/healthcare-data-platform

COPY --chown=10001:10001 --chmod=0755 \
  apps/task004/resolve_verified_landing_file.py \
  /data/spark/healthcare-data-platform/apps/task004/resolve_verified_landing_file.py

COPY --chown=10001:10001 --chmod=0755 \
  apps/task004/publish_synthea_landing.py \
  /data/spark/healthcare-data-platform/apps/task004/publish_synthea_landing.py

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/04c-run-synthea-generate-publish.sh \
  /data/spark/healthcare-data-platform/scripts/task004/04c-run-synthea-generate-publish.sh

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05c-resolve-runtime-lineage.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05c-resolve-runtime-lineage.sh

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05d-run-person-canonical.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05d-run-person-canonical.sh

COPY --chown=10001:10001 --chmod=0755 \
  scripts/task004/05e-run-visit-canonical.sh \
  /data/spark/healthcare-data-platform/scripts/task004/05e-run-visit-canonical.sh

COPY --chown=10001:10001 --chmod=0644 \
  kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl \
  /data/spark/healthcare-data-platform/kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl

COPY --chown=10001:10001 --chmod=0755 \
  spark/apps/person/synthea_patient_adapter.py \
  /data/spark/healthcare-data-platform/spark/apps/person/synthea_patient_adapter.py

COPY --chown=10001:10001 --chmod=0644 \
  spark/common/batch_manifest.py \
  /data/spark/healthcare-data-platform/spark/common/batch_manifest.py

COPY --chown=10001:10001 --chmod=0644 \
  spark/contracts/canonical/patient-v1.json \
  /data/spark/healthcare-data-platform/spark/contracts/canonical/patient-v1.json

COPY --chown=10001:10001 --chmod=0644 \
  spark/manifests/task002/person-canonical-adapter.yaml.tpl \
  /data/spark/healthcare-data-platform/spark/manifests/task002/person-canonical-adapter.yaml.tpl

COPY --chown=10001:10001 --chmod=0755 \
  spark/apps/visit/synthea_encounter_adapter.py \
  /data/spark/healthcare-data-platform/spark/apps/visit/synthea_encounter_adapter.py

COPY --chown=10001:10001 --chmod=0644 \
  spark/contracts/canonical/encounter-v1.json \
  /data/spark/healthcare-data-platform/spark/contracts/canonical/encounter-v1.json

COPY --chown=10001:10001 --chmod=0644 \
  spark/manifests/task003/encounter-canonical-adapter.yaml.tpl \
  /data/spark/healthcare-data-platform/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl

COPY --chown=10001:10001 --chmod=0755 \
  images/task004-runtime/entrypoint.sh \
  /usr/local/bin/task004-runtime

ENV PROJECT_ROOT=/data/spark/healthcare-data-platform
ENV TASK004_RUNTIME_CONTEXT=in-cluster
ENV PROJECT_GIT_SHA=${PROJECT_GIT_SHA}
ENV KUBECTL_VERSION=${KUBECTL_VERSION}

WORKDIR /data/spark/healthcare-data-platform

USER 10001:10001

ENTRYPOINT ["/usr/local/bin/task004-runtime"]
