# Proposal — HL7 v2 + dbt 多引擎 Canonical 集成评估

## Why
Healthcare 的目标是同时展示（1）CSV / FHIR / HL7 多种医疗数据源与（2）PySpark DataFrame / dbt SQL ELT 多种处理方式；不能误写为“仅为面试增加 dbt”或“为了 HL7 反复无意义转换”。此前 2026-10-30 Medallion ADR 的核心约束始终有效：不同来源分别适配，同一 Canonical 合同，同一后续 OMOP 业务引擎。

## What Changes
- **确认且暂不改变：** FHIR R4 → Azure Blob → Fabric PySpark → Canonical Candidate；正式 Approved Silver 是同一 Lakehouse Delta canonical_patient/canonical_encounter；之后统一共享 OMOP Candidate / Concept / Identity / DQ / Reconciliation，由平台专属 Writer 控制最终 Gold 事务。
- **计划中的 HL7 路线：** 模拟医院的 OIE 4.7.0 产生原始 HL7 v2.5.1 ADT → 不可变 Azure Blob Landing / manifest → 标准开源 HL7 Python Parser（例如 hl7apy，待版本/兼容验证）→ Structured Staging → dbt Core SQL Models 生成 Canonical Candidate → 统一 Contract/DQ/Publisher gate → 同一 Approved Silver Delta。
- **dbt 后端选择暂不定：** Self-Runner 先在隔离环境比较 dbt-duckdb（本地 DuckDB）与 dbt-fabricspark(method: session，本地 Spark）；如有必要，日后对照 Fabric Livy / 原生 dbt Job。测试结果未形成之前，不将一种后端写成已选定。
- **评估记录留在本 Change；所有实验代码/测试/fixture/运行脚本只放 JohnZhang-DataForge/Self-Runner。** Healthcare 本轮没有 HL7/dbt 实验源码、依赖、Workflow、云操作，也不改已有 FHIR 或 Local DP。

## Capabilities
- 多医院 feed 的隔离与 provenance（hospital_id / feed_id / request_id / raw SHA / processing_version）。
- 不手写完整 HL7 规范解析器；标准包只负责语法和字段抽取，dbt 负责来源特定 SQL 标准化，Contract 和 OMOP 语义继续由唯一权威控制。
- HL7 Canonical Candidate 经统一受控 Approval/Publication 才能进入正式 Silver；dbt test PASS 不能充当业务已提交。
- 初期只用合成 HL7 A01/A03，后续逐实体扩展，并对 v1 缺失字段 fail-closed。

## Impact / Non-goals
- 影响的权威：Medallion ADR、Native execution ADR、Canonical patient-v1/encounter-v1、Shared Engine Owner、现有 Fabric Gold OpenSpec。任何后续实施须对这些文档进行增量评审，不能悄悄覆盖。
- 本轮**不**替换 OIE、不重新开发第二套 OMOP Mapper、不使 Canonical Silver 出现多个无协调 Writer、不修改真实 Fabric/Blob/Capacity、不调用已经验收的 OIE 历史请求重放。
- 不承诺 DuckDB 对远程 OneLake Delta 的 MERGE 能力；不认为 dbt Core 在 Runner 上运行就意味着其 Fabric Adapter 的 SQL 不消耗 Fabric CU。
- 本 Change 是**评估与方案保留**，目前无新增运行行为需求/已采用 spec，故 skip_specs=true；正式功能实施前必须增加经批准的行为 Specs 并调整适用 OpenSpec，不能利用该配置跳过实施验收。
