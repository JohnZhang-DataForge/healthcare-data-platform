# Tasks

> DRAFT / DESIGN-ONLY。所有未完成任务保持未勾选；本设计即使日后被合并，也**不代表 Notebook、Pipeline、Delta 或 Azure 业务运行已部署**。本轮只提交 Git 文档，不进行 Azure/Blob/Spark/PG 的任何操作。具体设计见 [唯一初稿](../../../documents/architecture/design/FABRIC-FHIR-BLOB-INGESTION-DRAFT.md)。

## 1. Architecture draft and review

- [x] 1.1 从实际源代码核对 Publisher Landing Manifest v1、FHIR Source Handoff、Local Canonical/OMOP Contracts、Airflow NEW_ONLY/Writer 安全模型及 Fabric Notebook/Pipeline 占位状态。
- [x] 1.2 整理 Blob → Pipeline → Spark Notebook → Bronze/Silver → 候选 OMOP Delta 初稿，列出 Local DP 可复用/可优化内容、事务边界、身份、成本与验收门槛。
- [x] 1.3 在独立 feature 分支记录 proposal/design/tasks；不合并 main、不运行 Fabric、未经批准不生成可执行 Notebook/Pipeline。
- [ ] 1.4 用户讨论并确认 5 个设计决策（层级终点、Shortcut/Copy、NEW_ONLY/Update、跨来源 ID、Fabric 旧 POC HOLD 的安全推进路径）。
- [ ] 1.5 审核后补全正式 delta spec/验收场景、CODE 归属、源 SHA、需求边界；经静态 CI Review 后用户决定是否合并设计 PR。

## 2. Proposed future implementation (not authorized by this draft)

- [ ] 2.1 GET-only 核对新 FHIR 发布的 Manifest v1/对象 Byte SHA、实际 FHIR entry/Patient/Encounter/ref 形状、真实 Connection/RBAC/Runtime/Lakehouse 身份。
- [ ] 2.2 离线冻结合成 FHIR fixtures；解析/Schema/URI/Reference/Concept、source identity、Manifest drift、hash、重试与非法输入负向测试。
- [ ] 2.3 经用户新的明确授权后解决 Fabric Notebook Create/GetDefinition LRO/exitValue 旧三次失败；独立读回发布 Notebook 实际源 SHA 与处理结果，免费容量限制内运行。
- [ ] 2.4 只在允许的 Fabric 测试 Workspace、隔离表上完成 Byte-HASH→Bronze 的最小真实 5–10 Patient Run 与同 Manifest 重试。
- [ ] 2.5 100 人 FHIR Batch Patient/Encounter → Silver Canonical 的真实解析、FK/DQ/源追溯独立读回及负向测试。
- [ ] 2.6 OMOP Person/Visit Delta Stable ID、source-key map、跨表可见性/读回和部分失败恢复设计单独审核并执行受控测试。
- [ ] 2.7 真实 Pipeline Notebook 参数、Failed/Skipped/Committed 区分、成本/性能与 OpenLineage 完成事件独立核查。
- [ ] 2.8 完成所有授权的实机 E2E 证据与文档/CODE/Spec 同步后，才考虑完成业务 Change/Archive。

## 3. Explicit non-goals

- 本轮不改现有 Local PG17/S3/Airflow/Spark/Writer；不重放已经 COMMITTED 的 Source Batch。
- 本轮不改现有 Azure Publisher Manifest v1、HL7 OIE、PG→Blob OMOP export 或对外 Portal。
- 不创建/更改付费 Capacity、不 Apply Terraform、不创建云端 Pipeline/Notebook 或 Delta 表、不改变 Workspace 身份。
