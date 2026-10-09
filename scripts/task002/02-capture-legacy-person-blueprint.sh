#!/usr/bin/env bash
set -Eeuo pipefail


PROJECT_ROOT="${PROJECT_ROOT:-/data/spark/healthcare-data-platform}"
LEGACY="/data/spark/phase3c"

REPORT_DIR="${PROJECT_ROOT}/runtime/reports/task002/step02"

mkdir -p "${REPORT_DIR}"


SOURCE_REPORT="${REPORT_DIR}/legacy-person-source.txt"
SPARK_REPORT="${REPORT_DIR}/legacy-person-spark-specs.txt"
SECRET_REPORT="${REPORT_DIR}/runtime-secret-keys.txt"
SUMMARY="${REPORT_DIR}/blueprint-summary.txt"


echo "============================================================"
echo "Healthcare Data Platform V2.1"
echo "TASK-002 / STEP 02"
echo "Capture Legacy Person Blueprint"
echo "READ ONLY"
echo "============================================================"
echo


# ============================================================
# 1. Identify legacy Python applications
# ============================================================

echo "[1/6] Discovering historical Person Python apps..."

mapfile -t PY_FILES < <(
    find "${LEGACY}/apps" \
        -maxdepth 1 \
        -type f \
        -name '*.py' \
        | sort
)


if [[ "${#PY_FILES[@]}" -eq 0 ]]; then

    echo "ERROR:"
    echo "No Python apps found under:"
    echo "  ${LEGACY}/apps"

    exit 1

fi


printf '%s\n' "${PY_FILES[@]}"

echo


# ============================================================
# 2. Capture full Python source
# ============================================================

echo "[2/6] Capturing legacy Python source..."

: > "${SOURCE_REPORT}"


for file in "${PY_FILES[@]}"
do

    base="$(basename "${file}")"

    case "${base}" in

        *patient*|*person*|*omop*)

            {
                echo
                echo "============================================================"
                echo "FILE: ${file}"
                echo "SHA256: $(sha256sum "${file}" | awk '{print $1}')"
                echo "============================================================"
                echo

                cat "${file}"

                echo
                echo "============================ EOF ============================"
                echo

            } >> "${SOURCE_REPORT}"
            ;;

    esac

done


SOURCE_FILES_CAPTURED="$(
    grep -c '^FILE:' "${SOURCE_REPORT}" \
    || true
)"


echo "Captured Python files: ${SOURCE_FILES_CAPTURED}"

echo "Report:"
echo "  ${SOURCE_REPORT}"

echo


# ============================================================
# 3. Capture legacy SparkApplication specs
# ============================================================

echo "[3/6] Capturing historical SparkApplication specs..."

: > "${SPARK_REPORT}"


APPS=(
    phase3c-patients-raw
    phase3c-validate-patients-raw
    phase3c-map-person-omop
    phase3c-validate-omop-person
    phase3c-load-person-cdm
)


for app in "${APPS[@]}"
do

    echo "Inspecting ${app}..."

    if ! kubectl get sparkapplication \
        "${app}" \
        -n dw-spark \
        >/dev/null 2>&1
    then

        echo "WARN: SparkApplication not found: ${app}"

        continue

    fi


    {
        echo
        echo "============================================================"
        echo "SPARKAPPLICATION: ${app}"
        echo "============================================================"
        echo

        kubectl get sparkapplication \
            "${app}" \
            -n dw-spark \
            -o json \
        | python3 -c '
import json
import sys

obj = json.load(sys.stdin)

out = {
    "metadata": {
        "name": obj["metadata"]["name"],
        "namespace": obj["metadata"].get("namespace"),
        "labels": obj["metadata"].get("labels", {})
    },
    "spec": obj["spec"]
}

print(
    json.dumps(
        out,
        indent=2
    )
)
'

        echo

    } >> "${SPARK_REPORT}"

done


echo "Report:"
echo "  ${SPARK_REPORT}"

echo


# ============================================================
# 4. Capture relevant ConfigMap source
# ============================================================

echo "[4/6] Capturing application ConfigMaps..."

CONFIGMAPS=(
    phase3c-patients-raw-app
    phase3c-validate-patients-raw-app
    phase3c-map-person-omop-app
    phase3c-validate-omop-person-app
    phase3c-load-person-cdm-app
)


for cm in "${CONFIGMAPS[@]}"
do

    if ! kubectl get configmap \
        "${cm}" \
        -n dw-spark \
        >/dev/null 2>&1
    then

        echo "WARN: ConfigMap not found: ${cm}"
        continue
    fi


    {
        echo
        echo "============================================================"
        echo "CONFIGMAP: ${cm}"
        echo "============================================================"

        kubectl get configmap \
            "${cm}" \
            -n dw-spark \
            -o json \
        | python3 -c '
import json
import sys

obj = json.load(sys.stdin)

print(
    json.dumps(
        obj.get("data", {}),
        indent=2
    )
)
'

        echo

    } >> "${SOURCE_REPORT}"

done


echo "ConfigMap application source appended."

echo


# ============================================================
# 5. Capture Secret KEY NAMES only
# ============================================================

echo "[5/6] Capturing runtime Secret key names..."

: > "${SECRET_REPORT}"


for secret in \
    dw-spark-s3-secret \
    dw-spark-omop-secret
do

    {
        echo "SECRET=${secret}"

        kubectl get secret \
            "${secret}" \
            -n dw-spark \
            -o go-template='{{range $k,$v := .data}}{{printf "  %s\n" $k}}{{end}}'

        echo

    } >> "${SECRET_REPORT}"

done


cat "${SECRET_REPORT}"

echo "NOTE: values were NOT read or printed."

echo


# ============================================================
# 6. Produce compact blueprint summary
# ============================================================

echo "[6/6] Building compact blueprint summary..."

{
    echo "TASK-002 LEGACY PERSON BLUEPRINT"
    echo "================================"
    echo

    echo "Python source files:"
    grep '^FILE:' "${SOURCE_REPORT}" || true
    echo

    echo "SparkApplications:"
    for app in "${APPS[@]}"
    do
        kubectl get sparkapplication \
            "${app}" \
            -n dw-spark \
            -o custom-columns='NAME:.metadata.name,STATE:.status.applicationState.state,IMAGE:.spec.image,MAIN:.spec.mainApplicationFile' \
            --no-headers \
            2>/dev/null \
            || true
    done

    echo

    echo "Spark runtime:"
    kubectl get sparkapplication \
        phase3c-patients-raw \
        -n dw-spark \
        -o json \
    | python3 -c '
import json
import sys

spec = json.load(sys.stdin)["spec"]

print("type                 =", spec.get("type"))
print("mode                 =", spec.get("mode"))
print("image                =", spec.get("image"))
print("mainApplicationFile  =", spec.get("mainApplicationFile"))
print("sparkVersion         =", spec.get("sparkVersion"))
print(
    "driver.serviceAccount =",
    spec.get("driver", {}).get("serviceAccount")
)
print(
    "driver.cores          =",
    spec.get("driver", {}).get("cores")
)
print(
    "driver.memory         =",
    spec.get("driver", {}).get("memory")
)
print(
    "executor.instances    =",
    spec.get("executor", {}).get("instances")
)
print(
    "executor.cores        =",
    spec.get("executor", {}).get("cores")
)
print(
    "executor.memory       =",
    spec.get("executor", {}).get("memory")
)

print()
print("Spark conf:")

for k, v in sorted(
    spec.get("sparkConf", {}).items()
):
    print(f"  {k}={v}")
'

    echo

    echo "Secret key names:"
    cat "${SECRET_REPORT}"

    echo

    echo "Demographic mapping:"
    cat "${LEGACY}/mappings/person-demographic-mapping.csv"

} > "${SUMMARY}"


cat "${SUMMARY}"

echo


echo "============================================================"
echo "TASK-002 STEP 02 RESULT"
echo "============================================================"
echo
echo "STEP02=PASS"
echo "LEGACY_PYTHON_CAPTURED=${SOURCE_FILES_CAPTURED}"
echo "SPARKAPPLICATION_BLUEPRINT=CAPTURED"
echo "CONFIGMAP_BLUEPRINT=CAPTURED"
echo "SECRET_VALUES_EXPOSED=NO"
echo "S3_WRITE=NOT_RUN"
echo "DATABASE_WRITE=NOT_RUN"
echo "PHASE3C_TOUCHED=NO"
echo
echo "Reports:"
echo "  ${SOURCE_REPORT}"
echo "  ${SPARK_REPORT}"
echo "  ${SECRET_REPORT}"
echo "  ${SUMMARY}"
echo "============================================================"

