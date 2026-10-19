# Local DP 105-test source-level triage — preserving useful regression coverage

> **PINNED STATIC REVIEW / NOT TEST EXECUTION:** Healthcare `ea2d2e5ffd98c529c79626c7c926828a32fb7a7b` (2026-10-19). This record inventories **105/105** `local-data-platform/tests/**/*.py` tracked test files. Each **HOLD** disposition protects coverage until old/new behavior and static/runtime tests have been compared on the migrated SHA.

A `taskXXX` directory or broken pre-move file path is **not a deletion reason**: fix test code/location if it preserves meaningful assertions; retire only after covering equivalent semantics elsewhere. Each signal is textual evidence, not a pass/fail verdict.

| # | Test (frozen SHA) | Git blob | Approx. test methods | Root-path marker | Safety/contract markers | Explicit script/app/DAG path strings (sample) | Review lane | Action |
| ---: | --- | --- | ---: | --- | --- | --- | --- | --- |
