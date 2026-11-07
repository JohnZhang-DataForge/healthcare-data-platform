# Proposal — HL7 Python Parser → local Delta → dbt Canonical Candidate

## Why
OIE V2/Raw HL7 已完成真实 42 消息 Azure Blob Landing P3（[Run #42412009780](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42412009780)）。过去 Self-Runner 的 [PR #584](https://github.com/JohnZhang-DataForge/Self-Runner/pull/584) 已验收 `hl7apy` 原始消息结构化、Manifest 校验与 dbt Candidate；但测试为使 dbt-duckdb 方便输入，采用临时 CSV `dbt seed`，不能误认为 HL7→FHIR 或正式 Staging 格式。

## What Changes
- 按已确定的**本地 dbt Spark/Delta** 方案正式开发，而非继续试验引擎选型：Python Parser → 类型化本地 Delta `hl7_staging.hl7_events` → `dbt-fabricspark(method=session)` SQL → Canonical Patient/Encounter Candidate。
- 经审核的 Source Parser 与 Manifest 验证从隔离 POC 晋升到 Healthcare 单一业务 Owner `local-data-platform/spark/apps/hl7/`。保留原始 provenance、A01/A03 配对、HL7 coding、对缺失事实 fail closed。
- 统一下游 Canonical 合同与单 Publisher/OMOP，不创建第二个临床 Mapper 或正式 Silver Writer。
- 离线 GitHub-hosted CI 只使用新的合成 FHIR 输入通过真实 OIE V2 JS Mapper，生成本地模拟 Raw HL7/Manifest，不访问 Azure、OIE、Fabric 或其他共享基础设施。

## Capabilities
- 审核来源 OIE V2 Raw HL7 → 结构化源事件 → 持久 Local Delta Staging。
- 本地 dbt 读取 Delta Source 产生严格 Canonical Candidate、独立读回和 Source replay HOLD。
- 未来经授权对接原有统一 Silver Approval/Publisher，不直接操控 OMOP Gold。

## Impact
本 Change 是正式代码开发但**不是** 真实 Azure 42 对象的再拉取或正式 Fabric Silver/Gold 业务运行许可；所有共享资源与真实数据审批单独处理。本阶段无 Azure/K8s/OIE/Fabric I/O 或重放。
