#!/usr/bin/env bash
# Universal, reproducible, fail-closed wrapper. Actual TASK/STEP implementation lives in its own frozen shell.
set -Eeuo pipefail
if [[ "$#" != 3 ]]; then echo "Usage: bash scripts/ci/run-task.sh TASK STEP validate|execute" >&2; exit 2; fi
TASK="$1"; STEP="$2"; TASK_MODE="$3"
[[ "$TASK" =~ ^[a-z][a-z0-9_-]{0,39}$ ]] || { echo "Invalid TASK" >&2; exit 2; }
[[ "$STEP" =~ ^[a-z][a-z0-9_-]{0,39}$ ]] || { echo "Invalid STEP" >&2; exit 2; }
[[ "$TASK_MODE" == validate || "$TASK_MODE" == execute ]] || { echo "Invalid MODE" >&2; exit 2; }
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
SCRIPT="scripts/ci/tasks/${TASK}/${STEP}.sh"
[[ -f "$SCRIPT" && ! -L "$SCRIPT" ]] || { echo "Missing or unsafe step script: $SCRIPT" >&2; exit 2; }
# On an admin-capable runner, execution mode is only allowed from a manually dispatched main branch.
if [[ "$TASK_MODE" == execute ]]; then
  [[ "${GITHUB_EVENT_NAME:-local}" == workflow_dispatch && "${GITHUB_REF_NAME:-}" == main ]] ||
    { echo "Execution mode requires manual workflow_dispatch from main" >&2; exit 3; }
fi
REPORT_DIR="${CI_REPORT_DIR:-${RUNNER_TEMP:-/tmp}/task-reports}"
mkdir -p "$REPORT_DIR"
export TASK STEP TASK_MODE
export PYTHONDONTWRITEBYTECODE=1
COMMIT="$(git rev-parse HEAD)"
BRANCH="${GITHUB_REF_NAME:-$(git branch --show-current)}"
RC=1
finish() {
  local previous_rc="$?"
  trap - EXIT
  local result=FAIL
  if (( previous_rc == 0 )); then result=PASS; fi
  {
    echo "===== GENERIC_TASK_RESULT_BEGIN ====="
    echo "TASK=$TASK"
    echo "STEP=$STEP"
    echo "MODE=$TASK_MODE"
    echo "BRANCH=$BRANCH"
    echo "COMMIT=$COMMIT"
    echo "SHELL=$SCRIPT"
    echo "EXIT_CODE=$previous_rc"
    echo "FINAL_STATUS=$result"
    echo "===== GENERIC_TASK_RESULT_END ====="
  } | tee "$REPORT_DIR/result.txt"
  python3 - "$REPORT_DIR/report.json" "$TASK" "$STEP" "$TASK_MODE" "$BRANCH" "$COMMIT" "$SCRIPT" "$previous_rc" "$result" <<'PY'
import json, sys
path, task, step, mode, branch, sha, shell, rc, status = sys.argv[1:]
with open(path, "w", encoding="utf-8") as out:
    json.dump(dict(task=task, step=step, mode=mode, branch=branch, commit=sha,
                   shell=shell, exit_code=int(rc), status=status), out, indent=2)
PY
  exit "$previous_rc"
}
trap finish EXIT
echo "===== GENERIC_TASK_BEGIN ====="
echo "CHECKOUT_COMMIT=$COMMIT"
if [[ -n "${GITHUB_SHA:-}" ]]; then
  [[ "$COMMIT" == "$GITHUB_SHA" ]] || { echo "SHA mismatch" >&2; exit 4; }
fi
echo "Running approved repo script: $SCRIPT"
bash "$SCRIPT"
echo "===== GENERIC_TASK_END ====="
