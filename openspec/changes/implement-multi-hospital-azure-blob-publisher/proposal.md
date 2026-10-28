# Proposal — Multi-Hospital Azure Blob Landing Publisher

## Why

`synthea_new_generator` 的 FHIR R4 已实现、P4.1 `SOURCE_HANDOFF_VERIFIED` 已验证；Johns Creek 的 OIE 4.7.0 在 `dw-oie/worker01` 真实完成 31 个合成 Encounter（1 个 IMP→ADT^A01、30 个 AMB→SKIP），并读回持久化 Derby。**Atlanta FHIR 已通过真实 Azure Blob 5/100 人数据与 Manifest GET/ETag/SHA 验收；Johns Creek HL7 尚无 Azure Landing 发布收据。** 下一步必须将“本地数据有效”“OIE 转换完成”和“Blob 上传可消费”严格区分。

## What Changes

- 新增**共享且医院无关**的 Azure Blob Publisher，使用已经存在的 Azure Landing 存储账户和容器（具体 Endpoint/Container 由受控运行配置注入），不可变对象 Key、请求冻结、SHA256 校验、重复请求一致性和写后独立读回。
- Atlanta 模拟医院：当前稳定 Profile `atlanta-hospital-a` / `atlanta-hospital-a-fhir-r4` → 现有 Generator FHIR R4 → `SOURCE_HANDOFF_VERIFIED` → Blob FHIR 对象 + commit manifest。
- Johns Creek 模拟医院：当前稳定 Profile `johns-creek-hospital-b` / `johns-creek-hospital-b-hl7-v2` → Generator FHIR R4 → OIE 4.7 Channel → 通过独立 HL7 v2.5.1 解析验证的 ADT^A01 → Blob HL7 对象 + commit manifest。AMB 不伪造 A01。
- 外部医院配置只负责选择路由/交付；Generator 和现有 Local DP/OMOP 完全不修改。新增业务源码放 `local-data-platform/apps/clinical_producers/`，必要的安全执行 Workflow 在 Self-Runner。

## Capabilities

- `multi-hospital-azure-blob-publisher`：共享 immutable Blob 上传、实际读回和可审计收据。
- `hospital-landing-routes`：Atlanta FHIR 直达和 Johns Creek 经 OIE 的 HL7 交付。

## Impact

- **先代码与静态/隔离测试，之后经独立明确授权才执行 Azure/K8s 真实写入**；OpenSpec/CI 不构成部署许可。
- 不创建额外数据库、Kafka、微服务或 Fabric Notebook/Pipeline；不触碰 Airflow、Spark、Writer、OMOP 库、旧 PVC、既有已验收的 OIE 消息历史。
- 不承诺本轮创建 Azure 资源或取得存储权限；必须先核对实际账户、容器、RBAC、Secret、网络和收费边界。

> **2026-10-27 阶段边界：** 旧 OIE 31 个 Encounter 的实机转换不等于新医院身份已部署，也不等于 HL7 Azure 落地。新批次必须先核对持久 OIE Channel 的配置并获取受限账户/TLS，再由受控 Runner 产生新 POST 收据，完成 HL7 Azure 远端读回。静态 Job/离线适配器与源码分支不授权 Blob 写入。
