# Shared Data Engine — 公共业务引擎

> 跨 Local DP 与 Azure Fabric 的**唯一共享 Python Wheel**，源代码位于 [`shared-data-engine/src/healthcare_data_engine/`](../../../../shared-data-engine/src/healthcare_data_engine/)。这不是另一套 Airflow、Fabric 执行服务或数据库 Writer。

## 代码能力和验收边界（按最新 main 与独立 Run 核对）

- **当前源码版本：** [`pyproject.toml`](../../../../shared-data-engine/pyproject.toml) 为 `0.1.3`。已包含 FHIR R4 Patient/Encounter、Canonical v1 验证、Replay/Reconciliation、Handoff v1 结构校验、医院隔离的纯 OMOP Person/Visit Candidate Mapping。模块与测试以 [CODE.md](CODE.md) 的真实路径为准。
- **离线 Wheel：** Python 3.11/PySpark 3.5.7 和 Python 3.13/PySpark 4.1.1 的合成测试、独立安装与可复现构建已有 [0.1.3 CI 证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41827968535)。离线 PASS 只覆盖相应版本和测试范围。
- **Fabric Environment：** 0.1.3 已通过 [正式 Publish 和已发布库读回](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41834029745)，并由[临时 Notebook Spark 4.1 Import](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167) 独立验收。这**不代表**正式业务 `nb_fhir_ingest` 版本门禁、真实 FHIR/OMOP E2E 或 Gold COMMIT 已通过；参见 [Fabric Environment CODE](../../azure-fabric/environments/CODE.md)。
- **依赖边界：** Shared 只负责纯计算。Blob/S3/OneLake/Delta/PG/Warehouse 物理写入、SparkSession、Notebook/Pipeline、部署和 Secrets 均由各平台独立负责。
- **正式合同：** Local Canonical v1 [Patient/Encounter Contract](../../../../local-data-platform/spark/contracts/canonical/) 仍是唯一权威，使用固定原字节/SHA；不复制第二套 Schema。

## 权威导航

- [CODE.md](CODE.md)：唯一源码、Contract、测试和 CI 入口。
- [BUILD-AND-TEST.md](BUILD-AND-TEST.md)：离线依赖、Python/PySpark 测试、可重复 Wheel 构建与 FHIR–OMOP Handoff 指南。
- [目录级 AGENTS.md](../../../../shared-data-engine/AGENTS.md)：仅提供本组件 Agent 特殊规则；仓库根 [AGENTS.md](../../../../AGENTS.md) 管通用安全规范。
- [Shared Engine 结构和所有权](../../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)、[Fabric Native ADR](../../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。

既有 `shared-data-engine/tests/` 测试仍按历史例外原位保留，新测试遵循 `.github/quality/tests/`。当前开发进度和运行验收只记录在相关 OpenSpec/Run，不在 Agent 文件和 README 中重复维护。
