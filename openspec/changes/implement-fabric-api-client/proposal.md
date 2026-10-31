# Proposal

## Why

Healthcare 的 P0–P2 已在 GitHub 验证离线代码，但没有针对当时的代码建立通用、可证实的 Fabric API 只读预检。现有 Self-Runner 的 OIDC/Fabric/Blob 工作流已成功运行过，然而各自内嵌身份交换、HTTP、分页与断言，不能给后续 Agent 提供安全、稳定、可参数化的入口。用户明确指定正式文件名为 `fabric-api-client.yml`，不把临时测试命名用于正式代码。

## What Changes

- 在 **Self-Runner** 仓库正式维护 `.github/workflows/fabric-api-client.yml`，它是受控 API 客户端入口，不是一次性测试文件。
- 配套 `src/ci/fabric_api_client.py`：固定 Fabric API Host、OIDC Token audience、操作白名单、明确 workspace 作用域、HTTP/分页/限速/错误处理、状态和脱敏证据。
- 第一阶段提供 GET-only 的 `list_workspaces`、`list_items`、`get_item`、`get_job` 和 `get_operation`；仅允许目标 Workspace 为 `healthcare-omop`，并有严格的输入限制。
- 通过 `workflow_dispatch` 参数 JSON 调用；输入审计、机器 JSON Artifact、Run Summary、失败时非零退出；静态正反单测在不使用 Azure 的环境执行。
- 保留未来为 GET Definition（Fabric 用 POST）和受控 Notebook/Pipeline Job 运行加入独立批准 Gate 的扩展点，但 **不在第一阶段开放任何 POST/PATCH/PUT/DELETE**。

## Capabilities

### New Capabilities
- `fabric-api-client`：单一可信 Runner 的、受控、只读、可审计的 Fabric HTTP 能力，支持外部/Agent 参数化提交，清楚区分 SDK/单测、真实 OIDC API 读回和云端执行。

### Modified Capabilities
- 无既有 Azure/Local/Fabric 运行资源改动；仅新增 Self-Runner 正式源码及 Healthcare OpenSpec 设计依据。

## Impact

- 设计/任务权威位于 Healthcare `openspec/changes/implement-fabric-api-client/`；执行组件位于 `JohnZhang-DataForge/Self-Runner`。
- 不改 Healthcare P0–P2、Wheel/Notebook、Blob Publisher、Terraform State、Capacity、K8s 或 GitHub OIDC 信任。
- 代码/Mock Gate 通过不代表 Runner 的 Fabric API 当前仍可访问；真实 GET Run 才是该时点实际连接证据。
