# Design

## Context and scope

批准的长期架构：[Fabric Multi-Environment Rebuild](../../../../documents/architecture/design/FABRIC-MULTI-ENVIRONMENT-REBUILD-DESIGN.md)，现有 Root/State/权限现状：[Terraform Architecture](../../../../documents/systems/azure-fabric/infra-terraform/ARCHITECTURE.md)。此次只实现首个安全、可单测的“环境合同 + Preflight + 人工前置手册”，不创建云端资源。

## Contract

`azure-fabric/infra-terraform/environments/fabric-environment.example.json` 仅是**故意含占位符的非部署示例**；必须复制到私有/受保护位置填写真实的非敏感 Tenant/Capacity ID 才能运行成功。严禁在 Git 提交 Token/Service Principal Secret、SAS、PAT/Storage Key。真正的工作流身份走受保护的 GitHub Environment Variable/Secret 与分离的 OIDC 路径。

CLI：`python3 azure-fabric/infra-terraform/tools/fabric_environment_preflight.py --config PATH`

- schema 只接受 `schema_version=1`、`environment`、`backend`、`landing`、`fabric`。
- `backend`：Storage `johnzhang` / Container `tfstate` / Tenant A UUID / `state_prefix=fabric/<environment>`。
- `landing`：Storage `johnzhang` / Container `landing`。
- `fabric`：Tenant B UUID / Capacity UUID / `workspace_name=HDP-<environment>`。新环境必须与固定旧 Workspace 名称明显区分，拒绝使用旧 `dev` State。
- JSON 输入含任何多余/凭据字段或非法值必须报错（fail closed），不会联系 Azure/Fabric。成功输出 JSON 状态摘要、预期 `workspace`/`onelake`/`connection` State Key，供未来 Workflow 依赖；不写入 Terraform State。
- 用户对“旧 Workspace 可以不要”的表达仅允许我们**规划新建独立环境**；旧 Workspace 是否含隐藏 Items/RBAC/State 需只读核实并单独审批，绝不在本 Change 删除。

## Responsibility and CI

源码按功能命名；`documents/systems/azure-fabric/infra-terraform/CODE.md` 随新 CLI 和测试更新，运维 Runbook 统一归 `documents/engineering/operations/`。单元测试使用 Python 标准库 `unittest`，无第三方依赖；Healthcare PR 仍执行 OpenSpec Strict、Trusted Change Gate 和文档链接静态检查。单元测试需要实证，不把仅 CI 门禁绿色自动等同于此 CLI 已被执行。

## Next separate Changes

在本 Change 经静态及单测验收合并之后，按用户授权分别实现 (a) 两 Tenant 身份和 Backend 独立 Key 的 TF/Runner 路径，(b) Workspace/Lakehouse/Connection 静态资源，(c) fabric-cicd Notebook/Pipeline 发布，(d) 数据复制/验证。任何 Terraform Plan 会访问云端、读/锁 State；不能被本次开发请求视为授权。

## Rollback

由于只添加新工具和文档，回滚可仅移除本轮新增路径及 CODE/Runbook 导航；不会影响原有七 Root、远程 State 或旧 Workspace。
