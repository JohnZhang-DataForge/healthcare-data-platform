# Fabric Environments — CODE / 唯一原生源码地图

**当前验收（2026-11-01）：** `healthcare-omop` 的原生 `env_healthcare.Environment` 已通过可信 Git 更新部署 Wheel **0.1.1** 到云端 Staging，且已完成 **Fabric Environment 正式 Publish**，GA Published Libraries API 独立读回唯一 0.1.1 Wheel。Git/云端的库**文件名/发布状态**已验收；另在独立、由 Git 新建的临时 Notebook 中，**Environment 绑定和 Spark 4.1/Wheel 0.1.1 导入已真实运行 PASS**（[Run 41478807776](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41478807776)）。**正式业务 `nb_fhir_ingest` 的 Runtime/患者数据 E2E 尚未运行验收**；该临时 Notebook 已受控删除。

## 原生 Git 来源

| 原生源码文件 | 用途 |
| --- | --- |
| [env_healthcare.Environment/.platform](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/.platform) | Fabric Git 原生 Environment 元数据，保持 `logicalId` 不变 |
| [env_healthcare.Environment/Setting/Sparkcompute.yml](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Setting/Sparkcompute.yml) | Spark compute 声明；真实 Staging 读回 Runtime 2.0 |
| [env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.1-py3-none-any.whl](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.1-py3-none-any.whl) | 唯一 0.1.1 Wheel；Git/CI SHA256 `4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3`，发布后的 Library List 只验证**库名称**，不直接提供 Wheel 文件内容 SHA |

新增原生定义要在 CODE 映射中注册。Shared 源码只能在 `shared-data-engine/` 维护，Environment 的 `CustomLibraries/` 仅保存已构建版本制品；避免复制源码或同时保留多个 Wheel。

## P3 已完成的发布证据

- 受审 Git Wheel：Healthcare [PR #590](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/590)，0.1.1 Wheel 双重可重复构建、Python 3.11 / 3.13 安装与 PySpark 3.5.7 / 4.1.1 测试 PASS。
- [Self-Runner PR #384](https://github.com/JohnZhang-DataForge/Self-Runner/pull/384)，可信 [Run #41323755874](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41323755874)：受控 Git `UpdateFromGit` 一次，Staging 从仅 0.1.0 变更为仅 **0.1.1**，Notebook/Pipeline 原生定义前后 SHA256 一致；可恢复备份 Artifact `fabric-p3-environment-sync-41323755874`。
- [Self-Runner PR #385](https://github.com/JohnZhang-DataForge/Self-Runner/pull/385)，可信 [Run #41325158603](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41325158603)：正式版 `POST /staging/publish?beta=false` **只提交一次**，HTTP 202 → LRO `Succeeded`，Environment `publishDetails.state=Success`、`sparkLibraries.state=Success`、`targetVersion` 存在；`GET /libraries?beta=false` 独立读回仅 **0.1.1**（1 custom，0 external，旧 0.1.0 不存在）。发布证据 artifact `fabric-p3-environment-publish-41325158603`。

**仍然 HOLD（仅正式业务 Runtime/ETL）：** Git `main` 中 `nb_fhir_ingest` 已将 Engine 版本检查更新到 **0.1.1**，Native Notebook 已通过云端代码/Environment 定义读回；**但是正式业务 Notebook 自身的 Spark Runtime Smoke 和 FHIR Bronze/Silver 写入仍未验收**。此前已由**另一份全新 Git-native 临时 Notebook**真实验证 Spark 4.1 + Wheel 0.1.1 导入，不得把该结果外推为业务 Notebook 已运行。继续保留 `run_mode=HALT`、`write_authorized=False`、`retention_preflight_verified=False`，业务运行必须独立授权及验收。参见 [Notebook Git-first E2E 证据](../../../../openspec/changes/fabric-native-notebook-git-onboarding/tasks.md)。

详细受控发布记录见 [P3 Wheel Release Preflight](P3-WHEEL-RELEASE-PREFLIGHT.md)，Notebook/Environment Git-first 机制见 [Fabric Runbook](../notebooks/FABRIC-GIT-AUTHORING-RUNBOOK.md)。
