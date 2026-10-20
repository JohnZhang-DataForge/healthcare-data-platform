# Local Data Platform 历史代码一次性集中清理方案（2026-10-20）

> Change: `relocate-local-data-platform` · Tasks 4.1 / 4.7 / 4.8 / 4.9 / 4.10 / 5 · **DESIGN APPROVED FOR IMPLEMENTATION, NOT EXECUTED**。本文件是实施合同，不是已完成 E2E、删除批准清单或 Archive 证明。用于覆盖此前每 2–6 个文件一批的低效**实施粒度**；不覆盖 A/B/E 安全保护、恢复门、合并 Gate、行为不变性。

## 1. 决策和当前事实

- 冻结本轮方案起点：Healthcare Main `f257ee32fede83250451d4bd6bfe2e592190adcb`；Self-Runner Main `b5f46802ec63c8da6d047d7420dbbd7f5a292ace`。在实施清理前**必须**重新读取两仓 Main、开放 PR 和 Git Tree，记录实际 SHA、增量和并发差异，不能把这里的 SHA 或 8:50 时间点当作永久状态。
- 最新只读 Git Tree：Healthcare 全仓 736 个 tracked blob；`local-data-platform/` **371** 个文件、全部 Shell **101**、其中 `scripts/task003/*.sh` **69**。原始 Task003 94 个历史 Shell；七个 PR 批次已退役 **25** 个。原 [TASK003 冻结 94 行审计](LOCAL-DP-TASK003-SHELL-TRIAGE-20261019.md) 51 条“generator/history candidate”中，25 条已删除，余下 **26 条仍需复核**。**26 是候选数，不是获准删除数，更不是 69 个 Shell 全部过时。** 其余 43 个任务 Shell 也未因此被判定为无用。
- 已有真实迁移后的业务 E2E：Self-Runner [#39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)、[Helm GitSync #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)、[E2E + PG Readback + same-batch SKIP #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433) SUCCESS；这是**旧冻结业务 SHA 的 PASS**，不能代表本轮未来新 HEAD 的 PASS。
- **不以某时刻之后未修改、Shell 文件名、无 grep 命中、仅单次 NEW_ONLY E2E 成功作为删除条件**。未被代码引用的手动 PG 恢复/锁修复/故障审计入口也可能是正式功能。删除率不计入业务完成率。

## 2. 一次性分析对象与允许删除范围

本轮只对原冻结表里尚存的 **26 个 TASK003 候选**集中调查和建立一次性决策矩阵，默认只允许移除其经证明为 C/D 的**历史一次性源码安装器/生成器/重复历史脚本**。自动检测器必须只针对明确 allowlist 的具体文件实施删除；不执行 `find -mtime`、删除整个 `scripts/task003` 或 `tests/task003`、递归删除零引用文件，也不修改运行语义。

| 判定 | 允许行动 | 最低标准 |
| --- | --- | --- |
| A — 当前业务/执行器 | **KEEP** | DAG、Spark、Writer、Synthea、Runner、SQL、发布/验证、实际转换等正式入口和直接/间接依赖。 |
| B — 工程/安全/维护 | **KEEP** | Unit/Contract/回归、CI/Docker/Helm/K8s、Fencing、Claim、Lease、reservation、Rollback/PG Recovery、诊断和有效人工运维入口。 |
| C/D — 历史一次性安装器或已被正式源码完整替代的产物生成器 | **DELETE CANDIDATE** | 冻结 Git 可恢复；输出源码/Contract/Tests/Template 与当前正式文件**全字节相同**（包括末尾换行）；无动态生成独有输出、运行副作用或独立职责；无有效消费者、外部入口、镜像/工作流/测试保护依赖；所有目标/消费者经自动报告核实。 |
| E — 未知/动态/可能手动执行/安全依赖 | **HOLD** | 有无法解释的变量组合、动态 `source`/`eval`、外部 Workflow、固定旧 branch、发布保护、参数化 Contract、历史灾难恢复能力、无可替代产物或不能跑必要回归。不能把 HOLD 当作失败，也无需为清理率删除。 |

**已识别强制 HOLD/KEEP：**
- `05g4c1-prepare-processed-manifest-publisher-source.sh`：`05g4c2-prepare-processed-manifest-publication.sh` 与 `05g4c2-publish-processed-manifest.sh` 的 `git diff --quiet` checkpoint guard 明确引用其路径；即使两个 heredoc 产物匹配也不可未经变更、测试就删除。
- `06c4e-prepare-committed-cdm-visit-materialization.sh`：动态 CDM Contract 生成内容、依赖和回放闭包未证实；原 E/HOLD 继续。
- `05g2c2c3a-acquire-writer-reservation.sh`、`05g2c2c3c2-launch-visit-processed-writer.sh`、`05g2c2c3d1-observe-visit-processed-writer.sh`、`05g3a-build-processed-dq.sh`、`05g4a-build-processed-manifest.sh`、`05g3b2-prepare-processed-dq-publication.sh`、`05g4c2-prepare-processed-manifest-publication.sh` 等**行为执行/发布/安全相关**的脚本，不得仅依据 2026-10-19 粗分类“generator/history candidate”删除；没有额外实际替代和演练证据则 KEEP/HOLD。
- 43 个非候选 Task003 Shell、全部正式业务 DAG/Python/Spark/SQL/Contract、有效 tests、Helm/K8s/Secrets/RBAC、Task004 NEW_ONLY Runner 工作流及生产图像入口不在本轮批量删除范围。

## 3. 只做一次的批量分析：脚本实现与报告合同

在**隔离的 Runner Checkout**（禁止污染常驻开发目录）固定 Healthcare / Self-Runner **完整 Commit SHA**，一次读取工作树，运行一个不调用业务写入/集群管理 API 的只读审计器；不通过几十次单独 GitHub Contents API 构造扫描。

1. `git ls-files -s` + `git rev-parse HEAD` + `git status --porcelain`：输出当前 26 候选和 43 非候选及全局 tracked 文件和 Blob SHA；工作树必须 clean。跨仓比较本轮起点与当前 SHA 的新增/修改路径；发现并行改动则重新分析受影响范围。
2. 收集有效入口和消费者：Healthcare **全部** Workflows / `action.yml` / DAG / K8s / Helm / Dockerfile / Entrypoint / `local-data-platform` Python/SH/SQL/Contract/Tests + Self-Runner **全部** Workflows/Action/Task Executor（不只抽样 16 个）；静态 AST import、`source`/`exec`/`bash`/`python`、Docker COPY、GitSync/构建 Context 和代码生成目的路径；匹配完整路径、basename、可解析变量与固定/动态 branch ref。目录型批量复制、容器构建 Context 和 GitHub `working-directory` 不得仅靠 basename 搜索视为无引用。
3. 一次性拆解候选 Shell 中的所有 `cat >` heredoc、`cp`、`sed`、模板替换、`kubectl`、`psql`、`aws/s3`、Git 和外部命令；对完整可证明的静态产物以**字节/哈希**比较当前 Git 正式输出。任何动态输出/未捕获输出/有运行副作用或产物不存在一律 HOLD，不允许“只对已找到的输出 MATCH”冒充全匹配。
4. 输出逐文件 TSV/JSON/Markdown：路径、当前 Blob、类型、完整产物数量与 SHA、真实消费者、动态/手动/安全风险、单测保护、分类 KEEP/DELETE/HOLD、为什么保留/删除、固定 Main 恢复链接、检查结果。**禁止仅给一个删除文件名单而没有 KEEP/HOLD 决策。**
5. 初次只做 Dry Run，读取报告并锁定**显式 DELETE allowlist**，不提前修改正式源码。选择性更新受影响 CODE.md 导航和历史恢复 URL，确保原正式输出不删除、不误改。

## 4. 两次真实运行与精确 SHA 一致性门

**A. 删除前的当前 Main 基线：**新建唯一 `batch_id`，运行 Synthea → S3 READY → Airflow → Spark Person/Visit → Atomic OMOP Writer → 独立 PG/S3 读回 → 同 Batch 幂等 SKIP。记录 Runner commit、Healthcare checkout、GitSync 实际 Head/DAG 内容 SHA、镜像 ID/digest、Spark driver 实际来源、输入参数/Manifest、Person/Visit 的 count/唯一键、Writer insertion/update、Reconciliation 和数据库前后计数。失败先修真实业务，不进行盲删。

**B. 删除后的候选版本：**在**一个清理 PR** 中仅删除显式 allowlist 的 C/D 文件及修正 CODE.md/必要检查引用，随后完成：
- `bash -n`、适用单测/Contract/负向已删源码路径检查、CODE Map/相对文档链接/OpenSpec Gate、Airflow 3.2.2 DagBag Parse、各受影响 Docker Clean Build + 模块 `__file__`/Entrypoint Smoke、Writer Fencing/rollback/Claim/recovery 模拟测试；CI 必须绑定 PR **最终** HEAD。
- 对候选版本做全新唯一 Batch 的 **真实 E2E**。必须独立证明 Executor Checkout、实际 Airflow GitSync DAG 内容、Spark 使用的代码和镜像确实来自/匹配候选版本，不能拿 Main 上旧 GitSync、旧 GHCR Tag/旧 Image 或仅 PR CI 代替候选 E2E。
- 如现有单实例 Airflow GitSync **只能跟随 Main**、不能安全地切换至 PR SHA，则不能声称已验证候选 PR。选用隔离测试 Helm/DAG/Namespace/带 digest 的镜像（与当前集群其他工作不冲突）进行候选验证；若不可建立这种隔离，标记 **CANDIDATE_RUNTIME=NOT_VERIFIED/HOLD**，不要为了让测试 PASS 临时切主系统 GitSync，也不以“上线 Main 再看看”冒充预合并安全验证。
- 对不同 NEW_ONLY 随机 Batch 用**合同/维度不变量、计数核对、幂等和 Referential Integrity** 比较；不同随机人群的记录数本不应机械要求相等。禁止复用已提交 Batch 触发非幂等路径或重放历史成功批次。
- 发生运行错误，只回滚 Git 的候选删除变更（PR revert/restore），记录失败文件和阻断。Git 恢复不等于 PG/S3/K8s/镜像快照；应避免任何非必要的数据库/存储清理。

## 5. 归并门、快速退出与不做事项

- **文档设计 PR（本轮）**：仅将决策写入现有 `relocate-local-data-platform` 的 Proposal/Design/Tasks 和本 Evidence；运行真实 CI，全部适用检查 PASS 后 Squash Merge；**不删除任何业务文件、不触发 E2E**。
- **实施 PR（下一步）**：一次 Runner 批量扫描 → 生成冻结决策矩阵 → 同一组件内尽可能一次删除全部高置信度 C/D → 真实 CI 和候选 E2E → **全部**通过后 Squash Merge；如果绝大多数都为 KEEP/HOLD 或仅 3–5 个 C/D，就停止反复寻找删除对象，直接完成文档/Closeout。最多一个主清理 PR + 必要的修复 PR，避免无限小批次。
- GitHub PR Body 必须有独立两行 `OpenSpec-Change: relocate-local-data-platform`、`OpenSpec-Task: 4.9`；所有 Runner workflow 的真正写动作必须和针对其参数的授权相匹配；Self-Runner 不作为额外备份源。
- 不修改 NEW_ONLY Person/Visit/Writer 合同和 DDL、不改变正式 DAG ID/现行 GitSync 主路径、不删除 Fencing/PG Recovery、不对商业 Azure/Fabric 资源执行 Apply；不更改 `modernize-legacy-task-code` 的边界，不因删代码自动宣布支持 OLD_ONLY/MIXED。
- 删除与 E2E 完成后，补齐 Task 4.1/4.7/4.8/4.9/4.10 实际结果和文档状态；若仍有 E/HOLD，提供明确清单、原因和未来 Owner，而不是假称 100% 清理。仅当 OpenSpec Task 5 真实满足时才 Archive。

## 6. 当前状态（方案 PR 创建前）

- `PLAN=READY_FOR_PR`
- `FROZEN_CANDIDATE_MATRIX=PENDING`
- `BASELINE_NEW_BATCH_E2E=NOT_EXECUTED_FOR_THIS_SHA`
- `BATCH_DELETE=NOT_STARTED`
- `POST_DELETE_CANDIDATE_E2E=NOT_EXECUTED`
- `CHANGE_ARCHIVE=BLOCKED`

本方案不能倒写为此前 7 批的实施记录；之前 PR/evidence 均保留为事实历史。
