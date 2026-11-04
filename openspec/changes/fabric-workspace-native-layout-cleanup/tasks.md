# Tasks

- [x] 1.1 Inspect fresh Healthcare main, Workspace native item layout, legacy directories and protected Warehouse SQL source.
- [x] 1.2 Delete exactly the two obsolete empty `.gitkeep` files; retain all `*.Notebook`, `*.DataPipeline`, `*.Environment` and `*.Lakehouse` native Git items unchanged.
- [x] 1.3 Document the physical Warehouse Workspace affiliation and deliberately separate SQL source layout.
- [x] 1.4 GitHub PR #669 merged via squash to main `c6dfdc6dce0f85c830383b05c766e3660e12d14d`; six repository checks PASS (OpenSpec strict, trusted/change gates, docs links, source paths, Native Notebook offline). Verified obsolete paths absent and four canonical native Item directories retained on latest main.

## Final acceptance evidence — 2026-11-04

- [Merged PR #669](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/669) (commit `c6dfdc6dce0f85c830383b05c766e3660e12d14d`) deleted only two superseded empty placeholders and corrected canonical docs. No Warehouse SQL files or Git-native Fabric item content was changed.
- Six GitHub repository checks passed: `check-added-code-paths`, `check-links`, `validate-openspec`, `require-change`, `require-trusted-change`, `notebook-offline-contract`. A separate Cloudflare Workers healthcare-portal build check failed; not claimed as a Fabric validation pass and no Fabric deploy was triggered by these deleted non-native paths.
- Independent GitHub `main` API readback confirmed `notebooks/ingestion/` and `pipelines/` are absent and the actual `env_healthcare.Environment/`, `lh_omop_analytics.Lakehouse/`, `nb_fhir_ingest.Notebook/` and `pl_fhir_ingest.DataPipeline/` remain intact. Physical `dw-omop-5.4` stays in `healthcare-omop` as an existing protected Workspace-only item; SQL source remains under `azure-fabric/warehouse/`.
