---
status: reviewed
scope: openspec-g0-g7-rollout-implementation-plan
last_verified: 2026-10-18
source_sha: a5047ea41e50837351965fbee0ba053ac61d3a50
evidence: []
---

# OpenSpec 正式实施与 Data Platform 迁移计划（G0–G7）

> **执行计划已确认；实施未开始。** 本文件是 STEP09 的**唯一 G0–G7 执行步骤与阶段验收清单**。日期和 Source SHA 表示编写时的只读 Git 基线，不是 CLI、CI、集群或云端验收记录。后续按每个 PR、已安装版本、目标 SHA 和实际 Run 更新执行状态。
>
> [OpenSpec 接入架构设计](../../architecture/design/OPENSPEC-ADOPTION-DESIGN.md) 管原则和权威边界；[OpenSpec Readiness](OPENSPEC-READINESS.md) 管实施前核查；[Data Platform V2 设计](../../architecture/design/DATA-PLATFORM-V2-MIGRATION-DESIGN.md) 管目录兼容和回滚细节；[项目 CURRENT/NEXT](../status/PROJECT-STATUS.md) 管总体进度。禁止将这些文件变成相互矛盾的第二份 G0–G7 计划。

## 1. 不变原则与范围

- **仓库根目录 `openspec/` 与 `documents/` 平级**；`documents/` 保留架构、系统导航、工程规则及运维，`openspec/specs/` 只维护经核实的当前行为，`openspec/changes/` 管变更意图/设计/任务/增量要求。`contracts/`、源码、GitHub PR/Run、独立运行读回各自保持事实权威。
- STEP09 的 G0–G4 是 **OpenSpec 开发治理体系 Bootstrap**，**不移动业务源码、不自动创建 Current Specs、不触发 Live Runtime**。G5 是首个 Change 的设计与审批；G6 才允许按独立 PR 实际物理迁移；G7 是未来 Change 的持续运营。
- **不把历史 `docs/` 全量导入 OpenSpec**，历史证据由固定 Git Snapshot 保存；旧 PR #164 已关闭、未合并，不能复制其旧配置。
- 只复用 GitHub PR、GitHub Actions 与 Self-Runner；OpenSpec 不替代调度器、访问控制、分布式锁或数据提交验证。
- 对所有 **新增维护代码**，严禁 `taskNNN` / `stepNNN` 等开发编号作为组件目录、文件、函数、类、DAG ID、SQL、正式 Shell、镜像、Manifest、Workflow、测试及 Contract 的语义名称。开发计划、OpenSpec `tasks.md` 步骤号、Issue/PR、Run/日志与历史证据可以保留阶段编号。唯一命名权威：[Code Organization & Naming](../development/CODE-ORGANIZATION-AND-NAMING.md)。
- 旧 `task004` 路径、Python 导入、DAG/镜像、`etl.task004_*` 数据库对象、Batch/Manifest/Claim/Fingerprint 与冻结镜像 Digest **不得在纯目录迁移时批量重命名或更改行为**；这些另由 Modularization Change 管理。
- 共享 K8s/Airflow/Spark/PG/S3/Azure 操作需按 [Safe Operations](../operations/SAFE-OPERATIONS.md) 与 [Session Coordination](../development/SESSION-COORDINATION.md) 取得**针对具体操作的独立授权**。本计划本身不授予任何 Runtime 权限。

## 2. 单一阶段定义（G0–G7）

| 阶段 | 内容及正式交付 | 验收门槛 | 范围限制 |
| --- | --- | --- | --- |
| **G0 — 基线与前置检查** | 从实施时最新 Main 检查实际文件树、`AGENTS.md`、命名和 CODE Map CI、OpenSpec 现状、未合并 PR；确认 Node 与官方 OpenSpec CLI 版本/支持命令，固定准确 SHA | 输出 Repository SHA、Node/CLI 版本需求、原始 Workflow 与冲突清单、旧 PR #164 CLOSED/NOT MERGED 的审计结果 | 只读，不安装/迁移/执行 Runtime |
| **G1 — 官方 CLI 初始化** | 在仓库根目录用经过验证的 CLI 版本初始化标准 `openspec/`，记录实际生成结构与所选 AI 工具集成策略 | 官方 Init 成功；准确记录 CLI 版本、Node 版本、源 SHA 和生成文件；未生成过时 `docs/` 链接 | 不迁移业务文件；不将 CLI 文件存在等同 PASS |
| **G2 — 项目配置与治理对齐** | 最小 `openspec/config.yaml` 使用默认 `spec-driven`；引用 `AGENTS.md`、`documents/README.md`、当前 Status 和命名/安全规则；按已确认优先级同步项目状态 | 配置字段通过实际 CLI/Schema 校验；规范中只有一个权威入口；可用最小/空 Current Specs；明确 Condition 暂缓 | 不复制 `documents/`、`contracts/` 或历史全文 |
| **G3 — 静态 CI 集成** | Healthcare PR 集成 OpenSpec Validate（实际参数按版本确认）、文档链接/Schema 检查；扩展代码命名 Workflow 与检测器覆盖将来的 `data-platform/**`，并为纯历史移动设计受限兼容例外和单元测试 | 正向/负向用例及目标 PR SHA 的 CI 实际 PASS；新增 Task/Step 命名仍被拒绝；无任意 Shell/集群凭据要求 | **此阶段只准备检查规则与测试，绝不搬源码、无限放宽例外或执行 Runtime** |
| **G4 — Agent/PR/Self-Runner 流程接合** | 将 Explore→Proposal/Design/(适用的 Delta Specs)/Tasks→PR→Static/Test→适用的独立 Readback→Sync/Archive 的责任与接力固定；验证跨 Session 可由 Git/Change/Run 恢复；复用已有三轮失败停止规则 | 能演示不触及业务的 CLI/Change 校验和 PR 工作流；PR/Run 记录准确 SHA、失败方案、下一安全动作；确认何时允许 Archive | 不自建 Agent 调度器/锁服务；三轮停止是开发约束，不冒充已自动强制的 Runner 功能 |
| **G5 — 首个真实 Change 的设计/审核** | 创建 `relocate-local-data-platform`，只选一个小范围物理迁移切片；编写 Proposal、Design、Tasks，明确旧路径清单、兼容层、回滚和回归门禁；纯 Refactor 的 `skip_specs: true` 需经当前 CLI 实验确认 | Change Validate 成功、PR 审核范围/风险/回滚；针对旧 NEW_ONLY Person/Visit 的可观察行为定义不变性断言；**本阶段不移动源码** | 不进行 Task004 语义改名、公共基类重构或 Fabric ETL；不凭空编造 Delta Specs |
| **G6 — Data Platform 源码物理迁移** | 根据 G5 已审查 Change，按组件逐 PR 移入 `data-platform/`；先静态路径/引用兼容，再单独安排运行入口切换及必要授权的回归 | 新旧路径映射、CODE.md、CI、Import、DAG、GitSync、Docker COPY/Context、SparkApplication、Contract/Manifest、历史 Batch SKIP 及必要独立读回均与本切片验收相符；回滚可行 | **物理迁移 ≠ 模块化完成**；只有获批准且资源空闲时才进行 Live Gate |
| **G7 — 后续持续开发** | 独立 Changes 处理模块化、PG OMOP→Fabric、FHIR→Fabric、HL7 v2→Fabric、Lineage、公开只读 Showcase；按当前实际证据 Sync/Archive | 每个 Change 分别验证、PR/Run 与业务读回绑定；只有已核实且采用的行为进入 Current Specs | Condition/Procedure/Drug 和 UPDATE_ONLY/MIX_DATA 不在本阶段自动启动；Mirth 许可及门户安全单独决策 |

**Gate：G0–G4 结束后即可使用 OpenSpec 处理后续变更，无须等待全部 V2 Relocation。** G1–G4 可作为一个或多个独立 Bootstrap PR；G5/G6 的业务源码 Change **不得混入 Bootstrap PR**。单个大型 Relocation Change 可用多个有界 PR 实施，但每个 PR 要有对应具体切片、目标 SHA、回退、测试与状态；避免长期无法归档。

## 3. G3 命名 CI 与 G6 迁移特例

当前实际检查入口：[Workflow](../../../.github/workflows/code-component-naming-check.yml) 和 [Checker](../../../scripts/quality/check_new_code_names.py)。目前 Workflow `pull_request.paths` 和 Checker `ROOTS` 尚不包含 `data-platform/`；Checker 的 `git diff --no-renames --diff-filter=A` 还会把部分纯移动旧文件视作新增。**现状有效，但对未来目标目录不完整**。

G3 必须：

1. 在 PR Trigger 与 Checker 新增 `data-platform/**` / `data-platform/`，并按搬迁后 CODE Map 权属同步检查器和相应测试。
2. 设计受限的 legacy relocation 例外：源文件必须存在于明确的 Base SHA；源、目标路径有审查过的映射；内容 Git Blob SHA 完全一致或显式证明仅改变必需路径兼容；所有新写入内容仍按新代码规则检查。**不允许依靠名字或目录前缀无条件豁免**。
3. 加入至少这些负向测试：新建 `data-platform/scripts/task999/step03.sh` 必须失败；历史文件搬迁过程中夹带新 `taskNNN` 文件必须失败；修改过的 Legacy 文件不能借纯搬迁规则绕过审查；合法组件/功能路径必须通过。
4. 迁移兼容豁免须**限定到实际 Change/PR 的固定文件列表及准确 SHA**；试点验收后清理临时宽松策略，不永久豁免整个 `data-platform/` 目录。

G6 中无需立即 Rename 已验收的旧 `task004` 文件。应先保留兼容入口/适配层，以实际依赖审计为准处理不同路径；真正语义重命名留待独立 Change。

## 4. G5/G6 首个 Change 的实施边界

**首次选中的切片以低风险路径为优先**，先完成全仓依赖图，再按实际 Workflow/DAG/Docker 影响确定顺序，不能在设计阶段假定任意目录完全无运行引用：

- **先静态验证**：`git mv` 方案、Import、镜像 COPY、构建上下文、Self-Runner/Healthcare Workflow、`AGENTS.md`、`CODE.md`、合同与相对链接的引用矩阵。最初 PR 保留仍在运行的旧入口，避免合并 Main 后 GitSync 因路径变化删除 DAG。
- **再分离运行切换**：原 DAG ID、Schedule、安全路由、Writer/Batch/Fencing 不变；在获批的单独 Gate 下更新 GitSync/DAG/镜像的真实消费路径并检查部署后的实际读取、业务 SKIP 与持久化数据。
- **回退**：按被批准的 Git/镜像/配置回退，不自动重跑历史 Batch、不执行 Writer 重放、不触碰数据库持久化协议。Pure relocation 的 PR PASS 不等于整套 V2 Modularization 完成。
- **每切片停止条件**：路径或 CODE Map 不一致、同一问题连续三轮调试失败、真实共享环境状态未知、Writer 安全未知、GitSync 可能误删 DAG 均 **HOLD**；记录 Branch、完整 SHA、Run、失败原因/尝试方案及安全下一步。

G5 的纯重构可以在当前 CLI 与 Schema 确认后采用 `skip_specs: true`，但必须在 Design/Tasks 中列出不变性断言；涉及实际行为变化时必须另写 Delta Specs。**在 G6 经过适用验证并且源码行为确实被采用前，不能提前 Archive 并声称完成**。

## 5. G7 后续 Change 切分与安全边界

| 独立 Change 候选 | 当前事实与上线要求 |
| --- | --- |
| `refactor-local-component-boundaries` | 旧 Task 命名源码的功能名迁移、公共代码复用、模块化，保持 Legacy Runtime 持久标识的可验证兼容 |
| `replicate-omop-to-fabric` | 本地 PG 只读一致性快照 → 现有 Azure Blob → Fabric Pipeline 调用 Notebook → OneLake Delta；先 Person/Visit 双表 MVP，具备 Manifest、对账、幂等及独立读回，**不要求首个 MVP 一次建齐 Bronze/Silver/Gold** |
| `ingest-fhir-to-fabric` | 独立 FHIR R4 Patient/Encounter 来源 Batch、Reference、Source Identity、失败重放；不得凭相似字段臆断跨源同人 |
| `ingest-hl7v2-to-fabric` | HL7 v2 ADT 接入/ACK/去重；**部署 Mirth Connect 前明确发行版、维护/许可、成本及安全支持**，不假定免费官方最新版可以直接复用 |
| `integrate-lineage-reporting` | 实际 Airflow/Spark Dataset/Job/Run 证据；已有 A3/A4 分项 Smoke 不等于完整业务血缘 |
| `publish-public-showcase` | 第一版只读静态证据网站可提前基于 Local DP 历史 Run 上线，显示采集时间/SHA/Run；**不等于实时 Portal**、也不匿名暴露 Airflow/Marquez/Fabric Workspace 管理面；真正交互入口另立安全 Change |

Condition/TASK005 状态为**业务开发暂缓，原 STEP00 READ-ONLY 就绪及历史记录保留**；重新排序不等于删除历史或自动否认已有组件实现。

## 6. PR 与证据账本（开始执行后逐项更新）

| 批次 | 包含 Gate | GitHub 实施要求 | 当前结果 |
| --- | --- | --- | --- |
| Plan 更新 | 本文件及相关只读文档对齐 | 文档 Branch/PR、相对链接检查、审查不变事实 | **文档修改中；不是 CLI PASS** |
| Bootstrap | G0–G4 | 官方 CLI 固定版本、初始化/配置/CI/Agent 接力；不混入业务代码移动 | **NOT STARTED** |
| 首个 Change | G5 | `relocate-local-data-platform` Proposal/Design/Tasks/Static Validate，单独审查 | **NOT STARTED** |
| 物理迁移 | G6 | 分组件/切片 PR；路径兼容、CODE Map、测试；Live Gate 单独授权 | **NOT STARTED** |
| 后续能力 | G7 | 分领域 Changes，实际测试 + PR/Run + 独立读回后才归档 | **NOT STARTED** |

**实际完成声明必须填写**：实施日期、实际 Main 与 PR HEAD 完整 SHA、OpenSpec CLI/Node 版本、Workflow Run ID、检查参数/输出、目标环境（如有）、Batch/export_id（如有）、持久化独立读回（如有）及未验证范围。未运行的 Gate 始终为 NOT STARTED，不推测 PASS。
