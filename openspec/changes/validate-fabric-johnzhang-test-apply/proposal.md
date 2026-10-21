# Proposal

## Why

用户明确要求在当前 Fabric Terraform 模型上新建隔离 Workspace `johnzhang-test`，为真实测试新建最小正式 F2 Capacity，按顺序使用 Terraform 完成实际 Capacity / Workspace / OneLake 的 Plan/Apply，并读回资源和 State。原有 Trial、`healthcare-omop`、Shared Storage 和旧 State 均不改动。

## What Changes

- 新增 `fabric-workspace/johnzhang-test/workspace/` 和 `onelake/`，复制已验收的 Terraform Root 合同，仍调用原通用 Modules，独立 CLI Workspace `johnzhang-test` 和各自 State。
- 新增可复用 `modules/capacity/` 与 `shared-infra/capacity/` 独立 Terraform Root，现有 `OMOP` Resource Group、East US、新 Azure F2 PAYG Capacity 名 `fcjohnzhangtest`；创建收费但最小规格，并在受控验证后暂停。
- 仅通过 Terraform 创建三种资源；REST API 不创建 Workspace，也不更改 Workspace capacity_id。容量 REST 可用于测试后的暂停/核查。
- 新增 CI 合同和受控 Self-Runner 测试工作流，严格 SHA 绑定、不可扩容、不访问原先 trial、老 Roots、老 State。停止条件：计费/配额/权限阻塞立刻停，禁止绕过、扩大权限或默认保留付费 Active 状态。

## Capabilities

### Modified Capabilities

- `fabric-workspace-scoped-terraform`：新增独立 `johnzhang-test` 实例与单独 Capacity Root；原有 `healthcare-omop` 不受影响。

## Impact

实施源码 PR/静态 CI 不直接创建收费资源。真实 Apply 是用户明确提出的单次 `johnzhang-test` E2E 验证；F2 的计算计费按实际 Active 时长发生，OneLake Storage 可能继续收费。若真实 Apply 失败或暂停失败，以独立 Azure/Fabric 读回确认实际付费状态并立即报告，绝不声称安全结束。
