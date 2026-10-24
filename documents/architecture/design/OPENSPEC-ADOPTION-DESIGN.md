---
status: draft
scope: openspec-adoption-and-development-governance
last_verified: 2026-10-17
source_sha: de146b294b3aa16bf8fca3b627c8ed330e20efb6
evidence: []
---

# OpenSpec 接入与开发治理设计（讨论稿）

**实施状态说明（后续补记，保留原方案历史）**：本设计稿编制后，OpenSpec G0–G4 已经按 [正式 G0–G7 计划](../../engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 真实实施并合并；G5 尚未开始，业务源码迁移也未实施。下方“尚未初始化”“仅规划”均描述原设计时点，**不可作为当前 OpenSpec 状态**。

> **DRAFT / 编写时待审核，尚未实施。** 本文重新设计 Healthcare Data Platform 的 OpenSpec 接入方式，是 [文档迁移 STEP09](../../engineering/migration/MIGRATION-STATUS.md) 的候选实施设计；**不代表 OpenSpec 已安装、初始化、通过 CLI 校验，亦不构成运行环境授权**。
>
> **核对范围**：2026-10-17 Healthcare Main `de146b294b3aa16bf8fca3b627c8ed330e20efb6` 的文档结构、Agent/开发规则、项目状态和 [OpenSpec Readiness](../../engineering/migration/OPENSPEC-READINESS.md)；参考 OpenSpec 官方 Getting Started、Existing Projects、Project Configuration、CLI 与 Spec-driven Schema 文档。旧 OpenSpec Bootstrap PR #164 已于本次设计前**关闭且未合并**，不能继续使用其旧 `docs/` 路径配置。没有执行集群、云端或业务测试。

## 1. 背景与决策建议

此前 STEP01–08 以及后续整理已经形成以下长期文档入口：

- `documents/architecture/`：总体架构、数据流、基础设施、设计讨论与已批准的决策。
- `documents/systems/`：各子系统职责、实现边界和 `README.md` / `CODE.md` 源码地图。
- `documents/engineering/`：Agent 规则、开发工作流、测试证据、运维安全和项目状态。
- 真实 `contracts/`、代码、SQL、Terraform、Workflow 和已完成的 GitHub Run/独立读回仍保持各自的事实权威。

现有体系适合维护长期知识，但缺少一套统一的**变更意图 → 行为要求 → 技术设计 → 任务 → 验证 → 接力/归档**机制。过去以 Task/Step、日期和 Session Handoff 命名的大量文档会产生重复、矛盾和过时的 CURRENT/NEXT。

**建议：在同一个 Healthcare 仓库引入标准 OpenSpec，保持 `documents/` 不动，采用小步、按真实变更增长的 Specs/Changes，不将现有全部文档批量转换。** 先用默认 `spec-driven` Schema；没有证据表明标准流程不足之前不自建 Schema、Agent 调度器或锁服务。

## 2. 目标与明确不做的事情

### 2.1 目标

1. 让需求与重构在改代码之前拥有可审核的 Proposal / Design / Delta Specs / Tasks。
2. 让跨 Session 的 Agent 通过当前 Change、PR、Commit、Run 接力，不再创建新的长篇 Handoff。
3. 让 `openspec/specs/` 仅记录**已核实、已采用的当前系统行为**；尚未实现的目标仅出现在 Proposal/Change/Architecture Draft。
4. 继续用 Healthcare Git + PR 维护真实应用源码，Self-Runner/GitHub Actions 保存可信测试证据。
5. 让 Data Platform V2、Condition、Portal 真实 Spark 血缘与 Azure/Fabric ETL 等未来变更使用共同流程。
6. 将新的规范约束控制在少量索引与 `config.yaml` 中，避免常驻 Agent 上下文膨胀。

### 2.2 不在本次设计/初始化范围

- 不移动、重写全部 `documents/`、`contracts/` 或旧验收记录。
- 不初始化 `openspec/`，不创建未经证据支持的 Current Specs，不批量迁移旧 `docs/`。
- 不重命名 Task004 运行时标识，不重放历史 Batch，不启动 Condition Writer。
- 不修改业务代码、Self-Runner Workflow、K8s、Airflow、Spark、PostgreSQL、S3 或 Azure 资源。
- 不将 OpenSpec 当作共享资源的锁、授权、部署平台或业务成功的证明。

**2026-10-18 命名更新**：长期本地平台源码根目录采用 `local-data-platform/`（D-07），原 `data-platform/` 为旧候选；先用独立 docs-only 的 `adopt-local-data-platform-naming` Change 演练 OpenSpec 全流程，不替代 G5 原计划 `relocate-local-data-platform` 的源码迁移设计。G3 旧候选路径 CI 需在 G6 前另行适配并测试。

## 3. 权威边界：各层只管理自己的事实

| 层 | 唯一职责 | 不应复制/取代 |
| --- | --- | --- |
| `AGENTS.md` + `documents/engineering/development/` | Agent 通用约束、命名、分支、测试、安全、有限重试 | 每个 Change 的长篇内容 |
| `documents/architecture/` | 稳定的实际/目标架构、重要 ADR、未批准的设计草案 | 逐个实现步骤、最新 Session 进度 |
| `documents/systems/` | 子系统说明、依赖边界、`CODE.md` 源码导航 | 完整行为 Specs、每次 PR 检查表 |
| `documents/engineering/status/PROJECT-STATUS.md` | 唯一项目级 CURRENT/NEXT、跨工作线真实验收范围 | Change 内逐项待办清单 |
| `openspec/specs/` | **当前已建立的行为要求和可验证场景** | 待实施的计划、运维、源文件导航 |
| `openspec/changes/` | 待审/进行中变更的 Proposal、设计、增量行为 Specs 与 Tasks | 运行日志正文、资源锁、无边界 Session Handoff |
| GitHub PR / Commit / Actions + Self-Runner | 代码审查、目标 SHA、工作流执行和 Artifacts | PG/Delta/S3 实际业务结果的独立读回 |
| 源码、Contracts、Runtime 与独立验收 | 实际实现、合同、真实状态、持久化业务事实 | 由 Markdown 推定“已经部署/验收” |

**冲突处理**：安全门槛始终适用；Contract/源码说明能实现什么，真实运行证据证明执行了什么，审核后 Current Spec 规定系统应有什么行为，`documents/` 解释架构及如何维护。三者冲突必须明确记录并修订，不能仅以“OpenSpec 文件更新较晚”覆盖现状。

**Specs 不重复实现 Contract**：字段级 JSON Schema / DDL / 协议文件仍归真实 `contracts/` 与源码；Spec 用 Requirement、Scenario 和链接表达外部可观察行为、失败/幂等要求。实现变化如果改变当前行为，先审核 Change，再同步 Contract、代码与最终 Specs。

## 4. 目标目录（方案，不代表已经建立）

~~~text
healthcare-data-platform/
├── AGENTS.md
├── documents/
│   ├── architecture/
│   │   ├── design/                 # 采用前的讨论稿；本文件位于这里
│   │   └── decisions/              # 长期已批准 ADR
│   ├── systems/                    # 组件 README / CODE 源码地图
│   └── engineering/                # 治理、运维、安全、状态、证据
│
├── openspec/                        # STEP09 批准后由官方 CLI 初始化
│   ├── config.yaml                 # 简洁项目上下文和 artifact 规则
│   ├── specs/                      # 当前可验证行为；按需逐步增长
│   │   └── <capability>/
│   │       └── spec.md
│   └── changes/
│       ├── <change-name>/
│       │   ├── .openspec.yaml      # 由当前 CLI/Schema 按需生成
│       │   ├── proposal.md
│       │   ├── specs/
│       │   │   └── <capability>/
│       │   │       └── spec.md     # Delta requirements
│       │   ├── design.md
│       │   └── tasks.md
│       └── archive/                # 经验证、同步后由 OpenSpec 归档
│
├── local-data-platform/            # V2 设计目标（2026-10-18 已定名）；尚未完成源码迁移
├── azure-fabric/
└── platform-portal/
~~~

OpenSpec 是与 `documents/` 平级的治理目录，不属于 Data Platform、Azure 或 Portal 的业务运行目录。仓库目前未完成 Data Platform V2 源码迁移，以上结构中 `local-data-platform/` 是**未来目标**，不是当前 Main 实际文件树。

**命名**：Change 与 Capability 用稳定、功能导向的 kebab-case（如 `landing-batch-validation`、`omop-person-visit-ingestion`），不采用 `task005/step03`、日期或会话号作为代码或长期 Capability 名称。`task`/`step` 仍可作为阶段性实施计划及历史证据编号。

## 5. 采用方式：Brownfield-first，不预先重写全项目

官方 OpenSpec 对已有系统建议按**正在修改的最小切片**建立 Spec，而不是上来描述整个代码库。因此初期不强制一次创建五大组件全部 Baseline。

### 5.1 第一批范围的选择

| 领域 | 当前事实边界 | OpenSpec 处理 |
| --- | --- | --- |
| Synthea NEW_ONLY Producer | 独立生成、校验、READY 发布，已有历史验收 | 仅在相关变更触及时提炼当前行为与证据 |
| Landing Discovery/Claim + Batch | READY/Manifest、Batch 身份与已完成批次安全 SKIP 有已验收范围 | 可优先选定一个小切片作试点 |
| Spark Person / Visit + OMOP Writer | NEW_ONLY、原子 COMMIT、幂等与独立 PG 读回已验收 | 仅写已验收行为；不假设 UPDATE_ONLY/MIX_DATA |
| Condition / Procedure / Drug | 目标能力、尚无完整业务 E2E | **不建立虚假 Current Spec**；未来 Change 定义新要求 |
| Portal OpenLineage/Marquez | Airflow 事件和隔离 Spark Smoke 分项验证，真实全链路不完整 | 现状与缺口分开；真实 Dataset/Job 血缘属于后续 Change |
| Azure Blob → Fabric Notebook/Pipeline → OneLake | 已有 IaC 与 Plan-only，业务 E2E 未实现 | 不写“已运行”的 Current Spec；由未来 Exporter/ETL Change 定义 |

初次采用时，当前 Specs 允许为空或只有**已审查、可追溯的极小 Baseline**。如一个 Change 涉及既有功能，先读取有效 Contract 和历史验收建立它实际依赖的基线，再写 Delta Requirement；避免把已实现逻辑误写成新特性。

### 5.2 当前的 Data Platform V2 设计怎么处理

[Data Platform V2 重构讨论稿](DATA-PLATFORM-V2-MIGRATION-DESIGN.md) 已有架构选择、目录迁移、公共组件、Task004 兼容与回滚内容。**保留它作为人读的架构设计源，不立即原样复制到 Change。**

首个 Change 已选定候选 `relocate-local-data-platform`，仅审核一个小范围物理路径迁移切片，G5 只建立和审查 Proposal/Design/Tasks，G6 才允许实际改动源码。之后 Landing Manifest 接口或 OMOP Writer Handoff 等模块化改造分别创建新 Change、明确依赖与回滚。大规模 V2 计划仍由多个有界 Change 串联，避免单个 Change 长期无法归档。

## 6. 标准开发生命周期与 Agent 接力

采用官方默认 `spec-driven` 的核心思路，终端 CLI 和 AI 对话命令应明确区分：

~~~text
需求 / 疑问
  ↓
Explore（可选，只读分析，不实施）
  ↓
Propose → 生成 proposal / specs / design / tasks
  ↓
人工审阅范围、权威事实、安全风险与验收条件
  ↓
Healthcare feature branch + PR
  ↓
Apply：小步修改正式代码 / Contract / 就近测试 / CODE.md
  ↓
Static / Unit / Contract / 需要时的受控 Self-Runner 验证
  ↓
独立业务读回 + 对照 Spec/Design（如需要 Runtime）
  ↓
Verify（可使用官方扩展命令，或按现有测试规范人工核验）
  ↓
Sync / Archive：仅将已核实、经审核采用的行为更新到 Current Specs
  ↓
PR 复核并合并；必要时更新跨项目状态和长期架构
~~~

- **指令真实性**：官方当前默认 core 工作流提供 `/opsx:explore`、`/opsx:propose`、`/opsx:apply`、`/opsx:sync`、`/opsx:archive`。`/opsx:verify` 属于扩展 profile，不能假设它默认安装；具体命令名称取决于真实 CLI 版本和所选 AI 工具。
- **Git 实际工作流优先**：OpenSpec 的 Tasks 勾选只代表任务记录，不能代替 PR Merge、目标 SHA 的测试 PASS，或真实 PG/S3/Delta 读回。`archive` 不是自动部署。
- **归档时机**：选择合并前在同一个 PR 中完成经验证的 Spec Sync/Archive，或另起后续 docs-only PR；两种都要确保 Current Specs 不先于实际被采用的代码行为。最终审查时明确测试所对应的代码 SHA；若归档提交只改文档，也需复验相关静态链接与一致性。
- **失败与回滚**：失败记录放 Change 的相关 Task/阻塞说明和 GitHub PR/Run，而不另建 SESSION-HANDOFF 文件。每个失败至少记录原因、尝试方案、Branch、Commit SHA、Workflow Run、下一个可安全动作。建议沿用“同一问题最多连续调试三轮，仍失败则停止并交接”的保护规则；该规则应在 STEP09 正式实施时复核并纳入开发规则，而不是假定当前全部 Workflow 已自动强制。
- **多 Session**：新 Agent 读取 `AGENTS.md` → `documents/README.md` → 当前项目状态 → 所属组件 CODE/Contract → 对应 OpenSpec Change/Tasks → PR/Main SHA → Run/独立验收 → 实际资源状态。不同 Agent 不能仅凭 Tasks 未勾选就认定对方已释放 K8s/PG 等共享资源。
- **授权**：Terraform Apply/Destroy、PostgreSQL 写入、业务 Batch Replay、K8s/S3/Azure 共享 Runtime 操作继续受 [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md) 和 [Session Coordination](../../engineering/development/SESSION-COORDINATION.md) 管控。Proposal、CLI 或 PR 不授予额外权限。

## 7. `openspec/config.yaml` 的设计原则

第一次使用官方生成的默认 `spec-driven` Schema；按真实 CLI 版本验证配置字段。`config.yaml` 只放极简约束，不复制整份 `AGENTS.md`、安全规范或组件 CODE 地图。

以下仅为**待验证的配置示意**，不是已提交的实际配置：

~~~yaml
schema: spec-driven
context: |
  Project: Healthcare Data Platform monorepo.
  Canonical docs: documents/README.md and AGENTS.md.
  Current status: documents/engineering/status/PROJECT-STATUS.md.
  Keep documents/ as architecture, system, engineering and operations knowledge.
  Current specs describe only verified behavior; plans belong in changes.
  Use component/function names, not taskNNN/stepNNN, for new maintained code.
  Git PR and Self-Runner evidence do not replace independent runtime readback.
rules:
  proposal:
    - Identify affected systems and distinguish implemented vs proposed behavior.
    - State compatibility, rollback and runtime side effects.
  specs:
    - Write testable GIVEN/WHEN/THEN scenarios and cite existing contracts when relevant.
  design:
    - Record dependency boundaries, cross-component interfaces and migration strategy.
  tasks:
    - Break work into independently reviewable steps with explicit evidence and hold gates.
~~~

其他要点：

1. `context` 是所有阶段的短上下文；详细规则仍由 `AGENTS.md` 和 `documents/engineering/development/` 管理。
2. `rules` 约束 Proposal/Specs/Design/Tasks 的内容；不能代替真正的 CI、代码审查或资源权限检查。
3. 不在配置中硬编码 Runner Secrets、Kubeconfig、数据库连接、过时的 Commit SHA、已删除的 `docs/` 路径或旧 Task 状态。
4. 第一次初始化时核查 CLI 版本、配置 Schema、生成的 AI 工具命令和输出，再决定是否需要额外 Schema/CI。不要为了套流程预先构建复杂平台。

## 8. STEP09 正式实施：统一采用 G0–G7

> **唯一详细执行步骤、验收清单与实际状态记录**：[OpenSpec G0–G7 实施计划](../../engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md)。本设计稿负责架构边界，不再维护与实施计划重复的 Gate 表格。旧版 G0–G4 是**历史讨论稿编号**，已被 G0–G7 替换；其他文档不得继续用旧编号作为当前实施指令。

| 阶段 | 核心责任 | 是否修改业务源码 |
| --- | --- | --- |
| G0 | 核对 Main、当前 CI、CLI/Node 版本及冲突 | 否 |
| G1 | 官方 CLI 在仓库根目录初始化 `openspec/` | 否 |
| G2 | 最小 `config.yaml`、Agent/文档/状态治理对齐 | 否 |
| G3 | OpenSpec 校验 CI、`data-platform/` 命名 CI 覆盖、迁移兼容例外测试 | 否（只允许治理 CI/测试） |
| G4 | 与 PR/Self-Runner、三轮失败停止和跨 Session 证据接力集成 | 否 |
| G5 | 首个 `relocate-local-data-platform` Change 的 Proposal/Design/Tasks 审核 | **不移动源码** |
| G6 | 经审核的按组件物理迁移、路径兼容及另行授权的 Runtime 切换 | 是，分切片 PR |
| G7 | 独立管理 Modularization、Fabric、FHIR/HL7、Lineage、公开只读 Showcase | 按 Change 审核 |

**G0–G4 结束后治理体系即可使用，无需等 Data Platform V2 全部迁移。** G1–G4 Bootstrap 与 G5/G6 业务变更必须使用不同 PR。G3 只准备覆盖 `data-platform/**` 的新增命名检查、严格限定的旧文件迁移例外及其正负测试；G6 才用真实文件迁移验证它，不能取消检查。纯目录 Refactor 可在当前 CLI 验证后用 `skip_specs: true`，但不可省略“不改变当前 NEW_ONLY Person/Visit 行为”的断言与回滚验证。

新优先级为 **OpenSpec G0–G4 → G5/G6 物理迁移 → PG OMOP→Fabric 双表 E2E → FHIR / HL7 v2 独立 Fabric 输入 → Gold/只读展示**；模块化重构和 Lineage 可按依赖另立 Change，Condition 业务开发暂缓。Mirth Connect 版本/维护/许可必须先核定；公开只读静态证据与实时交互 Portal、Fabric Workspace/Marquez/Airflow 管理面明确隔离。见 [Healthcare V2 多来源路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)。

## 9. 设计验收与待审事项

- [ ] 确认同仓 OpenSpec，不把旧 Private Archive 或 Self-Runner 变成第二份当前 Specs。
- [ ] 确认默认 `spec-driven` 和最小 `config.yaml`，先不自建 Schema。
- [ ] 确认按变更增量建立 Specs，而非一次性全量 Baseline 迁移。
- [ ] 确认 Data Platform V2 使用小型 Change 逐阶段实现，不创建不可收尾的大 Change。
- [ ] 确认 “连续三轮失败停止” 应纳入的现行规则位置及报告格式。
- [x] 明确 G0–G4 只进行 Bootstrap/治理/CI，不搬业务源码；G5 只设计首个 Change，G6 才执行并按单独 Runtime Gate 审核。

已确定上述实施顺序，执行状态以 [G0–G7 计划](../../engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 为准。**本次只更新设计和计划，不表示已安装 CLI、初始化 `openspec/` 或开始 G6 源码迁移。**

## 10. 权威资料与参考

- [OpenSpec 官方 Getting Started](https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md)
- [OpenSpec 官方 Existing Projects（Brownfield-first）](https://github.com/Fission-AI/OpenSpec/blob/main/docs/existing-projects.md)
- [OpenSpec 官方 Project Configuration](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/customize/project-config.md)
- [OpenSpec 官方 CLI Reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/cli.md)
- [OpenSpec 官方 spec-driven Schema](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/schemas/spec-driven/index.md)
- [现行治理规则](../../engineering/development/DOCUMENTATION-GOVERNANCE.md) · [开发工作流](../../engineering/development/DEVELOPMENT-WORKFLOW.md)
- [当前项目状态](../../engineering/status/PROJECT-STATUS.md) · [STEP09 Readiness](../../engineering/migration/OPENSPEC-READINESS.md)
- [Data Platform V2 架构设计](DATA-PLATFORM-V2-MIGRATION-DESIGN.md)
