# Fabric Environments — CODE / 唯一原生源码地图

**历史 P3 验收（2026-11-01；已被下方 G5 0.1.3 发布覆盖）：** `healthcare-omop` 的原生 `env_healthcare.Environment` 已通过可信 Git 更新部署 Wheel **0.1.1** 到云端 Staging，且已完成 **Fabric Environment 正式 Publish**，GA Published Libraries API 独立读回唯一 0.1.1 Wheel。Git/云端的库**文件名/发布状态**已验收；另在独立、由 Git 新建的临时 Notebook 中，**Environment 绑定和 Spark 4.1/Wheel 0.1.1 导入已真实运行 PASS**（[Run 41478807776](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41478807776)）。**正式业务 `nb_fhir_ingest` 的 Runtime/患者数据 E2E 尚未运行验收**；该临时 Notebook 已受控删除。

## 原生 Git 来源

| 原生源码文件 | 用途 |
| --- | --- |
| [env_healthcare.Environment/.platform](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/.platform) | Fabric Git 原生 Environment 元数据，保持 `logicalId` 不变 |
| [env_healthcare.Environment/Setting/Sparkcompute.yml](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Setting/Sparkcompute.yml) | Spark compute 声明；真实 Staging 读回 Runtime 2.0 |
| [env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.6-py3-none-any.whl](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.6-py3-none-any.whl) | 唯一 Git Review 0.1.6 Wheel（**尚未同步/Published 到 Fabric**）；Git/CI SHA256 `473df0171de89a1260ce8bd4b58de301802a23f28cd7c6007c8f9563772748ff`，发布后的 Library List 只验证**库名称**，不直接提供 Wheel 文件内容 SHA |

新增原生定义要在 CODE 映射中注册。Shared 源码只能在 `shared-data-engine/` 维护，Environment 的 `CustomLibraries/` 仅保存已构建版本制品；避免复制源码或同时保留多个 Wheel。

## P3 已完成的发布证据

- 受审 Git Wheel：Healthcare [PR #590](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/590)，0.1.1 Wheel 双重可重复构建、Python 3.11 / 3.13 安装与 PySpark 3.5.7 / 4.1.1 测试 PASS。
- [Self-Runner PR #384](https://github.com/JohnZhang-DataForge/Self-Runner/pull/384)，可信 [Run #41323755874](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41323755874)：受控 Git `UpdateFromGit` 一次，Staging 从仅 0.1.0 变更为仅 **0.1.1**，Notebook/Pipeline 原生定义前后 SHA256 一致；可恢复备份 Artifact `fabric-p3-environment-sync-41323755874`。
- [Self-Runner PR #385](https://github.com/JohnZhang-DataForge/Self-Runner/pull/385)，可信 [Run #41325158603](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41325158603)：正式版 `POST /staging/publish?beta=false` **只提交一次**，HTTP 202 → LRO `Succeeded`，Environment `publishDetails.state=Success`、`sparkLibraries.state=Success`、`targetVersion` 存在；`GET /libraries?beta=false` 独立读回仅 **0.1.1**（1 custom，0 external，旧 0.1.0 不存在）。发布证据 artifact `fabric-p3-environment-publish-41325158603`。

**仍然 HOLD（仅正式业务 Runtime/ETL）：** Git `main` 中 `nb_fhir_ingest` 已将 Engine 版本检查更新到 **0.1.1**，Native Notebook 已通过云端代码/Environment 定义读回；**但是正式业务 Notebook 自身的 Spark Runtime Smoke 和 FHIR Bronze/Silver 写入仍未验收**。此前已由**另一份全新 Git-native 临时 Notebook**真实验证 Spark 4.1 + Wheel 0.1.1 导入，不得把该结果外推为业务 Notebook 已运行。继续保留 `run_mode=HALT`、`write_authorized=False`、`retention_preflight_verified=False`，业务运行必须独立授权及验收。参见 [Notebook Git-first E2E 证据](../../../../openspec/changes/archive/2026-11-05-fabric-native-notebook-git-onboarding/tasks.md)。

详细受控发布记录见 [P3 Wheel Release Preflight](P3-WHEEL-RELEASE-PREFLIGHT.md)，Notebook/Environment Git-first 机制见 [Fabric Runbook](../notebooks/FABRIC-GIT-AUTHORING-RUNBOOK.md)。

## G5 0.1.3 正式 Environment Published — 2026-11-04

- [Healthcare PR #652](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/652): exact 0.1.3 Native Git Wheel with immutable SHA256 `6f5d95a47ab87a553686afcdc405343198ded6c99d244eb57c6ab2907a1fac59`. Old 0.1.1 was replaced in Git, not duplicated.
- [Self-Runner #41832838614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41832838614) read-only verified **five** Fabric Git changes: one remote-only Environment and four local-only Warehouse/Lakehouse/Notebook/Pipeline changes. No conflicts; preserve all four local items.
- [Self-Runner #41833502954](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41833502954): exact 0.1.3 Wheel **real Staging sync PASS**, local-only items preserved.
- [Self-Runner #41834029745](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41834029745): official GA `POST /staging/publish?beta=false` single-call HTTP202, LRO/Publish Success, independent **Published sole Custom Wheel 0.1.3** readback and Runtime 2.0 PASS.
- **历史版本说明**：隔离 Spark 0.1.3 Import 已于下方 Run #41835694167 PASS；当前 Native 业务 Notebook 守卫已是 `engine_version == 0.1.3` 并保留 HALT，正式 G5/Gold 不等同于该 Import。 Do not run business Notebook until its package version and safeguards are reviewed.



### G5 实机 0.1.3 Spark Runtime Import 验收 — 2026-11-04

[Self-Runner #41835694167](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167) completed SUCCESS: published `env_healthcare` 0.1.3 preflight PASS; ephemeral Notebook exact definition readback PASS, Spark Job **Completed** with `G5_ENGINE_013_SPARK41_IMPORT_PASS`; temporary Notebook cleanup independently PASS. This supersedes previous 0.1.3 import HOLD, **not** the separate G5 business Notebook HALT/Gold COMMIT/Replay gates. Native business `nb_fhir_ingest` 已在后续 PR 中 source-guard 0.1.3，仍为 HALT；新 0.1.6 Git Wheel 发布和 Notebook 切换尚未完成。

## G5 0.1.6 Git review candidate — superseded by true Cloud Staging
This 0.1.6 Wheel replaced 0.1.3 in the immutable Git review branch. **At that Git-only moment** there was no Fabric staging/Publish/import. A later independently verified Fabric Git update has since confirmed cloud **Staging 0.1.6**, with GA Published still **0.1.3** at the live readback time (details below).

- Staging Workflows [#42280473991](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42280473991) **SUCCESS**: exact subtree `987ff3436761de57682d93f9a1c1205a42a8d242`, SHA256 `473df0171de89a1260ce8bd4b58de301802a23f28cd7c6007c8f9563772748ff` and four exact Git-only paths. Existing 0.1.3 Git Wheel removed, not both shipped. In this PR the historical 0.1.3 wheel is loaded only from immutable commit `b56b73207f7abe9d98e3fa4c3603fe045af6e15a` for old Notebook offline tests. **No Fabric UpdateFromGit, no Environment Publish, no cloud import yet**.

### 2026-11-06 — Cloud staging 0.1.6 independently verified, GA Publish separate

- [Real GET-only release audit #42282151277](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42282151277) initially saw Staging=0.1.3 and Published=0.1.3, five bounded Git differences, zero conflicts.
- [Git sync Run #42283543934](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42283543934) passed exact five-item/HEAD preflight and submitted exactly one `UpdateFromGit` POST (202), then lost operation GET connectivity. **Do not retry the acknowledged POST**; its original GitHub job is FAILED and remains so.
- Independent follow-up [GET-only Run #42283214760](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42283214760) **SUCCESS** with real cloud Staging **sole 0.1.6**, Published **sole 0.1.3**, Git synced/remote/workspace SHA `175caee20289f4b8056f4d39b4edca3a71210d61`, four local-only items unchanged, 0 remote changes, 0 conflicts. No cloud write from verification.
- Effective GA Publish and new Spark runtime import are separate gates. The existing Native business Notebook still checks 0.1.3 and is `HALT`. **Do not infer 0.1.6 Published from Cloud staging or from a Git-only review.**
