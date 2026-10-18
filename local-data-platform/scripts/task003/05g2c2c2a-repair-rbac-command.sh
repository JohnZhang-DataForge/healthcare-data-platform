#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

RUNNER="$ROOT/scripts/task003/05g2c2c2a-check-runtime-readonly.sh"
GEN="$ROOT/scripts/task003/05g2c2c2a-prepare-runtime-readonly.sh"

echo '#### TASK003 STEP05G2C2C2A RBAC REPAIR OUTPUT BEGIN ####'

finish() {
  rc=$?
  trap - EXIT
  echo "REPAIR_EXIT_CODE=$rc"
  echo '#### TASK003 STEP05G2C2C2A RBAC REPAIR OUTPUT END ####'
  exit "$rc"
}
trap finish EXIT

echo '=== 1. Repair formal runner and source generator ==='

python3 - "$RUNNER" "$GEN" <<'PY_PATCH'
import os
import stat
import sys
import tempfile
from pathlib import Path

paths = [Path(value) for value in sys.argv[1:]]

START = 'if kubectl auth can-i get configmaps ' + chr(92) + '\n'
END = "echo 'SPARK_JOB_NAMED_CONFIGMAP_GET=PASS'"

NEW = r'''if kubectl auth can-i get "configmaps/$LOCK" \
    --as="$SA" \
    -n dw-spark \
    > "$REPORT/named-configmap-can-i.txt" \
    2> "$REPORT/named-configmap-can-i.stderr"; then
  AUTH_RC=0
else
  AUTH_RC=$?
fi

ANSWER=$(tr -d '[:space:]' < "$REPORT/named-configmap-can-i.txt")

if [[ "$AUTH_RC" -eq 0 && "$ANSWER" == yes ]]; then
  echo 'SPARK_JOB_NAMED_CONFIGMAP_GET=PASS'
elif [[ "$ANSWER" == no ]]; then
  echo 'SPARK_JOB_NAMED_CONFIGMAP_GET=NO'
  echo 'RUNTIME_PREFLIGHT=STOP_RBAC'
  echo 'NO_RBAC_CHANGED=YES'
  exit 3
else
  echo 'SPARK_JOB_NAMED_CONFIGMAP_GET=CHECK_FAILED'
  echo "AUTH_EXIT_CODE=$AUTH_RC"
  echo 'ERROR: Kubernetes authorization review failed'
  sed -n '1,20p' "$REPORT/named-configmap-can-i.stderr"
  exit 1
fi'''

required = (
    '--resource-name="$LOCK"',
    "echo 'RUNTIME_PREFLIGHT=STOP_RBAC'",
    "SPARK_JOB_NAMED_CONFIGMAP_GET=CHECK_FAILED",
)

planned = []
original_blocks = []

# First verify BOTH files, before modifying either.
for path in paths:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(
            'Missing or unsafe formal source: ' + str(path)
        )

    source = path.read_text()

    if source.count(NEW) == 1 and source.count(START) == 0:
        planned.append((path, None))
        continue

    if source.count(START) != 1 or source.count(END) != 1:
        raise RuntimeError(
            'Unexpected original structure: ' + str(path)
        )

    begin = source.index(START)
    end = source.index(END, begin) + len(END)

    original = source[begin:end]

    if not all(item in original for item in required):
        raise RuntimeError(
            'Original RBAC block does not match: ' + str(path)
        )

    original_blocks.append(original)

    planned.append((
        path,
        source[:begin] + NEW + source[end:]
    ))

if len(set(original_blocks)) > 1:
    raise RuntimeError(
        'Runner and generator contain different RBAC blocks'
    )

for path, updated in planned:
    if updated is None:
        print('RBAC_SOURCE_REUSED=' + path.name)
        continue

    metadata = path.stat()

    fd, temporary = tempfile.mkstemp(
        prefix='.' + path.name + '.repair-',
        dir=str(path.parent),
    )

    try:
        with os.fdopen(fd, 'w') as output:
            output.write(updated)

        os.chmod(
            temporary,
            stat.S_IMODE(metadata.st_mode)
        )

        os.replace(temporary, path)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    print('RBAC_SOURCE_REPAIRED=' + path.name)

print('RBAC_SOURCE_PATCH=PASS')
PY_PATCH

echo '=== 2. Syntax and canonical consistency ==='

bash -n "$RUNNER"
bash -n "$GEN"

python3 - "$RUNNER" "$GEN" <<'PY_CHECK'
import sys
from pathlib import Path

runner, generator = [
    Path(value).read_text()
    for value in sys.argv[1:]
]

for source in (runner, generator):
    assert 'can-i get "configmaps/$LOCK"' in source
    assert '--resource-name="$LOCK"' not in source
    assert "RUNTIME_PREFLIGHT=STOP_RBAC" in source
    assert "AUTH_RC=$?" in source

print('NAMED_RESOURCE_SYNTAX=PASS')
print('RBAC_NO_HANDLING=PASS')
print('RUNNER_AND_GENERATOR_PATCH=PASS')
PY_CHECK

echo '=== 3. Verify permanent generator rebuild ==='

# Re-run the repaired generator. It must reproduce the same runner.
BEFORE=$(sha256sum "$RUNNER" | awk '{print $1}')

bash "$GEN"

AFTER=$(sha256sum "$RUNNER" | awk '{print $1}')

[[ "$BEFORE" == "$AFTER" ]] || {
  echo 'ERROR: generator rebuild changed formal runner'
  exit 1
}

echo 'CANONICAL_REBUILD=PASS'
echo 'RUNNER_SHA256_UNCHANGED=PASS'
echo 'RBAC_REPAIR=PASS'
echo 'RBAC_MODIFIED=NO'
echo 'K8S_RESERVATION_CREATED=NO'
echo 'S3_WRITE=NO'
echo 'DATABASE_WRITE=NO'
