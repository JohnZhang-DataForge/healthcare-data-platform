# Tasks

> **DESIGN-ONLY / NO RUNTIME AUTHORIZATION**：本 Change 只记录已确认的 FHIR/HL7 MVP 架构和 Markdown 交付，后续功能由单独 OpenSpec Changes 开发。勾选设计文档工作**不代表** FHIR、HL7、OIE、Blob 或 Fabric 已运行。

## 1. Design documentation

- [x] 1.1 核对当前 Healthcare Main、V2 总路线、Local DP 与 Azure/Fabric 验收边界及 Synthea/OIE 格式能力。
- [x] 1.2 将共用 Synthea Core、跨来源患者 Crosswalk、FHIR 原生 R4、OIE 转 HL7 v2、文件落 Blob、MVP 不使用 Kafka 与可观测失败边界形成完整长期设计文档。
- [x] 1.3 在 `documents/architecture/design/README.md` 添加唯一设计入口，并在已有 V2 Roadmap 链接新详情。
- [ ] 1.4 审核本 PR 的 OpenSpec/Trusted Gate/Markdown Links CI 结果，确认没有业务源码和运行资源变更。

## 2. Closeout

- [ ] 2.1 仅在 PR 合并并静态检查通过后，登记最终 Merge SHA / PR，按设计文档验收完成本 Change 并单独归档；不写 Current Specs 以冒充尚未实现的行为。
