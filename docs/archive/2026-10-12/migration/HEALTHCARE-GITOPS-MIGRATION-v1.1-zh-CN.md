# Healthcare STEP GitOps 跨仓库迁移方案 v1.1（架构定稿 / 暂不部署）

> 日期：2026-10-12｜状态：**DOCUMENT_ONLY / DESIGN_APPROVED_FOR_FUTURE_IMPLEMENTATION**  
> 源仓库：`JohnZhang-DataForge/Self-Runner`；目标仓库：`JohnZhang-DataForge/healthcare-data-platform`。  
> 本文件是 **v1.0 的新增架构修订版**，不修改、删除或覆盖 v1.0 及任何 Healthcare 现存历史文档、TASK Contract、冻结 Generator、Shell、工作流或运行环境。**本次仅提交文档，不实施 M2。**

## 1. 最终架构决策（与 v1.0 的区别）

**正式业务源码在 Healthcare；GitHub Actions 通用 Workflow 与 CI 控制面保留在 Self-Runner；ARC Runner 是临时执行面。**

```text
Healthcare (public, protected main)          Self-Runner (private CI control)
Feature Branch: code/tests/Shell                  config/targets/healthcare/<task>/<step>.json
         |  commit full SHA                                    |
         +-------------------> request pinned SHA -------------+
                                                              |
                                              Self-Runner GitHub Actions Workflow
                                                              |
                                                dw-runner-set (ARC, maxRunners=3)
                                                              |
                                                 checkout Healthcare exact SHA
                                                              |
                                       allowlisted, reviewed validation-only Shell
                                                              |
                                       PASS / FAIL + logs + report.json Artifact
                                                              |
                             feature HEAD validation -> Healthcare PR -> Merge Commit
                                                              |
                             post-merge validation of exact new main SHA -> Checkpoint via PR
```

**明确修改原 v1.0 M2 决策：** 不把通用 Workflow 搬入 Healthcare；不在 Healthcare 新增 `generic-step-validation-v1.yml`。Self-Runner 负责 Workflow、请求 JSON、策略/路由、验证证据。Healthcare 保留业务源码、测试、专属 Shell 以及正式 Contract/Checkpoint；没有自建跨仓库触发服务、Webhook 或额外公网入口的前置要求。

现有 Healthcare 的镜像构建 Workflows 是既有资产：保持原样，**本次不修改也不删除**。

## 2. 事件触发与身份绑定

1. ChatGPT 在 Healthcare 的 `feature/taskNNN-stepNN` 中提交业务 Python / PySpark / Airflow / YAML / tests / 验证 Shell。
2. 读取该提交的**完整 40 位 Git SHA**；不得只使用可变的 branch 名或 `main` 最新引用进行执行。
3. ChatGPT 更新 Self-Runner 中**该目标 STEP 固定且唯一的一份 JSON**，Push 到 Self-Runner 的执行许可分支，由 `on: push` 的 paths filter 触发 Workflow。**Healthcare Push 不会天然触发 Self-Runner 的 Push Workflow。**
4. 请求中的 `target_repo`、`target_sha`、`task`、`step`、`mode` 通过严格 Schema、allowlist 和目标 Commit 可读性核验后，才允许执行受批准入口。
5. Runner Checkout Self-Runner 的**工作流事件 SHA**读取可信路由策略，另 Checkout Healthcare **请求中明确的目标 SHA**；分别记录 `controller_sha` 和 `target_sha`，对照目标提交/配置/日志一致性。
6. 仅当 Healthcare 最新 Feature HEAD 与已经 PASS 的 `target_sha` 完全相等时才创建/合并 PR。遇到 HEAD 移动、代码变更、基线冲突，必须重新验证。
7. PR 采用 **Merge Commit** 合并受保护的 Healthcare main；验证准确的最终合并 SHA（至少独立发起相应 POST_MERGE_VALIDATE 请求），Checkpoint 也走 PR，不能绕过保护。
8. Workflow `Queued` 不是 PASS；Run 失败、取消、超时、网络闪断后必须重新核对 Job 和 Pod 状态。不能凭 `maxRunners=3` 推断同 STEP 串行。

### 参考请求（只是 v1.1 Schema 草案，尚未安装）

Self-Runner 路径：`config/targets/healthcare/taskNNN/stepNN.json`（每 STEP 固定文件，每次运行更新同一文件）。

```json
{
  "schema_version": "1.1",
  "request_id": "task004-step05-attempt001",
  "target_repo": "JohnZhang-DataForge/healthcare-data-platform",
  "target_sha": "<40-character-Healthcare-commit-sha>",
  "task": "task004",
  "step": "step05",
  "mode": "validate",
  "phase": "feature"
}
```

`request_id` 仅用于日志检索；唯一运行身份是 Self-Runner controller commit + GitHub run ID + Healthcare `target_sha`。实际接受的 STEP 和 Phase 需在实施时逐一明确批准。不得动态拼接 JSON 提供的 Shell 命令、文件路径、Namespace、镜像或 Kubernetes API 动作。

## 3. 仓库职责与变更边界

| 对象 | 所属仓库 / 平面 | 权威职责 |
| --- | --- | --- |
| 正式业务 Python/Spark/Airflow、YAML、测试 | Healthcare | 业务 Source of Truth；原有路径和冻结规则优先 |
| 新 STEP 专属执行/验证 Shell、Contract | Healthcare | 代码版本与 `target_sha` 绑定；历史 Generator 不改 |
| 通用 Workflow、目标请求 JSON、跨仓库路由、受控策略 | Self-Runner | CI Control Plane；不复制到 Healthcare |
| GitHub Actions logs、artifact、运行状态 | Self-Runner | 控制面证据；Healthcare Checkpoint 引用具体 Run URL |
| Healthcare PR / Merge Commit / Checkpoint | Healthcare | 业务正式验收、追溯与冻结 |
| ARC `dw-runner-set` 临时 Runner Pod | Kubernetes | 执行经批准的测试，`maxRunners=3` 仅为容量 |
| Spark Operator / 隔离临时验证 Pod | Kubernetes | 后续 M3 经单独授权的业务集成测试 |

- Self-Runner 是 Private repo，GitHub 当前计划**不强制**其 main 分支保护。它同时是能够访问高权限 Runner 的控制面：必须把“谁可以提交控制面代码”和“哪个 SHA 允许触发”作为实际安全 Gate；不得把未经信任的 Healthcare PR 任意 Shell 直接交给 cluster-admin Runner。
- Healthcare 是 Public repo，main 已实测拒绝直接提交；PR #7/#8 成功合并。**暂未强制 Required Status Checks**，因此“检查通过才合并”仍须在操作流程及工具校验中强制执行。
- 独立 Session/并发：同一文件的旧 Git Blob SHA 并发更新会 409；禁止自动盲覆盖。Workflow 应按目标 repo + task + step（及必要隔离维度）设置互斥，并确保每个 Run Checkout 自己固定的源 Commit。不同 STEP 是否允许并行须按共享资源风险判断。
- 跨仓库私有触发的最简方案是 ChatGPT 用现有 GitHub 连接向 Self-Runner 提交固定 JSON；**不是 GitHub 原生跨仓库 Push 自动转发**。后续可另评估 `repository_dispatch`，但当前连接没有被证明具备该调用能力，不做虚假承诺。
- Public Healthcare 代码不是天然安全输入：即使仓库写入者只有本人，也要审查外部 PR、依赖和可执行代码的可信边界。前期只做无副作用验证；危险操作需独立授权。

## 4. M1–M4 修订计划

### M0 — 文档迁移（本次）
- 在 Self-Runner **新增**本文件，经独立 PR 进入 main；再逐字复制到 Healthcare 的 `docs/migration/` 新路径，通过 protected main 的 PR 合并。
- 验证两边 Git Blob SHA 一致，Healthcare 原文件变更清单只有**新增本文件**。不启动 Runner 或 Kubernetes，不修改任何 Workflow。状态：`DOCUMENT_ONLY`。

### M1 — 只读现状基线（后续独立任务）
- 用 Healthcare main 的冻结清单、TASK001–TASK004 的 Contracts、Shell Generator、现有 Workflows/Triggers、Runbooks 做只读盘点；建立 SHA/路径/依赖与不可触碰清单。
- 核对 Self-Runner ARC Runner label、GitHub App 权限、可访问 Public Healthcare 的具体 Commit、工具链与并发策略。核对现有 Workflow/Config Path，避免事件过滤重复触发。
- 不执行历史 TASK，不修改 PostgreSQL、SeaweedFS、PVC、Airflow 正式 DAG 或 Spark 正式资源。
- 输出基线报告，新文档经 PR；M1 PASS 才允许实施 M2。

### M2 — **Self-Runner Cross-Repository GitOps Orchestrator**（后续独立实现；本次不做）
- **只在 Self-Runner 新增** v1.1 的跨仓库 Workflow、请求 Schema/allowlist、路由器、CI 测试 Shell 与负面测试；不覆盖 V1/V2/V3 已冻结 Workflow，且配置路径使用不冲突的新命名空间。
- Healthcare 仅在**未来新的 STEP 开发**时提交属于 Healthcare 的正式代码/验证 Shell；**不在 Healthcare 部署通用 Workflow**。
- 先选择一个**无业务副作用**的目标 Commit 做 Smoke：验证 exact-SHA 双仓 Checkout、受控任务选择、负面权限/参数测试、PASS/FAIL Artifact 与运行记录。
- 验证 GitHub Runner 的权限、Checkout 目标 SHA、存在目标文件、两仓代码与 Shell SHA、Workflow Job 状态、GitHub Run ID。不得以仅出现字符串 `PASS` 作为完整结果。
- `push` 默认只允许 `validate`，不自动触发部署/写数据；需显式授权才允许其他执行模式。核查合法文件变化与最新 Healthcare Feature SHA 一致。
- 先验证失败→修复→PASS→Healthcare PR→合并→main SHA 复验→Checkpoint；再逐步启用正式任务。Self-Runner Config 更新和 Healthcare PR 提交/合并属于两个不同仓库，需要明确跨仓库一致性与失败恢复，不存在天然原子事务。
- **M2 验收 Gate**：固定 Target SHA、冻结文件未变、无不受控 Shell、Runner 执行范围、被拒绝的非法请求、单次请求及重复运行识别、并发门槛、合并后验证和恢复路径。所有 Gate 需真实验证后才记 PASS。

### M3 — 受控集成扩展（后续另行批准）
- Self-Runner 仍是 Workflow 所属仓库，Runner 读取 Healthcare 已提交且准许的 SHA。
- Spark/Airflow 在独立 Namespace、唯一资源名、隔离输入/输出和审批后的权限范围内测试；解析 Airflow DAG 不能冒充调度器 DAG 真正运行。
- 不因普通 Git Push 重跑冻结 TASK003/004，不修改共享 PostgreSQL/OMOP、SeaweedFS、PVC、正式 DAG 或历史 Job。
- 每次具体的写入、部署或 Replay 必须另行授权、先验范围确认和清理策略。

### M4 — 审计、冻结与 Replay（后续）
- Healthcare Checkpoint 记录 target SHA、Self-Runner workflow/controller SHA、Run ID、Gate、Artifacts、合并 SHA、post-merge 验证 SHA、源码/Contract/输入/镜像哈希。
- Checkpoint 更新走 Healthcare PR，不能直接提交 protected main；新增 checkpoint 引起 HEAD 变化时，必须区分原业务内容已验证和最新纯文档 HEAD。
- Replay 按冻结依赖拓扑设计；无存储快照/Secrets/外部依赖就不能宣称完整可重建。真实恢复/数据导入仅在经批准的隔离环境执行。

## 5. 不可破坏约束与暂停条件

**此次 M0 完成后也不能自行进入 M2。** 必须先获得后续明确任务，再逐项实施。实施中遇到以下情况应停止合并或执行：目标 SHA 不再等于 PR HEAD、请求白名单不符、冻结文件被修改、缺失 Gate、Workflow 丢失/Queued/Cancelled、Kubernetes 权限异常、存在持久数据写入风险、Self-Runner 控制面变更未经独立验证、Git 返回 409 冲突等。

Healthcare 原有 `docs/BASELINE.md`、`docs/runbooks/GITHUB-SELF-HOSTED-RUNNER-DEVELOPMENT-V2.zh-CN.md`、`docs/architecture/**`、`docs/tasks/**`、`docs/task003/**`、`docs/handoffs/**` 以及冻结 Generator/Contracts/Checkpoint 均不更改。现存 `.github/workflows/build-synthea-image.yml`、`build-task004-runtime-image.yml` 保留。

## 6. 验证依据及未完成测试

已经证实的实验：Self-Runner STEP01 Spark、STEP02 Airflow 隔离解析、STEP03 allowlist/负面验证/merge skip/main 复验；两路同旧 Git Blob SHA 更新同文件时 GitHub 409 拒绝第二写入；Healthcare main 直接写拒绝，PR #7 和 #8 以 Merge Commit 合并。对应 Self-Runner 证据：
- `docs/STEP-BASED-GITOPS-DEVELOPMENT-STANDARD-v1.0-zh-CN.md`
- `docs/STEP-BASED-GITOPS-DEVELOPMENT-STANDARD-v1.1-ADDENDUM.md`
- `docs/checkpoints/task004/step01-spark-smoke.md`、`step02-airflow-fixed-json.md`、`step03-safety.md`
- `docs/runbooks/SELF-RUNNER-COMMON-LESSONS.md`
- `docs/migration/HEALTHCARE-GITOPS-MIGRATION-v1.0-zh-CN.md`

**仍未验证：本 v1.1 的跨仓库调度链路本身**、两个 Workflow 真正共享 Kubernetes 状态的竞态、异常断网孤儿资源恢复、面向任意不可信提交的运行隔离、全新环境完整 Replay、强制 GitHub Required Status Checks。本文件是架构决策和实施计划，不是这些能力的 PASS 证书。

## 7. 给后续新 Session 的操作指引

1. 先读 Healthcare 既有 `docs/BASELINE.md` 和当前 TASK Frozen Contract、Checkpoint，再读本 v1.1。旧 v1.0 仅为历史迁移方案，不再作为 M2 Workflow 所属仓库的决定依据。
2. 默认 **Healthcare = 业务 Source of Truth；Self-Runner = CI Control Plane；ARC = Execution Plane**。
3. 每次只实施一个受控 STEP；先允许列表和负面测试，再用精确 SHA 执行，最后是 PR 与 main 后验收；不因为 Runner Pod 成功启动就判业务 PASS。
4. 对 Self-Runner 的新 Workflow 必须与旧的触发路径隔离，并对 Healthcare 跨仓库权限、安全入口做独立审查。
5. 修改任何原历史内容、迁移旧业务代码、放开 execute 模式或运行数据变更前，都要单独获得用户批准。
