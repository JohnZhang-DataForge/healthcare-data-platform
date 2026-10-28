# Healthcare Portal — CODE map

> P0 新组件的唯一代码导航；本阶段仅维护机器可读接口、Mock 与无副作用离线验证。设计见 [README](README.md)，实施任务见 [OpenSpec](../../../../openspec/changes/healthcare-on-demand-live-demo/tasks.md)。

| 所有权 | 正式入口 | 说明 |
| --- | --- | --- |
| P0 契约 | [`platform-portal/portal/contracts/`](../../../../platform-portal/portal/contracts/) | `snapshot-v1.schema.json`、`trigger-request-v1.schema.json`、`trigger-response-v1.schema.json`、`run-status-v1.schema.json`、`api-error-v1.schema.json` |
| P0 Mock | [`platform-portal/portal/fixtures/`](../../../../platform-portal/portal/fixtures/) | 完全虚构、标明 MOCK 的 P1–P4 联调数据；绝非真实新 Batch |
| P0 Tests | [`platform-portal/portal/tests/test_contracts.py`](../../../../platform-portal/portal/tests/test_contracts.py) | jsonschema Draft 2020-12、格式校验、跨引用、负例、公开数据边界 |
| P0 Test deps | [`platform-portal/portal/requirements-test.txt`](../../../../platform-portal/portal/requirements-test.txt) | 离线单测依赖 |
| P0 CI | [`.github/workflows/portal-contract-validation.yml`](../../../../.github/workflows/portal-contract-validation.yml) | PR 无云/集群凭据的 Schema 验证 |
| Agent B Exporter | [`platform-portal/portal/exporter/`](../../../../platform-portal/portal/exporter/) | GET-only Marquez 原始事件导出、公开白名单、证据门槛和离线测试；**未执行真实 Marquez 读回/公网发布** |
| Agent B Offline CI | [`.github/workflows/portal-exporter-offline.yml`](../../../../.github/workflows/portal-exporter-offline.yml) | Fake GET + 真实 v1 JSON Schema 离线验证（无共享 Runtime） |

Exporter 源码、专用 CI 和离线测试已由 Agent B PR #523 实现，但**尚无真实 Marquez 数据读回或公网发布**；Web、Control 和公开部署仍由各自任务验收。新增维护源码须同步本 CODE 地图。

**当前并行开发分工（未实现）**：见 [OpenSpec 多 Agent 计划](../../../../openspec/changes/healthcare-on-demand-live-demo/parallel-workstreams.md)；Web= `platform-portal/portal/web/`、Exporter=`platform-portal/portal/exporter/`、Azure Relay=`azure-fabric/openlineage/` + `platform-portal/openlineage/blob-relay/`。Cloudflare 由用户手动配置，[手工指南](CLOUDFLARE-MANUAL.md)；旧 `portal/infra/` 不再列为当前开发任务。Agent 新增实际源码时，各自 PR 必须同步 owning CODE map 和本 CHANGE 的对应 Task。
