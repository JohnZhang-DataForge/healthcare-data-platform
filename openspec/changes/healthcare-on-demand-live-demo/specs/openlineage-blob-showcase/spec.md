# OpenLineage Blob Relay, Marquez Readback and Public Showcase

## ADDED Requirements

### Requirement: Immutable versioned OpenLineage Blob relay

两端标准 OpenLineage 事件 SHALL 保存在与业务 Azure Landing RAW/READY 和 Terraform State 隔离的受控 Blob 前缀或 Container；事件对象 MUST 使用幂等条件创建、稳定标识与 SHA256 校验，成功 commit Manifest 必须最后提交，未完成的部分批次不能被 Consumer 当成已完成处理。

#### Scenario: Partial event upload

- **GIVEN** 一个 Run 的多个事件中有对象未完成上传或校验失败
- **WHEN** Publisher 尝试声明这轮 Event Batch 成功
- **THEN** 系统 MUST NOT 发布成功 Manifest，并 SHALL 保留可读回的失败证据用于恢复

#### Scenario: Same key with different content

- **GIVEN** 目标 Blob Key 已经存在且原始 SHA 与本次事件不同
- **WHEN** 重试提交该对象
- **THEN** 系统 MUST 拒绝覆盖并记录冲突，不得悄悄取代既有事件

### Requirement: Reliable Consumer replays only lineage to Marquez

本地 Consumer SHALL 只读取 committed Manifest、验证 Schema/Hash、按稳定事件身份去重、经内网 Marquez Ingestion API 写入 PG14，并在独立 API 读回后推进持久 checkpoint。断网、超时、重复、乱序和不确定的写入结果 MUST 可恢复；**不允许**为补血缘而重跑 Synthea、OMOP Writer 或 Fabric ETL。

#### Scenario: Marquez API temporarily unavailable

- **GIVEN** Blob 已经持久化有效 OpenLineage Event，但内网 Marquez 暂不可达
- **WHEN** Consumer 执行这一事件
- **THEN** Consumer SHALL 保留未完成 checkpoint，并可在恢复后安全重投，不修改业务数据

### Requirement: Cross-platform lineage requires evidenced dataset identity

Local 与 Fabric 的 Dataset SHALL 仅在真实 URI/版本/来源 Manifest 证明是同一数据集或真实上下游交接时进行跨平台关联；单纯同名、推测或 Fabric 的 CascadeDelete 结构关系 MUST NOT 生成业务数据流边。

#### Scenario: Matching dataset labels without common manifest

- **GIVEN** 一个本地 Dataset 与 Fabric Item 显示名相似但没有相同 URI 或来源记录
- **WHEN** Graph Builder 合并两套血缘
- **THEN** 两者 SHALL 保持分离或者显示未证实状态，不能加入错误的真实依赖边

### Requirement: Anonymous UI consumes only allowlisted snapshots

公开页面 SHALL 只读取授权的、版本化的脱敏数据快照；不得读取私有 Blob OpenLineage Raw Event、SQL、患者资料、内网地址、GitHub/Azure Secret 或写入 Marquez 的 API。只有明确具有代码复用许可的前端实现才可以部署；Marquito 风格原型未经许可证确认不得复制其原源码。

#### Scenario: Raw lineage contains internal SQL or URI

- **GIVEN** OpenLineage Facet 内含 SQL 文本、内网 URL 或模拟患者数据
- **WHEN** Exporter 构建匿名快照
- **THEN** 它 MUST 删除或安全映射所有非白名单字段，禁止原文发布至公共 Cloudflare Assets

#### Scenario: Marquito source reuse not authorized

- **GIVEN** 上游 Marquito 仓库没有经过确认的公开再发布许可证
- **WHEN** 公网前端准备上线
- **THEN** 部署 MUST HOLD，直到取得作者明确授权或改用有明确许可的独立前端实现
