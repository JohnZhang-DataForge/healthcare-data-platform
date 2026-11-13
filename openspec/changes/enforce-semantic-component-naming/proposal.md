# Proposal — Enforce semantic component naming across repositories

## Why

Existing policy prohibits development task/step IDs from production names, but the implemented path gate matches only `taskNNN/stepNNN` and only newly added paths. New `G5/P2/F1/B4` source identifiers, schema names and Workflows passed CI. Healthcare's trusted required gate protects its own policy implementation; this change SHALL NOT bypass or silently mutate that protection. Self-Runner lacks an equivalent repository naming guard.

## What Changes

- Establish an explicit no-development-phase-ID policy for *new* business identifiers, file paths, pipeline names, status/error codes, and protocol identifiers. Recognize project-specific `G/P/F/B` single-digit stage segments and `task/step` counters; do not forbid true standards/versions such as FHIR R4, HL7 v2, OMOP CDM 5.4, or package versions.
- Add a read-only, diff-aware semantic checker with positive and negative regression tests, wired to Healthcare's existing head-branch Component Code Naming workflow for immediate feedback.
- Mirror the policy and tests into the Self-Runner repository and wire a dedicated PR check there.
- Require a separately authorized governance rollout to place the checker under trusted-default-branch execution and protected Required status. A green advisory check is **not** the same as an enforceable required protection.
- Retain historical frozen on-disk protocols, runtime interfaces, old task directories and evidence unchanged pending explicit compatibility migration. No production code rename in this PR.

## Impact

Healthcare: quality script, CI, tests, engineering policy/source map and this active Change. Self-Runner: separate implementation PR. No Azure, Fabric, Blob, K8s, PostgreSQL, OMOP or deployed artifact mutation.

## Scope

This change is static repository tooling and policy only, with no new business wire contract. `skip_specs: true` keeps it distinct from future separately approved protocol migrations.
