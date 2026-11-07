# Shared Data Engine — CODE / 唯一源码地图

> **当前候选状态（2026-11-07）：Shared 新映射源码候选版本为 0.1.10，现有 Fabric Environment Git CustomLibraries 保留唯一 0.1.7 Wheel；本次 PR 未发布或切换 Native Notebook/Environment。历史 0.1.6 Publish 与只读 Smoke 验收仍有效，但不能当作最新版本。Local 生产链尚未整体迁移 Shared；Fabric Candidate/Gold/Pipeline E2E 仍 OPEN。** `shared-data-engine/` 已包含真实共享包源码及合成测试；它不包含第二份 Local Canonical Contract、Fabric I/O 或云端发布。所有新增或移动的源码必须在同一 PR 中维护本唯一源码地图。

## 当前源码、测试和治理

- [`shared-data-engine/AGENTS.md`](../../../../shared-data-engine/AGENTS.md)：目录级 Agent 边界，不是运行时代码。
- Wheel 元数据、FHIR Patient/Encounter、Canonical 验证、Reconciliation 和合成测试：详见下方「P1 真实实现源码地图」，其中列出的路径已存在。
- `mapping/omop/candidates.py` 已实现医院隔离的纯 Person/Visit OMOP **Candidate**；CSV/HL7 Adapter 和持久身份分配/物理 Writer 仍不是当前 Shared 已交付能力。Candidate 不等于 Gold 写入。

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
| [pyproject.toml](../../../../shared-data-engine/pyproject.toml) | 单一共享 Wheel 当前源码候选 0.1.8；Native Environment Git 唯一旧 Wheel 0.1.7 未被本轮修改；历史 0.1.6 Git 定义/Import 只读 Smoke 已验收；Candidate/Gold 未验收 |
| [src/healthcare_data_engine/__init__.py](../../../../shared-data-engine/src/healthcare_data_engine/__init__.py) | 公共 API，无导入时副作用 |
| [src/healthcare_data_engine/models/batch_context.py](../../../../shared-data-engine/src/healthcare_data_engine/models/batch_context.py) | Source/Processing/Publication 显式身份与源字节 receipt |
| [src/healthcare_data_engine/quality/result.py](../../../../shared-data-engine/src/healthcare_data_engine/quality/result.py) | Accepted/Quarantined/Rejected/metrics 类型 |
| [src/healthcare_data_engine/adapters/fhir_r4/bundle.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/bundle.py) | FHIR Bundle 资源及重复 ID、来源隔离 |
| [src/healthcare_data_engine/adapters/fhir_r4/references.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/references.py) | fullUrl、URN、相对 Patient Reference |
| [src/healthcare_data_engine/adapters/fhir_r4/omop_code_aliases.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/omop_code_aliases.py) | FHIR R4 来源代码 → LocalDP 既有语义键的候选别名，以及 1002-5 / UNK 的**来源语义**待审提示；不包含 OMOP Concept ID，不改变 Canonical 输出或临床审批 |
| [src/healthcare_data_engine/adapters/fhir_r4/patient.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/patient.py) | FHIR Patient 到 Canonical v1，缺失值 Quarantine |
| [src/healthcare_data_engine/adapters/fhir_r4/encounter.py](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/encounter.py) | FHIR Encounter 到 Canonical v1，Reference 拒绝 |
| [src/healthcare_data_engine/canonical/validation.py](../../../../shared-data-engine/src/healthcare_data_engine/canonical/validation.py) | 原 Local SHA256 pin、逐字段类型与 Spark Schema |
| [src/healthcare_data_engine/reconciliation/patient_encounter.py](../../../../shared-data-engine/src/healthcare_data_engine/reconciliation/patient_encounter.py) | 纯 Canonical PK/FK/批次一致性和来源隔离 |
| [src/healthcare_data_engine/reconciliation/replay.py](../../../../shared-data-engine/src/healthcare_data_engine/reconciliation/replay.py) | NEW/SKIP/Conflict/Hold/ACK 只读重试策略 |
| [tests/fixtures/fhir_r4/patient_encounters_bundle.json](../../../../shared-data-engine/tests/fixtures/fhir_r4/patient_encounters_bundle.json) | 完全合成 FHIR Bundle Fixture |
| [tests/test_fhir_r4_contract.py](../../../../shared-data-engine/tests/test_fhir_r4_contract.py) | 来源、负向、去重、Contract 和 replay tests |
| [tests/test_spark_dataframe.py](../../../../shared-data-engine/tests/test_spark_dataframe.py) | PySpark Schema、输出及两表 FK |
| [requirements-test.txt](../../../../shared-data-engine/requirements-test.txt) | 固定 Python 3.11/PySpark 3.5.7/构建依赖 |
| [src/healthcare_data_engine/mapping/omop/registry.py](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/registry.py) | 0.1.4 引入的源码模块（0.1.5 继续保留）：显式 Person/Visit Entity Registry、依赖顺序、多 OMOP Target 定义和确定性派生来源键；无 ID 分配/物理写入 |
| [src/healthcare_data_engine/mapping/omop/entity_candidates.py](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/entity_candidates.py) | 0.1.4 引入的源码模块（0.1.5 继续保留）：对现有严格 Person/Visit G5 Mapper 的目标表分组适配；Visit INT ID 仍未分配，仍是 Candidate-only |
| [new multi-entity contract tests](../../../../.github/quality/tests/shared-data-engine/mapping/test_entity_registry.py) | 新规范目录中的纯单元/负向/旧 API 兼容测试，需 Python 3.11/3.13 CI 独立发现执行 |
| [src/healthcare_data_engine/identity/preview.py](../../../../shared-data-engine/src/healthcare_data_engine/identity/preview.py) | 0.1.5 源码候选：读取调用方提供的完整 Map/Gold/Allocator/Ledger 快照，验证现有 F2 Planner 的拟议 ID、版本指纹、PERSISTED/PROVISIONAL 及状态漂移；**不分配或持久化 ID** |
| [src/healthcare_data_engine/identity/references.py](../../../../shared-data-engine/src/healthcare_data_engine/identity/references.py) | 0.1.5 源码候选：显式依赖、同源命名空间、同事务组临时父 ID 与跨组已提交读回的 FK 纯预检 |
| [src/healthcare_data_engine/mapping/omop/target_concepts.py](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/target_concepts.py) | 0.1.5 源码候选：版本化目标表/字段级 Concept Profile、Source/Release/Domain/有效日期/审核证据 SHA 预检；**不是**临床审批 |
| [identity/FK synthetic tests](../../../../.github/quality/tests/shared-data-engine/mapping/test_identity_preview_and_fk.py) | Python 3.11/3.13 两版本对 Fabric F2 纯算法输出进行端到端 Adapter 验证、跨医院/溢出/快照漂移/跨组 FK 拒绝 |
| [target Concept synthetic tests](../../../../.github/quality/tests/shared-data-engine/mapping/test_target_concepts.py) | 表/字段概念 Domain、词表版本、错误 Code 和有效期的正负向测试，不能冒充真实 Clinical Reviewer Signoff |
| [src/healthcare_data_engine/identity/candidate_handoff.py](../../../../shared-data-engine/src/healthcare_data_engine/identity/candidate_handoff.py) | 0.1.6 源码候选：接收现有 F2 `IdentityPreview` 与 Warehouse 全量 `IdentitySnapshot`，对照 Caller 提供的 G4 Approved Silver Patient/Encounter 来源键，产生带 `PERSISTED/PROVISIONAL` 明确状态的 Person/Visit Candidate ID Lookup。**无 SQL/Delta I/O、无 ID 正式分配、无 Gold 权限、无临床审批** |
| [src/healthcare_data_engine/mapping/omop/candidate_publication.py](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/candidate_publication.py) | G5 P3 纯业务 Candidate 批次冻结/Replay/审批最后写入的执行**计划**、`PROVISIONAL` 标志和未映射数据分类（不进行 Delta I/O，不产生 Gold 授权）；Clinical Profile 的版本 SHA 是外部输入，不在算法中写死；新增源码还未发布至 Fabric Environment |
| [P3 Candidate publication tests](../../../../.github/quality/tests/shared-data-engine/mapping/test_candidate_publication.py) | 纯合成 100/5918、首次空 Map、相同 Request 重放 SKIP 必须独立读回、部分写入未知 ACK HOLD、映射失败隔离建议、错误 Domain/Release 和身份变化拒绝；不代表实机 Delta/Gold 验收 |
| [G5/F2 candidate preview synthetic tests](../../../../.github/quality/tests/shared-data-engine/mapping/test_candidate_identity_handoff.py) | 0.1.6 新增 18 项正负向合成用例：首批零映射、100/5918、完全重放、跨医院同键、源主外键/目标列长/快照漂移/伪造目标 ID 冲突。双版本 Wheel CI 明确执行 |
| [src/healthcare_data_engine/mapping/omop/candidates.py](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/candidates.py) | G5 Silver Approval/Concept + 外部 stable ID Map 保护的纯 Spark OMOP Person/Visit Candidate；不负责 Writer/Gold COMMIT |
| [tests/test_omop_candidates.py](../../../../shared-data-engine/tests/test_omop_candidates.py) | G5 真实本地 PySpark Schema/FK/DQ/Unknown Concept/Approval 拒绝/确定性 Replay 正负测试 |
| [contracts/fabric-fhir-omop-handoff-v1.json](../../../../shared-data-engine/contracts/fabric-fhir-omop-handoff-v1.json) | FHIR Approved Silver → Fabric OMOP F1 机器可读版本化交接规范；不授权 Gold 写入 |
| [src/healthcare_data_engine/models/fabric_omop_handoff.py](../../../../shared-data-engine/src/healthcare_data_engine/models/fabric_omop_handoff.py) | 无 I/O 的原始 SHA、来源命名空间、Approval/路径元数据校验；始终要求另行物理 Delta 读回 |
| [tests/test_fabric_omop_handoff.py](../../../../shared-data-engine/tests/test_fabric_omop_handoff.py) | 仓库 Canonical 原始 SHA、自定义 F1 作用域、拒绝跨医院/Quarantine/篡改/不可信路径的 Python 3.11/3.13 无云端测试 |
| [BUILD-AND-TEST.md](BUILD-AND-TEST.md) | 原源码 README 的离线安装、Python/PySpark 测试、Wheel 构建及 Handoff 操作边界（唯一维护入口） |
| [src/healthcare_data_engine/mapping/omop/race_resolution.py](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/race_resolution.py) | 0.1.10 Source/F1 Race **草稿**预检：检查 1002-5 原始 CDC Coding.system、UNK 原始 HL7 NullFlavor Coding.system、F1 输入候选行的 Race 标准域/有效日期；生成仅追加正数 Concept 的新 G5 Profile 草稿、保持 UNK 未映射/0 仅待审，不能替代物理 SQL 或临床审批 |
| [src/healthcare_data_engine/mapping/omop/local_profile.py](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/local_profile.py) | 0.1.9 平台无关 Mapping Profile + P100/E5918 **汇总级 CoverageReview**：复用原 LocalDP Person/Visit Concept 权威；检查四类源字段完整性、patient/encounter 总数、版本/manifest SHA、未知码与频数，产出不含 Patient ID 的临床审核缺口清单；不执行 I/O、不分配 OMOP ID、绝不代表 Clinical/License Approval |

## Local / Shared 等价性测试（2026-11-06，合成离线限定）

- [Local Person/Visit Shared parity tests](../../../../.github/quality/tests/shared-data-engine/parity/test_local_shared_person_visit_parity.py)：直接调用既有 Local Visit `map_encounter_to_candidate`、从真实 Local Person main 原样抽出的 `map_joined_patient_to_person` 纯函数及 Shared `build_omop_candidates`，使用冻结 Canonical v1 字段定义、现有 Local `visit-class-v1.json` 和 `common/omop.py` 中的概念常量，验证 Person（16 个人口学码交叉组合）与 Visit（10 种 Class）完整 Schema/全部字段/重放等价。对未知 Class、人口学码、跨医院 Identity 和非 Standard Concept 做 fail-closed 负向测试；使用合成、未临床审批的 Profile，绝不授权 Fabric Gold。
- Local Person 已将原有纯 OMOP 投影从 `local-data-platform/spark/apps/person/map_canonical_patient_to_omop.py::main` 原样抽为同文件 `map_joined_patient_to_person`，现役 main 调用这一函数。离线双 Spark Runtime 覆盖冻结 Schema、16 种合法人口学组合、行数据及 Replay 的 Local/Shared **投影等价**；原 JDBC/Manifest/原始来源验证、数据发布不在此纯函数内，未重写或切换任何 Local 生产系统。真正复用 Shared Wheel 的 Local 部署/交付验收、真实临床 Profile 和物理 Gold/PG/Fabric 写入仍 OPEN。
- 该测试由现有 Shared Wheel 离线 CI 分别在 Python 3.11/PySpark 3.5.7 与 Python 3.13/PySpark 4.1.1 执行，且不改变唯一 Wheel 0.1.6 的内容、现有 Fabric Notebook、Local 生产链或物理数据。

## 历史 P3 Python 3.13 兼容发行版候选（后续 0.1.3 与 0.1.6 均已发布）

- 版本候选 `0.1.1` 在 `pyproject.toml` 和公开 API `__version__` 同步，支持 Python 3.13。
- 本地 Python 3.11 / PySpark 3.5.7 与 Fabric 2.0 Python 3.13 / PySpark 4.1.1 的测试分离执行。
- 原有 Git Environment CustomLibraries `0.1.0` 是历史暂存版本；在新版源码 PR、确定性 Wheel SHA、离线安装验收、另行的 Wheel Git staging PR 全部通过前，不得直接更换 Fabric 运行环境。
- 必须确保从旧 Wheel 过渡至新 Wheel 时只有一个 CustomLibraries 文件；任何 Fabric Publish/Notebook Binding 都需独立授权。

此段仅代表历史 P3 阶段；0.1.6 Fabric GA Publish 已于后续独立 Run 完成。构建/安装仅针对其被测 SHA；见 [Shared Engine Wheel Offline Validation](../../../../.github/workflows/shared-engine-wheel-validation.yml)。

## G5 0.1.2 候选（2026-11-03 历史阶段；当前源码为 0.1.6）

- 源码中首次提供 `build_omop_candidates` 与 `load_omop_mapping_profile`。独立从已验收的物理 Delta 获取 Silver Approval、稳定 ID Map、标准/有效 OMOP Concept Lookup、Profile 原字节及 SHA 都是运行方的责任；模块本身没有 Fabric/PG/I/O，也不生成 ID。
- 当时新 Wheel 必须先经过离线 CI 和独立发布/读回；后续 0.1.3 已在 Fabric Environment 正式 Published。仍不得将临时 Notebook Import 外推为业务 Notebook 或 Gold 数据写入验收。
- Local 人口统计 Synthea 编码不同于 FHIR 源码语义；测试所用假 Profile 仅用于正负回归，绝不视为经过 OHDSI Concept 审核的 Fabric 运行时 Profile。

## G5 Hospital-scoped F1 Identity Map interface (2026-11-04)

- Pure mapper `build_omop_candidates(..., hospital_id=...)` **requires explicit verified hospital ID** and a `BatchContext.namespaced_source_system` matching `raw_source:hospital_id:feed_id`. Canonical v1 Patient/Encounter source tables do not carry a separate hospital column; do **not** silently alter their frozen schemas.
- F1 Warehouse `etl.identity_map` supplies columns `entity_type,hospital_id,source_system,source_business_key,omop_id`. Only `entity_type='PERSON'` is used to map Patient and Encounter's Person reference. Joins require exact hospital + source namespace + canonical source key; uniqueness/collation/INT checks span **all hospitals**, not only the selected one.
- G5 Candidate remains **Candidate-only**. A freshly planned F2 ID is not persisted, and a real Fabric Gold COMMIT is not implied. 后续 0.1.3 Wheel 已通过独立 Environment Publish + 临时 Spark 4.1 Import；业务 `nb_fhir_ingest` 版本门禁和 OMOP Gold COMMIT 尚未验收，不能仅靠离线测试或临时 Import 声称业务成功。

## 0.1.3 offline Wheel evidence

- [Shared Engine validation Run #41827968535](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41827968535) on [PR #647](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/647) passed Python 3.11 and Python 3.13 Spark suites, reproducible wheel SHA equality and independent installed 0.1.3 import. **This is not Fabric Environment publish or Notebook import evidence.**

## 0.1.3 Published / Isolated Import 独立证据（2026-11-04）

- [Staging 同步](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41833502954)、[正式 Environment Publish 与唯一 0.1.3 库读回](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41834029745)、[独立临时 Notebook Spark 4.1 Import](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167)。完整事实边界见 [Fabric Environment CODE](../../azure-fabric/environments/CODE.md)。
- [组件 README](README.md) 管架构和能力；[BUILD-AND-TEST.md](BUILD-AND-TEST.md) 管可复现离线测试与构建；[`shared-data-engine/AGENTS.md`](../../../../shared-data-engine/AGENTS.md) 只保留目录级 Agent 指令，不再作为业务状态记录。

## 2026-11-06 通用核心收口与 Fabric 开发基线

- **FABRIC_READY_CORE（不是 BUSINESS_E2E_DONE）**：单一 Shared Wheel 0.1.6，冻结 Canonical v1、Person/Visit、纯 Registry/Identity Snapshot/Preview Handoff、Concept/FK 和 Candidate；[双 Runtime 回归 #42281544230](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42281544230) 与 [Local/Shared parity #42273958120](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42273958120) PASS。
- **云端发布/执行 PASS**：[0.1.6 Publish #42284453546](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42284453546)、[正式 Notebook Git 双格式读回 #42291355563](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42291355563)、[正式业务只读 RUNTIME_SMOKE #42297766098](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42297766098)。Published/Staging 唯一 0.1.6，默认 HALT，历史 G4 `engine-0.1.1` 不改。
- **Local 维护模式**：不重构当前 Local PG Writer/Mapper，不阻塞 Fabric；任何未来 Local Shared 切换需独立 PR/回归。
- **接下来的业务权威**：[Fabric FHIR→OMOP E2E](../../../../openspec/changes/fabric-fhir-omop-unified-e2e/tasks.md) 及 [G5](../../../../openspec/changes/fabric-g5-approved-silver-omop-candidate/tasks.md)、[F2](../../../../openspec/changes/fabric-omop-foundation/tasks.md)。F1 release/license/临床 Profile、真实 Snapshot、Candidate Delta、Gold COMMIT/Replay、Pipeline E2E 未完成；Condition 作为后续第三实体证明，不提前复制另一套框架。

## G5 P3 Shared Engine 0.1.7 — 修正源码版本与 GA Wheel 漂移（2026-11-07）

- **GA 基线不变**：Fabric `env_healthcare` 的唯一已发布 0.1.6 Wheel SHA256 `473df0171de89a1260ce8bd4b58de301802a23f28cd7c6007c8f9563772748ff` 与官方 Notebook `engine_version==0.1.6`、HALT 均原样保留；其真实同步/Publish/Import 已独立验收。Shared Engine Main 的 P3 Planner 后于 GA Wheel 新增，却没有更新 `pyproject.toml` / `__init__.__version__`，**后续同版重建与 GA 字节不相等是正常版本漂移门禁失败，不是已发布业务 Wheel 损坏**。
- **0.1.7 源码候选**：`pyproject.toml` 与公开 `__version__` 同步升级，纯 P3 `CandidatePublicationPlan/FrozenCandidateScope/ObservedCandidate/freeze_candidate_scope/decide_candidate_publication/classify_mapping_failure` 正式导出；现有 Local/Canonical/FHIR/OMOP Mapper 业务 Contract 和 G4 已批准 Silver 不改。新增包装版本与 API 一致测试，保留原有合成临床/PK/FK、可恢复 Replay 负向回归。
- **离线 CI 两条独立线**：[Shared Wheel Validation](../../../../.github/workflows/shared-engine-wheel-validation.yml) 为 0.1.7 重复构建/安装及跨 Python 3.11/3.13；[Fabric Notebook Offline Contract](../../../../.github/workflows/fabric-fhir-notebook-offline.yml) 仍安装 SHA-pinned Native 0.1.6 跑既有 Notebook 回归，同时单独安装 0.1.7 以证明旧 Notebook **拒绝未发布的新版本**。新 P3 Native Writer 仍在 [Draft PR #773](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/773)，其中源码导入与实机 Writer/Pipeline 接线要等 Wheel GA 发布门禁，禁止借临时 Hash、旧版本包或清空测试绕过。
- **发行状态**：本节只描述 Git review 0.1.7 候选源码；尚未将 0.1.7 Wheel 复制到 Native Environment、未发生 Fabric Cloud UpdateFromGit/Publish/Notebook 运行或 Gold/Clinical 写入，版本候选的 Build SHA/CI Run 以真实合并后证据为准。后续 0.1.7 固定 SHA Git review Wheel 及云端 Publish 走现有 [Wheel Release Change](../../../../openspec/changes/fabric-environment-wheel-release/tasks.md) 的独立审批。

## LocalDP → FHIR G5 单一 Profile 对接（0.1.8 源码候选，2026-11-07）

- 新唯一 [`local_profile.py`](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/local_profile.py)：**只生产旧版 G5 Shared Mapper 已支持的八字段字典 Profile**，直接由调用方提供的 LocalDP 权威 [`omop.py`](../../../../local-data-platform/spark/common/omop.py) 人口学 Concept 常量与 [`visit-class-v1.json`](../../../../local-data-platform/spark/contracts/omop/visit-class-v1.json) 10 类 Visit 规则构建，无第二份写死的 OMOP ID 表、无新 Mapper、无文件或 SQL I/O。FHIR 入口代码别名为显式、待批准的源语义翻译，源端原始 Canonical 字段仍保留。
- [`test_localdp_g5_profile.py`](../../../../.github/quality/tests/shared-data-engine/mapping/test_localdp_g5_profile.py)：直接从现有 LocalDP 代码/Visit JSON 加载原始规则，对真实已知 G4 **aggregate-only** 源代码分布（P100/E5918）进行合成轮询，验证原值 Concept 对齐、Profile SHA 稳定、10 类 Visit 兼容、未知/伪造来源以及 `0`/默认 Concept 拒绝。原已完成的 [Local/Shared Person/Visit parity](../../../../.github/quality/tests/shared-data-engine/parity/test_local_shared_person_visit_parity.py) 保留。
- 真实 FHIR `race_code=1002-5` 与 `UNK` 在旧 LocalDP Race 规则中尚无对应键，明确列出为 unresolved **HOLD**；`2076-8` 对 `hawaiian` 的交叉含义须由临床 reviewer 根据 Population 语义正式确认。尚未发布真实经过批准的全覆盖 Mapping Profile，也不自动使用 OMOP Concept ID `0`。LocalDP 旧程序/持久 PG 数据均未修改。
- Wheel **先前 SOURCE/CI 已验证**版本 `0.1.8`（`pyproject.toml` 与 `__init__.py`）；现有 Fabric Environment Git 固定唯一 0.1.7 Wheel/此前源码 0.1.7 均保持原状，不把 CI 通过误称为 Fabric 实际发布。后续批准 Profile/临床/许可后，必须独立进行实际 Wheel Publish、Notebook 业务 Job、候选独立读回及 Gold 审批。


## FHIR 代码语义与 Mapping Coverage Review（0.1.9 SOURCE_ONLY）

- 现有 [`local_profile.py`](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/local_profile.py) **不再自身定义 FHIR alias 字典**，由 [FHIR Adapter `omop_code_aliases.py`](../../../../shared-data-engine/src/healthcare_data_engine/adapters/fhir_r4/omop_code_aliases.py) 统一拥有来源特定语义代码。为兼容 0.1.8 的引用路径，仅保留从 Adapter 直接重新导出同一对象；仍不复制 LocalDP OMOP Concept ID，来源语义须 Reviewer 确认。
- 新纯函数 `build_mapping_coverage_review` 对已构建的**同一个字节 SHA 的 G5 Mapper Profile**、完整 Caller-Supplied 四个 Canonical 字段频数、Source Batch/Manifest SHA 与 100/5918 两个总数执行全面校验。**物理 Silver 真实身份仍须独立证明，输入 SHA 的存在不是该证明**。同一来源多批次/跨医院可通过各自 Source Namespace、Manifest SHA 与 Code Inventory 生成独立审核包。
- 返回不含患者标识的 `MappingCoverageReview`：`gender_code` 未映射 0、`race_code` 未映射 3（`1002-5` 1、`UNK` 2）、`ethnicity_code` 0、`encounter_class` 0，均**仅为已核实 G4 代码频数的离线合同测试覆盖**；不是新实机验证。`1002-5` 是 CDC Race / HL7 表中 American Indian or Alaska Native，`UNK` 是 HL7 NullFlavor unknown，源码 Hint 不是目标 OMOP ID（[HL7 US Core race](https://www.hl7.org/fhir/us/core/STU2/ValueSet-omb-race-category.html)）。OMOP 5.4 Race 未知的 Concept 0 仅是未来临床审查时可考虑的正式 no-information 规则（[OHDSI CDM5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html)），**当前 G5 Profile 仍严禁 ID 0，不能靠假 ID 绕过**。
- 结果一律 `MAPPING_COVERAGE_REVIEW_ONLY_NO_CLINICAL_APPROVAL`、`candidate_write_authorized=False`，并显式列出每个未映射原码/数量/含义提示。类别、有效日期、标准 Concept、F1 Release rights 和人工 mapping reviewer 尚待真实签审。未知源值不改写入 Gold，不允许凭 SOURCE/CI PASS 推进 P3/P4。
- [映射与覆盖离线负向测试](../../../../.github/quality/tests/shared-data-engine/mapping/test_localdp_g5_profile.py) 覆盖四组 Source Count、manifest SHA、LocalDP parity、错误 Code/个数、碰撞、伪造授权、Profile 字节漂移、跨医院 Namespace 和 0/default 禁止。


## FHIR Race 1002-5 / UNK 源码草稿预检（0.1.10 SOURCE_ONLY）

- [Race resolution pure source](../../../../shared-data-engine/src/healthcare_data_engine/mapping/omop/race_resolution.py)：调用方提供已存在的 `MappingCoverageReview`、同一 SHA 的 `LocalProfileDraft`、**独立读取获得**的 F1 `concept_id/concept_name/domain_id/vocabulary_id/standard_concept/invalid_reason/valid_start_date/valid_end_date` 行、F1 元数据哈希、以及每个未映射 Race 代码的 FHIR `Coding.system` 汇总频数。纯函数 `propose_race_resolution` 严格核对源 Batch / Manifest / Profile SHA、唯一 Code System、数量、大小写、标准 Race Domain、有效日期与标准标记、不可重用旧 Mapping Version；只返回独立字节和 SHA 的**新草稿**，`clinically_approved=False`、`candidate_write_authorized=False`。
- 当前外部 HL7 [FHIR-to-OMOP Race guide](https://hl7.org/fhir/uv/omop/2.0.0-202609-ballot/en/RaceAndEthnicity.html) 将 American Indian or Alaska Native 列作 **8657（示例）**，该 ID **仅在合成测试输入中**，不在共享生产算法里硬编码。来源 `1002-5` 来自 CDC Race Coding System `urn:oid:2.16.840.1.113883.6.238`；`UNK` 必须来自 HL7 `v3-NullFlavor` `http://terminology.hl7.org/CodeSystem/v3-NullFlavor`，两者不可混淆，详见 [HL7 US Core Race](https://www.hl7.org/fhir/us/core/STU4/ValueSet-omb-race-category.html)。
- `UNK` = Unknown 不能映射为任何现成 Race 身份。OMOP [CDM 5.4 PERSON race_concept_id](https://ohdsi.github.io/CommonDataModel/cdm54.html) 允许无确切信息时用 `0`，**但本期不向正式 G5 Profile 注入 0，也不修改原本严格拒绝 0 的 Shared Mapper / private Runner Provider**。未来需要经批准的类型化 no-information 合同、原始 FHIR Code System 的真实来源证据及单独的临床/法律/发布门禁；不许仅仅因为 FHIR Code 文本为 `UNK` 即改写。
- 当前 LocalDP Rule 未包含 American Indian/Alaska Native，候选 Profile 仅在**合成 F1 记录满足标准+有效日期**时把此代码添加为对应的**正整数 Concept**，临床未经审批的字节 SHA 与任何正式 Profile 必须区分；仍有 `UNK` 2/100 **HOLD**。现有 Canonical Patient v1 只存 `race_code`，没有单独存 `Coding.system`，需要从冻结、可独立证明的 FHIR 原始资源生成外部来源 Code System 计数；未验收的调用方参数不算真实来源验收。
- [Positive/negative SOURCE tests](../../../../.github/quality/tests/shared-data-engine/mapping/test_localdp_g5_profile.py) 覆盖 8657 合成行、错误 F1 Domain/Standard/Name/Vocabulary、失效日期、Code System 混淆、错误来源数、缺少 Provenance、跨医院隔离及未知零值，LocalDP 旧实现/数据不修改。本期源码包候选为 0.1.10；现有 Fabric Environment Git Wheel 0.1.7 未改动；**无云端查询/签名审核/真实 Candidate/Gold 写入**。
