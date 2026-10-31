# Tasks

## 1. Design and scope

- [x] 1.1 核对真实 Self-Runner/main OIDC、Fabric/Blob 权限与历史 Job evidence；确认跨仓库 OpenSpec 所有者和正式 `fabric-api-client.yml` 文件名。
- [x] 1.2 用户 2026-10-31 批准通用客户端；建立 Proposal/Design/Delta Spec/Tasks，第一版限定 GET-only，明确真实运行授权边界。

## 2. First implementation — Self-Runner

- [ ] 2.1 从 Self-Runner 最新 main 开发 `.github/workflows/fabric-api-client.yml` + `src/ci/fabric_api_client.py`，提供安全可参数化 GET-only API。
- [ ] 2.2 单元测试/负向测试覆盖参数/URL/身份前验证、HTTP 错误/限流/脱敏、Pagination；GitHub PR CI 真正执行，验收再打勾。
- [ ] 2.3 独立真实 `workflow_dispatch` Fabric OIDC GET `healthcare-omop`，保存准确 Run/SHA/Artifact。若无 dispatch 能力，保持未完成，禁止把静态成功误标 Live。
- [ ] 2.4 经单独授权评审扩展 Blob/OneLake、getDefinition POST LRO、runNotebook/Pipeline、Environment Publish；不是本次第一版范围。

## 3. Safety

只允许 OpenSpec/代码/静态测试与只读 GET。未经独立批准，不触发 Spark Job、Notebook Create/Run、Pipeline、Environment Publish、Capacity Resume、Terraform Apply/Destroy、Blob/OneLake 写入或 Local runtime 操作。
