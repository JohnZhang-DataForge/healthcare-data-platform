---
status: active
scope: legacy-skill-35-chapter-coverage-audit
last_verified: 2026-10-16
source_sha: 0f4827e0c6d4b8b32caf8b7777e5dde5e0a24f7b
legacy_snapshot_sha: 49936b51d4beadc69383e931efc3e72d2f0db47e
---

# 旧 Skill（SKILL-cn.md）35 章完整性审计

**目的**：核对旧 Skill 在 Main 退休后是否丢失有价值的工程知识；明确每章的现行归属、需要补充或已被取代的内容。本文是**一次性历史映射和审计证据**，不是新执行型 Skill，不能单独授权任何 Shell、K8s、PG、S3 或 Azure 操作。

**来源：**[旧 Skill 完整快照](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/skill/SKILL-cn.md)，约 861 行、35 个编号章节，核对时间为 2026-10-16；静态核对源为 Healthcare Main `0f4827e0c6d4b8b32caf8b7777e5dde5e0a24f7b`。历史日期与 Main Source SHA 用于追溯，不是 Runtime 复验。

**判定口径：**
- **覆盖**：现行权威规则已说明同类要求，无须复制。
- **补充**：规则仍然有价值，但现行文档缺少关键细节；本轮增补到相应权威位置。
- **替代**：旧规则与新的目录/架构/语言/任务管理决策不符，不作为新规范；原文保留历史证据。

## 一、35 章对照表

| 旧章节 | 原规则主题 | 判定 | 核对结论与处理 | 当前文档 |
| ---: | --- | --- | --- | --- |
| 1 | 目的与可重现性 | **覆盖** | 小步交付、复现与验收已有规则 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 2 | 宿主机固定路径 | **补充** | 区分旧宿主机/Runner、保护历史目录 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 3 | 单 STEP 验收 | **覆盖** | 失败修同一步，分级验收 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 4 | 单 Bash 交付 | **覆盖** | 一次一段完整 Bash；脚本按组件归属 | [Agent 规则](../development/AGENT-RULES.md) |
| 5 | Source guard | **补充** | 可执行 Helper 防止误 source | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 6 | 严格模式 | **补充** | 只在子进程开启，不污染交互 root Shell | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 7 | 输出 BEGIN/END 与 EXIT trap | **补充** | 原始退出码、输出结束标记、真实断言 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 8 | Runtime truth | **覆盖** | 独立读回而非文件/退出码推定成功 | [测试证据](../development/TESTING-AND-EVIDENCE.md) |
| 9 | Canonical source 与临时 Installer | **补充** | 正式源码权威、临时 Helper 不作隐藏依赖 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 10 | Generator 同步修复 | **补充** | 修改生成器并重新生成、检查结果 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 11 | 大型 Markdown 交付 | **补充** | PR/文件交付与完整性检查，避免复制损坏 | [文档治理](../development/DOCUMENTATION-GOVERNANCE.md) |
| 12 | 双语及 -cn.md 规则 | **替代** | 不再强制一中一英或统一后缀，按读者选择 | [文档治理](../development/DOCUMENTATION-GOVERNANCE.md) |
| 13 | Development Lessons 维护 | **补充** | 原始历史证据留存，跨任务经验提炼 | [文档治理](../development/DOCUMENTATION-GOVERNANCE.md) |
| 14 | TASK/STEP 编号语义 | **覆盖** | 保留过程编号，不命名新增正式源码 | [命名规范](../development/CODE-ORGANIZATION-AND-NAMING.md) |
| 15 | Task 序号的永久 Shell 命名 | **替代** | 正式新脚本以组件/能力命名，旧脚本保留 | [命名规范](../development/CODE-ORGANIZATION-AND-NAMING.md) |
| 16 | Reset 默认允许/禁止清理 | **补充** | 白名单仅限临时；持久数据默认禁止 | [安全操作](../operations/SAFE-OPERATIONS.md) |
| 17 | Idempotency / Stable ID | **补充** | 重跑不膨胀、Stable ID 不改 | [测试证据](../development/TESTING-AND-EVIDENCE.md) |
| 18 | Batch 身份冲突规则 | **补充** | 同 batch_id 不同 SHA 必须 STOP | [安全操作](../operations/SAFE-OPERATIONS.md) |
| 19 | Publish boundary | **补充** | DQ/COMMIT/READY 分阶段，发布标记最后写 | [安全操作](../operations/SAFE-OPERATIONS.md) |
| 20 | Mutation 分阶段模型 | **覆盖** | 只读预检、单独授权、独立核验 | [安全操作](../operations/SAFE-OPERATIONS.md) |
| 21 | No Blind Retry | **覆盖** | Unknown 先读持久状态 | [安全操作](../operations/SAFE-OPERATIONS.md) |
| 22 | PostgreSQL Sequence 间隙 | **补充** | 不强制 gapless，不擅自 setval 回退 | [安全操作](../operations/SAFE-OPERATIONS.md) |
| 23 | Spark Driver Logs / Artifacts | **补充** | 结构化 Artifact 优先，wrapper 失败不盲重跑 | [安全操作](../operations/SAFE-OPERATIONS.md) |
| 24 | Shell Parser 陷阱 | **补充** | producer 退出码、stdin、grep 字面量/正则 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 25 | Git Checkpoint | **补充** | 精确暂存、staged diff、远端 SHA 检查 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 26 | 文件末尾/空白 | **补充** | 保留单个 EOF newline、格式检查 | [开发流程](../development/DEVELOPMENT-WORKFLOW.md) |
| 27 | Runtime/Secrets 不入 Git | **覆盖** | 敏感凭据和原始业务文件不提交 | [Agent 规则](../development/AGENT-RULES.md) |
| 28 | TASK Closeout 条件 | **补充** | 核心 Verifier、独立读回、PR/证据闭环 | [测试证据](../development/TESTING-AND-EVIDENCE.md) |
| 29 | TASK003 作为 Reference Implementation | **替代** | 参考历史思想，不复制全部 Bash/旧目录 | [命名规范](../development/CODE-ORGANIZATION-AND-NAMING.md) |
| 30 | 代码通用化方向 | **覆盖** | 按组件/Domain 拆公共逻辑并保护兼容 | [命名规范](../development/CODE-ORGANIZATION-AND-NAMING.md) |
| 31 | 旧 Pod/Image 两镜像路线 | **替代** | 历史方案不能强制未来镜像分层 | [当前架构](../../architecture/SYSTEM-OVERVIEW.md) |
| 32 | 旧 Airflow Generate Synthea 目标 | **替代** | 已被独立 Producer + READY Consumer 取代 | [当前数据流](../../architecture/DATA-FLOW.md) |
| 33 | batch_id vs pipeline_run_id | **补充** | 一个 Batch 可对应多个运行事件 | [测试证据](../development/TESTING-AND-EVIDENCE.md) |
| 34 | Agent 安全行为 | **覆盖** | 限界、权限、状态分级、禁止盲动 | [Agent 规则](../development/AGENT-RULES.md) |
| 35 | 原 SKILL 自维护流程 | **替代** | 不再更新旧 Skill；按主题更新现行文档 | [文档治理](../development/DOCUMENTATION-GOVERNANCE.md) |

**合计：35 章；已覆盖 10 章，本次补充 19 章，历史替代 6 章。** 各项是规则覆盖率和合理性审计，**不是**在当前运行环境重新执行全部历史步骤。

## 二、额外的历史状态纠偏

旧 Skill 的编号章节之前还存在“当前执行模式”段落（不计入 35 章）。其中 TASK004 STEP04A 是唯一 NEXT、TASK004 overall IN PROGRESS、旧 `docs/tasks/TASK-STATUS.md` 是唯一现状，以及 Airflow 直接 Generate Synthea 等，都只反映当时历史设计/状态。后续已完成的 NEW_ONLY Person/Visit 实际验收、Producer/Consumer 解耦和新文档治理以[项目状态](../status/PROJECT-STATUS.md)、[整体架构](../../architecture/SYSTEM-OVERVIEW.md)和[数据流](../../architecture/DATA-FLOW.md)为准。**不能据旧 Skill 触发任何批次重放或数据库写入。**

## 三、本次回填的长期规则

- [开发工作流](../development/DEVELOPMENT-WORKFLOW.md)：Source guard、Shell 子进程严格模式、BEGIN/END+EXIT trap、Parser 陷阱、Canonical Source/永久 Generator、精确 Git Checkpoint、文本文件卫生。
- [安全操作](../operations/SAFE-OPERATIONS.md)：Reset 边界、同批次不同 Hash 冲突、READY/APPROVED 发布门、Unknown 后独立读回、Sequence 不要求 gapless、Spark Artifact 优先。
- [测试与证据](../development/TESTING-AND-EVIDENCE.md)：安全重跑与稳定 ID 断言、冲突负向用例、Batch/Run 身份区分、Publish/Closeout 的测试门槛。
- [文档治理](../development/DOCUMENTATION-GOVERNANCE.md)：原始 Lessons/Run 保留、可复用经验提炼、文档语言及大文件交付新策略。

## 四、历史规则不得重新启用

不得恢复 `docs/skill/`、旧 `docs/runbooks/` 作为 Agent 当前入口，不以 `scripts/taskNNN/`、旧固定绝对宿主机路径、新镜像拆分计划或“Airflow 生成 Synthea”作为新增代码规范。不强制每篇架构文档写双语副本，不用 TASK003 旧物理脚本结构机械复制未来实体。旧证据应通过固定 Commit 访问，不修改其原文。

**维护约定**：审计完成后，未来规则调整只编辑现行主题文档，不循环增长本审计表或旧 Skill；功能实现和运行验收各由实际代码、Contract、PR、真实 Run/Readback 负责。有关历史证据的固定入口见 [Legacy Docs Snapshot](LEGACY-DOCS-SNAPSHOT.md)。
