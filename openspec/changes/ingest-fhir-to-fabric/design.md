# Design

## Status, authority and scope

**DRAFT / 未通过评审 / 不授权运行。** 完整、可讨论的技术设计与 Local 对照矩阵维护在唯一正文：[Fabric FHIR Blob → Notebook/Pipeline → OneLake 入库初稿](../../../documents/architecture/design/FABRIC-FHIR-BLOB-INGESTION-DRAFT.md)。本文件仅固定 OpenSpec 决策背景、未决项、风险与实现门槛，避免复制另一份可能漂移的详细设计。

## Local architecture deep-dive (2026-10-27)

源码级分层复盘与新通用代码目录树见 [Local DP → Fabric 代码架构](../../../documents/architecture/design/LOCAL-DP-TO-FABRIC-CODE-ARCHITECTURE-DRAFT.md)。核心改进：

- 明确 Local 历史 Processing/Canonical/Approved Raw/Processed/Candidate/Writer 的逻辑合同与当前 NEW_ONLY 并行 Person/Encounter Spark → Reconciliation → Handoff → PG Writer 的实际运行路径不同，不把所有历史发布器说成当前 DAG 默认工作。
- Fabric Bronze 为原始 FHIR 字节，Local Approved Raw 为 Canonical Parquet；Silver 对应 approved Canonical，Candidate/Serving 保留持久化 Gate。
- 候选源码采用 azure-fabric/ingestion/ 下的 Python package：sources、canonical、mapping、quality、publishing、jobs、runtime 与单测；Fabric 原生 Notebook/Pipeline 仅薄调用，不把所有 Mapper 写进 notebook-content.py。
- 单 Notebook 首批降低成本，但严格 OMOP Person+Visit 的多表 readback/commit visibility 可使用独立 verifier Notebook；Delta 不等于 PG single-TX。
- Local Canonical/OMOP Contracts 以既有文件为唯一事实，不手工创建第二套不一致 schema；FHIR/HL7/PG Snapshot 的源 Adapter 独立，不强行共用原始 Manifest 协议。

核对基准 Healthcare Main 4596c1cec866032e5753597201b595dd1505b2ae（2026-10-27）。对现有代码和合同仅做只读核对；没有对用户提到的 Azure Blob 成功提交做本轮独立 Runtime GET，也没有把三次 Fabric Notebook Test FAILED 改写成成功。

## Candidate decisions for review (not adopted)

1. **Source-of-truth**：现有 Publisher 最终不可变 landing-manifest.json 是严格读取入口；源格式 FHIR_R4；本轮只消费 Patient/Encounter，不从 Blob List 推断 READY/最新。
2. **MVP compute**：一个受控 Fabric Data Pipeline + 一个参数化 PySpark Notebook + 可独立测试的解析/映射核心；优先一个 Spark Session，不复制本地十几个调度/Writer 步骤。
3. **Source access**：先做 Azure Blob Shortcut 可用性和 byte-level SHA/RBAC POC；不支持时用 Copy Activity 作为备选，并增加目的端独立读回。
4. **State and idempotence**：hospital_id/feed_id/request_id/manifest_sha 构成 batch identity；same Manifest COMMITTED→SKIP，drift→HOLD；资源键以 source_system + FHIR resourceType + id 隔离，不按姓名/生日跨院自动合并。
5. **Schema and mapping**：复用 Local Canonical Patient/Encounter 和 OMOP v5.4 字段/PK/FK 的结构性约束，FHIR Bundle/ref/Concept 的新 Mapper 必须重新测试；FHIR 不绕行 Local PG Writer。
6. **Writer safety**：Delta 单表事务不能等同于 Person+Visit 原子事务；批次版本化 staging、显式 cross-table reconciliation、最后 visibility commit 和只读 committed serving views 是候选保护方案。
7. **Business evidence**：Pipeline/Notebook Job Completed 不能证明业务提交；必须有真实 Notebook 输出、Delta 版本/PK/FK/计数独立 Readback、批次 Audit。Fabric 旧兼容性 HOLD 优先解决或取得新的用户授权。
8. **Delivery owner**：业务 Notebook/Pipeline 由已规划 fabric-cicd 独占，不能与旧 Terraform Bootstrap 双管理；真实 .platform logicalId 只从 Fabric 实际 Item 获得。

## Risks and tradeoffs

- Manifest v1 没有 READY 布尔值和 cohort_id；额外字段需要单独带版本协议，不能原地修改和假定后向兼容。
- FHIR fullUrl/urn:uuid、相对 Reference、缺失/扩展字段、resource version 与 OMOP Concept 需要适配层；Synthea 测试通过并不等于所有 FHIR R4 输入都被正确支持。
- Delta 不提供跨多个独立表的原子事务；任何尚未证明的 serving view/ID-map 并发协议应使 OMOP commit 保持 HOLD。
- Fabric Trial Spark Notebook Create/GetDefinition/exitValue 旧失败未解；未获得新决策不执行第四轮试验，不能用调度 Completed 替代 hash/output。
- Blob Reader 权限、Workspace identity、Shortcut、容量和成本不能凭设计推定。用户要求免费优先；Paid F2 不在本轮授权范围内。
- OpenLineage Local Scala 2.12 Listener 不直接兼容推定的 Fabric Scala 2.13；血缘正确性是独立测试 Gate。

## Review questions

- 本轮目标先到 Bronze/Silver，还是含 OMOP 5.4 Person+Visit Delta Gold？
- 先尝试 Shortcut 零拷贝，或 Copy Activity 冻结归档？
- 首版严格 NEW_ONLY，还是允许同 FHIR source key 更新？
- 是否明确 Local PG OMOP 与 FHIR Delta 分开 IDs、crosswalk 以后独立联结？
- Fabric POC 三次失败后的下一步是否需要新的 Notebook LRO/readback 只读核查与实机授权？

## Validation and rollback

现在只校验文件链接、OpenSpec Schema/Gate、文档事实来源与误报；不运行 Fabric。后续根据 tasks.md 的 Gate 实施，代码和测试单独 PR，不合并设计分支之前用户可直接修改候选选择。回退仅取消 Git Draft，无数据持久副作用。
