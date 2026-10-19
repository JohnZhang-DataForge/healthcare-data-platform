---
status: historical
scope: openspec-g0-g7-rollout-implementation-plan
last_verified: 2026-10-18
source_sha: a5047ea41e50837351965fbee0ba053ac61d3a50
evidence: []
---

# OpenSpec 正式实施与 Data Platform 迁移计划（G0–G7）

> **历史 G0–G7 Bootstrap 计划 / 实际实施证据（2026-10-18）**：G0–G4 COMPLETE；原定 G5 先设计/G6 再迁移的顺序与后来用户批准的实际执行不同：PR #225–#227 先完成物理目录迁移，PR #228–#229 后补追溯 Change，**运行入口与 E2E 仍待验证**。本页保留原 G0–G7 原方案、固定 SHA/PR/Run 及失败记录，**不再是当前实施任务来源**；请改读 [relocate-local-data-platform](../../../openspec/changes/relocate-local-data-platform/tasks.md)、[enforce-openspec-change-gate](../../../openspec/changes/enforce-openspec-change-gate/tasks.md) 及 [PROJECT-STATUS](../status/PROJECT-STATUS.md)。下文原将来时表格是历史原计划，不自动授权未来开发。
>
> [OpenSpec 接入架构设计](../../architecture/design/OPENSPEC-ADOPTION-DESIGN.md) 管原则和权威边界；[OpenSpec Readiness](OPENSPEC-READINESS.md) 管实施前核查；[Data Platform V2 设计](../../architecture/design/DATA-PLATFORM-V2-MIGRATION-DESIGN.md) 管目录兼容和回滚细节；[项目 CURRENT/NEXT](../status/PROJECT-STATUS.md) 管总体进度。禁止将这些文件变成相互矛盾的第二份 G0–G7 计划。

## 1. 不变原则与范围

- **仓库根目录 `openspec/` 与 `documents/` 平级**；`documents/` 保留架构、系统导航、工程规则及运维，`openspec/specs/` 只维护经核实的当前行为，`openspec/changes/` 管变更意图/设计/任务/增量要求。`contracts/`、源码、GitHub PR/Run、独立运行读回各自保持事实权威。
- STEP09 的 G0–G4 是 **OpenSpec 开发治理体系 Bootstrap**，**不移动业务源码、不自动创建 Current Specs、不触发 Live Runtime**。原设计规定 G5 先审核 Change、G6 再物理迁移；实际因用户授权调整顺序，PR #225–#227 在正式 Change 建立之前已合并。现通过 Active `relocate-local-data-platform` 补全**事后追溯**记录，原 G5 事前审核未发生，G6 运行验收仍未完成；G7 是未来持续运营。
- **不把历史 `docs/` 全量导入 OpenSpec**，历史证据由固定 Git Snapshot 保存；旧 PR #164 已关闭、未合并，不能复制其旧配置。
- 只复用 GitHub PR、GitHub Actions 与 Self-Runner；OpenSpec 不替代调度器、访问控制、分布式锁或数据提交验证。
- 对所有 **新增维护代码**，严禁 `taskNNN` / `stepNNN` 等开发编号作为组件目录、文件、函数、类、DAG ID、SQL、正式 Shell、镜像、Manifest、Workflow、测试及 Contract 的语义名称。开发计划、OpenSpec `tasks.md` 步骤号、Issue/PR、Run/日志与历史证据可以保留阶段编号。唯一命名权威：[Code Organization & Naming](../development/CODE-ORGANIZATION-AND-NAMING.md)。
- 旧 `task004` 路径、Python 导入、DAG/镜像、`etl.task004_*` 数据库对象、Batch/Manifest/Claim/Fingerprint 与冻结镜像 Digest **不得在纯目录迁移时批量重命名或更改行为**；这些另由 Modularization Change 管理。
- 共享 K8s/Airflow/Spark/PG/S3/Azure 操作需按 [Safe Operations](../operations/SAFE-OPERATIONS.md) 与 [Session Coordination](../development/SESSION-COORDINATION.md) 取得**针对具体操作的独立授权**。本计划本身不授予任何 Runtime 权限。

**2026-10-18 命名决策 D-07 与小型试点**：未来 Local DP 源码根目录正式为 `local-data-platform/`；先通过独立、docs-only 的 `adopt-local-data-platform-naming` Change 演练 Proposal → Design → Tasks → PR/CI → Archive。该练习不替代原计划 G5 的 `relocate-local-data-platform` 迁移设计审核，也不提前开始 G6。下面 G3 的 `data-platform/**`、历史负向测试及旧门禁**全部是当时真实证据**，不得批量改写成新路径已 PASS；G6 前需要对 CI/Checker/CODE Map/迁移审批模型做新的显式修改和正反测试。

## 2. 单一阶段定义（G0–G7）

| 阶段 | 内容及正式交付 | 验收门槛 | 范围限制 |
| --- | --- | --- | --- |
| **G0 — 基线与前置检查** | 从实施时最新 Main 检查实际文件树、`AGENTS.md`、命名和 CODE Map CI、OpenSpec 现状、未合并 PR；确认 Node 与官方 OpenSpec CLI 版本/支持命令，固定准确 SHA | 输出 Repository SHA、Node/CLI 版本需求、原始 Workflow 与冲突清单、旧 PR #164 CLOSED/NOT MERGED 的审计结果 | 只读，不安装/迁移/执行 Runtime |
| **G1 — 官方 CLI 初始化** | 在仓库根目录用经过验证的 CLI 版本初始化标准 `openspec/`，记录实际生成结构与所选 AI 工具集成策略 | 官方 Init 成功；准确记录 CLI 版本、Node 版本、源 SHA 和生成文件；未生成过时 `docs/` 链接 | 不迁移业务文件；不将 CLI 文件存在等同 PASS |
| **G2 — 项目配置与治理对齐** | 最小 `openspec/config.yaml` 使用默认 `spec-driven`；引用 `AGENTS.md`、`documents/README.md`、当前 Status 和命名/安全规则；按已确认优先级同步项目状态 | 配置字段通过实际 CLI/Schema 校验；规范中只有一个权威入口；可用最小/空 Current Specs；明确 Condition 暂缓 | 不复制 `documents/`、`contracts/` 或历史全文 |
| **G3 — 静态 CI 集成** | Healthcare PR 集成 OpenSpec Validate（实际参数按版本确认）、文档链接/Schema 检查；扩展代码命名 Workflow 与检测器覆盖将来的 `data-platform/**`，并为纯历史移动设计受限兼容例外和单元测试 | 正向/负向用例及目标 PR SHA 的 CI 实际 PASS；新增 Task/Step 命名仍被拒绝；无任意 Shell/集群凭据要求 | **此阶段只准备检查规则与测试，绝不搬源码、无限放宽例外或执行 Runtime** |
| **G4 — Agent/PR/Self-Runner 流程接合** | 将 Explore→Proposal/Design/(适用的 Delta Specs)/Tasks→PR→Static/Test→适用的独立 Readback→Sync/Archive 的责任与接力固定；验证跨 Session 可由 Git/Change/Run 恢复；复用已有三轮失败停止规则 | 能演示不触及业务的 CLI/Change 校验和 PR 工作流；PR/Run 记录准确 SHA、失败方案、下一安全动作；确认何时允许 Archive | 不自建 Agent 调度器/锁服务；三轮停止是开发约束，不冒充已自动强制的 Runner 功能 |
| **G5 — 首个真实 Change 的设计/审核** | 创建 `relocate-local-data-platform`，只选一个小范围物理迁移切片；编写 Proposal、Design、Tasks，明确旧路径清单、兼容层、回滚和回归门禁；纯 Refactor 的 `skip_specs: true` 需经当前 CLI 实验确认 | Change Validate 成功、PR 审核范围/风险/回滚；针对旧 NEW_ONLY Person/Visit 的可观察行为定义不变性断言；**本阶段不移动源码** | 不进行 Task004 语义改名、公共基类重构或 Fabric ETL；不凭空编造 Delta Specs |
| **G6 — Data Platform 源码物理迁移** | 根据 G5 已审查 Change，按组件逐 PR 移入 `local-data-platform/`；先静态路径/引用兼容，再单独安排运行入口切换及必要授权的回归 | 新旧路径映射、CODE.md、CI、Import、DAG、GitSync、Docker COPY/Context、SparkApplication、Contract/Manifest、历史 Batch SKIP 及必要独立读回均与本切片验收相符；回滚可行 | **物理迁移 ≠ 模块化完成**；只有获批准且资源空闲时才进行 Live Gate |
| **G7 — 后续持续开发** | 独立 Changes 处理模块化、PG OMOP→Fabric、FHIR→Fabric、HL7 v2→Fabric、Lineage、公开只读 Showcase；按当前实际证据 Sync/Archive | 每个 Change 分别验证、PR/Run 与业务读回绑定；只有已核实且采用的行为进入 Current Specs | Condition/Procedure/Drug 和 UPDATE_ONLY/MIX_DATA 不在本阶段自动启动；Mirth 许可及门户安全单独决策 |

**Gate：G0–G4 结束后即可使用 OpenSpec 处理后续变更，无须等待全部 V2 Relocation。** G1–G4 可作为一个或多个独立 Bootstrap PR；G5/G6 的业务源码 Change **不得混入 Bootstrap PR**。单个大型 Relocation Change 可用多个有界 PR 实施，但每个 PR 要有对应具体切片、目标 SHA、回退、测试与状态；避免长期无法归档。

## 3. G3 命名 CI 与 G6 迁移特例

**G3 实施前问题（历史基线，已由 PR #218 修复）**：当时 [Workflow](../../../.github/workflows/code-component-naming-check.yml) 的 `pull_request.paths` 和 [Checker](../../../.github/quality/scripts/check_new_code_names.py) 的 `ROOTS` 尚未覆盖 `data-platform/`，仅凭 `git diff --no-renames --diff-filter=A` 无法安全区分部分旧文件纯搬迁和违规新增。**当前 Main 已覆盖 `data-platform/**` 并启用在 Base 预批准、内容 Blob 严格一致的 legacy 搬迁审查；见本节 G3 完成证据。**

G3 必须：

1. 在 PR Trigger 与 Checker 新增 `data-platform/**` / `data-platform/`，并按搬迁后 CODE Map 权属同步检查器和相应测试。
2. 设计受限的 legacy relocation 例外：源文件必须存在于明确的 Base SHA；源、目标路径有审查过的映射；内容 Git Blob SHA 完全一致或显式证明仅改变必需路径兼容；所有新写入内容仍按新代码规则检查。**不允许依靠名字或目录前缀无条件豁免**。
3. 加入至少这些负向测试：新建 `data-platform/scripts/task999/step03.sh` 必须失败；历史文件搬迁过程中夹带新 `taskNNN` 文件必须失败；修改过的 Legacy 文件不能借纯搬迁规则绕过审查；合法组件/功能路径必须通过。
4. 迁移兼容豁免须**限定到实际 Change/PR 的固定文件列表及准确 SHA**；试点验收后清理临时宽松策略，不永久豁免整个 `data-platform/` 目录。

**G3 已落实的受限搬迁机制（2026-10-18，PR #218）**：

- 永久 [OpenSpec Static Validation](../../../.github/workflows/openspec-validation.yml) 使用 GitHub-hosted Node 22、CLI 1.14.3；官方 Schema / 中文上下文、`validate --all --strict`、临时 Change 正反用例验证。当前仓库 **0 个 Current Specs、0 个 Active Changes**，空集 PASS **不代表业务 Specs 验收**。临时测试 Change 只在 Runner 的临时目录创建。
- [Component Naming Workflow](../../../.github/workflows/code-component-naming-check.yml) 和 [Naming Checker](../../../.github/quality/scripts/check_new_code_names.py) 检查 `data-platform/**`；[CODE Map Checker](../../../.github/quality/scripts/check_component_code_map.py) 将未来目录纳入现有组件文件所有权与路径链接校验，仍要求对应 CODE.md 在同一 PR 同步。
- 精确审批清单 [`.github/legacy-relocations.json`](../../../.github/legacy-relocations.json) 初始为空。需**先经独立 PR 审核并合并**具体 `old_path / new_path / source_commit / blob_sha` 映射（完整 SHA）；下一份纯移动 PR 的 Naming Gate **仅从其 Base Commit 读取已批准名单**，验证 Source Commit 是 Base 祖先、源文件在该 Commit 与 Base 内容 Blob 相同、目标仅为 `data-platform/<old_path>`、旧路径已在 HEAD 删除、目标 Blob 与源 Blob 完全一致。PR 内自加豁免、带修改搬运、夹带新的违规路径均失败，任何变更行为不得冒充纯物理搬迁；G6 使用前另作逐文件审查。清单必须在迁移完成后收口清理，不能保留无限期豁免。
- 正向临时 Change 返回 Exit 0，缺少 Scenario 的负向 Change 返回 Exit 1；新的 `data-platform/scripts/task999/step03.sh` 以及混入历史搬迁的新 Task/Step 名称均由单元测试拒绝。证据为 [OpenSpec Run #39148008534](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148008534)、[Naming Run #39148008629](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148008629)，目标 HEAD `3f39781167dde125c806a44838ccf7e1f0060e74`。未执行 K8s、业务 SQL、Terraform 或 Self-Runner。
- **G4 进入条件（G3 已满足）**：PR #218 已合并 Main，最终 PR HEAD `39972abf19535d892bc5759fd792187c89f29d67` 上的 [OpenSpec Run #39148192774](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148192774)、[Component Naming Run #39148192762](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148192762)、[Documentation Relative Links Run #39148192871](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148192871) 三项 SUCCESS，Main Merge SHA `b28660a28e7c9d6b72cc64ae19d3584d7f6f52e9`。G4 已隔离 Self-Runner 对已删除旧 `docs/BASELINE.md` 的历史依赖，新增独立只读 PR 接力；不直接运行旧跨仓流水线。

G6 中无需立即 Rename 已验收的旧 `task004` 文件。应先保留兼容入口/适配层，以实际依赖审计为准处理不同路径；真正语义重命名留待独立 Change。

## 4. G5/G6 首个 Change 的实施边界

**原始 G5/G6 方案与实际偏离**：命名试点已经按 OpenSpec 归档；实际经用户同意，先将 393 个业务文件独立备份到 Healthcare-Specs（PR #2），再将整体源码迁入 `local-data-platform/`（Healthcare PR #225），修复文档/源码地图（#226）并将质量工具收归 `.github/quality/`（#227）。这些发生时**未创建正式 G5 Change**；PR #225 的组件质量检查失败但仍合并。事后由 [Active 迁移 Change](../../../openspec/changes/relocate-local-data-platform/tasks.md) 记录原 PR/SHA/Run 与尚未完成的 Import、DAG、GitSync、Docker、Spark、Workflow、E2E 安全门槛。上文原 G5 先审批/G6 分片实施的流程仍作为**历史原计划**保留，不声称其已被遵守。

**原 G6 前置 CI 迁移 Gate（历史设计，未按此顺序执行）**：现有 [Naming Workflow](../../../.github/workflows/code-component-naming-check.yml)、[Naming Checker](../../../.github/quality/scripts/check_new_code_names.py)、[CODE Map Checker](../../../.github/quality/scripts/check_component_code_map.py) 和 [Relocation Approval](../../../.github/legacy-relocations.json) 中的 `data-platform/**` 只代表历史通过检查的候选。先单独适配 `local-data-platform/**` 并验证合法、违规新增、旧 Blob 搬迁及混合拷贝场景，再审迁移清单。不得默认两套根目录长期并存。


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
| Plan 更新 | 本文件及相关只读文档对齐 | [PR #209](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/209) 已合并，[Documentation Relative Links Run](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39136532662) SUCCESS | **COMPLETE（仅文档）** |
| G0 静态基线审计 | G0 | [Baseline Audit](OPENSPEC-BASELINE-AUDIT.md)：双仓 SHA、开放 PR/过时 PR、官方 CLI/Node 前提、既有 CI/Workflow 缺口 | **COMPLETE（2026-10-18，只读；目标环境 Node/npm 未实测）** |
| 官方 CLI Bootstrap | G1 | GitHub-hosted Node `v22.23.3` / npm `10.9.9`，Registry `@fission-ai/openspec@1.14.3`；[首次 CLI Init Run #39144400763](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39144400763) 与[已提交文件的再次 Init Run #39144489059](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39144489059) 均 SUCCESS；生成 `openspec/config.yaml`、`specs/.gitkeep`、`changes/archive/.gitkeep`，无 AI 工具集成 | **COMPLETE（GitHub-hosted Runner 的官方 CLI Init，非 Self-Runner 安装）** |
| 中文项目配置 | G2 | `openspec/config.yaml` 采用 `spec-driven`、简体中文描述及英文结构保留约束，引用现有文档和安全命名规则；[官方 CLI 配置注入 Smoke Run #39145378211](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39145378211) SUCCESS，四项指令注入断言 PASS；不包含业务 Specs/Changes | **COMPLETE（配置/治理，未实施业务 Change）** |
| G3 静态 CI | G3 | [PR #218](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/218)：永久 [OpenSpec CI](../../../.github/workflows/openspec-validation.yml)、命名检查及 CODE Map 新旧路径覆盖、受限预授权搬迁白名单；[OpenSpec Run #39148008534](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148008534) SUCCESS，[命名 Run #39148008629](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39148008629) SUCCESS；功能验证 HEAD `3f39781167dde125c806a44838ccf7e1f0060e74`；G3 文档提交后仍须检查最终 PR HEAD 的所有触发 CI | **COMPLETE — PR #218 MERGED，合并 SHA `b28660a28e7c9d6b72cc64ae19d3584d7f6f52e9`** |
| Agent / PR 静态接力 | G4 | [生命周期](../development/OPENSPEC-DEVELOPMENT-LIFECYCLE.md)、Healthcare [PR #220](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/220)、Self-Runner [PR #136](https://github.com/JohnZhang-DataForge/Self-Runner/pull/136) 已合并（SHA `ffd0eccecbf0148183b956e6e4416d4b8d99002b`）；Policy CI [39149481844](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39149481844) SUCCESS，实际跨仓静态绑定 [Run 39149531730](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39149531730) SUCCESS（Controller `3b40533fcf9ec63b15f9c51bf84c7e400149d43c`，Healthcare PR #220 HEAD `f6859911a58dcae6396e359244e282799346d051`）；临时请求已在测试分支删除，未进入 Main | **COMPLETE — Healthcare PR #220 MERGED `10d65bb8e7a83ca5a308a738201bbf6d82669d22`；Self-Runner PR #136 MERGED `ffd0eccecbf0148183b956e6e4416d4b8d99002b`** |
| G4 终验补充 | G4 | 最终 Healthcare PR #220 HEAD `7b1fc6e6308a0fa5821b418f76ee1da7accf7b2e` 上 [OpenSpec Run #39149670066](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39149670066) 与 [Documentation Links Run #39149670014](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39149670014) 均 SUCCESS；已合并的 Self-Runner Main 上受控请求 controller commit `ac6873aa31cafa4b554162aa03a3fcbde09efbd0`，[实际跨仓 Run #39149690050](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39149690050) SUCCESS，Artifact `openspec-pr-handoff-39149690050` 保存身份与静态校验证据，目标 SHA 与最终 Healthcare PR HEAD 一致；临时请求已删除，不在 Self-Runner Main | **COMPLETE / STATIC ONLY，未执行任何业务 Runtime** |
| 首个源码迁移 Change（命名试点另行追踪） | G5 | [`relocate-local-data-platform`](../../../openspec/changes/relocate-local-data-platform/tasks.md) 已事后补建 Proposal/Design/Tasks；原 PR #225–#227 **没有**事前 Change 审核，正在通过独立追溯 PR 做 OpenSpec Static Validate | **RETROSPECTIVE ACTIVE；不宣称事前门禁满足** |
| Naming docs-only 试点 | G5 前置演练 | `adopt-local-data-platform-naming` [PR #223](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/223) 已合并 Main `d97f7bb7babe1468cc2fc115e511c836360f721a`；严格校验 [OpenSpec Run #39155840396](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39155840396) SUCCESS，文档链接 [Run #39155840375](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39155840375) SUCCESS，均绑定最终 PR HEAD `f16baba0e993c5f4d92d1aed2b3eb5ec31fcf00f`；[Archive PR #224](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/224) 以本次提交合并 Main 为归档生效 Gate | **NAMING PILOT VERIFIED；ARCHIVE 随 PR #224 合并生效；不涉及 G5 源码迁移设计或 G6** |
| 物理迁移 | G6 | Healthcare [PR #225](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/225) 文件搬迁（组件 CI FAIL）、[PR #226](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/226) 文档/CODE Map（CI PASS）、[PR #227](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/227) 质量工具整理（CI PASS）；备份 Healthcare-Specs PR #2。运行入口、Import、镜像/DAG/Spark 与真实 E2E 仍需要后续独立验证与授权 | **PHYSICAL TREE COMPLETE / RUNTIME NOT VERIFIED** |
| 后续能力 | G7 | 分领域 Changes，实际测试 + PR/Run + 独立读回后才归档 | **NOT STARTED** |

**实际完成声明必须填写**：实施日期、实际 Main 与 PR HEAD 完整 SHA、OpenSpec CLI/Node 版本、Workflow Run ID、检查参数/输出、目标环境（如有）、Batch/export_id（如有）、持久化独立读回（如有）及未验证范围。未运行的 Gate 始终为 NOT STARTED，不推测 PASS。
