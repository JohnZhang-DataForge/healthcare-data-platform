# Fabric Environments — CODE / 唯一原生源码地图

**当前状态：原生 `env_healthcare.Environment` 已由 Fabric Git Integration 真实导出。** 初始化 Commit `a6c3d0d6`；`.platform` logicalId 非零。但目前只含 Spark 配置，**Shared Wheel 尚未安装和 Publish**。

## 实际拥有的原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| [env_healthcare.Environment/.platform](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/.platform) | Fabric Git 同步的 Environment 原生元数据；不要手工改 logicalId |
| [env_healthcare.Environment/Setting/Sparkcompute.yml](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Setting/Sparkcompute.yml) | Fabric 导出的 Spark compute 配置；Wheel 尚未发布 |
| [env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.0-py3-none-any.whl](../../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/Libraries/CustomLibraries/healthcare_data_engine-0.1.0-py3-none-any.whl) | 唯一 Shared Engine Wheel；SHA256 603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7；尚未在 Fabric 发布 |

新增原生定义时，每一个真实源文件都必须单独使用 `../../../../azure-fabric/workspaces/healthcare-omop/environments/...` 相对链接列入本表。Shared 源码不可复制到 Environment Item；只能安装发布已构建、固定版本/hash 的唯一 Shared Engine Wheel。

**P2 Git-first 阶段：** Shared Wheel 在独立 GitHub-hosted CI 构建并按固定 SHA256 校验，产生 Artifact；尚未纳入此 Environment 的 CustomLibraries，也没有在 Fabric 发布/读回有效版本。不要把 CI Wheel 当作运行环境已安装。

**Git-first Wheel 已暂存，非 Fabric Publish。** 后续仍需在目标 Workspace 验证 Git 更新、Environment Publish、有效 Wheel 版本及 Notebook Environment 绑定。
