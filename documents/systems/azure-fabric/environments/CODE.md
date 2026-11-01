# Fabric Environments — CODE / 唯一原生源码地图

**当前状态：原生 `env_healthcare.Environment` 已由 Fabric Git Integration 真实导出。** 初始化 Commit `a6c3d0d6`；`.platform` logicalId 非零。**截至 2026-11-01 的真实只读检查：Git main 已声明 0.1.1，Fabric 云端 Staging 仍是 0.1.0，Published Libraries API HTTP 404；历史 Publish Success 不能证明 0.1.1 生效。**

## 实际拥有的原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| [env_healthcare.Environment/.platform](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/.platform) | Fabric Git 同步的 Environment 原生元数据；不要手工改 logicalId |
| [env_healthcare.Environment/Setting/Sparkcompute.yml](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Setting/Sparkcompute.yml) | Fabric 导出的 Spark compute 配置；Wheel 有效发布仍需独立读回 |
| [env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.1-py3-none-any.whl](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.1-py3-none-any.whl) | 唯一 Shared Engine Wheel；Git Wheel SHA256 4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3；Git main 0.1.1 版本/哈希 CI PASS；可信云端 GET 证明 Staging **仍仅有 0.1.0**、Published 404 UNKNOWN，0.1.1 未在云端 Staging |

新增原生定义时，每一个真实源文件都必须单独使用 `../../../../azure-fabric/workspaces/healthcare-omop/environments/...` 相对链接列入本表。Shared 源码不可复制到 Environment Item；只能安装发布已构建、固定版本/hash 的唯一 Shared Engine Wheel。

**历史 P2 与当前 P3 必须分开：** P2 0.1.0 曾进入 Fabric Staging；P3 0.1.1 已在 Git main 声明但尚未云端同步。Published 当前有效版本、Notebook 绑定和 Spark import 均未通过验收。不要把 CI Wheel 当作运行环境已安装。

**当前没有 P3 Cloud Staging/PUBLISH。** 可信只读 Git status 发现 env_healthcare 有 remote-only Modified、Notebook 与 Pipeline 有 workspace-only Modified；自动同步已按策略 HOLD。后续 Git UpdateFromGit、Environment Publish、Notebook 版本/绑定和 Spark Session 必须分别评估及授权。

**关键经验：** Git Sync → Staging → Publish → Published List → Notebook binding → Runtime 是不同的验证门禁。详见 [Fabric Notebook/Environment Git-first Runbook](../notebooks/FABRIC-GIT-AUTHORING-RUNBOOK.md)。历史 [Self-Runner Run #41263182097](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41263182097) 与发布后只读重跑记录：Staging Wheel 已存在；Published list HTTP 404；Publish Success 不能单独证明新 Wheel 有效。请先验收，不要由 Agent 无授权触发 Publish。

**P3 0.1.1 Git-only 声明替换：** PR #590 删除旧 0.1.0 Wheel，并声明唯一 0.1.1 Wheel（SHA256 `4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3`）。即使此 PR 合并，**Git main 发生变更不等于 Fabric staging 已同步，更不等于 Publish**；需按单独门禁读取 Fabric Staging/Published 和 Notebook 环境。Environment Publish、Notebook binding 和 Spark import 均保持 HOLD。

## P3 实际云端预检与受控发布

参见 [P3 Wheel Release Preflight](P3-WHEEL-RELEASE-PREFLIGHT.md)；可信 Self-Runner [GET-only Run #41319069996](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41319069996) 全部 3 jobs PASS，证实云端旧 Staging、新 Git main 和双向漂移。现阶段 HOLD，无自动 Git Update、无 Publish、无 Session/数据写入。
