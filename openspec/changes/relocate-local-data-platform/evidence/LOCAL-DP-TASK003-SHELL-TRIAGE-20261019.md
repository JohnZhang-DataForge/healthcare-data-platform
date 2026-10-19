# Task003 historical shell inventory — deep static triage

> **Source snapshot**: Healthcare `ea2d2e5ffd98c529c79626c7c926828a32fb7a7b` (2026-10-19). Full set **94 tracked Shell files** under `local-data-platform/scripts/task003/`. **READ-ONLY SOURCE INSPECTION**. The results below are a *preliminary static triage*, NOT proof of absence of callers and NOT deletion authorization. No program was executed.

These observations must be combined with the full active CI/Docker/Runner/K8s/Spark call graph, actual unit/regression value, pinned restore SHA and safety review before a particular file can move from `HOLD` to `REMOVE`.

## Source-by-source facts

- `generate` = likely emits new code/artifacts via heredoc `cat >`, `write_text`, etc; not a verified replacement nor a valid reason to delete alone.
- `cluster`, `db`, `object` = **textual command/reference signals only**; do not interpret as executable behavior without control-flow review. Reading scripts has no side effects.
- `relative` = computes project root relative to its own location; `host-hardcoded` = literal old host path; `variable-default` = explicit override/default. These flags do not prove migrated runtime correctness.
- `HOLD` = no deletion approved. Every item listed retains exact Git blob SHA and a source URL.

| # | Shell (source at frozen SHA) | Blob SHA | Lines | Root resolution | Static signals | Observed direct Task003 script references | Candidate review lane | Action |
| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |
