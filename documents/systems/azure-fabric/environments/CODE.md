# Fabric Environments — CODE / 唯一原生源码地图

**当前状态：原生 `env_healthcare.Environment` 已由 Fabric Git Integration 真实导出。** 初始化 Commit `a6c3d0d6`；`.platform` logicalId 非零。当前 Shared Wheel 已进入真实 Fabric Staging；Published 列表的只读查询仍返回 HTTP 404，即使 Environment 曾显示 Publish Success，仍需验证当前 Wheel 是否有效。

## 实际拥有的原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| [env_healthcare.Environment/.platform](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/.platform) | Fabric Git 同步的 Environment 原生元数据；不要手工改 logicalId |
| [env_healthcare.Environment/Setting/Sparkcompute.yml](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Setting/Sparkcompute.yml) | Fabric 导出的 Spark compute 配置；Wheel 有效发布仍需独立读回 |
| [env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.1-py3-none-any.whl](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.1-py3-none-any.whl) | 唯一 Shared Engine Wheel；Git Wheel SHA256 4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3；0.1.1 仅在 Git 审阅分支中；Fabric 0.1.1 Staging/Published 尚未读回 |

新增原生定义时，每一个真实源文件都必须单独使用 `../../../../azure-fabric/workspaces/healthcare-omop/environments/...` 相对链接列入本表。Shared 源码不可复制到 Environment Item；只能安装发布已构建、固定版本/hash 的唯一 Shared Engine Wheel。

**P2 Git-first 阶段：** Shared Wheel 在独立 GitHub-hosted CI 构建并按固定 SHA256 校验，产生 Artifact；现已在 Git Environment CustomLibraries 与 Fabric Staging 中；Published 的当前有效版本和 Notebook 运行时绑定仍未通过验收。不要把 CI Wheel 当作运行环境已安装。

**Git-first Wheel 已暂存，非 Fabric Publish。** 后续仍需在目标 Workspace 验证 Git 更新、Environment Publish、有效 Wheel 版本及 Notebook Environment 绑定。

**关键经验：** Git Sync → Staging → Publish → Published List → Notebook binding → Runtime 是不同的验证门禁。详见 [Fabric Notebook/Environment Git-first Runbook](../notebooks/FABRIC-GIT-AUTHORING-RUNBOOK.md)。历史 [Self-Runner Run #41263182097](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41263182097) 与发布后只读重跑记录：Staging Wheel 已存在；Published list HTTP 404；Publish Success 不能单独证明新 Wheel 有效。请先验收，不要由 Agent 无授权触发 Publish。

**P3 0.1.1 Git-only 审阅候选：** 本分支将旧 0.1.0 Wheel 替换为唯一 0.1.1 Wheel（SHA256 `4a914830b4835f784ddae9f8f075279325550fd7f7a4b0aa345be26ef3f7a2a3`）。合并前不是 Git main，也不是 Fabric staging；合并后仍需要独立 readback。Environment Publish、Notebook binding 和 Spark import 均保持 HOLD。
