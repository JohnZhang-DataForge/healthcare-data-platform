#!/usr/bin/env bash
set -Eeuo pipefail
[[ "${TASK_MODE:?}" == validate || "${TASK_MODE}" == execute ]]
export PYTHONDONTWRITEBYTECODE=1
echo "===== DEMO_CODE_BEGIN ====="
cat scripts/ci/examples/number_summary.py
echo "===== DEMO_CODE_END ====="
echo "===== DEMO_TEST_BEGIN ====="
python3 - <<'PY'
from scripts.ci.examples.number_summary import summarize
assert summarize([3, 5, 8, 13, 21]) == {
    "count": 5, "total": 50, "squares": [9, 25, 64, 169, 441]
}
try:
    summarize([])
except ValueError:
    pass
else:
    raise AssertionError("Expected empty input rejection")
print("DEMO_UNIT_TESTS=PASS")
PY
echo "===== DEMO_TEST_END ====="
