# Shared Data Engine — CODE / 唯一源码地图

> **状态：P1 Shared Engine 0.1.0 已进入 main 并完成离线 CI；P3 0.1.1 为 Python 3.13 兼容候选，尚未替换 Fabric Environment 里的旧 Wheel。** `shared-data-engine/` 已包含真实共享包源码及合成测试；它不包含第二份 Local Canonical Contract、Fabric I/O 或云端发布。所有新增或移动的源码必须在同一 PR 中维护本唯一源码地图。

## 当前源码、测试和治理

- [`shared-data-engine/AGENTS.md`](../../../../shared-data-engine/AGENTS.md)：目录级 Agent 边界，不是运行时代码。
- Wheel 元数据、FHIR Patient/Encounter、Canonical 验证、Reconciliation 和合成测试：详见下方「P1 真实实现源码地图」，其中列出的路径已存在。
- 当前 CSV/HL7 Adapter、OMOP Person/Visit Mapping 和独立 Identity 模块仍是将来可能增加的代码，**不得**视为已实现或已通过 CI 的功能。

共享包不能包含 Azure Blob/OneLake SDK、Airflow、Fabric Item、PG/Warehouse 写入或云 Secrets；这些平台侧源码分别归属于现有 Local 与 Azure/Fabric 组件。静态边界 Gate 与代码导航随源码一同审查。

详情参阅 [Shared Engine authority](../../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) 与 [总 Agent 规则](../../../../AGENTS.md)。

## P0 工具与冻结合同（2026-10-31）

- [静态边界 Gate](../../../../.github/quality/scripts/check_shared_fabric_boundaries.py)：检查 Shared/Fabric 全量源码地图、唯一 owner、禁止平台依赖、非法 Mapper/Contract 复制。
- Local Patient v1 SHA256 `e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab`。
- Local Encounter v1 SHA256 `473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837`。
- 以上 hash 对应仓库 `445da04b6a4f96d8aea8280cbfb976fb5cbb28ac` 原始文件字节；权威路径原位保留。CI 每次按候选 Git HEAD 读原字节复核，不复制 Schema。

## P1 真实实现源码地图（不包含规划路径）

| 源码/测试文件 | 唯一业务归属 |
| --- | --- |
| [pyproject.toml](../../../../shared-data-engine/pyproject.toml) | 单一共享 Wheel 元数据，固定版本 0.1.1，支持 Python 3.13 的新候选版本；Fabric 仍暂存 0.1.0 |
| [src/healthcare_data_engine/__init__.py](../../../../shared-data-engine/src/healthcare_data_engine/__init__.py) | 公共 API，无导入时副作用 |
| [src/healthcare_data_engine/models/batch_context.py](../../../../shared-data-engine/src/healthcare_data_engine/models/batch_context.py) | Source/Processing/Publication 显式身份与源字节 receipt |
| [src/healthcare_data_engine/quality/result.py](../../../../shared-data-engine/src/healthcare_data_engine/quality/result.py) | Accepted/Quarantined/Rejected/metrics 类型 |
| [src/healthcare_data_engine/adapters/fhir_r4/bundle.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/bundle.py) | FHIR Bundle 资源及重复 ID、来源隔离 |
| [src/healthcare_data_engine/adapters/fhir_r4/references.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/references.py) | fullUrl、URN、相对 Patient Reference |
| [src/healthcare_data_engine/adapters/fhir_r4/patient.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/patient.py) | FHIR Patient 到 Canonical v1，缺失值 Quarantine |
| [src/healthcare_data_engine/adapters/fhir_r4/encounter.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/encounter.py) | FHIR Encounter 到 Canonical v1，Reference 拒绝 |
| [src/healthcare_data_engine/canonical/validation.py](../../../../shared-data-engine/src/healthcare_data_engine/canonical/validation.py) | 原 Local SHA256 pin、逐字段类型与 Spark Schema |
| [src/healthcare_data_engine/reconciliation/patient_encounter.py](../../../../shared-data-engine/src/healthcare_data_engine/reconciliation/patient_encounter.py) | 纯 Canonical PK/FK/批次一致性和来源隔离 |
| [src/healthcare_data_engine/reconciliation/replay.py](../../../../shared-data-engine/src/healthcare_data_engine/reconciliation/replay.py) | NEW/SKIP/Conflict/Hold/ACK 只读重试策略 |
| [tests/fixtures/fhir_r4/patient_encounters_bundle.json](../../../../shared-data-engine/tests/fixtures/fhir_r4/patient_encounters_bundle.json) | 完全合成 FHIR Bundle Fixture |
| [tests/test_fhir_r4_contract.py](../../../../shared-data-engine/tests/test_fhir_r4_contract.py) | 来源、负向、去重、Contract 和 replay tests |
| [tests/test_spark_dataframe.py](../../../../shared-data-engine/tests/test_spark_dataframe.py) | PySpark Schema、输出及两表 FK |
| [requirements-test.txt](../../../../shared-data-engine/requirements-test.txt) | 固定 Python 3.11/PySpark 3.5.7/构建依赖 |
| [README.md](../../../../shared-data-engine/README.md) | 构建、无网络安装、测试操作说明 |

## P3 Python 3.13 兼容发行版候选（尚未上传 Fabric）

- 版本候选 `0.1.1` 在 `pyproject.toml` 和公开 API `__version__` 同步，支持 Python 3.13。
- 本地 Python 3.11 / PySpark 3.5.7 与 Fabric 2.0 Python 3.13 / PySpark 4.1.1 的测试分离执行。
- 原有 Git Environment CustomLibraries `0.1.0` 是历史暂存版本；在新版源码 PR、确定性 Wheel SHA、离线安装验收、另行的 Wheel Git staging PR 全部通过前，不得直接更换 Fabric 运行环境。
- 必须确保从旧 Wheel 过渡至新 Wheel 时只有一个 CustomLibraries 文件；任何 Fabric Publish/Notebook Binding 都需独立授权。

CI 见 [Shared Engine Wheel Offline Validation](../../../../.github/workflows/shared-engine-wheel-validation.yml)，构建/安装证据只适用于该 PR HEAD 的测试版本；Fabric Publish 未授权。
