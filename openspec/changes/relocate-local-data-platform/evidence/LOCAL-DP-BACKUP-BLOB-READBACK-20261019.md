# Local DP — current 393/393 Git Blob backup readback (Task 4.8 partial)

> **2026-10-19: REAL CROSS-REPOSITORY GIT TREE COMPARISON; READ-ONLY.** This verifies frozen Git-source backup content at two immutable commits. It does **not** verify Kubernetes/PG/S3, image rollback, or absent runtime consumers. Task 4.8 remains **OPEN** because delete-candidate-by-candidate safety gates are incomplete.

## Sources and method

1. Authoritative current Healthcare source: [Healthcare commit `ea2d2e5ffd98c529c79626c7c926828a32fb7a7b`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/ea2d2e5ffd98c529c79626c7c926828a32fb7a7b), [recursive Git Tree](https://api.github.com/repos/JohnZhang-DataForge/healthcare-data-platform/git/trees/ea2d2e5ffd98c529c79626c7c926828a32fb7a7b?recursive=1), **not truncated**.
2. Historical private Healthcare-Specs backup: [`6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`](https://github.com/JohnZhang-DataForge/Healthcare-Specs/tree/6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5), [recursive backup Git Tree](https://api.github.com/repos/JohnZhang-DataForge/Healthcare-Specs/git/trees/6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5?recursive=1), **not truncated**. This repository is private and recoverability requires ongoing access.
3. Treat `local-data-platform/` in Healthcare and `backup/local-data-platform-20261018-eb216b54/` in Healthcare-Specs as corresponding source prefixes. Exclude **only** the two non-business backup metadata files `README.md` and `SOURCE-BLOBS.tsv` from the backup count.
4. For each tracked source path, look up its corresponding backup file, compare **full Git object Blob SHA**; check both directions for extra/missing paths. This is stronger than filenames or rough file counts alone, and it does not require running any historical Shell or generating data.

## Verified result

| Check | Actual result |
| --- | ---: |
| Healthcare current tracked Local DP blobs | **393** |
| Backup corresponding business blobs | **393** |
| **Exact relative path + Blob SHA matches** | **393 / 393** |
| Missing current source in backup | **0** |
| Different content / mismatched Blob SHA | **0** |
| Extra backup business paths not on current Local DP tree | **0** |
| Recursive Git Trees truncated | **NO (both)** |
| Git source content backup verdict at these two SHAs | **PASS** |
| Current live deployment / Docker / database / object store recovery | **NOT CHECKED** |
| Delete candidates approved | **0** |

**Caveats**: the backup is a Git source tree, not a Git-ref/branch or OCI image registry snapshot. A removed file can be restored **from its exact blob** only when the corresponding repository and Git commit remain available and any dependent historical workflow/version is considered. Do not assume private backup access is available to all contributors or automated runners. If main source changes after the pinned Healthcare SHA, this PASS must be **recomputed against the new SHA** before deleting the modified file. Do not imply a current repo-wide Git clone or rebuilt image was verified; this was a connector-based read-only Git object metadata comparison.

## Immediate next gates

- Continue OpenSpec 4.1 to complete implicit consumers, code-generators, safe source ownership, Airflow GitSync and Spark runtime provenance. An old `healthcare/apps/` path in a *frozen-SHA Self-Runner workflow* must not be mechanically retargeted.
- For each future 4.9/4.10 removal record **current** file path and Blob SHA, immutable recovery commit, exact consumer graph, surviving test assertions, CODE map, and clean source/build/DAG/Spark checks.
- No Git files were deleted or modified as a result of this backup verification; no K8s/PG/S3, Self-Runner dispatch, or Docker push was performed.
