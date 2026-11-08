# Design — Exact dbt tests exception with a protected policy rollout

## 1. Approved paths and negative boundary
- **Allow**: `azure-fabric/dbt/hl7-canonical/tests/.gitkeep` and named `*.sql` singular tests under that same exact project (nested domain subdirectories allowed).
- **Reject**: any `tests/*.py` / `.yml` / `README.md`, fake project `fhir-canonical/tests/`, generic `azure-fabric/warehouse/tests/`, unsafe traversal, nested `.gitkeep`; Python tests stay in `.github/quality/tests/`. YAML model schema tests stay beside dbt `models/` per existing convention.
- The checker already normalizes Git paths and rejects path traversal. Only the source-local test classification is exempted; code/map ownership, root list, Native Item policy, immutable baseline, protected policy mutation guard and required test checks remain unchanged.

## 2. Rollout constraints
The default-branch `openspec-trusted-change-gate.yml` runs `check_repository_layout.py` **from the trusted default branch**. That old checker explicitly rejects PRs that edit itself (`trusted-policy-mutation`), so this PR's Required `require-trusted-change` will be FAIL as designed even if its proposed rules are correct. Never claim that a PR-head unit test overrides this; it is only a candidate test.

**Administrator procedure (outside this agent's available write permissions):**
1. Review the exact governance diff and candidate's isolated positive/negative test results, verify PR head and no business/runtime changes.
2. In an explicitly approved, time-bounded maintenance window, temporarily adjust the specific GitHub Ruleset Required context blocking this protected policy update, **only** for this reviewed PR; leave unrelated protections and branch access intact. Record the window, approver and original rule.
3. Merge the reviewed PR with exact expected head, immediately restore the original Required Checks, and independently verify Ruleset and default-branch trusted gate.
4. Open a normal **positive** PR adding `tests/.gitkeep` in the approved project, confirm it passes; and a disposable **negative** PR adding `tests/helper.py` or foreign project `tests/`, confirm it is blocked, then close without merge. Do not count unit tests alone as proven enforcement.

If no administrative procedure is available, keep this exception PR **OPEN/BLOCKED** and do not submit new dbt project `tests/` to Main. No disabling protection silently; if a checker or required context is missing, HOLD.

## 3. Security and rollback
No Repo Secrets, Azure capacity, Fabric/Delta/warehouse or cloud API. The PR-head policy smoke uses plain `pull_request` with read-only permissions and runs Python unittest on the checkout with no secrets; the protected default-branch gate still executes only trusted base policy. Rollback, if needed, requires the same separately approved maintenance procedure, not a casual bypass.
