---
status: active
scope: fabric-native-git-notebook-pipeline-environment-authoring
last_verified: 2026-11-01
verification_method: isolated-Fabric-API-roundtrip-and-live-GetDefinition
---

# Fabric 原生资源 Git-first 开发规范与事故复盘

**适用范围：** Healthcare Workspace 的 Notebook、DataPipeline、Environment，以及今后 Agent 开发的其他 Fabric 原生资源。

**首要原则：** Git 源码正确、CI 通过、Git 同步 SHA 正确、Fabric 云端保存的定义完整、Spark 依赖已经发布、业务处理成功，是六个不同的验证层次。前一层 PASS 不意味着后一层 PASS。

## 事故经过与确认的原因

2026-10-31 至 2026-11-01，GitHub main 的 nb_fhir_ingest.Notebook/notebook-content.py 保留了完整 P2 业务代码，但 Fabric Notebook 实际导出仅有 26 bytes。Git 同步已经抵达 f0603576，所以不是忘记 Update，也不是浏览器渲染问题。双格式只读验证证实：FabricGitSource 只有 26 B，ipynb 只有 145 B 且没有代码单元格。

先修正参数单元格标记（普通 CELL 改成 PARAMETERS CELL），但仍未恢复业务代码。后发现 Agent 生成的源文件省略了 Fabric 导出示例中的分隔空行。

受控 [Self-Runner Run #41261920081](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41261920081) 在 Fabric 创建、读回、删除三个临时 Notebook，保持业务测试标记相同，仅改变格式：

| 对照 | 结果 |
| --- | --- |
| 规范分隔空行的 FabricGitSource | 测试代码成功保留 |
| 压缩空行的 FabricGitSource | 测试代码未保留 |
| ipynb 对照 | 测试代码成功保留 |
| 临时资源清理 | 已全部删除 |

这是**当前 Fabric 原生 API 路径的实际解析兼容性证据**。微软并未明确公布所有空行作为普遍语法必需条件；我们将它作为此项目已验证的强制工程约束，不能把它当成随便可删的格式空白。

[Healthcare PR #576](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/576) 只增加 13 个分隔空行，没有改变 P2 算法与安全门禁。随后用户人工检查并完成 Git incoming changes；[Self-Runner Run #41262254996](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41262254996) 重运行 job 124718913119 证实 Git 同步到 9e667468、FabricGitSource 20,053 B、ipynb 21,689 B / 3 code cells、业务函数 / 参数 / HALT 存在，Pipeline 安全参数正确。

## 编写 Notebook 原生代码的强制要求

权威源码位于 azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py；相邻的 .platform 保留 Fabric 生成的 logicalId，不得伪造、归零、移动 Item 目录。

**不要将 FabricGitSource 视作纯 Python 脚本。** 它必须保留 Notebook Header、METADATA / META JSON、CELL / PARAMETERS CELL 标记和正确的单元格边界。参考下面的**简化结构示例**；它不是另一个可发布的 Notebook：

~~~python
# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   }
# META }

# CELL ********************

def read_only_example():
    return "HALT"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# PARAMETERS CELL ********************

run_mode = "HALT"
write_authorized = False

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark",
# META   "tags": ["parameters"]
# META }

# CELL ********************

raise RuntimeError("HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
~~~

**禁止的 Agent 行为：**

- 为了代码美观压缩、删除或自动 normalize Cell/Metadata 的分隔空行。
- 将多行 META JSON 简化为自行发明的单行格式，或把 Parameters Cell 当成普通 Cell。
- 将 Git Native Notebook 的业务逻辑复制成另一个独立维护的 Python 实现；离线兼容加载器不得成为第二业务权威。
- 将 Fabric Workspace 的空壳 Notebook 反向 Commit 到 Git main。
- 根据 GitHub 绿色 CI、Git 已同步、Notebook UI 可打开，就认定完整业务代码已经部署。
- 修改真实 .platform logicalId 或错误地当成可自由复用的物理 Item GUID。
- 为检查格式问题而运行 Pipeline、解除 HALT、重复执行 Bronze/Silver 写入。

**维护规则：** 首选真实 Fabric 导出的文件作为模板。保持文件 Header 后、每处 METADATA 和 META 之间、META 块与 CELL 标记之间、CELL 标记与代码之间的原有空行。将其视为序列化协议的一部分。若要改格式，先用独立 Notebook 做最小 API round-trip 和双格式读回，再改变主 Notebook。

微软官方：[Notebook definition](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/definitions/notebook-definition) 支持 FabricGitSource 与 ipynb。

## Pipeline / Environment 的额外教训

**DataPipeline：** 当前 TridentNotebook 在 Git Native 定义中引用对应 Notebook .platform.config.logicalId，并使用当前 Workspace 的全零 workspaceId；参数必须写在 typeProperties.parameters，不能写到曾被 Fabric 丢弃的 notebookParameters。保留 run_mode=HALT、write_authorized=false、retention_preflight_verified=false、无 schedule、retry=0。Pipeline 执行成功≠Silver Commit PASS。

**Environment：** Git 中 Wheel 存在≠Staging 有 Wheel≠Published 有 Wheel≠Notebook 实际绑定此 Environment≠运行时装载了期望的版本。微软说明 Git 的库变更进入 staging，必须单独 Publish 才生效：[Environment Git integration](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline)。

本项目唯一 Shared Wheel 为 healthcare_data_engine-0.1.0-py3-none-any.whl，Git 构建预期 SHA256 为 603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7。云端列出**文件名**并不证明运行时装载的 Wheel hash。

[Self-Runner Run #41263182097](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41263182097) 曾出现 Staging Wheel 有、Published 列表 HTTP 404、Environment publishDetails=Success 的组合。这里的 Success 只表示**某次**发布操作成功，不能证明当前 Git 新增 Wheel 生效。每次手工 Publish 之后必须重新读取 Published 列表和 Notebook 绑定，不能复用旧的 Publish 状态。单纯 HTTP 404 尚需结合 Fabric 环境最新实际状态解释。

## 每次 Fabric PR 的分层验收

| Gate | 需要验证 | 不代表 |
| --- | --- | --- |
| A. 源码与结构 | Python/JSON、Native Cell/Meta/空行/参数、安全门禁、本地 PySpark 测试 | 云端已导入 |
| B. Git | PR 审查、CI、目标资源范围、真实 .platform、Wheel SHA | Workspace 更新成功 |
| C. Workspace 定义 | 人工核查 incoming diff，无意外删除/覆盖；对实际 Item 执行 GetDefinition，同时读取 FabricGitSource/ipynb；检查业务函数、参数、HALT 和 Git sync HEAD | 可以运行或写入 |
| D. Runtime 依赖 | Staging 与 Published 分开检查；Wheel 期望版本/实际 hash 和 Notebook Environment 绑定验证 | Spark 业务通过 |
| E. 业务 | 单独授权非写入 Smoke → 最小受控数据写入 → 独立 Delta/Manifest/行数/审批 Readback | 仅凭 Pipeline success 不足 |

**事故排查顺序：** 先确认 Git 业务代码完整；再比对 Git HEAD 与 Fabric Git sync HEAD；然后读取真实 Notebook 的两种 Definition。若两个格式都只有 Header，先做隔离原生格式实验，绝不反复用正式 Notebook 猜测或执行。检查 Pending Items 仅影响目标 Notebook 时，才人工确认 Git incoming。最后另外验证 Environment 的发布和运行时绑定。

## 已实现的防回归检查与 Agent 接手清单

- [Notebook Native Contract tests](../../../../azure-fabric/notebook-development/tests/test_fabric_git_native_contract.py) 已检查 Header、四个 META 块、2 个普通 CELL + 1 个 PARAMETERS CELL、规范分隔空行、业务函数和 HALT。
- [Fabric FHIR Notebook offline CI](../../../../.github/workflows/fabric-fhir-notebook-offline.yml) 执行离线单测与 Wheel SHA 验证；这些仅证明 A/B Gate。
- Self-Runner 的 fabric_p2_native_readback.py / fabric-api-client.yml 做真实云端定义双格式只读验收；只有它通过才可以说 C Gate PASS。
- Self-Runner Environment Staging/Published 只读 API 对比用于 D Gate；不自动 Publish。
- 接手 Agent 必须先读取此 Runbook、[Notebook CODE](CODE.md)、[Environment CODE](../environments/CODE.md) 和 [OpenSpec](../../../../openspec/changes/ingest-fhir-to-fabric/design.md)。
- 每次修改要给出 PR、精确 commit、Git / Fabric 同步 SHA、Notebook 两种定义的 bytes / code cells / 业务关键标记、Environment 发布与依赖状态，明确标注 PASS/HOLD/NOT_RUN。
- 任何缺失或歧义均保留 HOLD。没有授权不得运行 Notebook/Pipeline、解除 HALT 或写 Bronze/Silver。

**版本约束：** 本规范是现阶段真实测量出来的工程兼容性经验。Fabric 官方格式或 API 改版时先做隔离验证和 CI 迁移，不能为了省事直接修改正式 Item。
