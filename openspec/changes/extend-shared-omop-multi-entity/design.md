# Design — Shared Multi-Entity OMOP contracts

## 1. 当前事实、不可改变的边界

- **业务路径：** CSV / FHIR R4 / HL7 v2 由各自 Source/Entity Adapter 转换为统一 Canonical Silver；Approved Silver 进入同一个平台中立的 Shared OMOP Mapper；Local PG / Fabric Warehouse 各由自己的物理 Writer 负责落盘。FHIR G4 Silver 实际 P100/E5918/Q0 已通过；HL7 Shared Adapter 与其他 Canonical Entity 是未来 Change。
- **已存在的实现：** `shared-data-engine/src/healthcare_data_engine/mapping/omop/candidates.py` 返回 `OmopCandidates(person, visit,...)`，按固定人口学/Visit Profile 检查。Fabric `azure-fabric/warehouse/omop-foundation/writer/identity_plan.py` 纯 Preview 的 `KINDS` 只有 PERSON、VISIT_OCCURRENCE；`silver_identity.py` 也只为 Patient/Encounter 生成 Preview。现有 Fabric Handoff v1 固定两表。
- **实现状态：** Shared 0.1.3 构建/发布/真实 Spark Import PASS；G5 物理源只读 PASS，但 Candidate Delta、正式临床映射审批、F2 Gold COMMIT 与全 Pipeline E2E 未验收。不得因新契约把上述标记为完成。
- **冻结/安全：** Canonical Patient/Encounter v1 与 Source namespace/已批准历史分区不变；一个 Warehouse 内 OMOP PK 为正 INT（≤ 2,147,483,647），不使用 BIGINT IDENTITY/row_number/hash modulo/姓名出生日期替代；Fabric 约束可能 NOT ENFORCED，隔离不等同 SERIALIZABLE。

## 2. 最小公共合同，拒绝抽象过度

### 2.1 EntityDefinition（声明式 Registry）

Registry 由源代码中**显式审核**的 Entity Definition 组成，不从输入字符串反射导入任意模块、自动发现 SQL 表、执行任意 Python 或生成 DDL。不提前为 39 张 CDM 表创建空模块。每个 Definition 至少包含：

| 字段 | 含义 |
| --- | --- |
| `entity_key` / `definition_version` | 稳定的业务实体标识、注册定义版本（不是 Task 编号） |
| `canonical_contract_refs[]` | 输入实体/合同版本和确切 SHA（由现有 Local 合同权威提供） |
| `source_identity_fields` | Hospital、Source System、Source Business Key 与必要的派生角色来源 |
| `targets[]` | 一个或多个 OMOP 目标表、主键列、目标 Contract 版本 |
| `mapping_profile_refs[]` | 每个目标字段所需来源 Mapping/Concept 规则与 SHA |
| `dependencies[]` | 必需/可选的父实体、目标 FK、必须达到的发布状态 |
| `quality_rules[]` | 必须通过的 Schema、PK、FK、Domain、日期、数量和确定性规则 |
| `publication_group` | 该输出属于哪个受控事务/发布组 |

Person/Visit 作为第一个已注册组合；其他 Entity 只在其业务 Change 实施时注册。定义必须经版本化测试，未注册/重复/循环依赖/冲突输出必然 HOLD。

**来源与目标不是一一对应：** 例如未来 Canonical Observation 可根据经审核的医疗语义分为 OMOP Measurement 或 Observation，一个 Canonical 源行也可能产生多个目标行；不能假设字段名相同即临床语义相同。某些 Vocabulary、Metadata、Era/衍生表采用专门的装载/计算路径，不应强制套用每个临床 Entity 的 Mapper。

### 2.2 Entity Mapper 的纯接口

输入为 `ApprovedCanonicalInput`、`EntityDefinition`、版本/SHA 固定的临床 `MappingProfile`、已验证的 Vocabulary Concept 快照、`IdentityPlan`、`ResolvedParents`、Source/Processing Fence；输出为 `EntityCandidateSet`（以目标表名区分 `CandidateRows`，包括行数、稳定目标行身份、来源记录血缘、映射/合同/处理哈希、DQ 结果和明确的 `CANDIDATE_ONLY` 状态）。

Shared 只处理确定性变换和验证，不创建 SparkSession、不调用云 SDK、不读取/写入 Fabric 或 PG、不分配持久 ID、不颁发 `GOLD_COMMITTED`。执行层负责从真实 Approval/Delta/SQL 独立读回并提供带来源的证据；不能以调用方布尔值本身冒充真实物理验证。

旧 `build_omop_candidates(...)` 与 `OmopCandidates(person, visit,...)` 在调用方迁移之前保留兼容适配，历史 Person/Visit 输出语义、主键、Profile pin、Error/HOLD 不回退。先实现两个实际使用的 Entity Definition 和接口，不新建 Condition 空类。

### 2.3 IdentityPlan / stable derived row identity

稳定目标行键的逻辑范围至少包含：
`(target_table, entity_key, hospital_id, source_system, source_business_key, derived_role, derived_discriminator)`。
`derived_role/discriminator` 对于一对一输出允许规定的空/固定语义，对于一对多必须来自**确定性、可审核、业务稳定的来源字段**，不能来自输入次序、随机数、会改变的行号或单纯哈希取模。目标表或目标 ID namespace 不允许被不同实体无意混用；相同来源记录在不同目标表可以独立持有目标 ID。

Identity Planner 读取完整已验证的 Warehouse Map/Allocator/Gold/Ledger 快照，并同时处理已提交映射和新拟议 ID；结果显式区分 `PERSISTED` 与 `PROVISIONAL`，含 snapshot fingerprint/版本。Preview **没有预留 ID 权力**；Candidate 中的拟议 ID 不能被其他已经发布的事务组当作持久父 ID。实际 COMMIT 前必须在全局 single-writer fence 下重新读完并验证快照，冲突则 HOLD/重做规划；Writer 在一个短事务中提交对应 Map/Allocator/实体目标表/Ledger，异常 ROLLBACK、未知 ACK 先独立 SQL 读回。Fabric Writer 与 Local PG Writer 分开；目标行为共用，不照搬 SQL/连接/隔离语义。

**与现有实现的桥接：** `identity_plan.KINDS` 的扩展属于有版本/测试的后续代码 PR，不得简单改字符串允许名单后就宣称完整稳定 ID；`candidates.py` 当前要求已经持久化的 ID Map，后续必须引入经校验的临时计划输入，并在 COMMIT 时重验，不得造假预先持久化 ID。原 FHIR Handoff v1 继续服务历史 G4 数据，未来 Handoff 的多实体结构另行版本化，禁止原位改变 v1 语义。

### 2.4 Concept Profile

按 `(source_system, target_table, target_field, mapping_version, vocabulary_release_sha)` 定位经过审核的规则：字段值归一化、来源编码/系统、标准目标 Concept ID/Domain、有效日期、许可与审批证明。映射一对多或条件路由必须明示规则、可追溯且确定性，不得仅按词面名称匹配。真实代码中的 `UNK`、Race/Ethnicity LOINC 错 Domain、Visit source code 错 Domain 当前必须 HOLD 或由明确审核规则处理，不能兜底猜成 0 或静默截断字段。当前 F1 release/license 还未全部审计，不可把新 Profile 规范当作临床批准。

### 2.5 Dependency DAG / FK

依赖通过显式 Entity Definition 表达；无环；必须父实体达到 `COMMITTED_AND_READBACK_VERIFIED`，或在**同一个已验证的原子事务组内**一起提交时才能引用拟议父 ID。可选 FK 只有在临床源数据确实没有对应关系且 CDM 允许 NULL 时可省略，不能对无效/缺失但应有的父记录默默丢弃。引用需要同 Hospital/Source namespace，跨医院 ID 连接必须有独立批准的 Identity Crosswalk；姓名/DOB 自动匹配不允许。

Person + Visit 是当前同事务基础组；Condition/Measurement 等后续可分组，并行只允许在依赖/资源不冲突时进行。提交父组后可提交独立子组；这些组并非跨 Warehouse 事务的总体原子提交。

### 2.6 Candidate / Publication / Replay

`SourceBatchFence` 绑定 hospital/feed/request/manifest SHA；`ProcessingFingerprint` 绑定 adapter、Canonical contract、mapping profile、vocabulary release、entity definition、code SHA；`PublicationGroup` 绑定实体/目标表集合、依赖、Candidate manifest/行数/hash、独立验证证据及已提交 Ledger。

每个目标 Candidate 写入 immutable request/version-scoped Delta，独立读回 Schema/Count/Keys/FK/Hash；**Approval-last** 且异常不批准。写入/读回不等于 Gold COMMIT。Gold Writer 事务内逐实体校验目标输入、ID、Concept/FK/Replay/Allocator 和已提交父实体；COMMIT 后使用独立新 SQL 连接验证 Ledger、全目标表及数量/引用，最终才报告 `GOLD_COMMITTED_AND_READBACK_VERIFIED`。相同完整 fingerprint + 完整验证的重放 SKIP；同 Batch 变更指纹、未知 ACK、部分 Candidate、并发冲突、计数不符都 HOLD，不盲重试。

`PublicationBarrier` 作为逻辑版本/数据产品对下游的可见性门禁：仅当该版本**要求的所有事务组**都独立完成才将整个发布版本标为可消费；不冒称跨事务组有 SQL 原子性。对已经可见的父组以及失败的子组必须保留明确的状态和恢复边界。禁止把一个后续可选 Entity 的失败误判为已提交 Person/Visit 丢失或在未标明发布版本的消费者中泄漏部分新版本。

## 3. 实施切片与真实位置

| 切片 | Scope / Owner | 禁止 |
| --- | --- | --- |
| PR1 本文 | `openspec/changes/extend-shared-omop-multi-entity/` | 源码、Warehouse、Native Item、真实 Writer 修改 |
| PR2 最小 Entity Registry / Adapter | `shared-data-engine/src/healthcare_data_engine/mapping/` + 新测试 `.github/quality/tests/shared-data-engine/` | 新增泛用 I/O 层、空 Entity/Task 目录 |
| PR3 Identity/Concept/FK 紧缩扩展 | 纯 Shared 规则；Fabric 现有 Preview 模块保持唯一实现，迁移需跨调用方测试/专项评审 | 两套互相分叉的 ID 引擎或未审核的 Concept |
| PR4 G5 Candidate 实际集成 | 现有 Native Notebook 调用 Shared；其读写/Approval 归既有 G5 Change | 直接把 Candidate 当 Gold |
| PR5 F2 实际 Gold | `azure-fabric/warehouse/omop-foundation/writer/` 及受控 SQL asset；原 F2/统一 E2E Change | 无授权物理写入、无单 Writer Fence、提前标 COMMIT |
| PR6 Condition extension | 新 Canonical/Mapper 和平台适配业务 Change，使用公共契约先测合成输入 | 擅自填全 39 表或自动部署 |

新增测试必须位于 `.github/quality/tests/<system>/<component>/`，已有 `shared-data-engine/tests/` 保持原路径。所有新增文件遵守 root AGENTS、Shared scoped AGENTS、现行 `documents/engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md` 及 `documents/engineering/development/REPOSITORY-STRUCTURE-AND-HUMAN-NAVIGATION.md`。相应源码 PR 修改唯一组件 CODE.md；不在源码树另建 README。当前 Local 业务合同仍唯一位于 `local-data-platform/spark/contracts/`，不复制一份到 Shared。

## 4. 测试与负向验收

1. 兼容：100 Patient / 5,918 Encounter 合成契约，已有 Person/Visit 候选 API、字段、Profile pin/禁止默认值以及 ID 语义等价；同一旧 G4 分区/Local PG 数据不被修改。
2. Registry：重复 Entity、未注册 Entity、循环依赖、无合法来源键、矛盾 target、动态模块路径拒绝。
3. 产生多个目标行：相同源行的确定性 fan-out，不同目标 PK 不碰撞，输入重排/重跑输出完全一致；非确定性/缺派生身份拒绝。
4. Identity：原有和新增目标表、跨医院相同来源键、casefold、Allocator 漂移/回退/溢出、Preview 快照失效、未提交父 ID 被子组引用均 HOLD。
5. Concept：错误 Domain、已失效/非 Standard、缺少 Vocabulary Release/许可证据、未知/UNK、Profile SHA 不匹配和长度溢出 HOLD。
6. FK / DAG：缺少必需父实体、跨来源错误引用、循环依赖、组内临时 ID 合法/跨组临时 ID 不合法。
7. Candidate：不可变路径、独立真实 Delta Readback、Approval-last、部分输出失败不发布、相同指纹 Replay SKIP。
8. Gold：多实体目标表/Map/Allocator/Ledger 同组原子 COMMIT/Rollback，单写入锁、未知 ACK、并发竞争、NOT ENFORCED 约束应用级验证；使用独立 SQL 连接重新查证。
9. 第三实体：Condition 的合成样本在后续业务 PR 增加，不改变 Person/Visit 核心业务算法、无需复制第二套编排器/Writer。

## 5. 决策、非目标与回滚

- **决策 D1：** 不写一个“可以配置所有 SQL 的万能 Mapper”；临床转换保持明确 Entity 专用逻辑，公共层只管理安全、版本、身份、依赖与结果契约。
- **决策 D2：** 不修改已验收 Canonical Patient/Encounter v1 的物理字节；需要新医疗字段/可选性时通过独立版本/Change 审核。
- **决策 D3：** 保留一个 Shared Wheel、各平台各自物理 Writer；并行 Local/Cloud 不共享未迁移的生产实现。
- **决策 D4：** 沿用已有 G5/F2/统一 E2E Change 的真实 runtime acceptance；本 Change 完成的是**公共架构实现/兼容性**，不是临床 Gold 通过。
- **风险：** 医院/Feed 命名空间与源键漂移、现有 Profile 强制模式、Fabric INT 全局空间、Derived ID 碰撞、跨组部分可见、契约向后兼容。每个风险需要对应失败用例和可恢复的 HOLD。
- **回滚：** PR1 可 Git revert；PR2/3 保持旧函数及原版本 Wheel，可回退调用路径；PR4/5 必须有实际版本/事务/独立数据读回的回退计划，不能 DELETE 已提交医院记录来“回滚”。
