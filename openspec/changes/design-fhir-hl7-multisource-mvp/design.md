# Design

## Scope & source of truth

本 Change 是一次**经用户讨论确认的架构设计冻结**，长期人类可读设计见 [FHIR/HL7 多来源 MVP](../../../documents/architecture/design/FHIR-HL7-MULTISOURCE-MVP-DESIGN.md)，整体背景见 [Healthcare V2 Roadmap](../../../documents/architecture/design/HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)。这里只记录本轮文档决策、前提、风险、验证及回退；不重复维护实现计划，也不声明任何新业务 E2E 已运行。

## Decisions

- Synthea 为**单一核心与冻结合成源群体**；三个医院模拟不同系统的来源合同和 ID，不声称独立真实 EHR。固定 Crosswalk 最小实现允许版本化 CSV/JSON，且没有 Crosswalk 时不合并患者。
- FHIR 保持 Synthea 原生 R4 Bundle JSON，第一版不依赖 HAPI FHIR Server、NDJSON 转换或全量 FHIR 功能。
- HL7 v2 由 OIE Transformer 将已规整的临床事件转为 ADT A01/A08；需少量数据关联/事件准备代码，但无需 Python HL7 v2 报文编码器。OIE 首版 File Writer → 本地持久 spool → Blob Publisher，不加入 Kafka；MLLP/ACK 作为下一阶段可选扩展。
- Azure Blob RAW/Manifest/READY 与 Fabric Bronze/Silver 保留可重复读回的来源身份、文件校验和幂等策略；任何失败都不伪装业务成功。
- 保留已验收的 local OMOP NEW_ONLY 事实；Local DP 迁移后兼容与 Fabric 未实现状态不能因本设计变为完成。

## Compatibility, operational risk, and validation

- **OIE 风险**：本轮未核对可部署镜像和对应发行版的全部 Connector/Transformer 运行兼容；开工前做许可/版本及最小 Channel 实测。社区 Mirth 示例不能当作 OIE 验收。
- **身份风险**：独立 Synthea 重跑、Seed/Snapshot 漂移、字段变化可能导致假重叠。固定 cohort+scenario+crosswalk 版本并以身份映射验证；不强制启用现有 UPDATE/MIX。
- **发布风险**：OIE 成功生成文件 ≠ Azure Blob READY ≠ Fabric 已处理。分层校验、原始文件保留、异常 Batch 不发布 READY。
- **运行权限**：本轮仅静态 Markdown；不部署/修改共享集群、Cloud 或历史 Writer。后续功能 Change 需单独授权并提供真实 Source SHA、Batch 与读回。
- **文档验证**：PR 上检查 OpenSpec schema/Strict、Trusted Change Gate 和 Markdown links；仅证明文档/治理符合静态门槛。

## Rollback

若本方案需重审，更新或撤回本 PR 中的新设计和索引即可；没有 Runtime 副作用。若未来调整技术选型，应建立独立 Change，不改写既有运行验收历史。

## Follow-up boundary

本 Change 合并并按文档完成情况归档后，FHIR、HL7、Patient Crosswalk、Fabric Analytics 各自后续 Change 负责实现/测试/验收。此处不放置下游功能实施的平行 Tasks。
