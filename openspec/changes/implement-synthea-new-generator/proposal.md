# Proposal

## Why

现有 `local-data-platform/apps/synthea/new_only/` 已深度绑定 Local DP 的 18 CSV、SeaweedFS S3、历史批次身份和 OMOP 消费路径，真实新批次 E2E 已经过验收；不应为 FHIR/HL7 修改既有 Generator 或重置运行合同。

此前 FHIR/HL7 多来源目标设计将 Hospital A/B/C 与共享 Cohort / Crosswalk 绑定，增加了当前 MVP 不需要的跨医院患者关联复杂度。2026-10-24 用户明确的新决定是：Local DP/OMOP 是可承载多来源数据的本地集成平台，**不是** Atlanta 某一家医院；新模拟来源独立为 Atlanta/FHIR R4 和 Johns Creek/HL7 v2。两家医院仅共享 Synthea 生成器代码，各自独立生成患者；第一版不需要全局共享 Cohort 或跨医院 Crosswalk。

## What Changes

- 在 `local-data-platform/apps/synthea/synthea_new_generator/` 建立独立 `synthea_new_generator`：使用现有固定版本 Synthea 引擎，接收版本化、可验证的生成请求参数（population/state/city/seed/reference_date/output_formats），仅实现 `NEW_ONLY`，输出 CSV 和/或 FHIR R4 原始文件。
- Request 参数在第一次运行时冻结，生成结果为本地不可变、可校验的数据资产，附来源、实际文件、记录数量与 SHA-256 Manifest；重复同一请求不得静默产生新数据。
- 医院与 Feed 的外部 Profile 负责映射参数与后续路由，不把 Atlanta、Johns Creek、FHIR、OIE、Azure Blob 逻辑写死在 Generator。
- 两条 MVP Profile：Atlanta → 独立调用 Generator、FHIR R4 原生 JSON → FHIR 验证与后续 Blob Publisher；Johns Creek → 独立调用 Generator、FHIR R4 原生 JSON → 下游 Eclipse OIE 映射/转换 → HL7 v2 → 后续 Publisher。实际 OIE 直读 Bundle 的正确性必须由单独真实 PoC 证明。
- 与现有 Local DP `apps/synthea/new_only/`、SeaweedFS、Airflow、Spark、PostgreSQL OMOP Writer、原 Batch/Manifest 合同完全隔离；新 Generator 不触发 OIE、不写 Azure、不接 PostgreSQL。
- 新功能为独立 OpenSpec Capability，按代码、合同、测试、镜像/K8s Job 切片实现并逐项验收；本 PR 仅新增设计/Spec/Tasks，不实施、发布或运行新 Generator。

## Capabilities

### New Capabilities

- `synthea-parameterized-new-generation`：通用、参数化、可重试、可验证且与既有 OMOP NEW_ONLY 隔离的合成新患者生成能力。
- `synthea-source-profile-handoff`：外部医院/Feed Profile 到生成请求的显式映射，以及 FHIR R4 本地输出供不同下游使用的交接边界。

### Modified Capabilities

- 无现有业务合同变更。旧的 `design-fhir-hl7-multisource-mvp` 是当时的目标设计记录；在 **新 Generator 与两家独立模拟医院** 的 MVP 范围内，本 Change 明确取代其共享 Cohort、跨医院重叠前提。其余 HL7/OIE、Blob 和 Fabric 实现应由后续独立 Change 细化，并同步长期架构文档。

## Impact

预期新增：`local-data-platform/apps/synthea/synthea_new_generator/`、`local-data-platform/contracts/synthea/new-generator/`、`local-data-platform/config/` 或现有配置目录下的医院 Profile、`local-data-platform/images/synthea-new-generator/`、`local-data-platform/kubernetes/manifests/synthea/new-generator/`、`local-data-platform/tests/synthea_new_generator/`。实际落地路径以仓库 CODE Map 与 CI 命名规则核对后为准，同 PR 同步对应 `documents/systems/data-platform/synthea/CODE.md`。

明确不在本 Change：OMOP PG Exporter、FHIR→HL7 OIE Channel 的正式实现与 Live 验收、Azure Publisher/Fabric ETL、全局共享 Cohort、跨医院患者匹配、`UPDATE_ONLY/MIX_DATA`、原生产数据修改或清理。共享 K8s/云运行必须另行经过 Safe Operations 和资源协调；静态验收不代表运行验收。
