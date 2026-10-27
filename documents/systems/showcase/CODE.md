# Healthcare Showcase — CODE map

> P0 新组件的唯一代码导航；本阶段仅维护机器可读接口、Mock 与无副作用离线验证。设计见 [README](README.md)，实施任务见 [OpenSpec](../../../openspec/changes/healthcare-on-demand-live-demo/tasks.md)。

| 所有权 | 正式入口 | 说明 |
| --- | --- | --- |
| P0 契约 | [`showcase/contracts/`](../../../showcase/contracts/) | `snapshot-v1.schema.json`、`trigger-request-v1.schema.json`、`trigger-response-v1.schema.json`、`run-status-v1.schema.json`、`api-error-v1.schema.json` |
| P0 Mock | [`showcase/fixtures/`](../../../showcase/fixtures/) | 完全虚构、标明 MOCK 的 P1–P4 联调数据；绝非真实新 Batch |
| P0 Tests | [`showcase/tests/test_contracts.py`](../../../showcase/tests/test_contracts.py) | jsonschema Draft 2020-12、格式校验、跨引用、负例、公开数据边界 |
| P0 Test deps | [`showcase/requirements-test.txt`](../../../showcase/requirements-test.txt) | 离线单测依赖 |
| P0 CI | [`.github/workflows/showcase-contract-validation.yml`](../../../.github/workflows/showcase-contract-validation.yml) | PR 无云/集群凭据的 Schema 验证 |

P1–P4 对应的 `showcase/web/`、`showcase/exporter/`、`showcase/control/`、`showcase/infra/` 尚未实施；新增维护源码时必须同步更新本 CODE 地图，勿提前写成已部署。
