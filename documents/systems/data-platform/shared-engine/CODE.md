# Shared Data Engine — CODE / 唯一源码地图

> **状态：P0 静态 Gate 已编码（待 PR CI/Main 验证），业务 Wheel 尚未创建。** `shared-data-engine/` 目前只有 scoped Agent 规则，**尚未建立 Python 模块、Wheel 或第二份 Contract**。未来增加源文件时必须在同一个 PR 更新此处的唯一源文件导航，不能将计划文件列为实际文件。

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

业务代码真正创建后，此表应由**指向每个真实实现/测试文件的源码地图**替代；不能只登记目录名以绕过 CODE-map 对应测试。

共享包不能包含 Azure Blob/OneLake SDK、Airflow、Fabric Item、PG/Warehouse 写入或云 Secrets；这些平台侧源码分别归属于现有 Local 与 Azure/Fabric 的组件 CODE。

详情参阅 [Shared Engine authority](../../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md) 与 [总 Agent 规则](../../../../AGENTS.md)。**当前 CODE-map CI 尚未覆盖此新源码域；必须在首个真实 Python 源码 PR 中扩充静态检查。**

## P0 工具与冻结合同（2026-10-31）

- [静态边界 Gate](../../../../.github/quality/scripts/check_shared_fabric_boundaries.py)：检查 Shared/Fabric 全量源码地图、唯一 owner、禁止平台依赖、非法 Mapper/Contract 复制。
- Local Patient v1 SHA256 `e0be146222f13b2f24a84d883d70117fac9aab984c184558dab88726ac5a3dab`。
- Local Encounter v1 SHA256 `473ae45225c9063a7560b0092ed7914d71a43623f593d4959c66294e942a5837`。
- 以上 hash 对应仓库 `445da04b6a4f96d8aea8280cbfb976fb5cbb28ac` 原始文件字节；权威路径原位保留。CI 每次按候选 Git HEAD 读原字节复核，不复制 Schema。
