# Portable Local and Fabric Spark with OpenLineage

## ADDED Requirements

### Requirement: PySpark ETL core is backend-neutral

未来的 FHIR/HL7 Spark ETL SHALL 将确定性的 PySpark 转换逻辑与 Fabric Notebook 和本地 Kubernetes Spark Operator 的环境启动、认证和路径 Adapter 分离。共享业务逻辑 MUST NOT 依赖 Fabric-only notebookutils 或硬编码特定 Lakehouse/本地文件位置。当前 backend 保持 UNDECIDED，直到对同一个冻结 Manifest 的免费真实测试完成。

#### Scenario: Same FHIR manifest on Fabric and local runtimes

- **GIVEN** 一份已验证的合成 FHIR Source Manifest 及固定 Schema、ETL 版本
- **WHEN** 通过 Fabric Adapter 与 Local Adapter 分别运行相同转换
- **THEN** 两端 SHALL 在业务行数、主键、质量规则和字段级输出上满足同一对账合同，且平台差异仅通过 Adapter 表达

### Requirement: Spark compatibility matrix must be verified

实施 SHALL 固定 Spark、Python、Scala、Delta Protocol、存储 Connector、OpenLineage Listener/SDK 的版本与认证边界；不得因为 PySpark API 相似就承诺整份 Fabric Notebook 可直接作为 K8s SparkApplication 运行。

#### Scenario: Fabric-specific utility invoked in core ETL

- **GIVEN** 转换核心调用 Fabric-only notebookutils 或假定 /lakehouse/default 路径
- **WHEN** 本地兼容性检查执行
- **THEN** 合同 MUST 拒绝将它标记为 portable，直到环境专属部分下沉至 Adapter

### Requirement: Both runtimes produce standard verifiable OpenLineage events

两端成功采集的运行 SHALL 产出标准 OpenLineage Run Events，包含真实 Job namespace/name、Run ID、Event Type、Input/Output Datasets 和实际可用的 Schema/ColumnLineage Facet。非 Spark 组件只在真实埋点已验证后才能展示完整端到端血缘。Marquito 解析通过不等于原始 Fabric Listener 已验收。

#### Scenario: Spark emits only parent application START

- **GIVEN** 一条只有父 Spark Application START 的事件，没有实际 Dataset 输出或 COMPLETE
- **WHEN** 展示端生成血缘图和状态
- **THEN** 系统 MUST NOT 伪造业务完成、表级或列级血缘边，并 SHALL 标记覆盖范围不完整

### Requirement: Free POC precedes cost-bearing backend selection

系统 SHALL 在已有经授权免费 Fabric 与本地 K8s 环境中记录真实启动时间、ETL 时长、DQ 结果、OpenLineage 质量及成本边界，并由用户在 POC 后决定日常执行平台；任何 paid F2 自动恢复都不得成为测试的隐式条件。

#### Scenario: Backend selection before evidence

- **GIVEN** 只有本地 PySpark E2E 证据而 Fabric Listener 尚未真实验证
- **WHEN** 有人试图将 Fabric Backend 设为已验收默认
- **THEN** 实施流程 MUST 保持 backend UNDECIDED 或明确标记实验态，不能宣称双运行时兼容已通过
