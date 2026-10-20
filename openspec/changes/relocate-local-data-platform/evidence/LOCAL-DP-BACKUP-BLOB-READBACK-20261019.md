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


## 2026-10-20 增量备份完成：当前 Local DP 395/395（仅 Git Blob 与 File Mode）

> **在旧 393/393 冻结结果基础上追加，不改写当时 2026-10-19 的范围。** 固定 Healthcare Main [`57ce87f866f50f35fc28887c2fbd3675735dd394`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/57ce87f866f50f35fc28887c2fbd3675735dd394)，迁移后原 393 文件基线 [`f3b2d9e97d9afe4e7457a1d48fde9e655add47d7`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/f3b2d9e97d9afe4e7457a1d48fde9e655add47d7)，原独立私有备份 SHA `6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`；上述三份 Git Tree 均 `truncated=false`。
>
> 三方逐路径比较得到 **391 个原 Git Blob 不变（与原备份相同）+ 2 个现行 Test Git Blob 已修改 + 2 个 Quality 工具文件新增、0 删除**。修改或新增 4 个现行版本没有覆盖旧 393 文件快照，故独立追加：
>
> - 新增 `scripts/quality/read-only-gitsync-spark-provenance.sh`（Blob `bf17dbcd3b3b7fdf41c056d4eba8595ae43e6e1b`）；
> - 新增 `tests/quality/test_readonly_provenance_probe.py`（Blob `867d0ef7d2c7ae8cc40362de0089636d60e4c42c`）；
> - 修改 `tests/task004/test_synthea_ghcr_workflow.py`（当前 Blob `3ecb0834b79598f1711dc967d038e60150db3728`，原备份旧 Blob `3f32e7d3fc52f86f434711003d13a9da933e2dff`）；
> - 修改 `tests/task004/test_unified_runtime_image_source.py`（当前 Blob `0e29e560f93b3f9dc31644a647df6ba087d34c60`，原备份旧 Blob `5db8da588281c1509f854b1b6c8353a90759e517`）。
>
> **实际独立备份**：在 `JohnZhang-DataForge/Healthcare-Specs` 中，四份源文本经 Git Blob 独立创建，逐份与源仓库 SHA **4/4 精确一致**；[PR #3](https://github.com/JohnZhang-DataForge/Healthcare-Specs/pull/3) 已合并该仓 Main `18bd4fe2a22cc4a99ff0037364725790f11e6d9a`，只新增 `backup/local-data-platform-increment-20261020-57ce87f8/` 的 README、SOURCE-BLOBS.tsv 与四份源码；原 393 文件的 Snapshot 没有任何更改。
>
> **合并后独立读回**：同时读取固定 Healthcare 来源和新的 Healthcare-Specs Main 非截断 Git Tree，将原冻结 393 文件路径/Blob/Mode 与 4 文件增量在内存中 Overlay，得到 **395/395 路径 + Git Blob SHA + `100644` File Mode 精确一致，缺失 0、错误 0、额外文件 0**。此为**Git 对象级重建/读回对照**，没有实际执行 `git checkout` 还原到运行机，也不意味着 K8s/PG/S3、OCI 镜像或 DAG/Driver 已完成灾备演练。四个旧/新文件仍均属于工程保护或测试回归资产，不作为删除候选。
>
> Healthcare Main 随后被独立 Fabric 变更推进到 `addca9ed935b256931b8c67e349639a3f4bb5e9a`；实际 Git Compare 从 `57ce87f8` 到该 SHA，`local-data-platform/` **0 个文件变化**（仅在该比较区间成立）。未来 Source 变化仍需新版本/增量备份，不能把 395/395 推论为永久同步。
>
> **结论：源文件备份覆盖在上述固定源 SHA 下达到 395/395 PASS；4.8 仍 PARTIAL**，因为候选文件直接/间接消费者、行为兼容、实际业务恢复与删除授权尚未闭合。已删除/获准删除 **0/0**。
