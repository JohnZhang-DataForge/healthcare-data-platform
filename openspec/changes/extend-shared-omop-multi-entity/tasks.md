# Tasks — Shared OMOP Multi-Entity architecture and incremental implementation

> 本 Change 跟踪**平台中立公共能力**，不重复关闭 `fabric-g5-approved-silver-omop-candidate` 的 Candidate、`fabric-omop-foundation` 的 Gold 或 `fabric-fhir-omop-unified-e2e` 的真实运行任务。每个 PR 修改本文件与其实际业务 Change 的有关任务；只有真实证据满足时才勾选 Runtime Gate。

## 1. PR1 — 契约和架构（Docs/OpenSpec only）

- [x] 1.1 核对 Healthcare 最新 main `52b113d07c6d959c86201dfd7e17137bebdb2721`（2026-11-05 ET）、0 Open PR、根/Shared AGENTS、目录/CODE/测试规则、冻结 Canonical v1、G5/P1/F2 与 F0/F1 独立证据；不把以前的 G4/G5 ROLLBACK/只读当作 Gold COMMIT。
- [x] 1.2 建立 `proposal.md`、`design.md`、`specs/shared-omop-multi-entity/spec.md`，明确定义 Registry、Mapper、派生目标身份、Concept、依赖、Candidate、事务组与 Publication Barrier；声明非目标、兼容和安全边界。
- [x] 1.3 规划六个有界 PR、唯一源码/文档/新增测试 owner、负向验收与回滚；没有修改真实 Shared Wheel/Notebook/SQL/Local 运行环境。
- [ ] 1.4 PR1 严格 OpenSpec 校验、文档链接、Trusted Change/Source Layout 等 Required 检查全部针对最终 PR HEAD 通过；审核并合并 main 后记录 PR/Run 和最终 SHA。仅确认设计，不声称实现。

## 2. PR2 — 最小 Shared Entity Registry / Candidate API

- [x] 2.1 提供仅声明式、显式注册的 Person/Visit `EntityDefinition` / Registry，支持一个来源实体映射多个目标表及多输出 stable derived key，不引入自动 SQL/动态 import/第二轮空框架。
- [x] 2.2 增加统一 `EntityCandidateSet` 输出/一致性校验，现有 `build_omop_candidates` / `OmopCandidates` 接口仍兼容；明确 Entity、Source、Processing SHA 与审批证据。
- [x] 2.3 新增 `.github/quality/tests/shared-data-engine/mapping/test_entity_registry.py` 15 项正负向/兼容测试；CI 精确发现执行 15/15（Python 3.11 与 3.13）；现有 Spark/Canonical 回归、重复 Wheel 构建、独立安装均通过；唯一组件 CODE.md 同 PR 更新。实际 Run/SHA 见下方 PR2 证据。

## 3. PR3 — Identity / Concept / FK 公共能力

- [ ] 3.1 复用并审核 F2 `identity_plan.py`、`silver_identity.py` 与 Shared Candidate 接口，设计单一真实纯逻辑 owner 和兼容桥接；支持按目标表全局稳定 INT ID、source/derived namespace、已提交/拟议显式区分，不提前改动历史 ID。
- [ ] 3.2 Preview 输入携带完整 Warehouse snapshot fingerprint；Candidate 可使用经验证的 `PROVISIONAL` ID，但只有同组经事务验证时可被引用；真实 Writer COMMIT 前必须在 single-writer fence 下重新读取 Map/Gold/Allocator/Ledger，失败 HOLD。
- [ ] 3.3 扩展按 Entity/Target/Field/Source/Vocabulary SHA 固定的临床 Concept Profile、Domain/Standard/Validity/License 审核；真实 F1 临床 Profile 审批仍由 `fabric-fhir-omop-unified-e2e` P1.4–P1.5 验收。
- [ ] 3.4 引入最小依赖 DAG/FK Resolver，验证必需/可选父实体、同医院命名空间、同组拟议/跨组已提交的引用规则；跨医院自动 Patient 合并禁止。
- [ ] 3.5 正负向单测覆盖 ID 拟议与重放、第三目标表注册而无需重写 Person/Visit、跨医院、casefold、溢出、错误 Concept Domain、缺失 FK、DAG 环和 Snapshot drift。

## 4. PR4 — 当前 Fabric G5 Candidate 恢复主线

- [ ] 4.1 维持当前 G4 P100/E5918/Q0 和 Approval 不可变，复用正式 Notebook/Environment 0.1.3+ 经审核发布版本与原 G5 源只读门禁；不冒充多实体 Runtime PASS。
- [ ] 4.2 真实临床 Mapping Profile 和 Warehouse ID 完整 Snapshot 审核通过后，按 Person/Visit 目标输出 Candidate Delta；独立读回 Count/Keys/Hash/FK，Approval-last、冲突 HOLD、Replay SKIP。
- [ ] 4.3 将真实 Candidate Evidence 写回现有 G5 OpenSpec，相关 Run/SHA/物理 Delta 路径真实可查；本 Change 只确认公共契约集成。

## 5. PR5 — F2 Gold Writer / Publication Groups

- [ ] 5.1 受控 global single-writer fence 下，把 Person、Visit、Map、Allocator、Ledger、Audit 在短 Warehouse SQL 事务中原子提交，失败 ROLLBACK；重验完整快照，检查非强制 PK/FK。
- [ ] 5.2 独立 SQL readback + ACK unknown 诊断 + Replay SKIP / fingerprint conflict HOLD / 并发 / 部分失败测试；真实 COMMIT 只在独立授权、实际云端验收后声明完成。
- [ ] 5.3 PublicationGroup/Barrier 增加「基础组 + 未来临床子组」模型，区分单组 SQL 原子性与多组逻辑发布完整性，验证半完成不对下游宣称整体 READY。
- [ ] 5.4 同步现有 `fabric-omop-foundation` / `fabric-fhir-omop-unified-e2e` 任务及实际 PR/Run，完成真实 Native Pipeline E2E 的独立验收。

## 6. PR6 — Condition 作为第三实体证明

- [ ] 6.1 在独立 Condition 业务 OpenSpec 下定义 Canonical Condition 合同/来源字段/Clinical Profile/目标 `condition_occurrence`，不默改 v1 Patient/Encounter，也不把新合同放入代码任务目录。
- [ ] 6.2 使用已有 Registry、Identity/FK Resolver、Candidate 和 Publisher 接口新增 Condition Mapper；不复制一套 Writer/编排，不改变 Person/Visit 业务算法。
- [ ] 6.3 合成数据分别验证标准链路、跨医院、FK、未知 Concept、缺失父行、重复输入、Replay、Rollback 和跨组 Publication Barrier；实际云端写入另行授权。
- [ ] 6.4 完成目录 CODE map、人类文档与 Current Specs 行为证据同步；跨运行时验证 Local PG 兼容性，只有达标后归档相关 Change。

## Evidence / boundaries

- PR1 baseline：Healthcare main `52b113d07c6d959c86201dfd7e17137bebdb2721`；G4 已验收 Silver P100/E5918/Q0、正式 Wheel 0.1.3 Import、F0/F1 基础/Vocabulary 与 F2 合成 ROLLBACK；P1 正式临床 Map、G5 实体 Candidate、Gold COMMIT/全 E2E **仍 OPEN**。
- PR1 已通过静态 Required Checks 并合并（见 1.4）；PR2 当前为源代码候选，新增 CI、Wheel 构建与版本验收仍在 2.3 OPEN，绝非 Fabric Cloud 发布。现场任何 Azure/Fabric、PG/Local/Capacity、K8s/Blob 操作必须依照 `SAFE-OPERATIONS` 与 `SESSION-COORDINATION` 单独授权。

## PR2 — Registry/Adapter 源码候选离线验收（2026-11-05 ET）

- [PR #724](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/724)；受测精确源码 HEAD `d803a10bc6d1828b824473606d24a8e9194bb240`；本次仅新增 2 个 Shared 纯源码模块、1 个新测试文件、原有 Wheel Workflow 新目录发现/版本、包 0.1.4 源码候选、CODE/README 及本 OpenSpec。无 Azure/Fabric/PG/Local 运行写入。
- [Shared Engine Wheel Offline Validation Run #42157435397](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42157435397) 两个独立 Job **SUCCESS**：
  - Python 3.11/PySpark 3.5.7：现有合成 FHIR/Canonical/OMOP 35/35 PASS、新规范目录 Multi-Entity 15/15 PASS、两次相同 Wheel 字节校验 `REPRODUCIBLE_WHEEL_PASS`、独立安装 `WHEEL_IMPORT_PASS 0.1.4`。
  - Python 3.13/PySpark 4.1.1：FHIR pure 13/13 PASS、新 Multi-Entity 15/15 PASS、原有 Spark DataFrame 2/2 与 OMOP 11/11 PASS、Wheel `FABRIC_P3_PY313_WHEEL_INSTALL_IMPORT=PASS 0.1.4`。
- 同精确受测 SHA 上，Required `require-trusted-change`、`validate-openspec`、`require-trusted-fabric-deployment-owner`、`require-trusted-component-paths` 全部 **SUCCESS**；链接、路径命名、Change Gate、Active Index 也 **SUCCESS**。Cloudflare 可选 Portal Build 是 FAILURE，与本次 Shared/OMOP 代码无关，不冒充 Portal 成功。最终 tasks 文档证据编辑会产生新 PR HEAD，必须重新核对该 HEAD 的适用 Required Checks。
- **仅 SOURCE/UNIT/BUILD PASS；未发布到 Fabric Environment：** 正式 Cloud Wheel 仍是 0.1.3；新 Entity Registry/Adapter 只针对当前 Person/Visit，真实临床 Profile、G5 物理 Candidate、F2 stable ID Gold COMMIT 和统一 E2E 仍 OPEN。
