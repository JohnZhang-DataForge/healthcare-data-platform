# Shared Data Engine — 公共业务引擎

> 跨 Local DP 与 Azure Fabric 的**唯一共享 Python Wheel**，源代码位于 [`shared-data-engine/src/healthcare_data_engine/`](../../../../shared-data-engine/src/healthcare_data_engine/)。这不是另一套 Airflow、Fabric 执行服务或数据库 Writer。

## Canonical-first 的唯一业务归属

[Medallion Canonical ADR](../../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) 已确定：CSV、FHIR R4、HL7 v2 各使用 Source/Entity Adapter；所有来源先进入唯一的 Canonical Patient/Encounter 合同，再调用平台无关的 OMOP Candidate Mapper、DQ、Concept/Identity 规则、Reconciliation。Source-specific 编码差异由**经审核的版本化 Mapping Profile**传入同一 Mapper，不能靠名字相似猜测 OMOP Concept ID，也不允许复制一份 Fabric 专用 Mapper。Local PG Writer 和 Fabric Warehouse Writer 各自处理持久化事务，Shared 不承担 I/O。

**目标与当前实现必须分开**：正式发布的 0.1.6 已有 FHIR R4→Canonical、Person/Visit Registry、纯 Identity/Concept/FK 预检及 Shared OMOP Candidate；Local CSV/Person/Visit 的历史生产转换尚没有整体迁移到此 Wheel，HL7 Shared Adapter 也尚未实现。现存 Fabric `azure-fabric/warehouse/omop-foundation/writer/identity_plan.py` 负责无 I/O 的 F2 Preview；**不能据此声称统一 Identity 持久化/Gold Writer 已经在 Shared 内完成**。纯规则提炼需独立 OpenSpec、Local/Fabric 双 Runtime 等价测试和无损行为验证。现行平台详情见 [总体架构](../../../architecture/SYSTEM-OVERVIEW.md)。

## 代码能力和验收边界（按最新 main 与独立 Run 核对）

- **当前源码候选：** [`pyproject.toml`](../../../../shared-data-engine/pyproject.toml) 为 `0.1.6`，包含 Entity Registry / Person-Visit Candidate 兼容适配，并新增纯 Identity Snapshot / Concept 规则 / FK Reference Preflight（F2 原分配器保留唯一算法归属）；新增 F2 Preview → G5 Person/Visit Candidate 的安全 ID Handoff，全部输出仍保留拟议/已持久化状态且不进入 SQL/Delta Writer；本版本**已正式发布到 Fabric**（唯一 CustomLibraries Wheel 0.1.6）；正式业务 Notebook 已对齐 0.1.6 并完成只读 Spark 4.1 Runtime Smoke。已包含 FHIR R4 Patient/Encounter、Canonical v1 验证、Replay/Reconciliation、Handoff v1 结构校验、医院隔离的纯 OMOP Person/Visit Candidate Mapping。模块与测试以 [CODE.md](CODE.md) 的真实路径为准。
- **离线 Wheel：** [0.1.6 双运行时 CI #42281544230](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42281544230) 的可重复构建、独立安装与合成测试 PASS；[Local/Shared Person/Visit parity #42273958120](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42273958120) PASS。这仅证明覆盖的纯转换等价，不代表 Local 生产链已迁移。
- **Fabric Runtime：** [GA Publish #42284453546](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42284453546)、[正式 Notebook 定义读回 #42291355563](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42291355563)、[正式 Notebook Spark 4.1 只读 RUNTIME_SMOKE #42297766098](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42297766098) 均 PASS，Job Completed、精确 0.1.6 退出值、无临床数据读写。**此证明 Fabric 开发基线就绪，非 Gold E2E 已完成。**
- **依赖边界：** Shared 只负责纯计算。Blob/S3/OneLake/Delta/PG/Warehouse 物理写入、SparkSession、Notebook/Pipeline、部署和 Secrets 均由各平台独立负责。
- **正式合同：** Local Canonical v1 [Patient/Encounter Contract](../../../../local-data-platform/spark/contracts/canonical/) 仍是唯一权威，使用固定原字节/SHA；不复制第二套 Schema。

## 切换至 Fabric 主开发（2026-11-06）

- **Shared Engine 核心基线就绪**：冻结 0.1.6 API、Canonical Patient/Encounter v1、Person/Visit 回归及纯 Registry/Identity Snapshot/Concept/FK/Candidate 能力；开发按 OpenSpec 最小增量，不再造第二套 Mapper、Identity Planner 或 Writer。
- **Local DP 维护模式**：保留已运行的 CSV→Airflow/Spark→PG Person/Visit；仅故障、兼容性和回归修复。Local 迁移 Shared Wheel、Condition 的 Local 端兼容暂缓，不阻塞 Fabric。
- **Fabric 下一步**：真正 F1 release/license 与临床 Mapping Profile、F2 Warehouse Identity Snapshot、G5 Candidate Delta、Warehouse Gold 单事务/Replay、Pipeline E2E。见 [Fabric E2E 任务](../../../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) 及 [多实体 Change](../../../../openspec/changes/extend-shared-omop-multi-entity/tasks.md)。

## 权威导航

- [CODE.md](CODE.md)：唯一源码、Contract、测试和 CI 入口。
- [BUILD-AND-TEST.md](BUILD-AND-TEST.md)：离线依赖、Python/PySpark 测试、可重复 Wheel 构建与 FHIR–OMOP Handoff 指南。
- [目录级 AGENTS.md](../../../../shared-data-engine/AGENTS.md)：仅提供本组件 Agent 特殊规则；仓库根 [AGENTS.md](../../../../AGENTS.md) 管通用安全规范。
- [Shared Engine 结构和所有权](../../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)、[Fabric Native ADR](../../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。

既有 `shared-data-engine/tests/` 测试仍按历史例外原位保留，新测试遵循 `.github/quality/tests/`。当前开发进度和运行验收只记录在相关 OpenSpec/Run，不在 Agent 文件和 README 中重复维护。
