# Proposal

## Why

Healthcare V2 已确定先把多来源 FHIR/HL7 做成**能实际运行和展示的最小版本**。此前的总路线只说明 FHIR R4/HL7 v2 为独立来源，没有冻结 Synthea 复用、部分患者重叠、OIE 转码、是否使用 Kafka 等决定，容易在后续任务中反复扩展范围。

## What Changes

- 冻结可复用的 Synthea Core + 有版本的基础合成患者群体与固定 Patient Crosswalk：三个模拟医院具有各自来源身份，部分患者重叠但事件不盲目复制。
- Hospital B：Synthea 原生 FHIR R4 Bundle JSON → Azure Blob READY → Fabric Bronze/Silver（目标）。
- Hospital C：Synthea CSV/JSON 经轻量场景关联成为标准化事件 → 本地 Kubernetes OIE Channel 转换 HL7 v2 ADT → 持久化文件/Blob Publisher → Azure Blob READY → Fabric Bronze/Silver（目标）。
- 明确 MVP **不使用 Kafka、不另造 Python HL7 v2 编码器、不部署第二套 OIE、不把 MLLP/ACK 作为上线门槛**；部署前核验 OIE 发行版与实际 Channel 能力。
- 在 `documents/architecture/design/` 新增长期目标设计并从已有 V2 总路线及目录索引引用。

## Capabilities

### New Capabilities

本 Change **仅明确未来架构目标和验收边界**，不新增运行能力。正式 FHIR/HL7 业务功能分别另建 Change，届时添加可验证的 Specs。

### Modified Capabilities

无现行业务或合同变更。本 Change `skip_specs: true`，不得把未来目标发布为当前已实现需求。

## Impact

只有 `documents/architecture/design/` 的文档和本 OpenSpec Change；不触碰 Python、DAG、Spark、Synthea 镜像、OIE/K8s、Self-Runner、Terraform、Azure Blob、Fabric 或历史已经提交的 Batch。Fabric 账号重建设计本轮不讨论。
