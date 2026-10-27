# Healthcare Portal — CODE map

> P0 新组件的唯一代码导航；本阶段仅维护机器可读接口、Mock 与无副作用离线验证。设计见 [README](README.md)，实施任务见 [OpenSpec](../../../../openspec/changes/healthcare-on-demand-live-demo/tasks.md)。

| 所有权 | 正式入口 | 说明 |
| --- | --- | --- |
| P0 契约 | [`platform-portal/portal/contracts/`](../../../../platform-portal/portal/contracts/) | `snapshot-v1.schema.json`、`trigger-request-v1.schema.json`、`trigger-response-v1.schema.json`、`run-status-v1.schema.json`、`api-error-v1.schema.json` |
| P0 Mock | [`platform-portal/portal/fixtures/`](../../../../platform-portal/portal/fixtures/) | 完全虚构、标明 MOCK 的 P1–P4 联调数据；绝非真实新 Batch |
| P0 Tests | [`platform-portal/portal/tests/test_contracts.py`](../../../../platform-portal/portal/tests/test_contracts.py) | jsonschema Draft 2020-12、格式校验、跨引用、负例、公开数据边界 |
| P0 Test deps | [`platform-portal/portal/requirements-test.txt`](../../../../platform-portal/portal/requirements-test.txt) | 离线单测依赖 |
| P0 CI | [`.github/workflows/portal-contract-validation.yml`](../../../../.github/workflows/portal-contract-validation.yml) | PR 无云/集群凭据的 Schema 验证 |
| Agent A Web adapter | [`platform-portal/portal/web/src/publicDataSource.mjs`](../../../../platform-portal/portal/web/src/publicDataSource.mjs) | 自有 GET-only 公共静态摘要与候选 OpenLineage JSONL 读取、Mock/Verified 标记；未接入授权 Marquito UI，未部署 |
| Agent A Web tests | [`platform-portal/portal/web/test/publicDataSource.test.mjs`](../../../../platform-portal/portal/web/test/publicDataSource.test.mjs) | 原创 synthetic JSONL、P0 Mock 快照、失败/最后成功快照离线测试；数据与结果说明见 [Web README](../../../../platform-portal/portal/web/README.md) |

Agent A 已加入 Web 静态数据读取适配器和离线测试，**没有 Marquito 图形 UI 或公网部署**；Exporter/Control/Infra 原历史模块仍待分别实现或按最新决定取消。新增维护源码时必须同步更新本 CODE 地图，勿提前写成已部署。

**当前并行开发分工（未实现）**：见 [OpenSpec 多 Agent 计划](../../../../openspec/changes/healthcare-on-demand-live-demo/parallel-workstreams.md)；Web= `platform-portal/portal/web/`、Exporter=`platform-portal/portal/exporter/`、Azure Relay=`azure-fabric/openlineage/` + `platform-portal/openlineage/blob-relay/`。Cloudflare 由用户手动配置，[手工指南](CLOUDFLARE-MANUAL.md)；旧 `portal/infra/` 不再列为当前开发任务。Agent 新增实际源码时，各自 PR 必须同步 owning CODE map 和本 CHANGE 的对应 Task。
