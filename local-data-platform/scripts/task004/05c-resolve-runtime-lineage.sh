#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"

RESOLVER="${ROOT}/apps/task004/resolve_verified_landing_file.py"

SPARK_NAMESPACE="${SPARK_NAMESPACE:-dw-spark}"
S3_SECRET_NAME="${S3_SECRET_NAME:-dw-spark-s3-secret}"

VERIFY_NAMESPACE="${VERIFY_NAMESPACE:-dw-airflow}"
VERIFY_CONTAINER="${VERIFY_CONTAINER:-scheduler}"

S3_ENDPOINT="${S3_ENDPOINT:-http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333}"
S3_REGION="${S3_REGION:-us-east-1}"

TASK004_RUNTIME_CONTEXT="${TASK004_RUNTIME_CONTEXT:-manual}"

DATASET="${1:-}"

fail() {
  echo "ERROR=$*" >&2
  exit 1
}

[[ -n "$DATASET" ]] \
  || fail "dataset argument is required"

[[ -s "$RESOLVER" ]] \
  || fail "generic resolver missing"

: "${BATCH_ID:?BATCH_ID is required}"
: "${MANIFEST_URI:?MANIFEST_URI is required}"
: "${MANIFEST_SHA256:?MANIFEST_SHA256 is required}"

[[ "$MANIFEST_SHA256" =~ ^[0-9a-f]{64}$ ]] \
  || fail "MANIFEST_SHA256 is invalid"

case "$TASK004_RUNTIME_CONTEXT" in

  in-cluster)
    : "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required in-cluster}"
    : "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required in-cluster}"

    exec python3 \
      "$RESOLVER" \
      "$DATASET" \
      --batch-id "$BATCH_ID" \
      --manifest-uri "$MANIFEST_URI" \
      --manifest-sha256 "$MANIFEST_SHA256" \
      --endpoint "$S3_ENDPOINT" \
      --region "$S3_REGION" \
      --format json
    ;;

  manual)
    VERIFY_POD="$(
      kubectl get pods \
        -n "$VERIFY_NAMESPACE" \
        --no-headers \
      | awk '
          $1 ~ /^dw-airflow-scheduler-/ &&
          $3 == "Running" {
            print $1
            exit
          }
        '
    )"

    [[ -n "$VERIFY_POD" ]] \
      || fail "No Running Airflow scheduler Pod"

    AWS_ACCESS_KEY_ID="$(
      kubectl get secret \
        "$S3_SECRET_NAME" \
        -n "$SPARK_NAMESPACE" \
        -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' \
      | base64 --decode
    )"

    AWS_SECRET_ACCESS_KEY="$(
      kubectl get secret \
        "$S3_SECRET_NAME" \
        -n "$SPARK_NAMESPACE" \
        -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' \
      | base64 --decode
    )"

    [[ -n "$AWS_ACCESS_KEY_ID" ]] \
      || fail "AWS access key is empty"

    [[ -n "$AWS_SECRET_ACCESS_KEY" ]] \
      || fail "AWS secret key is empty"

    kubectl exec \
      -i \
      "$VERIFY_POD" \
      -n "$VERIFY_NAMESPACE" \
      -c "$VERIFY_CONTAINER" \
      -- env \
        AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
        AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
        S3_ENDPOINT="$S3_ENDPOINT" \
        S3_REGION="$S3_REGION" \
        python3 - \
          "$DATASET" \
          --batch-id "$BATCH_ID" \
          --manifest-uri "$MANIFEST_URI" \
          --manifest-sha256 "$MANIFEST_SHA256" \
          --format json \
      < "$RESOLVER"

    unset AWS_ACCESS_KEY_ID
    unset AWS_SECRET_ACCESS_KEY
    ;;

  *)
    fail "TASK004_RUNTIME_CONTEXT must be manual or in-cluster"
    ;;

esac
