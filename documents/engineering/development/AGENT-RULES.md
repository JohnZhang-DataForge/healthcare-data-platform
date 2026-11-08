# AI / Agent 开发与安全规则（所有 AI 工具通用）

> **状态：ACTIVE · 版本：v1 · 生效范围：Healthcare 主仓库 · 2026-10-16**
>
> **定位**：用于根目录 `AGENTS.md` 引导的统一规则；不因 AI 工具、会话或模型不同而改变。历史 Skill 只供查证，现行安全门槛以本规则与 [Safe Operations](../operations/SAFE-OPERATIONS.md) 为准。

## 1. 开工前必须确认

1. 读取根 `AGENTS.md`、`documents/README.md` 和本规则；按任务沿 [Active OpenSpec Changes](../../../openspec/changes/) 和组件 README/CODE 进入相关 `tasks.md`，如需追溯旧文档迁移再查 `documents/engineering/migration/MIGRATION-STATUS.md`。`PROJECT-STATUS.md` 仅为兼容导航，不是第二份 CURRENT/NEXT。
2. 查询当前 `main` **准确完整 40 位 SHA**，确认本轮工作范围、已有 PR/未合并代码、相关模块及冻结 Contract。
3. 只读查看实际代码/配置、已合并 PR、测试和最终验收；旧 Handoff 的 CURRENT/NEXT 只能代表其记录时点。
4. 明确改动类别：**仅文档 / 代码 / Workflow / Terraform plan / 运行环境操作**；逐项列明副作用和是否需要授权。
5. 源代码、业务契约、实际运行状态、设计意图必须分开：`PLANNED`、`IMPLEMENTED`、`STATIC_PASS`、`RUNTIME_VERIFIED`、`DEPLOYED`、`E2E_ACCEPTED` 不可混用。

工作步骤及流程细节以 [Development Workflow](DEVELOPMENT-WORKFLOW.md) 为准，测试结论等级以 [Testing & Evidence](TESTING-AND-EVIDENCE.md) 为准。两文档解释本规则而不放宽安全边界。

## 2. 开发方式：小步、可重放、可验证

- 一次交付一个边界明确的 STEP；代码和测试以 Git 正式文件为准，执行与验证优先复用受控 Workflow。仅在确需人工操作时使用 Shell，不通过 Shell 默认生成新源码。
- 开发/改动逻辑必须同步覆盖有意义的正常、失败、重复运行或幂等性测试；优先使用现有公共组件，避免各模块复制相同能力。
- **新的业务 Runtime 脚本只放组件功能目录**（例如 `scripts/omop/verify_condition_fk.sh`），禁止新增 `scripts/taskXXX/`；历史 `scripts/task001–004/` 按原样保留以支持已验证运行与证据；用户需要单步 Shell 时给出**单个完整 Bash**，执行输出清晰使用 `#### ... OUTPUT BEGIN/END ####` 标识；不得假定旧宿主机目录会出现在 Runner 中。
- 不跳过失败步骤、不把 Mock/Static PASS 解释成 Live 验证；不为普通功能额外建设与需求无关的大型 CI、锁服务或平台。
- 当前已验收 Person/Visit、TASK001–TASK003 冻结范围及旧系统持久化数据不得因开发新功能而擅自重新生成、回放或写入。

**新增文件唯一归属（OpenSpec P1）**：新自动化测试 `.github/quality/tests/<system>/<component>/`；新静态质量检查 `.github/quality/scripts/`；Fixture `.github/quality/fixtures/`；人类技术说明 `documents/`。不能新建源码区 README/CODE/ARCHITECTURE/PUBLISHER，也不能在现存 `shared-data-engine/tests/`、`azure-fabric/**/tests/`、`local-data-platform/tests/` 或 `platform-portal/**/tests/` 新增自动化测试；这些目录只按原有精确路径作为过渡例外。Workspace Git Native Item 在真实根级 `*.Notebook` / `*.DataPipeline` / `*.Environment` / `*.Lakehouse`；Warehouse SQL/Writer 仍位于 `azure-fabric/warehouse/`。查看 [权威 Change](../../../openspec/changes/archive/2026-11-05-standardize-fabric-source-test-document-layout/tasks.md)，P1 不搬现有文件。

## 3. 新代码目录和命名强制规则

- **开发进度可以称 TASK/STEP，但新代码必须按组件/功能命名。** Python、DAG ID、Spark、SQL、镜像、K8s、正式 Shell、Workflow、Tests 的新增路径与公开标识符不允许 `taskNNN/stepNNN`。具体以 [Code Organization & Naming](CODE-ORGANIZATION-AND-NAMING.md) 为准。
- 现有 Task-named 代码及数据库/Contract/镜像持久标识**不批量重命名**；先有依赖清单、兼容回归与必要 Runtime 授权，再逐模块切换。
- CI 自动检查新建代码路径；代码内部的新标识符与职责归属由 Agent/Reviewer 复核。Task ID 只属于 PR/开发计划/历史验收。
- **源码地图强制同步**：凡组件源码文件新增、删除、移动或改名，必须在同一 PR 更新其 **对应系统的** `documents/systems/<system>/<component>/CODE.md`（Native Item 使用 Azure/Fabric 的唯一 owner CODE Map）；重要入口、职责、依赖变化也要审查并同步。已落地 [Airflow CODE](../../systems/data-platform/airflow/CODE.md)，并将混合 `apps/` 源码按唯一功能归属映射到 [Synthea CODE](../../systems/data-platform/synthea/CODE.md)、[Landing CODE](../../systems/data-platform/landing/CODE.md)、[OMOP CODE](../../systems/data-platform/omop/CODE.md) 及 Airflow CODE；CI 检查新增/删除/改名、唯一所有者及同 PR 维护；[Spark CODE](../../systems/data-platform/spark/CODE.md) 现也覆盖 Spark 源码、Contract 和模板，`contracts/`、`sql/`、`images/` 与 `kubernetes/` 也已按 Synthea/Landing/OMOP/Airflow 组件归属纳入 CODE.md 与 CI；不允许因为删除原导航 README 就把 Runtime 模板当作直接可 Apply 的资源。`scripts/` 和 `config/` 现已按业务所有者与 [Developer CODE](CODE.md) 维护；旧 Shell 可产生仓库源码、Pod、Job、S3、PG 写入或 Secret 变更，浏览 CODE.md 不构成运行授权。其它目录逐步接入。

### Fabric dbt 工程目录专用强制规则（2026-11-07）

- 创建/移动任何 dbt 项目之前必须读 [Fabric dbt 目录与准入](../../systems/azure-fabric/dbt/README.md)、真实 Main/CODE Map 和 [OpenSpec dbt Change](../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md)。未来统一归 `azure-fabric/dbt/<project>/`，首期 `hl7-canonical`，内部名 `hl7_canonical`。**现有可执行工程仍在 Local DP**，文档批准不等于源码已经迁移。
- 标准完整工程骨架和空目录 `.gitkeep` 为强制要求。**HL7 dbt 原生 `tests/` 狭义例外已通过受保护 [PR #815](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/815) 落地**，真实正向 [#816](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/816) PASS、负向 [#817](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/817) 被阻止，四项 Required 已恢复；允许严格限定的 `azure-fabric/dbt/hl7-canonical/tests/.gitkeep` / singular `.sql`，其他项目仍须独立治理审批。一般 Python 自动化测试仍仅放 `.github/quality/tests/`。
- 新的 `fhir-canonical` / `csv-canonical` / 共享业务 dbt 工程必须另走 OpenSpec 和唯一 Owner 审查；不允许自行另建 `azure-fabric/ingestion/`、Native 假目录或第二套 Canonical/OMOP 共享 Mapper；迁移时更新 CI、消费路径与 CODE Map。

## 4. Git / GitHub / Self-Runner

- Healthcare Repo 保存业务 Python、Airflow、Spark、SQL、Contracts、部署定义、Tests 与正式脚本；Self-Runner Repo 保存跨仓库执行 Workflow/受控 Request/Run 证据。
- 从最新 `main` 建功能分支，以 PR Review/Merge 进入主线；不得将 PR 已创建、CI 绿灯或分支代码当作 Main 生效。
- 优先检查并复用现有 Workflow，只有功能确实无法支持时才增加新 Workflow；不假设旧教程描述的 Workflow 仍存在或 Schema 不变。
- Self-Runner 实际验证需显式关联目标 Healthcare Repo、完整目标 SHA、Workflow/Run ID、必要 Batch / Manifest / Digest。HEAD 变化则旧测试不能验证新 HEAD。
- 实际 Runtime 验证应当绑定运行环境、验证范围和独立 Readback；Run SUCCESS 只证明该 Workflow 实际执行和断言覆盖到的范围。
- `git add` 只提交预期文件；严禁提交 Token、Kubeconfig、.env Secret、生产数据或临时 artifacts。

## 5. 明确的安全边界

- **没有用户授权不执行** Terraform `apply`/`destroy`、持久化数据库业务写入、S3 删除/覆盖、集群资源破坏或绕过安全门槛的生产式任务；`fmt/validate/plan` 不代表准许 Apply。
- 涉及共享 Kubernetes、Spark、Airflow、PostgreSQL 时先核对并行 Agent/Workflow/Pod/Job/DAG 及可能产生的副作用，按照当前协作政策确认操作窗口；不得把“只读检查”扩展成新的真实 SparkApplication、COMMIT 或重放。
- 不自动重跑历史一次性 Synthea Producer、冻结 Batch 的 Writer、已完成 Claim；失败恢复必须先独立检查真实状态。
- Never echo、存储或提交敏感凭据。即使开发 Runner 已授予较高集群权限，也不等于允许 Agent 使用全部能力。

## 6. 证据、状态与交接

- 以已实现代码 + 对应版本的测试/部署/真实验收为依据；设计批准不等于完成，Terraform Plan 不等于资源创建，Airflow DAG success 不等于 PG COMMIT。
- 标明版本（完整 SHA）、测试类型、真实 Run URL/ID、业务批次或环境；缺证据的结论标为 **UNVERIFIED / NEEDS REVIEW**，不要猜测或夸大。
- 一个 STEP 结束要说明：已完成内容、验证结果、未完成项、下一个最小步骤、需要额外授权的动作。复杂项目需要有文件化交接，不依赖旧聊天对话。
- 代码/功能修改若改变事实或接口，随 PR 更新已迁移的文档；旧证据保持原貌。文档迁移优先读 [治理规则](DOCUMENTATION-GOVERNANCE.md)。

## 7. 规则冲突如何处理

按照任务领域判断权威，而非“后写的文件必胜”：**当前真实代码和有效合同**负责“系统能做什么”；**实际运行读回与验收证据**负责“确实运行并通过什么”；**已审核的 documents ACTIVE 页面**负责对应模块的“当前解释”；**现有仍生效的操作安全约束**必须保留直到被明确取代。计划、样例、旧 `docs/` 时间快照不得覆盖真实验收。

当 `documents/` 与旧资料冲突：先在迁移追踪里登记源/差异/证据，再修订候选，未经审核不擅自改运行环境。涉及权限或安全，选择更保守的行为并请求必要授权。

**Local DP forward-only（2026-11-05）**：现有 TASK001–TASK004/历史 TASK005、`task004_*` DAG/SQL/Writer、旧测试、已验收 Run/Batch 和有效合同均按原地事实保留；**不**为 OpenSpec 重建旧业务实现、重写历史 PASS/FAIL 或清理旧任务代码。今后新增 Local DP 业务域（如 Condition）、行为/接口/Runtime 配置的实质性变更，必须事前使用一个对应 Active OpenSpec Change，并由其 `tasks.md` 独占进度；旧 TASK 文件只能作历史技术参考，禁止新的人工 CURRENT/NEXT。已有 [Local DP relocation Change](../../../openspec/changes/relocate-local-data-platform/tasks.md) 仅管理迁移收尾，不是新 Condition 的工作项；具体 Owner 路由见 [Local DP README](../../systems/data-platform/README.md)。新增测试仍按 `.github/quality/tests/<system>/<component>/` 放置，原位 Legacy 文件冻结保护，任何业务运行与数据修改均须独立授权。

> **OpenSpec 强制关联（2026-10-18 已验证）**：实质性代码/Workflow/架构/治理变更应在实施前创建或使用 Active Change，PR Body 声明 `OpenSpec-Change` 与 `OpenSpec-Task`，同 PR 更新该 Change 的 `tasks.md`。[Trusted Change Gate](../../../.github/workflows/openspec-trusted-change-gate.yml) 和 Main Ruleset #25365902 已通过真实正反 PR；文档和 Engineering 不再记录平行实施 Tasks。业务目录已物理迁移到 `local-data-platform/`，但运行路径和 E2E 尚未验收。真正共享环境操作仍需单独授权，未经证实行为不得进入 Current Specs。
