---
status: active
scope: development-workflow
last_verified: 2026-10-16
source_sha: 63524cc244b64f784ff0e7887caa8e63fed5049f
---

# Healthcare 开发工作流（Development Workflow v1）

> **角色**：给所有 AI/Agent 和开发人员提供可执行的开发路线，不是新的自动执行器、权限授权或运行环境证明。安全及规则冲突参见 [Agent 规则](AGENT-RULES.md)，测试/证据判定参见 [测试与验收](TESTING-AND-EVIDENCE.md)。
>
> **核对基线**：Healthcare Main `63524cc244b64f784ff0e7887caa8e63fed5049f`；Self-Runner Main `8f8cb877887540cbed697260c3e8154e218a49c7`（2026-10-16 GitHub 源码只读核对）。此处是**代码存在与静态结构核验**，不是本轮 Runtime 复验。实际执行前须重新查看当前 Main / Workflow。

## 1. 责任与真正的开发主线

**当前工程模式：Source-first + Workflow-driven。** Agent 直接维护 Git 中的正式业务源码、测试和配置；GitHub Actions / Self-Runner 负责受控检查、构建、必要时部署或执行，并保存 Run/Artifact 证据。Airflow 仍负责编排实际数据处理。Shell 只用于确有需要的 Workflow 步骤、现有运维脚本或人工诊断，不再默认承担业务源码生成。

| 系统 | 保存什么 | 不负责什么 |
| --- | --- | --- |
| [Healthcare Repo](https://github.com/JohnZhang-DataForge/healthcare-data-platform) | Airflow DAG、PySpark、Python Apps、SQL、Contracts、K8s 定义、Terraform 源码、Tests、正式 Shell、`documents/` | 不把业务实现永久放在 Runner 控制仓库 |
| [Self-Runner Repo](https://github.com/JohnZhang-DataForge/Self-Runner) | GitHub Workflow、受控请求、执行/验证辅助工具、跨仓绑定及 GitHub Run/Artifact | 不把 Runner 层测试或旧分支代码直接视为 Healthcare 已验收 |
| ARC `dw-runner-set` | 按选定 Workflow 运行临时 Job，签发执行结果、连接受控 K8s / 云资源 | 不是长期运行的业务 ETL Worker，也不自动继承宿主机 `/data` |
| Airflow/Spark/PostgreSQL/S3/Azure | 有明确部署与授权的实际业务运行/存储 | 不因 PR 或计划存在就自动部署 |

旧 `docs/` 已从 Main 退休。现行规范以 `documents/`、有效 Contract 和真实代码/验收证据为准；历史 Skill、固定宿主机路径和旧 `CURRENT/NEXT` 不能成为新开发指令。

**新代码命名为强制工程规范**：Task/Step 用于 PR/计划/证据，不用于新增源码、测试、正式 Shell、DAG ID 或镜像名；见 [Code Organization & Naming](CODE-ORGANIZATION-AND-NAMING.md)。现有 `task004` Import、SQL 表和冻结镜像必须按单独迁移计划保留兼容。

## 2. 日常开发闭环（一次一个有界 STEP）

```text
确认用户目标、动作授权与当前 main SHA
  → 阅读 documents + 当前代码/Contract + 相关真实验收
  → 定义最小 STEP、验收标准、数据/环境副作用
  → Healthcare feature 分支修改 canonical source 和测试
  → 静态检查 + 单测 + 负向/幂等性检查（按风险）
  → 需要 Runtime 时：选择现有 Self-Runner Workflow，固定 Healthcare SHA 与输入
  → 受控执行并读回真实状态；失败修同一步，不扩大范围
  → 复查 PR 当前 HEAD SHA 与证据，Review / Merge Healthcare PR
  → 需要时复验合并后 Main（如 Airflow GitSync、实际代码 pin）
  → 更新已迁移文档的当前事实、关键证据及剩余工作
  → 下一 STEP 从最新 Main 开始
```

原则：
- 一个 STEP 要有输入、受影响文件、断言、允许副作用、退出/恢复方式和可验证的完成条件；不要以无限细分步骤替代业务目标。
- 在 Healthcare 仓库中直接修改模块源码、测试及配置，由适用的 Workflow 执行检查和受控验证。历史 Generator 若仍被现有代码依赖，仅维护兼容，不把这种生成模式复制到新组件。
- 确需新增 Shell 时按组件/功能命名（如 `scripts/omop/`），不创建新的 `scripts/taskXXX/`；维护旧脚本先检查其实际副作用。人工要求命令时提供单段可执行 Bash 和清晰结果，不额外生成永久 Shell 来包裹每个代码变更。
- 普通代码变更优先就近单测/契约测试；无需每次全量重跑旧项目或建设企业级复杂治理系统。
- 不因新任务擅自重放或覆盖已验收 Batch 与持久化数据；具体 CURRENT/NEXT 始终以 [Project Status](../status/PROJECT-STATUS.md) 为准。

**组件源码导航**：按功能读取 [Synthea CODE](../../systems/data-platform/synthea/CODE.md)、[Landing CODE](../../systems/data-platform/landing/CODE.md)、[Spark CODE](../../systems/data-platform/spark/CODE.md)、[OMOP CODE](../../systems/data-platform/omop/CODE.md)、[Airflow CODE](../../systems/data-platform/airflow/CODE.md)。通用静态工具、文档生成辅助和 [`config/local.env.example`](../../../config/local.env.example) 由 [Developer CODE](CODE.md) 维护。清单只提供源码入口，不代表可以重放已完成阶段。

## 3. 如何正确选择 Workflow（先核对再复用）

**每轮不要凭 Workflow 名字决定行为**。到 Self-Runner `.github/workflows/` 读取该文件的 `on`、branches、paths、`workflow_dispatch.inputs`、`runs-on`、checkout `repository/ref`、参数校验、脚本、资源操作与清理策略。Workflow 在 Git 上“存在”不等于对当前代码或目标环境已验证。

| 仓库中的真实 Workflow | 已核对能力 / 重要局限 | 适用策略 |
| --- | --- | --- |
| [Generic Task Executor](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/generic-task-executor.yml) | Self-Runner 内 `scripts/ci/tasks/<task>/<step>.sh`；手工 `validate/execute`；push 读取受控 `requests/taskNNN/stepNN/run-NNN.json`；执行代码要求手工触发且在 Main | 是 Runner 仓库内执行器，**不是**可以动态运行 Healthcare 任意脚本的跨仓引擎 |
| [Generic Task Executor V2](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/generic-task-executor-v2.yml) | 同样运行 Runner 仓库本地脚本；push 读取 `config/tasks/**`，但现有校验仅放行 `task004/step02`，手工模式另有模式/分支约束 | 不得声称通用放行所有 TASK |
| [M2 Generic Healthcare PR Readonly V4](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/cross-repo-generic-pr-v4.yml) | 固定 `migration-readonly.json` 的 feature push；策略验证、checkout Healthcare **指定 SHA**、核查远程 HEAD；无任意业务执行 | 是跨仓 PR 绑定的只读历史验证范例，并非当前所有 TASK 的动态执行入口 |
| [Azure-Infra-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) | Main 手工触发；component/environment/operation 白名单；`plan` 默认但确实也提供 `apply`；checkout Healthcare `main` 后在日志记录实际 SHA；不提供 destroy 入口 | `plan` 也需核对状态文件和云认证；**已有 apply 选项不等于获得本次 Apply 授权** |
| [Synthea NEW_ONLY Independent Request](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/synthea-new-only-run-new-request.yml) | 手动触发，但源码采用固定历史 Healthcare SHA 和固定镜像 digest，并进行实际生成/读写流程 | 是具体里程碑 Workflow；未经审查和授权禁止当普通 smoke 重跑 |
| [Healthcare build workflows](../../../.github/workflows) | 有镜像构建、Contract 检查、GHCR 发布等；许多 `task004-*` 属于历史里程碑 | Build PASS 不是 Spark/数据库 Runtime PASS |

**重用优先级**：当前现有、适合本轮副作用/版本/输入的 Workflow → 轻量调整受控 Request / 复用固定入口 → 确实缺能力再申请最小新 Workflow。禁止因为容易创建 YAML 就每次建一个临时业务执行器。跨仓变更必须分别处理两仓源码、Review、SHA 与 PR；不要把 Self-Runner 的一个成功 Run 当成两个仓库都已更新。

**特别警示**：“readonly” Workflow 也可能创建临时 ConfigMap、Pod、Job 后清理；例如 [Landing readonly discovery](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/landing-batch-discovery-readonly.yml)。要检查**资源实际副作用**，不能只看名称。

## 4. 跨仓 SHA/PR 绑定

对需要运行 Healthcare 分支代码的受控验证，准确绑定以下字段（字段名称必须以**所选 Workflow 当前 Schema** 为准）：

| 信息 | 最小要求 |
| --- | --- |
| Healthcare 身份 | `target_repo`、目标分支或 Ref、**40 位目标 HEAD SHA** |
| 审查身份 | Healthcare PR 编号（如该 Workflow 需要）和对应的 Base |
| 操作范围 | 任务、步骤、`validate` 或真实授权的动作、固定执行入口 |
| 数据绑定 | 如适用，Batch ID、Manifest URI+SHA、目标镜像 Digest、环境、预期读回 |
| 执行证据 | Self-Runner Workflow 名/版本、GitHub Run URL/ID、实际 Checkout SHA、PASS/FAIL、独立后置读回 |

不要从例子照搬 JSON，不能通过请求参数注入自由 Shell 路径、Namespace 或任意 kubectl。某些旧 Workflow `ref` **写死历史 SHA**；某些如 Azure 工作流直接 checkout `main`，因此要使用**日志实际 checkout SHA**，不能假定它必然等于发起操作之前观察到的 HEAD。

如果 Healthcare PR 的 HEAD 变动，旧分支 PASS 不覆盖新 HEAD；GitHub Actions `success` 是该 Workflow 的结论，不自动等于业务功能 E2E 完成。合并后如 GitSync、部署控制引用 Main，需要明确进行匹配 Main SHA 的复验或记录其尚未执行。

## 5. 测试与验收分级

按照 [测试与证据策略](TESTING-AND-EVIDENCE.md) 选择最低足够又不漏核心风险的层级：Static / Unit / Contract → Packaging / Image → Controlled Runtime → E2E + Independent Durable Readback。明确标记 **PLANNED、CODED、STATIC_PASS、RUNTIME_PASS、E2E_ACCEPTED**，未运行的不声称通过。历史 Run 不能替代不同 Source SHA 的新验收。

完整读回通常关注 S3 对象/Manifest SHA、Airflow DagRun/task 状态、SparkApplication driver/结果、PostgreSQL Ledger/Stage/Row Counts / FK / Idempotent replay；按实际 STEP 缩小范围，不把全部检查强行分配给文档修改。

## 6. 权限、授权、环境安全

- 文档编辑、静态验证和 PR Review 不许可额外的 Runtime 动作。每次真正运行 Self-Runner 前先检查脚本是否在集群/数据库/S3/Azure 产生实际副作用。
- 未授权不做 Terraform `apply`/`destroy`、数据库业务 DML/COMMIT、S3 删除或覆盖、K8s 破坏性操作、历史已完成批次重放；不能绕过 Writer Fencing、批次 Claim 或任何 Secret Gate。
- **Terraform Plan 非无副作用的纯本地命令**：可能访问云端、读取并锁定远程 State；需确认本轮允许的云端读取范围。Apply/Destroy 必须单独授权。
- 共享 Airflow/Spark/Kubernetes 真实执行须检查并行 Session/Run/Job/资源，并遵守当前 [跨 Session 协调规则](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md)。CLI 权限或 GitHub dispatch 可用不代表业务授权。
- Worker 路径与 Runner Pod 文件系统不同，不能把本地 `/data` 直接当作临时 Runner 容器路径；不得打印 Secrets 或将 Azure/PG 凭据写进 Git。

## 7. 合并、失败、交接与后续变更

- PR 至少写清：本轮 STEP、代码/文档改动、前置条件、是否触碰冻结范围、Workflow/测试链接、失败风险、是否有资源写入。只有完成所声明的验收才可写 PASS。
- 失败时查明是编译、策略 Gate、Runner、环境、业务逻辑还是后置读回；修同一个 STEP 后运行必要的复验。未知 Writer 状态一律独立只读审计，不盲目重试。
- **同一问题最多连续调试 3 轮**：每轮指针对同一故障的一次有依据的“分析 → 修改 → 验证”；验证失败后计入一轮。若第 3 轮仍未解决，或更早已明显没有新证据，Agent 必须停止自动修改和重复触发 Workflow，不得通过改名、拆分步骤或重开 Session 规避上限。停止后应**优先在当前开发 PR 的 Conversation 评论区**简要记录三轮修改和结果、失败原因或尚未证实的假设、当前 Branch/HEAD SHA、Workflow Run/Artifact 链接及下一步建议；尚无 PR 时记录在对应 GitHub Issue。详细执行日志保留在 Workflow/Artifact 中，不新建重复 Handoff 文档。交由用户决定是否继续或另开 Session；**新 Session 必须先查看既有 PR/Issue 调试记录并沿用同一问题的失败轮数，不得从零重试**。不同的独立问题分别计数；成功后正常完成验收，不强制停工。
- 复杂的 STEP 需要**可恢复的短交接**：Repo+PR+完整 HEAD SHA、任务目标、已通过/未通过的具体 Run、当前真实资源/Batch、未完成任务、下一最小动作、明确禁止/需批准的操作。能在现有状态/PR/证据里表达的，不重复新建巨大 Handoff Markdown。
- 任务状态只更新对应当前权威位置；新 `documents/` 模块 **仅在迁移表已经 ACTIVE 时**承接当前事实。旧 `docs/` 的历史 NEXT 不需要每轮修补。
- 将来使用 OpenSpec 时：Proposal/Design/Tasks/Delta Specs 管需求演进，本文件继续管代码执行、Self-Runner、测试、安全与交接；不为此阶段提前创建 `openspec/`。

## 8. 多 Session 协作与接力（简化）

统一使用 [Session Coordination](SESSION-COORDINATION.md)：OpenSpec 引入前由 PR/Issue 的 Done/Next/SHA/Run 交接；OpenSpec 引入后由 Change/Tasks 负责变更进度。**不要新建每次 Session 的 Handoff 文件**，共享 K8s/PG/Cloud 操作前还必须核对实际资源与独立授权；详细门槛见 [Safe Operations](../operations/SAFE-OPERATIONS.md)。
