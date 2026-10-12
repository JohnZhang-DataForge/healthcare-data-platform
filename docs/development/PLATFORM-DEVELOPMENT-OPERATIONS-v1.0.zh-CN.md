# Healthcare Data Platform — Agent 开发与跨仓库执行操作手册 v1.0（最终版）

> **状态：正式生效 / DEVELOPMENT WORKFLOW VALIDATED**  
> 日期：2026-10-12  
> 适用：`JohnZhang-DataForge/Self-Runner` 与 `JohnZhang-DataForge/healthcare-data-platform`  
> 两仓库保存**同一份规范正文**；本文件是后续 Agent 的开发流程入口，而非生产级 CI/CD 合规证明。  
> **当前目标：快速、可靠地开发平台功能；不要为了 CI/CD 完善度延误业务开发。**

## 0. Agent 开始工作前必须知道的结论

1. **开发链路已真实验证，可以直接进入新 TASK/STEP 开发。** 不需要重复证明 GitHub → ARC Runner → Kubernetes → Spark 的连通性；也不要求先做 Airflow 专项 CI 基建测试。
2. **允许手工关联两个仓库的 PR、分支、完整 40 位 Commit SHA 与固定 TASK/STEP。** 手工维护 Request 是当前被接受的工作方式，不必等待自动跨仓库 PR 通知或强制检查。
3. **Self-Runner 是执行控制仓库，Healthcare 是正式业务源码仓库。** 业务 Python/Spark/Airflow/SQL/Helm/Contracts/Tests 应放在 Healthcare 的合适现有目录；不要把业务实现长期放进 Self-Runner。
4. **当前 `dw-runner-set` 使用开发集群高权限 ServiceAccount 是有意选择。** 不得将只读 Runner、NetworkPolicy、企业级审批、强制 Branch Protection 作为普通开发 STEP 的前置任务；同样不得在日志泄漏凭据或擅自删除共享资源。
5. **测试结果必须绑定准确源码版本。** PR 的 HEAD SHA 变化，旧 PASS 不能代表新 HEAD；修改后重新验证。
6. **V8/V9 验证的是固定请求 + 固定 STEP Workflow，不是已经实现的任意 TASK 通用执行器。** 新 TASK 优先复用现有已验证模式；只做必要的轻量适配，不要声称通用自动路由已存在。
7. **历史 TASK001–TASK004 已冻结的源码/生成器/Contract/Checkpoint 不可擅自改写。** 新功能以新增文件和新 STEP 为主；如确实需要修改冻结文件，先提出明确的变更范围与恢复方案。

## 1. 角色、位置与职责

| 层 | 位置 | 责任 |
|---|---|---|
| 正式开发 | `JohnZhang-DataForge/healthcare-data-platform` | TASK/STEP 的源码、部署定义、测试、运行 Shell、Contracts、技术文档、业务 PR |
| 执行控制 | `JohnZhang-DataForge/Self-Runner` | GitHub Actions Workflow、受控 Request、版本绑定、Policy Gate、Runner 调度、结果 Artifact、CI Checkpoint |
| Runner | Kubernetes ARC `dw-runner-set` | Checkout 指定 Healthcare SHA、运行 Shell / kubectl、读取测试结果；不是长期 ETL Worker |
| 实际工作负载 | `dw-spark` / `dw-airflow` 等 | SparkApplication / Job / DAG 等真实运行与数据验证 |
| 历史记录 | 两仓库的 `docs/` | 运行证据、PR、SHA、决策、复现条件、开发 Lessons |

**本地路径仅供需要手工执行时参考**：Healthcare 可能位于 `/data/spark/healthcare-data-platform`，Self-Runner 位于 `/data/Self-Runner`。ARC Runner Pod 是独立临时环境，**不得假设能访问这些宿主机目录**。在 Workflow 中通过 Checkout 获取源码，传入 `PROJECT_ROOT`，并显式准备缺失工具。

## 2. 正式日常操作流程（Agent 必须遵循）

```text
读取最新 main / TASK 权威文档 / 上一步 Checkpoint / 冻结边界
  → Healthcare: feature 分支开发（直接维护 canonical Python/YAML/SQL/Tests/Shell）
  → 静态检查、单测与最小本地验证
  → Push 并创建 Healthcare PR，记录 PR 号和完整 HEAD SHA
  → Self-Runner: feature 分支，创建/更新受控 Request，绑定 PR + HEAD SHA + TASK/STEP
  → Push 触发已有或最小适配的 GitHub Actions
  → GitHub-hosted Policy Gate（白名单、SHA/PR、参数、测试）
  → ARC dw-runner-set Checkout Healthcare exact SHA，执行固定入口
  → 收集 GitHub Run、PASS/FAIL、日志、Artifact；失败修复并重跑
  → 确认 PASS 对应 Healthcare PR **当前** HEAD，合并 Healthcare PR（merge commit）
  → 如该 STEP 需要：绑定合并后的 main SHA 复验；记录未复验时的实际状态
  → 生成/更新 Checkpoint、Lessons；提交到相应仓库
  → 合并 Self-Runner 控制层 PR；从最新 main 开始下一 STEP
```

**开发迭代允许人工协调。** GitHub PR 不是自动触发 Self-Runner 的必要条件；只要 Request 绑定正确、Runner 实际执行且有可追溯证据，就满足现阶段开发要求。

### 2.1 Healthcare 开发分支

- 从最新 `main` 创建 `feature/taskNNN-stepNN` 或描述性分支（如 `feature/task005-condition`）。
- 先阅读 `docs/skill/SKILL-cn.md`、相关 TASK README/Contract、`docs/runbooks/development-lessons-cn.md`、最新 Checkpoint；确认当前业务代码的权威入口。
- 新代码直接入 Git，Shell 负责准备、执行、验证与报告；**不要把“所有源码必须由 Shell 生成”强加给新 STEP**。已冻结的历史 generator 仍按原重建规则保留。
- 测试应覆盖本次变更的实际风险；无需每次都重跑所有旧 TASK。
- `git add` 指定文件；不提交 `runtime/`、凭据、kubeconfig、Secret、原始数据或临时目录。
- PR 描述至少说明：TASK/STEP、变更文件、依赖、预期副作用、验证方式、是否触碰冻结边界。

### 2.2 手工跨仓库绑定：必须记录的字段

| 字段 | 含义 |
|---|---|
| `target_repo` | Healthcare 仓库全名 |
| `target_ref` | `feature/...` 或 `main` |
| `target_pr` | 待合并 Healthcare PR 号；对 main 复验可不使用 |
| `target_sha` | **完整 40 位 SHA**，不得用缩写 |
| `task` / `step` | 受控 TASK/STEP 标识 |
| `mode` | 当前固定 Workflow 允许的操作（例如 `execute`），以代码白名单为准 |
| `script` | 固定允许的执行入口；不得由 Request 任意指定路径 |
| 输入上下文 | 批次、Manifest 哈希、数据 URI、预期行数、环境/依赖（按 STEP 需要） |

**示意（不是可直接提交的 V8/V9 Schema）：**

```json
{
  "target_repo": "JohnZhang-DataForge/healthcare-data-platform",
  "target_ref": "feature/task005-condition",
  "target_pr": 18,
  "target_sha": "<40位真实HEAD_SHA>",
  "task": "task005",
  "step": "condition-validation",
  "mode": "execute"
}
```

**不得直接复制上述示意触发运行。** 具体 JSON 路径、字段、Schema、白名单、Workflow trigger 必须查看当前 Self-Runner 实际文件；新 TASK 尚无白名单时，先做最小增量适配。禁止把 `script` 变成“任意 Shell 命令”入口。

### 2.3 当前已经验证的可参考实现

**V8：真实 Visit canonical STEP**

- Workflow: `Self-Runner/.github/workflows/cross-repo-task004-visit-v8.yml`
- Request: `Self-Runner/config/targets/healthcare/steps/task004-visit-runtime-v8.json`
- Healthcare 执行入口: `scripts/task004/05e-run-visit-canonical.sh`
- 正向 Run `38250467965`：exact SHA / kubectl / Spark / Processing readback PASS；2459 Encounter；PostgreSQL 未写入。

**V9：真实 Person/Visit Batch Reconciliation**

- Workflow: `Self-Runner/.github/workflows/cross-repo-task004-reconciliation-v9.yml`
- Request: `Self-Runner/config/targets/healthcare/steps/task004-batch-reconciliation-v9.json`
- Policy: `Self-Runner/src/ci/task004_reconciliation_v9.py`
- Healthcare 执行入口: `scripts/task004/05f-reconcile-person-visit.sh`
- 负测 Run `38251924029`：错误 mode → Policy FAIL、ARC 执行 SKIPPED。
- 合并前 Run `38251984921`：Healthcare PR #16 exact HEAD PASS。
- 合并后 Run `38252497171`：Healthcare main exact SHA PASS；20 Patient、2459 Encounter、0 orphan、Processing/PostgreSQL 无新数据写入。
- Healthcare PR #16、#17 已合并；Self-Runner PR #25 已合并。

**结论边界**：V8/V9 证明了实际开发闭环；**没有**证明任意新 TASK 自动被发现、任意多仓库 PR 自动同步、GitHub 自动阻止所有未验证 PR 合并。不要把这些未实现功能写成 PASS。

### 2.4 Agent 如何触发与检查（现阶段）

1. 在 Healthcare 建好 PR，读取最新 `head.sha`；核对与分支 HEAD 一致。
2. 在 Self-Runner 的对应 feature 分支，修改**该 STEP 已存在的固定 Request JSON**；新 STEP 才新增固定配置及必要的受控适配。
3. 确认 Workflow 的 `on.push.branches` 与 `paths` **确实覆盖本次提交**。V8/V9 由 Self-Runner feature 分支对固定 Request/Workflow 路径的 Push 触发；仅修改 Healthcare PR 不会自动触发。
4. 先在 GitHub-hosted Policy Job 验证字段、白名单、当前 PR HEAD 或 main HEAD；Policy FAIL 必须使 ARC Job SKIPPED。
5. ARC Job 必须 `checkout` 精确 SHA 并检查 `git rev-parse HEAD`；需要 `kubectl` 时参照 V8/V9 的版本固定 + 官方 SHA256 校验启动方式。
6. 真实执行固定 Shell；校验 Job exit code、业务 Marker、Kubernetes 终态、数据 readback（适用时），并上传日志/Artifact。
7. GitHub Run 为 SUCCESS 且所有**适用**业务 Gates 为 PASS，才记录该 HEAD 的 PASS；不能只看 `kubectl apply` 成功或日志出现一个 PASS。
8. 如果 PR HEAD 改变、输入数据版本改变或执行脚本改变，更新绑定并重新运行；不要复用旧 PASS。
9. 合并后检查真实 main SHA；重要 STEP 可像 V9 一样再跑 post-merge。若未执行，不得写“post-merge PASS”。

**手工检查示例（已安装 `gh` 且有授权时）：**

```bash
gh pr view <PR_NUMBER> -R JohnZhang-DataForge/healthcare-data-platform --json headRefOid,url
gh run list -R JohnZhang-DataForge/Self-Runner --limit 10
gh run view <RUN_ID> -R JohnZhang-DataForge/Self-Runner
```

Agent 若可通过已连接的 GitHub 工具完成上述操作，优先直接使用；不要要求用户为了查询状态重复手工操作。没有权限或工具时，明确说明未验证状态。

## 3. PASS/FAIL 与副作用约束

每个 STEP 的具体 Gate 由该 STEP Contract 定义，最低要求：

- **身份**：repo、PR、分支、完整 SHA、TASK/STEP、输入数据版本可追溯。
- **代码**：语法/单测/契约检查（适用时）与冻结文件范围检查。
- **运行**：Job/Pod/SparkApplication 的真实终态，失败返回非零退出码。
- **业务**：Schema、Row Count、唯一性、FK、Lineage、Readback 等按 STEP 适用；未运行的 Gate 写 `NOT_RUN`，不得写 PASS。
- **证据**：GitHub Run ID、Job 结果、关键 Marker、Artifact 名称/可用性、异常诊断与 Cleanup 状态。
- **变更安全**：仅清理本次唯一命名的临时资源；不自动删除冻结数据、PV/PVC、Secret、Bucket、Namespace、持久 ID 映射。
- **持久写入**：必须定义幂等性、重复执行与冲突策略；出现不确定的写入结果时先只读 reconciliation，**不要盲目重试**。
- **失败处理**：同一 feature 分支修复、提交新的 SHA、重新触发；不把失败历史覆盖成成功。

建议 Checkpoint 字段：

```text
TASK=...
STEP=...
HEALTHCARE_PR=...
HEALTHCARE_TESTED_HEAD_SHA=...
HEALTHCARE_MERGE_SHA=... / NOT_MERGED
SELF_RUNNER_PR=...
SELF_RUNNER_WORKFLOW_SHA=...
GITHUB_ACTIONS_RUN_ID=...
INPUT_BATCH_OR_MANIFEST=...
POLICY_GATE=PASS/FAIL/NOT_RUN
RUNTIME_GATE=PASS/FAIL/NOT_RUN
BUSINESS_GATE=PASS/FAIL/NOT_RUN
POST_MERGE_GATE=PASS/FAIL/NOT_RUN
ARTIFACT=...
FROZEN_FILES_CHANGED=NO
FINAL_STATUS=PASS/FAIL/IN_PROGRESS
```

**Checkpoint 应写入实际已核验事实**，不能将设计、推断或上一轮聊天口述视为运行证据。

## 4. 何时才需要修改 Self-Runner 基建

默认**不修改** Self-Runner 运行架构。新 TASK 优先沿用 V8/V9 的固定模式，仅在必要时添加固定配置、白名单、少量 Workflow/Adapter。

只有以下情况才值得暂停业务开发并做最小 CI 变更：

1. 当前 Runner 无法执行新的业务 STEP（例如缺工具或运行入口不兼容）。
2. 无法准确绑定 PR/SHA，或出现错版本执行。
3. 不能可靠判定 PASS/FAIL、不能保留必要证据。
4. 当前触发机制明显阻碍重复开发（届时再提取通用执行器）。

**现阶段不作为阻塞项**：自动 Healthcare PR → Self-Runner 事件通知、强制 PR status check、第二套 readonly Runner、细粒度 RBAC、生产级发布审批、全自动多仓库同步、全量 Replay/灾备平台。V7 的安全设计文档保留供未来参考，**不是当前实施计划**。

多仓库（例如未来单独 Helm Repo）可手工记录各仓库的 PR + SHA，但**V8/V9 尚未验证多仓库同时 checkout/binding**；首次真实使用时增加最小验证，不要预先为此建设平台。

## 5. 新 Agent 接手时的最小阅读与执行顺序

1. 阅读**本文件**（两仓库相同内容，任取一份即可）。
2. 阅读 Healthcare `docs/skill/SKILL-cn.md`、本 TASK 最新 Checkpoint、Contract、冻结边界、`docs/runbooks/development-lessons-cn.md`。
3. 阅读 Self-Runner V9 Workflow、Request、Policy、最终 Checkpoint；如业务 STEP 更接近 V8，则看 V8。
4. 查询两仓库 `main` 的真实 HEAD、当前 feature 分支、未合并 PR、Actions 最新结果；**不要依赖旧会话记忆替代 GitHub 当前状态**。
5. 说明本次变更的 TASK/STEP、允许路径、测试计划和副作用；按**一个 bounded STEP**迭代。
6. 开发 → 固定 SHA 验证 → PASS → PR 合并 → Checkpoint；然后再进入下一 STEP。
7. 如需用户在 `runner01` 执行命令，遵守 Healthcare Skill：**一次提供一个完整可直接粘贴的 Bash code block**；严格模式写在子脚本里，避免污染交互 Shell。
8. 如有疑点，先读取现有源码/证据再决定，不得擅自推翻已冻结设计。

## 6. 规范优先级与历史文档的关系

本文件是 **2026-10-12 起开发流程的最终操作入口**，两仓库同步生效；此前的 Self-Runner `STEP-BASED-GITOPS-DEVELOPMENT-STANDARD-v1.0`、v1.1 Addendum、M1/M2 Pilot 和 V7 安全设计仍保留为历史资料。

若历史文件写有“尚未验证跨仓库运行”“必须先完成通用自动路由”“必须自动合并 PR”“Push execute 一律不可用”等与 **V8/V9 真实已验证的开发模式**不一致的阶段性设想，**当前日常开发以本文件和实际 Workflow 代码为准**。但本文件不覆盖 Healthcare TASK 的 Contract、冻结边界、数据一致性/Mutation 安全规则，也不允许绕过 GitHub 实际权限或审批限制。

本文件所说“开发流程已通过”只表示**已验证的手工关联 + 固定 SHA + 受控 Workflow + ARC + 业务执行 + PASS/FAIL + PR/Checkpoint 闭环可用**。不是生产级安全或所有业务组件测试都自动通过。

---

## 7. 已验收的开发流程终态

```text
DEVELOPMENT_WORKFLOW_STATUS=VALIDATED
CROSS_REPO_MANUAL_PR_SHA_BINDING=SUPPORTED
SELF_RUNNER_TRIGGER=PASS
GITHUB_HOSTED_POLICY_GATE=PASS
ARC_DW_RUNNER_SET=PASS
KUBERNETES_REAL_WORKLOAD=PASS
SPARK_PROCESSING_READBACK=PASS
FAIL_CLOSED_NEGATIVE_TEST=PASS
HEALTHCARE_PR_PREMERGE_EXECUTION=PASS
HEALTHCARE_MAIN_POSTMERGE_EXECUTION=PASS
GITHUB_ACTIONS_ARTIFACT=PASS
AUTOMATIC_CROSS_REPO_PR_DISPATCH=NOT_IMPLEMENTED_NOT_REQUIRED
MANDATORY_PR_STATUS_CHECK=NOT_REQUIRED
PRODUCTION_GRADE_RBAC=NOT_REQUIRED
GENERIC_ARBITRARY_TASK_DISPATCHER=NOT_IMPLEMENTED_NOT_REQUIRED
NEXT_PRIORITY=HEALTHCARE_PLATFORM_FEATURE_DEVELOPMENT
```

**Agent 的执行指令：不要再以完善 CI/CD 为目标重复开展 V10/V11 基建实验。直接使用本手册进行正式平台代码开发；仅在某个真实 TASK 被现有流程阻塞时，做最小必要修复。**
