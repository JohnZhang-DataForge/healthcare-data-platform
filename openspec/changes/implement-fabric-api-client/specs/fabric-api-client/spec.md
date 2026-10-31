# Fabric API Client

## ADDED Requirements

### Requirement: Restrict cloud APIs to an explicit operation allowlist
受控入口 SHALL 仅在 `Self-Runner/main` 的 OIDC 身份下访问固定 Fabric API Origin；初版 SHALL 仅允许 GET `list_workspaces`、`list_items`、`get_item`、`get_job`、`get_operation`。未知字段、任意 URL/HTTP Method、非法 UUID、目标非 `healthcare-omop` MUST fail closed before cloud token exchange.

#### Scenario: Deny an arbitrary API mutation
- **GIVEN** 调用者传入 `POST`、`DELETE`、`run_notebook` 或任意外部 URL
- **WHEN** Workflow 解析请求
- **THEN** 请求 SHALL 被拒绝，不进行 Fabric API 或 Token 交换

### Requirement: Provide bounded, auditable read-only results
接口 MUST 约束请求和响应大小、分页、重试、读超时，SHALL 生成不含 Token/敏感定义正文的 JSON Artifact 与 Run Summary，并用 HTTP 状态/非零退出准确表示 API 错误。

#### Scenario: Successful Fabric metadata inspection
- **GIVEN** 被授权 Principal 可以 GET `healthcare-omop` 的 Workspace/Items
- **WHEN** `list_items` 请求执行
- **THEN** 报告 SHALL 包含准确 Run/Commit/operation/request_id、HTTP 成功状态及有限数量的已脱敏 Item 元数据

#### Scenario: Fabric returns 403 or fails repeatedly
- **GIVEN** API 拒绝授权或重试到达上限
- **WHEN** 请求执行
- **THEN** 报告 MUST 标记失败且 Workflow 退出非零；不得将离线模拟成功当作真实连接

### Requirement: Keep live job execution and data mutation out of v1
客户端 MUST NOT 发布 Environment、执行 Notebook/Pipeline、修改 Fabric Capacity 或访问 Azure Blob/OneLake；`get_job` 仅检查状态，不代表业务 Output 或 Silver Readback 验收。

#### Scenario: Completed Job has no verified exitValue
- **GIVEN** Notebook Job 状态是 `Completed`
- **WHEN** `get_job` 返回
- **THEN** 报告仅描述 Job 元数据，不得标为数据业务验收 PASS
