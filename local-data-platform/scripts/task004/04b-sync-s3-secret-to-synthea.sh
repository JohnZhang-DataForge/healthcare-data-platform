#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_NAMESPACE="dw-spark"
SOURCE_SECRET="dw-spark-s3-secret"

TARGET_NAMESPACE="dw-synthea"
TARGET_SECRET="dw-synthea-s3-secret"

fail() {
  echo "ERROR=$*"
  exit 1
}

echo '#### TASK004 SYNTHEA S3 SECRET SYNC OUTPUT BEGIN ####'

kubectl get namespace \
  "$SOURCE_NAMESPACE" \
  >/dev/null \
  || fail "Source namespace missing"

kubectl get namespace \
  "$TARGET_NAMESPACE" \
  >/dev/null \
  || fail "Target namespace missing"

kubectl get secret \
  "$SOURCE_SECRET" \
  -n "$SOURCE_NAMESPACE" \
  >/dev/null \
  || fail "Source S3 secret missing"

SOURCE_KEYS="$(
  kubectl get secret \
    "$SOURCE_SECRET" \
    -n "$SOURCE_NAMESPACE" \
    -o go-template='{{range $key, $value := .data}}{{$key}}{{"\n"}}{{end}}' \
  | sort
)"

printf '%s\n' "$SOURCE_KEYS" \
  | grep -Fx "AWS_ACCESS_KEY_ID" \
  >/dev/null \
  || fail "Source access-key field missing"

printf '%s\n' "$SOURCE_KEYS" \
  | grep -Fx "AWS_SECRET_ACCESS_KEY" \
  >/dev/null \
  || fail "Source secret-key field missing"

ACCESS_KEY="$(
  kubectl get secret \
    "$SOURCE_SECRET" \
    -n "$SOURCE_NAMESPACE" \
    -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' \
  | base64 --decode
)"

SECRET_KEY="$(
  kubectl get secret \
    "$SOURCE_SECRET" \
    -n "$SOURCE_NAMESPACE" \
    -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' \
  | base64 --decode
)"

[[ -n "$ACCESS_KEY" ]] \
  || fail "Decoded access key is empty"

[[ -n "$SECRET_KEY" ]] \
  || fail "Decoded secret key is empty"

kubectl create secret generic \
  "$TARGET_SECRET" \
  -n "$TARGET_NAMESPACE" \
  --from-literal=AWS_ACCESS_KEY_ID="$ACCESS_KEY" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$SECRET_KEY" \
  --dry-run=client \
  -o yaml \
| kubectl apply \
    -f - \
    >/dev/null

TARGET_ACCESS="$(
  kubectl get secret \
    "$TARGET_SECRET" \
    -n "$TARGET_NAMESPACE" \
    -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' \
  | base64 --decode
)"

TARGET_SECRET_VALUE="$(
  kubectl get secret \
    "$TARGET_SECRET" \
    -n "$TARGET_NAMESPACE" \
    -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' \
  | base64 --decode
)"

[[ "$TARGET_ACCESS" == "$ACCESS_KEY" ]] \
  || fail "Target access key differs"

[[ "$TARGET_SECRET_VALUE" == "$SECRET_KEY" ]] \
  || fail "Target secret key differs"

unset ACCESS_KEY
unset SECRET_KEY
unset TARGET_ACCESS
unset TARGET_SECRET_VALUE

echo "SOURCE_SECRET=${SOURCE_NAMESPACE}/${SOURCE_SECRET}"
echo "TARGET_SECRET=${TARGET_NAMESPACE}/${TARGET_SECRET}"
echo "SECRET_VALUES_DISPLAYED=NO"
echo "CREDENTIAL_MATCH=YES"
echo "TASK004_SYNTHEA_S3_SECRET_SYNC=PASS"
echo '#### TASK004 SYNTHEA S3 SECRET SYNC OUTPUT END ####'
