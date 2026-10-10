# syntax=docker/dockerfile:1

ARG BUILDER_IMAGE=eclipse-temurin:17-jdk-jammy

FROM ${BUILDER_IMAGE} AS synthea-builder

ARG SYNTHEA_REPOSITORY=https://github.com/synthetichealth/synthea.git
ARG SYNTHEA_VERSION=v3.3.0
ARG SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git init synthea \
    && cd synthea \
    && git remote add origin "${SYNTHEA_REPOSITORY}" \
    && git fetch --depth=1 origin "${SYNTHEA_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${SYNTHEA_COMMIT}" \
    && test "$(git describe --tags --exact-match HEAD)" = "${SYNTHEA_VERSION}"

WORKDIR /src/synthea

RUN ./gradlew --no-daemon clean uberJar \
    && test -s build/libs/synthea-with-dependencies.jar


ARG RUNTIME_IMAGE=eclipse-temurin:17-jre-jammy

FROM ${RUNTIME_IMAGE}

ARG PROJECT_GIT_SHA=unknown
ARG SYNTHEA_VERSION=v3.3.0
ARG SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221

LABEL org.opencontainers.image.title="healthcare-data-platform-synthea"
LABEL org.opencontainers.image.description="Pinned Synthea generator for Healthcare Data Platform TASK004"
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"
LABEL org.opencontainers.image.revision="${PROJECT_GIT_SHA}"
LABEL org.opencontainers.image.version="${SYNTHEA_VERSION}"
LABEL io.healthcare-data-platform.synthea.commit="${SYNTHEA_COMMIT}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       python3 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 hdp \
    && useradd \
       --uid 10001 \
       --gid 10001 \
       --create-home \
       --home-dir /home/hdp \
       --shell /usr/sbin/nologin \
       hdp

COPY --from=synthea-builder \
  /src/synthea/build/libs/synthea-with-dependencies.jar \
  /opt/synthea/synthea-with-dependencies.jar

COPY --from=synthea-builder \
  /src/synthea/LICENSE \
  /opt/synthea/LICENSE

COPY --from=synthea-builder \
  /src/synthea/NOTICE \
  /opt/synthea/NOTICE

COPY \
  contracts/synthea/v3.3.0/csv-contract.json \
  /opt/healthcare/contracts/synthea/v3.3.0/csv-contract.json

COPY \
  apps/task004/validate_generated_synthea_batch.py \
  /opt/healthcare/apps/task004/validate_generated_synthea_batch.py

COPY \
  images/synthea/entrypoint.sh \
  /usr/local/bin/healthcare-synthea-generator

RUN chmod 0755 \
      /usr/local/bin/healthcare-synthea-generator \
      /opt/healthcare/apps/task004/validate_generated_synthea_batch.py \
    && mkdir -p \
      /work/output \
      /work/evidence \
    && chown -R 10001:10001 \
      /work \
      /opt/healthcare \
      /opt/synthea

ENV SYNTHEA_VERSION=v3.3.0
ENV SYNTHEA_COMMIT=995cf2fd33e67918d4e33110d9f68ad248002221
ENV SYNTHEA_JAR=/opt/synthea/synthea-with-dependencies.jar
ENV CSV_CONTRACT=/opt/healthcare/contracts/synthea/v3.3.0/csv-contract.json
ENV VALIDATOR=/opt/healthcare/apps/task004/validate_generated_synthea_batch.py
ENV OUTPUT_ROOT=/work/output
ENV EVIDENCE_ROOT=/work/evidence

WORKDIR /work

USER 10001:10001

ENTRYPOINT ["/usr/local/bin/healthcare-synthea-generator"]
