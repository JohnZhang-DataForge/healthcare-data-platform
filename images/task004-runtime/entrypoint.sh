#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
export PROJECT_ROOT

usage() {
  cat <<'HELP'
Healthcare Data Platform TASK004 Control Runtime

Commands:
  version
  resolve <dataset>
  generate-publish [runner args]
  person [--render-only]
  visit [--render-only]

Runtime contract:
  TASK004_RUNTIME_CONTEXT=in-cluster
  PROJECT_ROOT=/data/spark/healthcare-data-platform

The runtime image is a control-plane image.
It does not contain Synthea, Java, Spark or Airflow.
HELP
}

command_name="${1:-help}"

case "$command_name" in

  help|-h|--help)
    usage
    ;;

  version)
    echo "TASK004_RUNTIME_IMAGE=YES"
    echo "PROJECT_GIT_SHA=${PROJECT_GIT_SHA:-unknown}"
    echo "KUBECTL_VERSION=${KUBECTL_VERSION:-unknown}"
    echo "PROJECT_ROOT=${PROJECT_ROOT}"
    ;;

  resolve)
    shift

    [[ "$#" -eq 1 ]] || {
      echo "ERROR=resolve requires exactly one dataset" >&2
      exit 2
    }

    export TASK004_RUNTIME_CONTEXT=in-cluster

    exec \
      "${PROJECT_ROOT}/scripts/task004/05c-resolve-runtime-lineage.sh" \
      "$1"
    ;;

  generate-publish)
    shift

    exec \
      "${PROJECT_ROOT}/scripts/task004/04c-run-synthea-generate-publish.sh" \
      "$@"
    ;;

  person)
    shift

    export TASK004_RUNTIME_CONTEXT=in-cluster

    exec \
      "${PROJECT_ROOT}/scripts/task004/05d-run-person-canonical.sh" \
      "$@"
    ;;

  visit)
    shift

    export TASK004_RUNTIME_CONTEXT=in-cluster

    exec \
      "${PROJECT_ROOT}/scripts/task004/05e-run-visit-canonical.sh" \
      "$@"
    ;;

  *)
    echo "ERROR=unsupported command: ${command_name}" >&2
    usage >&2
    exit 2
    ;;

esac
