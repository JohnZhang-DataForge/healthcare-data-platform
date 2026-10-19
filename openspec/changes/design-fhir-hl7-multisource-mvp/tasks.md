# Tasks

> **DESIGN-ONLY / NO RUNTIME AUTHORIZATION**：本 Change 只记录已确认的 FHIR/HL7 MVP 架构和 Markdown 交付，后续功能由单独 OpenSpec Changes 开发。勾选设计文档工作**不代表** FHIR、HL7、OIE、Blob 或 Fabric 已运行。

## 1. Design documentation

- [x] 1.1 核对当前 Healthcare Main、V2 总路线、Local DP 与 Azure/Fabric 验收边界及 Synthea/OIE 格式能力。
- [x] 1.2 将共用 Synthea Core、跨来源患者 Crosswalk、FHIR 原生 R4、OIE 转 HL7 v2、文件落 Blob、MVP 不使用 Kafka 与可观测失败边界形成完整长期设计文档。
- [x] 1.3 在 `documents/architecture/design/README.md` 添加唯一设计入口，并在已有 V2 Roadmap 链接新详情。
- [x] 1.4 审核本 PR 的 OpenSpec Static Validation、Change Gate、Documentation Relative Links CI 结果（修正后 SHA `5d27f92710f1fc022e64d607e11a81797c33b3ee`，三个 Job SUCCESS）；Trusted Change Gate 由主分支受信任 Workflow 执行，以最终 PR GitHub 合并门禁为准；确认本 PR 仅修改设计与 OpenSpec 文档、没有业务源码或 Runtime 操作。

## 2. Closeout

- [ ] 2.1 仅在 PR 合并并静态检查通过后，登记最终 Merge SHA / PR，按设计文档验收完成本 Change 并单独归档；不写 Current Specs 以冒充尚未实现的行为。
