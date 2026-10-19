# Fabric Environment Preflight

## ADDED Requirements

### Requirement: Reject legacy or ambiguous remote state targets

环境预检 SHALL 仅接受显式 `fabric/<environment>` State Prefix，且 `environment` MUST 为限定字符的新环境名称；不允许 `dev`、`dev/workspace.tfstate`、路径穿越、任意外部 Storage 或旧工作区名称。预检本身 MUST NOT 访问 Azure 远程 State、调用 Terraform 或触发云端资源修改。

#### Scenario: new deployment profile is accepted

- **GIVEN** 一个符合 Schema 的环境文件，使用现有 `johnzhang/tfstate`、隔离的 `fabric/lab-b` Prefix 和有效 GUID
- **WHEN** 使用 Preflight CLI 校验
- **THEN** 输出独立 `fabric/lab-b/workspace.tfstate`、`onelake.tfstate`、`connection.tfstate` 的确定性预期路径，且不产生外部副作用

#### Scenario: legacy state or path traversal is rejected

- **GIVEN** 将 State Prefix 改为 `dev` 或 `../dev`，或环境名含路径遍历
- **WHEN** 执行 Preflight
- **THEN** 以失败退出并不产生有效环境输出

### Requirement: Explicit tenant and capacity inputs

预检 SHALL 要求 Backend Tenant、Fabric Tenant、Fabric Capacity 是显式的有效非零 UUID，并允许两 Tenant 相同或不同。它 SHALL 将现有 Azure `landing` Container 固定为单一数据入口，而不得将 Fabric Workspace 的 GUID 与 Blob 发布端混用。

#### Scenario: malformed identity is rejected

- **GIVEN** Fabric Capacity ID 缺失或含示例占位符
- **WHEN** 执行 Preflight
- **THEN** 失败并报告对应字段，不推断或填入虚构 GUID

### Requirement: Configuration contains no credentials

配置 JSON SHALL 只允许公开声明的非敏感键；未知键、内嵌 Secret、SAS、PAT、Access Key MUST 导致失败。CLI 成功日志只输出非敏感环境目标摘要，不打印 Token 或凭据。

#### Scenario: credential sneaks into configuration

- **GIVEN** 用户在 `fabric` 节点意外加入 `client_secret` 字段
- **WHEN** 执行 Preflight
- **THEN** 失败，并提醒凭据不能保存在配置中
