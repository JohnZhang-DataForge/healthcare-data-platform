# Tasks

## 1. Design and scope

- [x] 1.1 核对真实 Self-Runner/main OIDC、Fabric/Blob 权限与历史 Job evidence；确认跨仓库 OpenSpec 所有者和正式 `fabric-api-client.yml` 文件名。
- [x] 1.2 用户 2026-10-31 批准通用客户端；建立 Proposal/Design/Delta Spec/Tasks，第一版限定 GET-only，明确真实运行授权边界。

## 2. First implementation — Self-Runner

- [x] 2.1 [Self-Runner PR #351, Main cc477ad020d903bfda35a228611d0f897b5f2e11] 从 Self-Runner 最新 main 开发 `.github/workflows/fabric-api-client.yml` + `src/ci/fabric_api_client.py`，提供安全可参数化 GET-only API。
- [x] 2.2 [Run #41240329501, 18/18 tests PASS, source a2b18bca42fc01c071997e4082c1e80a46d37048] 单元测试/负向测试覆盖参数/URL/身份前验证、HTTP 错误/限流/脱敏、Pagination；GitHub PR CI 真正执行，验收再打勾。
- [ ] 2.3 独立真实 `workflow_dispatch` Fabric OIDC GET `healthcare-omop`，保存准确 Run/SHA/Artifact。若无 dispatch 能力，保持未完成，禁止把静态成功误标 Live。
- [x] 2.5 [Run #41240364687, Main cc477ad020d903bfda35a228611d0f897b5f2e11] 真实 Self-Runner/main Push → GitHub OIDC → Fabric list_items GET 已通过，报告 Artifact `fabric-api-client-41240364687`（ID 13057316260）。这只证明固定只读请求在当时成功，不等于手动 workflow_dispatch、自定义参数或业务 E2E。
- [ ] 2.4 经单独授权评审扩展 Blob/OneLake、getDefinition POST LRO、runNotebook/Pipeline、Environment Publish；不是本次第一版范围。

- [ ] 2.6 在同一正式 `fabric-api-client.yml` 添加 P0–P2 实施验收：GitHub-hosted 按固定 Healthcare Main SHA 重跑 P0 CODE-map/Contract、P1 Wheel/Synthetic/PySpark、P2 Notebook 离线测试/Native Export fail-closed；Self-Runner 保持只读 Fabric `list_items` 并独立统计 Native Notebook/DataPipeline/Environment/Lakehouse 的实际出现情况。所有测试按阶段标记 PASS/HOLD，Native Item/Delta E2E 未上线不得标为 PASS。
- [ ] 2.7 记录精确 Self-Runner 合并 SHA、Workflow Run/Artifact、P0/P1/P2 测试数量与 Fabric 真实 Item 类型；对未运行或阻断的业务 Gate 保持未勾选，不做云发布。

## 3. Safety

只允许 OpenSpec/代码/静态测试与只读 GET。未经独立批准，不触发 Spark Job、Notebook Create/Run、Pipeline、Environment Publish、Capacity Resume、Terraform Apply/Destroy、Blob/OneLake 写入或 Local runtime 操作。

## 4. Exact verification evidence — 2026-10-31

- OpenSpec 设计先行：Healthcare [PR #562](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/562)，Main `89856be10b7fc7e9790d05e331b5edcd0020cadc`。
- Self-Runner 正式源码：[PR #351](https://github.com/JohnZhang-DataForge/Self-Runner/pull/351)，Merge-Commit `cc477ad020d903bfda35a228611d0f897b5f2e11`；文件名为永久 `fabric-api-client.yml` 而非 test。
- 离线 CI：[Run #41240329501](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41240329501)，18/18 Python tests PASS；PR 环境不发起 OIDC/cloud GET，云端 Job 按设计 SKIPPED。
- 真实元数据只读：[Run #41240364687](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41240364687)，Main merge 的自动 Push GET；单测+真实 Fabric Job 均 SUCCESS，真实日志 `FABRIC_API_CLIENT_OUTCOME=PASS`、`FABRIC_API_CLIENT_OPERATION=list_items`、`FABRIC_API_CLIENT_ERROR=NONE`，对应 JSON Artifact ID `13057316260`。
- **尚未运行**：`workflow_dispatch` 传入自定义 JSON、完整 Notebook/Pipeline/Environment/GetDefinition、Blob/OneLake 独立测试、Silver 数据读回。没有任何云端写入。
