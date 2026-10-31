# Shared Data Engine — CODE / 唯一源码地图

> **状态：P0 GitHub Main 静态 Gate 已验证；P1 Shared Engine 0.1.0 源码已提交功能分支，待 Wheel CI 验证。** `shared-data-engine/` 现已包含唯一共享包源码；仍**没有**第二份 Local Canonical Contract、Fabric I/O 或云端发布。未来增加源文件时必须在同一个 PR 更新此处的唯一源文件导航，不能将计划文件列为实际文件。

## 当前已存在的本组件文件

| 源码/治理文件 | 归属说明 |
| --- | --- |
| [`shared-data-engine/AGENTS.md`](../../../../shared-data-engine/AGENTS.md) | 当前唯一的共享目录内文件：Agent 边界及禁止依赖；**不是可运行代码** |

## 未来预留的唯一拥有者

| 功能 | 将来实际目录（未创建，不作为源码链接） |
| --- | --- |
| Pip wheel | `shared-data-engine/pyproject.toml` 与 `src/healthcare_data_engine/` |
| FHIR Patient/Encounter adapters | `src/healthcare_data_engine/adapters/fhir_r4/` |
| CSV / HL7 adapters | `src/healthcare_data_engine/adapters/csv/`、`hl7_v2/` |
| Canonical Patient/Encounter | `src/healthcare_data_engine/canonical/` |
| OMOP Person/Visit candidates | `src/healthcare_data_engine/mapping/omop/` |
| Identity + DQ + Reconciliation | `src/healthcare_data_engine/identity/`、`quality/`、`reconciliation/` |
| Synthetic fixtures + tests | `shared-data-engine/tests/` |

P1 的实际源码和测试逐文件列在下表，静态 CI 会阻止新增/移动源码未及时登记或重复拥有者。

共享包不能包含 Azure Blob/OneLake SDK、Airflow、Fabric Item、PG/Warehouse 写入或云 Secrets；这些平台侧源码分别归属于现有 Local 与 Azure/Fabric 的组件 CODE。

详情参阅 [Shared Engine authority](../../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) 与 [总 Agent 规则](../../../../AGENTS.md)。**当前 CODE-map CI 尚未覆盖此新源码域；必须在首个真实 Python 源码 PR 中扩充静态检查。**

## P0 工具与冻结合同（2026-10-31）

- [静态边界 Gate](../../../../.github/quality/scripts/check_shared_fabric_boundaries.py)：检查 Shared/Fabric 全量源码地图、唯一 owner、禁止平台依赖、非法 Mapper/Contract 复制。
- Local Patient v1 SHA256 `e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab`。
- Local Encounter v1 SHA256 `473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837`。
- 以上 hash 对应仓库 `445da04b6a4f96d8aea8280cbfb976fb5cbb28ac` 原始文件字节；权威路径原位保留。CI 每次按候选 Git HEAD 读原字节复核，不复制 Schema。

## P1 真实实现源码地图（不包含规划路径）

| 源码/测试文件 | 唯一业务归属 |
| --- | --- |
| [pyproject.toml](../../../../shared-data-engine/pyproject.toml) | 单一共享 Wheel 元数据，固定版本 0.1.0 |
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

CI 见 [Shared Engine Wheel Offline Validation](../../../../.github/workflows/shared-engine-wheel-validation.yml)，构建/安装证据只适用于该 PR HEAD 的测试版本；Fabric Publish 未授权。
