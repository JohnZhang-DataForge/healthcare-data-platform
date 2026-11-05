# Shared Engine scoped Agent and documentation consolidation

## 0 — Baseline and scope
- [x] 0.1 Read main `ba01b4e7d2aa28831264998e5d4366bb9a8321c5`, zero open PRs, source AGENTS/README, centralized README/CODE, owner policy, package source and authoritative Fabric Publish/Import evidence.
- [x] 0.2 Freeze scope to Markdown/Agent only; no Python source/tests/contract/Workflow/native Wheel/Runtime.

## 1 — Implement
- [x] 1.1 Retain and simplify scoped `shared-data-engine/AGENTS.md`, removing obsolete implementation/version status.
- [x] 1.2 Transfer unique source README procedures and limits to centrally owned BUILD-AND-TEST; retire source README.
- [x] 1.3 Update centralized README/CODE and engineering ownership policy; distinguish 0.1.3 source/offline CI, Published/isolated Import and unaccepted business E2E.
- [x] 1.4 PR #707 final HEAD `5d142d205b6e4aa3cff86069d4068f07a82dc4e3`: Required `require-trusted-change` #127589931614, `validate-openspec` #127589930614 and `require-trusted-fabric-deployment-owner` #127589931701 SUCCESS; `check-links` #127589929973 SUCCESS; Shared Engine Python 3.11 Wheel #127589929749 and Python 3.13/Spark 4.1 Wheel #127589930326 SUCCESS. The unrelated Cloudflare Portal build failed but is NOT Required/Shared Engine acceptance.

## 2 — Protected acceptance
- [x] 2.1 PR #707 squash-merged to main `343c58f886f2ad461c8fefaaea2049b32881803d` with all three Required Checks green. Independent main Git-tree readback confirms scoped `shared-data-engine/AGENTS.md` present, source `README.md` absent, centralized `BUILD-AND-TEST.md` present, no open PRs. Base/head Git blob comparison: all 33 tracked shared Python/test/Contract/package and Fabric Native Item/Contract blobs unchanged.
- [x] 2.2 Publish Current Spec `openspec/specs/shared-engine-documentation-ownership/spec.md` and move the five change files unchanged except final evidence in tasks to `openspec/changes/archive/2026-11-05-align-shared-engine-agent-and-documentation/` using protected PR #708. The archive PR itself requires three Required Checks and independent main readback; no Fabric runtime action.

## Final audited scope (2026-11-05 ET)

- Source README retired under the repository's frozen exact legacy path rules (baseline unchanged); no new source-area Markdown introduced.
- Source `AGENTS.md` remains scoped; actual Python package `pyproject.toml` is 0.1.3. CI Pythons 3.11 and 3.13 both PASS without any new source, test or Native Environment Wheel changes.
- Published Fabric 0.1.3 and isolated Spark Import referenced by previously accepted Self-Runner Run #41834029745 and #41835694167; this document migration did NOT perform live Fabric operations and does NOT accept business `nb_fhir_ingest`, Silver data approval, Warehouse Gold COMMIT, or replay.
- Fixed-SHA historical Wheel staging workflows were not modified. Existing source-root Git tree SHA changes from AGENTS/README docs only; do not interpret pinned historical staging Workflow as current build validation.
