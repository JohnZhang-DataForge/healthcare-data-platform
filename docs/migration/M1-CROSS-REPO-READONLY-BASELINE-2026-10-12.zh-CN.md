# M1 — 跨仓库 GitOps 只读基线核查（2026-10-12）

> 状态：**REPOSITORY_PREFLIGHT=PASS / LIVE_RUNTIME_CHECK=NOT_RUN / M2=NOT_DEPLOYED**。
> 文档来源 Self-Runner，只新增文档并经 PR 迁入 Healthcare。本文没有运行 Shell、Actions、Kubernetes，也没有写数据库或对象存储；不能据此认定全套 M1 运行时前提通过。
> 关联设计：`docs/migration/HEALTHCARE-GITOPS-MIGRATION-v1.1-zh-CN.md`。控制面 Workflow **只放 Self-Runner**。

## 1. 被检查的精确版本与方法

| 仓库 | 核查时 main SHA | 扫描 |
| --- | --- | --- |
| `JohnZhang-DataForge/Self-Runner` | `ef80895f35ea6afbdd362312f3bc1eacb4e5ddc8` | GitHub API 递归 Git Tree、关键文件内容和 blob SHA |
| `JohnZhang-DataForge/healthcare-data-platform` | `ab9546e096af7c411ab9e829e2dbee086a3bcb39` | GitHub API 递归 Git Tree、关键文件内容和 blob SHA |

两棵树均未截断，分别为 65 和 340 个 Tree 节点（目录+文件）。后续提交 M1 报告必然推进 main HEAD，**上表是 M1 扫描基线，不应冒称文档合并后的 HEAD**。

## 2. Self-Runner 控制面现状

| Workflow | 触发 | Runner | 冻结 blob SHA |
| --- | --- | --- | --- |
| `.github/workflows/generic-task-executor.yml` | `push: requests/**`，`feature/**`/main；另有手动 Dispatch | `dw-runner-set` | `7ef3d07cd879c4fd3f8837301cf58780e3ad9bfe` |
| `.github/workflows/generic-task-executor-v2.yml` | `push: config/tasks/**`；另有手动 Dispatch | `dw-runner-set` | `6a7ace6d3e5a114c73c3d21418236a235ee0dd67` |
| `.github/workflows/generic-safety-v3.yml` | `push: config/policy/tasks/task004/step03.json`；另有手动 Dispatch | `dw-runner-set` | `b9b5855b3861548f8fe4f84176541c3612d4e902` |

- 三条现有 Workflow 均只给 `GITHUB_TOKEN` `contents: read`，使用固定 runner label、精确当前事件 SHA checkout，并有 `concurrency`。三个 Workflow 对应的 concurrency key **不完全一致**，不能认为彼此互斥。
- V1 接受历史 `requests/task004/step01/run-*.json`；V2 固定 `config/tasks/task004/step02.json`；V3 固定 `config/policy/tasks/task004/step03.json`。历史均保留、不复用为 Healthcare 跨仓库入口。
- V1/V2 使用 `git diff-tree -r HEAD` 解析本次变更，对 Merge Commit 无结果的风险存在；V3 对多父 Merge Commit 明确 SKIP。**M2 必须另行设计合并后复验，不继承这项 SKIP 作为 PASS**。
- Self-Runner 的 `config/targets/healthcare/**` 目前没有正式部署的跨仓库调度器和请求文件；必须新建不与现有 paths filter 冲突的 Workflow。
- Self-Runner 是 private，账户计划不能对其 main 强制 GitHub 分支保护；高权限 Runner 控制面依赖 repo 写权限、独立可信检查及对危险 execute 的拒绝。不能假设 Self-Runner 工作流仓库受 Healthcare main 保护。
- [STEP01](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/checkpoints/task004/step01-spark-smoke.md) [STEP02](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/checkpoints/task004/step02-airflow-fixed-json.md) [STEP03](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/docs/checkpoints/task004/step03-safety.md) 的 PASS 属于**同仓库 Pilot**；不证明跨仓库 Checkout 已执行。

## 3. Healthcare 正式业务仓库现状

- 当前可读取 Public Healthcare 指定 main Commit 和已知文件，证明**控制侧 GitHub 读取能力**，但尚未从 ARC Runner 的执行容器内验证 git fetch/checkout 指定 SHA。
- Healthcare 现存 Workflow **仅两条**：
  - `.github/workflows/build-synthea-image.yml`：`workflow_dispatch`，或者 **main** 上变更 `images/synthea/**`、指定 Synthea Contract/脚本/测试或该 Workflow 时 Push 触发。Runner 为 `ubuntu-latest`；`contents: read` 与 `packages: write`；Blob `bb1f6fb0ec880b465014d0a70a7976c317a16c4a`。
  - `.github/workflows/build-task004-runtime-image.yml`：`workflow_dispatch`，或者 **main** 上变更 `images/task004-runtime/**`、指定 TASK004 应用/Spark/脚本/测试或该 Workflow 时 Push 触发。Runner 为 `ubuntu-latest`；`contents: read` 与 `packages: write`；Blob `be18bc8305b0d32af8b6ba84fef5553c4f40a620`。
- **文档变更不在这两条 Workflow 的 Push path 白名单**。新增本 M1 文档不会因现有过滤器触发镜像构建；如未来直接编辑上述指定业务文件并合并 main，现有构建 Workflow 仍可正常触发，这属于原有行为。
- Healthcare `main` 已在此前真实测试中拒绝 GitHub App 直接写入（409：必须通过 PR），且 PR #7/#8 采用 Merge Commit 成功；尚未要求指定 CI Status Checks，因此未来必须由 ChatGPT 按完整 SHA 审核结果，不能认为 GitHub 自动阻止所有失败 PR。
- 现有业务/冻结入口：`docs/BASELINE.md`、`docs/runbooks/GITHUB-SELF-HOSTED-RUNNER-DEVELOPMENT-V2.zh-CN.md`、`docs/tasks/**`、`docs/task003/**`、`docs/handoffs/**`、`scripts/task001/**`、`scripts/task002/**`、`scripts/task003/**`、`scripts/task004/**`、`contracts/**`、`spark/contracts/**`、`apps/**`、`spark/**`。
- **冻结状态区分：** `docs/tasks/TASK-003-FINAL-CLOSEOUT.md` 将 TASK003 标为 COMPLETE/CLOSED，历史最终验收 SHA `373439c323c82388f559538204b1ba6348916fa0`；`docs/tasks/TASK-004-PROGRESS-CHECKPOINT-AFTER-PERSON.md` 标记 TASK004 仍 **IN PROGRESS**，Person 已 PASS，Visit、Reconciliation、Airflow 尚未完成（此为该 Checkpoint 记载，后续进展需以更新的任务权威证据核实，不能将其视作实时集群状态）。
- Healthcare 的 `docs/migration/v1.0` 与 `v1.1` 两文档保留。v1.0 中“把通用 Workflow 放 Healthcare”方案已被 v1.1 新决策替代，**不能同时执行这两个互斥 M2 设计**。

## 4. 必须维持的禁止清单（M1、M2 早期）

- 禁止覆盖或修改任何现有 Workflow、TASK001–TASK004 Shell Generator、Frozen Contract、Checkpoint、旧任务文档、数据发布与数据库状态；不要为了配置 M2 对历史构建流程做路径重写。
- 禁止直接 Push Healthcare main；禁止伪造 Workflow PASS 或把 `Queued`/`Cancelled`/多父 Merge Commit SKIP 视为 PASS。
- 未经专项授权，不许对 PostgreSQL/OMOP、SeaweedFS、PVC、共享 Airflow DAG/metadata DB、现有 SparkApplication、持久 Kubernetes 资源进行写操作。
- M2 早期只允许固定目标 Public repo + 完整 40 位 SHA + `validate`；不接受 JSON 提供自定义 Bash/URL/Namespace/Kubernetes 命令。
- Runner 工作流中的高权限 SA 属于安全敏感执行环境；**即使 validate 模式，也不能简单执行不可信 checkout 后的任意 Shell**。首次跨仓库 Smoke 应只运行控制面拥有的、无副作用的验证器（如校验已 checkout SHA 和仓库内容），而不是直接调用目标仓库任意脚本。

## 5. M2 前提检查：已确认 vs 待验证

| Gate | 状态 | 说明 |
| --- | --- | --- |
| Healthcare / Self-Runner 现有文件与触发器结构 | PASS（API 只读） | 基于上表完整 tree 与 Workflow 内容 |
| 未发现现成的 Healthcare 跨仓库执行 Workflow | PASS（库存） | 三条 Self-Runner Workflow 无跨仓库目的 SHA；Healthcare 只有两条 image builder |
| 读取 Public Healthcare 指定 Commit | PASS（GitHub API） | 非 Runner Pod 内部 |
| Healthcare main PR 受保护 | PASS（既往真实测试） | 直接写拒绝，PR 7/8 Merge 成功 |
| ARC Pod 实时 Ready、Listener 会话、maxRunners | NOT_RUN（M1 未接触集群） | 此前实验 max=3、有成功运行证据，不等于现在的在线状态 |
| Kubernetes ServiceAccount 的实际 RBAC / cluster-admin | NOT_RUN | 需要用户在集群只读执行 `kubectl auth can-i` 或后续受控核验 |
| Runner Pod 中 Healthcare 精确 Git SHA checkout | NOT_RUN | 必须 M2 Smoke 真正验证 |
| 跨仓库请求 Schema/Allowlist/Workflow 与负面测试 | NOT_IMPLEMENTED | M2 的工作 |
| GitHub App 对两个仓库的写/PR 和保护权限 | PARTIAL | 两库以往 PR 成功；跨仓库自动状态回写未验证 |
| 目标 `config/targets/healthcare/**` 与旧 Workflow path 冲突 | PASS（设计层） | 旧 V1/V2/V3 路径均不匹配；新 Workflow 待实施 |
| 持久数据隔离 / 并发资源占用 | NOT_RUN | M3 才需要专门测试 |

## 6. M1 结论与交接 M2 的允许范围

- **M1 仓库结构与设计前提已检查；实时 Runner/RBAC/精确跨仓库执行仍未验收**。因此仅批准“进入 M2 的**设计与最小无副作用 Smoke 实施**”，不批准部署、数据写入或旧 STEP 重跑。
- M2 从 Self-Runner main 新 Feature Branch 开始：新增 `config/targets/healthcare/**` 和不冲突的 `.github/workflows/cross-repo-validation-v1.yml`，配套白名单、测试和 Runner-side 精确 SHA 验证。起步只 checkout Healthcare 的一个固定 Public SHA 并运行 Self-Runner 自有只读验证；禁止调用 Healthcare 的历史 Generator。
- 同一控制请求由 Self-Runner 完整 SHA+Run ID 确定；目标 SHA 另行记录。任何进一步的业务 Shell 调用须在可信来源/权限审查后单独开启。
- 等最小跨仓库 Smoke / 非法请求拦截 / Artifact PASS 后，才允许提升到 Healthcare 真实 STEP 的验证闭环。

## 7. 审计边界

本 M1 通过 GitHub Connector 只读取 Git tree/文件/既有历史证据；报告新增通过分支→PR→merge commit。**没有实际连接 kube-apiserver、读取 Kubernetes Secret、运行 Shell、访问数据库或执行 Actions**。文档合并前必须确认差异仅包含这个新增文档。
