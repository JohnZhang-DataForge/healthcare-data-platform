# Proposal

## Why

现有本地 Portal P1–P6 已完成内网阶段，但 Emory 招聘展示需要访客**无需 Azure/GitHub 身份即可看见**真实完成的跨云 E2E、按需触发一次新合成数据处理且控制 Fabric 成本。固定每 15 分钟全天运行低流量 Spark 不经济；仅将 Azure Fabric Item Relations JSON 转成展示图还不能覆盖真正的表/列级运行血缘。需要统一的可移植 Spark、OpenLineage、Blob 缓冲与匿名只读站点，并有硬性额度/权限闸门。

## What Changes

- 冻结 [Healthcare On-Demand Live Demo 专项基础设施方案](../../../documents/infra/HEALTHCARE-ON-DEMAND-LIVE-DEMO.md)：Cloudflare 静态快照、真实访客受控触发、Self-Runner 编排、Synthea 5–10 人、FHIR/HL7 Azure Blob Publisher、Spark Notebook / Local Operator 双后端。
- 规范美国 IP 触发、Turnstile、人机校验、每 IP 每 UTC 日 3 次、全站成本闸门（初期建议 6 次/日）、single-flight、默认 OFF、管理员独立开关、邮件和故障回退；普通 GET 不触发任何云端任务。
- 业务 PySpark 采用平台无关转换核心和 Fabric / Kubernetes Adapter；最终 Spark 执行地由后续免费真实 POC 决策，暂不部署付费 F2。
- Local/Fabric 血缘统一 OpenLineage Run Event → Azure Blob 不可变 JSON/JSONL → 本地 Consumer → Marquez Ingestion API → PG14，公开导出白名单安全快照；无需血缘专用 Delta Table，业务 Bronze/Silver Delta 仍保留。
- 公开展示**暂定 Marquito 风格**，作者源码复用许可未确认时禁止复制部署；必要时以许可明确的可视化库替代。
- 在同一个 Active OpenSpec Change 管理未来开发、接口行为、测试与真实验收，不在文档下复制并行 Tasks。

## Capabilities

### New Capabilities

- on-demand-healthcare-demo: 匿名只读展示和严格限额/鉴权的受控真实任务触发。
- portable-healthcare-spark: Local/Fabric 共用业务 PySpark 合同，采集可验证标准 OpenLineage。
- openlineage-blob-showcase: 不可变 Blob 缓冲、Marquez/PG14 可靠同步以及公开脱敏血缘快照。

### Modified Capabilities

本轮不改动已有 Producer、OMOP Writer、Portal、PG14、Workspace Terraform 或 Capacity Controller 的实际接口。未来实现 Change 必须保护其现有行为与安全规则。

## Impact

**当前 PR 只修改 Markdown 与 OpenSpec 设计/未来验收合同**；不修改代码、Workflow、Kubernetes、PostgreSQL、Azure Blob、Fabric Items、Cloudflare、外部邮件或收费资源。新增 Specs 是目标需求，不是 Current Spec 或已验收能力。任何后续共享环境操作继续依照 Safe Operations 和 Session Coordination 单独审批。
