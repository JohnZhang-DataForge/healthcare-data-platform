# Proposal — 将 OIE 从 A01 演示升级为可操作的 HL7 v2.5.1 ADT 医院数据源

## Why
Healthcare 同时演示 **多医疗数据来源**（CSV/FHIR/HL7）与 **多处理技术**（FHIR Fabric PySpark、HL7 开源 Parser + 自托管 dbt Core）；HL7 作为独立医院输入格式必须保留原始 HL7 字节、事件生命周期及完整交付证据。当前 OIE 4.7.0 Johns Creek Channel 在 worker01/dw-oie 持久化运行，已实机证明 FHIR→ADT^A01 的少量转换，但 Channel Reader 从内部 REST API 接收 mini FHIR Bundle；Writer 仍是 none，**不曾**验收 MLLP/ACK、A03、Blob Publisher、Fabric Silver。

当前 `adt_a01.js` 未输出 Patient DOB/Gender/Race/Ethnicity 和 PV1-45，无法满足冻结的 Canonical Patient v1（18 字段）及 Encounter v1（27 字段，非空 end_datetime）。不能靠 Parser/dbt 猜医学事实。OIE 必须成为**可真实运行和独立校验的 HL7 v2.5.1 ADT producer/integration endpoint**，而不是只制造能通过合成 dbt 测试的 HL7。

## What Changes
- **P0 本 Change：** 记录合理的**首期完整可操作范围**：FHIR 源模拟 Hospital B，OIE 真正输出严格的 HL7 v2.5.1 ADT^A01（admit）和 ADT^A03（discharge），对实际存在的临床字段映射；A08（患者信息更新）和 HL7 MLLP/ACK 作为后续独立验证阶段，可扩展且不冒称已具备。按事件发布原始 HL7 bytes、batch/manifest SHA、下游独立读回。
- **兼容性优先：** 不覆盖已验收的持久 OIE Channel ID `69ace705-a675-45f6-b126-a3b22a65212a`、Derby/PVC、旧历史 Batch；新事件/Channel 使用新的版本身份，完成只读审计和审批后才能实机部署。
- **分步开发：** 新 OIE 生产业务 Mapper / Channel 规划与源测试通过独立 OpenSpec Task；实际 OIE / Azure 操作不能被文档 PR 自动授权。新测试归 `.github/quality/tests/data-platform/clinical-producers/oie/`；本地源码仍归 `local-data-platform/apps/clinical_producers/oie/`；具体人类文档归 `documents/systems/data-platform/clinical-producers/`。
- **HL7 消费技术不改变：** OIE 只做医院事件生产、路由、原始 HL7 交付；Azure Blob 保存 Raw HL7 + verified manifest；Self-Runner `hl7apy` Parser + dbt SQL 各自处理（后端 DuckDB/Local Spark **PENDING**），统一到 Canonical Candidate → ONE Silver Publisher → Delta Silver → Shared OMOP。此 Change 不开发重复 OMOP Mapper、也不把 FHIR↔HL7↔FHIR 作为业务流程。

## Capabilities
- Source scoped ADT events A01/A03、合法 Patient/Encounter 映射、稳定控制 ID、重跑不重复；Event lifecycle 可靠处理 A01-only HOLD/A03 完成、晚到/重复/冲突。
- OIE 输出可与 `hl7apy` 独立解析，默认原始 HL7 保留而不是 OIE 解码 JSON 后再上传。
- 未提供真实 DOB/gender/race/ethnicity/end 时间时 fail closed 并留下可审核 Quarantine/HOLD；禁止发明医疗事实。
- HL7 Raw Blob 交付 manifest-last + SHA256 + source/proc ID + 独立远端 GET + Replay/Conflict Policy。
- 可选 MLLP Listener / ACK/NACK / A08 生命周期按单独验收定义，不将其混为已有生产能力。

## Impact
- 保留 `documents/architecture/DATA-FLOW.md`、Medallion ADR 和 Shared Engine 合同权威；实际生效后更新对应 ACTIVE 系统文档与 CODE owner，不引入不必要目录。
- 不修改 FHIR Fabric 主线、已验收 Silver、OMOP Gold、现有 OIE Channel/Derby/worker01，亦不操作正式 Azure/Fabric。任何实机操作遵循 SAFE-OPERATIONS 与 SESSION-COORDINATION，并锁定 SHA、批次、资源 ID、独立读回。
