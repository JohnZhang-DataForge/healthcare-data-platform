#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="$ROOT/runtime/reports/task003/step05"

REPORT=''
FINAL_STATE='UNKNOWN'
DRIVER_POD=''

echo '#### TASK003 STEP05G2C2C3D1 WRITER OBSERVATION OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT

  [[ -z "$REPORT" ]] || echo "WRITER_OBSERVATION_REPORT=$REPORT"

  echo "FINAL_SPARK_APPLICATION_STATE=$FINAL_STATE"
  echo 'RESERVATION_RELEASED=NO'
  echo 'RUNTIME_CONFIGMAP_DELETED=NO'
  echo 'SPARKAPPLICATION_DELETED=NO'
  echo 'DATABASE_WRITE_BY_OBSERVER=NO'
  echo 'S3_WRITE_BY_OBSERVER=NO'
  echo "OBSERVE_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C3D1 WRITER OBSERVATION OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

[[ $# -eq 3 ]] || {
  echo "Usage: $0 RUN_ID ATOMIC_LAUNCH_REPORT C3A_REPORT"
  exit 2
}

RUN_ID="$1"
LAUNCH_REPORT="$2"
C3A_REPORT="$3"

LAUNCH_STATE="$LAUNCH_REPORT/run-state.json"
C3A_STATE="$C3A_REPORT/run-state.json"

for path in "$LAUNCH_STATE" "$C3A_STATE"; do
  [[ -s "$path" && ! -L "$path" ]] || {
    echo "ERROR: missing evidence: $path"
    exit 2
  }
done

for cmd in kubectl python3; do
  command -v "$cmd" >/dev/null || {
    echo "ERROR: missing command: $cmd"
    exit 2
  }
done

REPORT=$(
  mktemp -d \
    "$BASE/writer-observation.XXXXXXXX"
)

echo '=== 1. Validate launch evidence ==='

python3 - \
  "$LAUNCH_STATE" \
  "$C3A_STATE" \
  "$RUN_ID" \
  "$REPORT" \
  <<'PY'
import json
import sys
from pathlib import Path

launch = json.loads(Path(sys.argv[1]).read_bytes())
c3a = json.loads(Path(sys.argv[2]).read_bytes())
run_id = sys.argv[3]
report = Path(sys.argv[4])

assert (
    launch["task"],
    launch["step"],
    launch["status"],
) == (
    "TASK-003",
    "STEP-05G2C2C3C2",
    "SPARK_APPLICATION_SUBMITTED",
)

assert launch["run_id"] == run_id
assert launch["runtime_configmap_created"] is True
assert launch["spark_application_submitted"] is True
assert launch["candidate_published"] is False
assert launch["s3_write_verified"] is False
assert launch["postgresql_write"] is False

assert c3a["run_id"] == run_id
assert c3a["reservation_verified"] is True

report.joinpath("spark-app.txt").write_text(
    launch["spark_application_name"] + "\n"
)

report.joinpath("runtime-cm.txt").write_text(
    launch["runtime_configmap_name"] + "\n"
)

report.joinpath("lock.txt").write_text(
    c3a["reservation_name"] + "\n"
)

report.joinpath("lock-uid.txt").write_text(
    c3a["reservation_uid"] + "\n"
)

report.joinpath("lock-rv.txt").write_text(
    c3a["reservation_resource_version"] + "\n"
)

print("ATOMIC_LAUNCH_EVIDENCE=PASS")
print("SPARK_APPLICATION_NAME=" + launch["spark_application_name"])
print("RUNTIME_CONFIGMAP_NAME=" + launch["runtime_configmap_name"])
print("RESERVATION_NAME=" + c3a["reservation_name"])
PY

APP=$(tr -d '\r\n' < "$REPORT/spark-app.txt")
CM=$(tr -d '\r\n' < "$REPORT/runtime-cm.txt")
LOCK=$(tr -d '\r\n' < "$REPORT/lock.txt")
LOCK_UID=$(tr -d '\r\n' < "$REPORT/lock-uid.txt")
LOCK_RV=$(tr -d '\r\n' < "$REPORT/lock-rv.txt")

echo '=== 2. Verify runtime objects still exist ==='

kubectl -n dw-spark \
  get configmap "$CM" \
  -o json \
  > "$REPORT/runtime-configmap-live.json"

kubectl -n dw-spark \
  get sparkapplication "$APP" \
  -o json \
  > "$REPORT/sparkapplication-initial.json"

echo 'RUNTIME_CONFIGMAP_LIVE=PASS'
echo 'SPARK_APPLICATION_LIVE=PASS'

echo '=== 3. Reverify Writer Reservation ==='

kubectl -n dw-spark \
  get configmap "$LOCK" \
  -o json \
  > "$REPORT/reservation-live.json"

python3 - \
  "$REPORT/reservation-live.json" \
  "$LOCK_UID" \
  "$LOCK_RV" \
  <<'PY'
import json
import sys
from pathlib import Path

live = json.loads(Path(sys.argv[1]).read_bytes())

assert live["metadata"]["uid"] == sys.argv[2]
assert live["metadata"]["resourceVersion"] == sys.argv[3]
assert live.get("immutable") is True

print("LIVE_RESERVATION_STILL_IDENTICAL=PASS")
print("RESERVATION_LOCK_HELD=YES")
PY

echo '=== 4. Observe SparkApplication until terminal state ==='

LAST_STATE=''

for attempt in $(seq 1 180); do

  kubectl -n dw-spark \
    get sparkapplication "$APP" \
    -o json \
    > "$REPORT/sparkapplication-current.json"

  STATE=$(
    python3 - \
      "$REPORT/sparkapplication-current.json" \
      <<'PY'
import json
import sys
from pathlib import Path

obj = json.loads(Path(sys.argv[1]).read_bytes())

print(
    obj.get("status", {})
       .get("applicationState", {})
       .get("state", "NOT_REPORTED")
)
PY
  )

  if [[ "$STATE" != "$LAST_STATE" ]]; then
    echo "SPARK_APPLICATION_STATE=$STATE"
    LAST_STATE="$STATE"
  fi

  case "$STATE" in
    COMPLETED)
      FINAL_STATE=COMPLETED
      break
      ;;

    FAILED|SUBMISSION_FAILED|UNKNOWN|INVALIDATING)
      FINAL_STATE="$STATE"
      break
      ;;
  esac

  sleep 5
done

if [[ "$FINAL_STATE" == UNKNOWN ]]; then
  echo 'ERROR: SparkApplication did not reach a supported terminal state'
  exit 3
fi

kubectl -n dw-spark \
  get sparkapplication "$APP" \
  -o json \
  > "$REPORT/sparkapplication-final.json"

echo "SPARK_APPLICATION_TERMINAL_STATE=$FINAL_STATE"

echo '=== 5. Capture Driver identity and logs ==='

DRIVER_POD=$(
  python3 - \
    "$REPORT/sparkapplication-final.json" \
    <<'PY'
import json
import sys
from pathlib import Path

obj = json.loads(Path(sys.argv[1]).read_bytes())

print(
    obj.get("status", {})
       .get("driverInfo", {})
       .get("podName", "")
)
PY
)

if [[ -n "$DRIVER_POD" ]]; then

  echo "DRIVER_POD=$DRIVER_POD"

  if kubectl -n dw-spark \
      get pod "$DRIVER_POD" \
      -o json \
      > "$REPORT/driver-pod.json" \
      2> "$REPORT/driver-pod.stderr"
  then
    echo 'DRIVER_POD_READBACK=PASS'

    if kubectl -n dw-spark \
        logs "$DRIVER_POD" \
        --timestamps \
        > "$REPORT/driver.log" \
        2> "$REPORT/driver-log.stderr"
    then
      echo 'DRIVER_LOG_CAPTURE=PASS'
    else
      echo 'DRIVER_LOG_CAPTURE=UNAVAILABLE'
    fi
  else
    echo 'DRIVER_POD_READBACK=UNAVAILABLE'
    echo 'DRIVER_LOG_CAPTURE=UNAVAILABLE'
  fi

else
  echo 'DRIVER_POD=NOT_REPORTED'
  echo 'DRIVER_LOG_CAPTURE=UNAVAILABLE'
fi

echo '=== 6. Persist observation evidence ==='

python3 - \
  "$LAUNCH_STATE" \
  "$REPORT/sparkapplication-final.json" \
  "$REPORT" \
  "$RUN_ID" \
  "$FINAL_STATE" \
  <<'PY'
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

launch_path = Path(sys.argv[1])
app_path = Path(sys.argv[2])
report = Path(sys.argv[3])
run_id = sys.argv[4]
final_state = sys.argv[5]

launch_bytes = launch_path.read_bytes()
app_bytes = app_path.read_bytes()

launch = json.loads(launch_bytes)
app = json.loads(app_bytes)

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

state = {
    "task": "TASK-003",
    "step": "STEP-05G2C2C3D1",
    "status": (
        "SPARK_COMPLETED"
        if final_state == "COMPLETED"
        else "SPARK_TERMINAL_FAILURE"
    ),
    "run_id": run_id,
    "spark_application_name":
        launch["spark_application_name"],
    "spark_application_uid":
        launch["spark_application_uid"],
    "spark_application_state":
        final_state,
    "atomic_launch_state_sha256":
        sha(launch_bytes),
    "sparkapplication_final_sha256":
        sha(app_bytes),
    "reservation_released": False,
    "candidate_published_verified": False,
    "s3_write_verified": False,
    "postgresql_write": False,
    "observed_at_utc":
        datetime.now(timezone.utc).isoformat(),
}

target = report / "run-state.json"

target.write_text(
    json.dumps(
        state,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)

print("WRITER_OBSERVATION_STATE=PASS")
print("OBSERVATION_STATE_FILE=" + str(target))
print(
    "OBSERVATION_STATE_SHA256="
    + sha(target.read_bytes())
)
print("CANDIDATE_PUBLISHED_VERIFIED=NO")
print("S3_WRITE_VERIFIED=NO")
print("DATABASE_WRITE=NO")
PY

echo '=== 7. Final observation result ==='

if [[ "$FINAL_STATE" != COMPLETED ]]; then

  echo 'WRITER_EXECUTION_RESULT=TERMINAL_FAILURE'
  echo 'AUTOMATIC_CLEANUP=NO'

  if [[ -s "$REPORT/driver.log" ]]; then
    echo '--- DRIVER LOG TAIL BEGIN ---'
    tail -n 100 "$REPORT/driver.log"
    echo '--- DRIVER LOG TAIL END ---'
  fi

  exit 4
fi

echo 'WRITER_EXECUTION_RESULT=COMPLETED'
echo 'STEP05G2C2C3D1_WRITER_OBSERVATION=PASS'

if [[ -s "$REPORT/driver.log" ]]; then
  echo '--- DRIVER LOG TAIL BEGIN ---'
  tail -n 80 "$REPORT/driver.log"
  echo '--- DRIVER LOG TAIL END ---'
fi

echo 'CANDIDATE_PUBLISHED_VERIFIED=NO'
echo 'S3_WRITE_VERIFIED=NO'
echo 'DATABASE_WRITE=NO'
