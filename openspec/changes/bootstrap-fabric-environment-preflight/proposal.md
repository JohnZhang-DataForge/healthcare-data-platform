# Proposal

## Why

Fabric 多环境重建目标架构已批准并归档，但当前仅有绑定旧 `dev` Remote State 和 Azure/Fabric 单 Tenant OIDC 的七个 Terraform Root，现有 Self-Runner 不支持安全切换目标环境。用户希望从现在开始开发可重建部署，并把每个新 Tenant 必须手工完成的账号/授权/Capacity 步骤固化为 Runbook。旧手工建 Workspace 缺少真实 State/Resource 审计，不能因“尚无业务数据”便直接删除或复用旧 State。

## What Changes

- 先实现一个**纯本地、无云端副作用**的 Fabric 环境配置合同和 fail-closed Preflight CLI；强制独立 State prefix、现有稳定 `johnzhang/landing` 与 `johnzhang/tfstate`、独立 Entra 租户字段、全 UUID 格式和旧 Workspace 名称保护。
- 通过标准库 Python 单测覆盖成功、未知字段/Secret、非法环境名、旧 State 路径、缺失/非法 GUID、Workspace 碰撞等失败场景。
- 新增中文人工前置 Runbook，逐项说明 Capacity、Fabric Tenant Service Principal、Azure Backend 与 Blob Reader 权限、GitHub OIDC/Secrets、跨租户连通性及旧 Workspace 资产安全处理；为后续 Self-Runner 自动部署提供输入检查单。
- 同 PR 更新 Azure Terraform CODE/Operations 导航。后续真正 Terraform Root/Provider 分离、fabric-cicd 发布与 Self-Runner 部署，均由独立后续 Change 实施。

## Capabilities

### New Capabilities

- `fabric-environment-preflight`：读入不含 Secret 的目标环境配置，拒绝使用旧 `dev` State、无效 Identity ID 与任何未声明配置项，输出供后续 workflow 读取的确定性、非敏感部署目标摘要。

### Modified Capabilities

本轮没有修改任何已经部署的 Fabric 行为、Terraform Root/Provider、Workflow 或 Azure 资源。

## Impact

只新增静态配置示例、纯本地校验器和单测、运维 Runbook 与源码导航。**不执行 Terraform plan/apply/destroy、Azure/Fabric API 调用、K8s、DB 或 Blob 写入；不删除旧 Workspace 或更改旧 State。**
