---
status: active-contract
scope: healthcare-portal-contract-foundation-v1
decision_date: 2026-10-27
implementation_status: rename-pending-ci; no-runtime-or-public-deployment
---

# Healthcare Portal — P0 Contract Foundation

本页是 *Portal P0* 的接口与 Agent 协作权威入口。Portal 属于既有 `platform-portal/` 子组件，不是新独立系统；此前误建的顶级源码已迁移。长期目标架构继续以 [按需真实演示设计](../../../infra/HEALTHCARE-ON-DEMAND-LIVE-DEMO.md) 为准；任务进度只在 [Active OpenSpec tasks](../../../../openspec/changes/healthcare-on-demand-live-demo/tasks.md) 管理。Source map 见 [CODE](CODE.md)。

## P0 契约版本与范围

- 冻结 **v1 的字段名、枚举、JSON Schemas、Mock Fixtures、公开 URL 和写权限边界**。冻结表示供 P1–P4 基于一个版本开发，**不表示这些服务已经实现、运行或部署**。
- `data_origin=MOCK` 永远有醒目的 `mock_notice`；Mock 的患者、Encounter、医院城市、日期、指标及运行状态**均为虚构的 UI 例子**，不是 2026-10-25 P5 真实批次，也不是三家医院业务已经打通。
- P2 导出真实数据时只能发布 `VERIFIED_EXPORT` 且具备源 SHA、真实 Manifest SHA256、GitHub 执行证据，需额外做独立读回及白名单脱敏；完整 OpenLineage 事件、SQL、内部 IP、PHI、私有 URI、凭据绝不入公开快照。
- URL、对象模型与枚举变更须提出 `v2` 或兼容性审查，由 P0 owner 统一修改 Schema/Fixture/Tests；其他 Agent **只读取**合同，不擅自扩充字段。

## 对 P1–P4 冻结的 HTTP / 静态发布契约

| 端点 | 对外行为 | Schema / 注意 |
| --- | --- | --- |
| `GET /data/latest.json` | Cloudflare Pages 静态只读 **最后成功**脱敏快照；GET 不运行任务 | [snapshot-v1](../../../../platform-portal/portal/contracts/snapshot-v1.schema.json)；P2 生成、P4 发布、P1 读取 |
| `GET /data/snapshots/{snapshot_id}.json` | 同一快照的不可变版本资源；`latest.json` 最后更新 | 同上；失败不得覆写成功历史 |
| `POST /api/demo/trigger` | 仅受服务端 Gate 许可时返回 202，受理固定 allowlisted 任务 | [request](../../../../platform-portal/portal/contracts/trigger-request-v1.schema.json)、[accepted](../../../../platform-portal/portal/contracts/trigger-response-v1.schema.json)、[error](../../../../platform-portal/portal/contracts/api-error-v1.schema.json) |
| `GET /api/demo/status/{request_id}` | 只读进度；必须来自真实后端 readback，绝不因为 GET 启动计算 | [run-status-v1](../../../../platform-portal/portal/contracts/run-status-v1.schema.json)，未找到返回 404 与 error envelope |

**重要**：`/data/` 为 Pages 公共静态路径，不是 Marquez 私有 API 代理；`/api/demo/` 为 Worker 受控接口，不在前端暴露 GitHub/Azure 凭证。P3 的 POST 校验在服务端执行 US Geo + Turnstile + keyed HMAC IP 配额（3/UTC 日）+ 全局限额 + 原子 single-flight + OFF/ON/Emergency OFF + 预算 Gate。GET/preview/crawler/refresh **无副作用**。Client 请求只有随机 `client_request_id` 与一次性 `turnstile_token`，不得控制 Backend/Workflow/CPU/Fabric SKU；POST Token 不持久化、不公开、不打印。拒绝统一返回 HTTP 400/403/409/429/503 及 error envelope，禁止泄露内部状态。

## 状态、身份及数据证据

运行状态按 `ACCEPTED → GENERATING → BLOB_READY → SPARK_RUNNING → QUALITY_PASSED → LINEAGE_SYNCED → SNAPSHOT_PUBLISHED → COMPLETE` 推进，终态还可 `FAILED` 或 `EXPIRED`；每次推进依赖真实的独立运行读回，不能以 Notebook Job `Completed` 代替数据结果验收。Fabric 仍 `UNDECIDED/HOLD`。前端永远显示静态 `last_success_at` 和 `data_origin`；失败状态不替换上次成功快照。

`request_id` 为服务器分配随机 UUID，`client_request_id` 为客户端随机 UUID 用于请求幂等。公开 Dataset/Job/Run 使用不包含内部 URI 的 `*_ref` 标识；若多个输入来自同一 Dataset，必须经真实 Manifest/版本证据才能合并，不可用名称相似性编造跨平台连线。Column 边只表示实际存在、可追溯的上游/下游列。

## Agent 工作目录与冲突门槛

| Owner | 可以独占修改 | 禁止擅自修改 / 运行 |
| --- | --- | --- |
| P0 — Contract Coordinator | `platform-portal/portal/contracts/**`, `platform-portal/portal/fixtures/**`, `platform-portal/portal/tests/test_contracts.py`, `documents/systems/platform-portal/portal/**`, 这个变更的 OpenSpec 任务编号 | P1–P4 代码实现 / 任意共享环境操作 |
| P1 — Frontend | `platform-portal/portal/web/**`，其专属测试 | P0 Schema、P2 Exporter、P3 Worker、部署密钥 |
| P2 — Exporter | `platform-portal/portal/exporter/**`，其专属测试 | 生产 PG14/Marquez POST、任意已验收 Writer 变更 |
| P3 — Control API | `platform-portal/portal/control/**`，其专属测试 | 随意 dispatch Workflow / 真实 Fabric Capacity / P4 发布 |
| P4 — Deployment | `platform-portal/portal/infra/**`、有界的 `.github/workflows/portal-*` 发布 Workflow | P0 Schema、P3 控制策略或未经批准上线公网 |
| Later P5 — Lineage Relay | `platform-portal/portal/relay/**` | 真实 Blob/Marquez POST 必须单独授权 |
| Later P6 — Fabric POC | 独立获授权的 Fabric/兼容性隔离模块 | 不能绕过现有三次 HOLD 或改生产 Runtime |

各 Agent 在独立 Branch/PR 工作；在接手前读取 `AGENTS.md`、本页、[session coordination](../../../engineering/development/SESSION-COORDINATION.md) 与当前 `main` / 开放 PR。每份 PR 正文包含 `OpenSpec-Change: healthcare-on-demand-live-demo` 和具体 `OpenSpec-Task: n.n`；PR 合并前必须通过 Required CI。一次涉及相同 Workflow/Schema/Infra root 的修改先协调 Owner；即使目录不同，共享 Spark、Airflow、PostgreSQL、K8s、Azure 的实机写入**不能并行默认执行**。P0 没有给任何 Agent 运行或收费授权。

## P4 Infra 的职责与边界

P4 的 `portal/infra/` 管理 **本 Portal** 的 Cloudflare Pages/Worker 发布配置、路由与域名、staging/production 环境绑定、经 P3 确认的 D1 migrations / Durable Object bindings、Secret **引用名称**、可回滚部署配置；不得保存 Secret 值。`.github/workflows/` 存放 Actions 发布入口。P3 `portal/control/` 才负责 Turnstile、地域判断、原子配额、single-flight 和固定 Workflow 的业务控制。P4 不接管 Marquez/PG14、业务 Spark/Airflow/OMOP 或现有 Azure/Fabric Terraform，也不能自行上线公网或启用收费资源。

## P0 已验证的 Git 证据（2026-10-27）

- [PR #513](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/513)：六项 GitHub CI **SUCCESS**（Schema Contract、OpenSpec Static、Change Gate、Trusted Change Gate、Documentation Links、Naming）。
- 目标 PR HEAD `516721a055a2a0bb2babdf91102691c293cb68c1` → Main Squash `a5778f50b06f4cfb3051df3a1870b5be0dd97aee`；合并后从 Main 对关键 Schema/README 实际读回确认。
- **最初 P0 版本已通过验收（此次重命名后需重新检查路径/接口前缀）**；仅静态 Schema/Mock 经过验证，P1–P4 代码、实际 UI、Marquez 真实导出、Cloudflare 控制和部署 **均未实现**。安全与付费操作边界照旧。

## P0 验证 / 下一 Gate

`python -m pip install -r platform-portal/portal/requirements-test.txt`，随后 `python -m unittest discover -s platform-portal/portal/tests -p 'test_*.py' -v`；专用 CI 只执行 schema/fixtures 的离线检测。初版 P0 验收已通过；本次移动后，以最新 PR CI、Main 合并与新路径读回完成 **PORTAL CONTRACT FROZEN v1**。P1–P4 可消费冻结契约进行代码并行；其中 P2/P3 的真实 Runtime 集成与 P4 公网发布仍分别需要独立安全/成本 Gate，不得由 P0 自动授权。
