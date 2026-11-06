# Tasks — HL7 + dbt Multi-Engine Canonical Evaluation

> 当前仅是**设计与隔离验证**，不是原生生产实施；dbt 后端选择为 **PENDING**。实验源码只在 Self-Runner，Healthcare 不写 POC 代码。每个 PASS 必须有明确真实运行证据。

## 1. 讨论内容持久化（先于实验）
- [x] 1.1 核对现有 FHIR / OIE 运行事实、Canonical v1 合同、Unified Silver 与 Shared Engine 归属。
- [x] 1.2 写入多来源、多处理引擎、统一 Canonical / OMOP 的目标、风险与未来 Entity 扩展原则。
- [x] 1.3 写清本地 dbt-duckdb、本地 dbt-fabricspark session、远端 Livy 三条路线的算力/成本边界；明确后端待实验验证后选择。
- [ ] 1.4 形成 docs-only PR，CI 验证、审查/合并；在完成前不得称本方案已并入 main。

## 2. Self-Runner 纯本地离线 POC
- [ ] 2.1 在 Self-Runner 自有隔离目录建立独立实验代码、固定版本、合成 HL7 fixtures 和 runner-only 测试入口；不得引入云凭据/真实集群访问。
- [ ] 2.2 验证开源 HL7 Parser 的 v2.5.1 解析与缺字段/转义/时间/重复消息负向断言。
- [ ] 2.3 执行 dbt Core + DuckDB compile/run/test，记录实际日志、schema 与 replay。
- [ ] 2.4 执行 dbt Core + Local Spark (dbt-fabricspark session) compile/run/test，记录版本和本地 Delta 读写；不可运行则提供具体阻断证据。
- [ ] 2.5 同一 synthetic fixture 对齐 Candidate 值、异常分类、SQL/Delta 能力、运行成本；对比打分，**测试后**提议选型。

## 3. 正式 HL7 集成（尚未授权、与 POC 分离）
- [ ] 3.1 评审 OIE Producer 扩展（PID-7/8、race/ethnicity 真实来源、A03 discharge 或 Canonical v2）及原始 HL7 Blob Publisher。
- [ ] 3.2 以单独 Implementation OpenSpec 完善实体插件/Schema/版本化 Profile、单一 Silver Publisher、quarantine、replay、readback。
- [ ] 3.3 Azure/Fabric 真实 E2E 需要单独的执行授权和证据；不得因本地 POC PASS 推导真实 Silver Approved 或 Gold COMMITTED。

## Evidence / Blockers
- 设计基线：2026-11-05 Healthcare 最新 main 的 Medallion ADR、DATA-FLOW、OIE Channel 文档、两个 Local Canonical v1 Contract。
- OIE 真实 FHIR→HL7 消息已验收，但 HL7 Blob 发布未验收；FHIR G4 Approved Silver 已验收，Gold 仍 OPEN。
- A01 单消息缺少 Canonical v1 必需字段；必须将缺失事实与来源 Profile 约束作为阻断条件，不得靠默认值绕过。
- 本 Change 实验全部执行证据指向 Self-Runner 的单独 PR/commit/run；不往 Healthcare 增加实验资产。
