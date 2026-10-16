# Documentation Lifecycle & Archive Standard v1.0 / 文档生命周期与归档规范

> **2026-10-16 location override / 归档位置调整：** 历史文档已经完整复制到独立的 Private 仓库 [Healthcare-Specs/archive](https://github.com/JohnZhang-DataForge/Healthcare-Specs/tree/main/archive)，并经文件路径、Blob SHA 和大小逐项核对。原 `docs/archive/` 将从此仓库移除。本文旧的 `docs/archive/` 路径与“同仓库归档”操作步骤已不再适用；在完成跨仓库归档政策正式修订前，新增迁移应独立审核，禁止据旧命令向源仓库重建归档目录。

> **状态：CURRENT / 正式生效**  
> 生效日期：2026-10-12  
> 适用仓库：`JohnZhang-DataForge/Self-Runner`、`JohnZhang-DataForge/healthcare-data-platform`  
> 两仓库应保持**本规范内容一致**；各自独立管理文档清单、归档批次、PR 与历史证据。  
> 目标：让新 Agent 从 `main` 快速找到**当前有效**的规则，同时保留可追溯的历史文档与决策。

## 1. 核心原则

1. **Current Source of Truth**：`docs/` 常规目录保留当前有效的操作规范、Agent Skill、架构、TASK Contract、最新状态与必要的技术经验。历史性、已被取代的指导文档应迁入 `docs/archive/`。
2. **Archive in Git**：采用 `docs/archive/YYYY-MM-DD/` 作为重大调整的历史归档。若同一天有多个独立批次，使用 `YYYY-MM-DD-<topic>/`。归档文件在当前 `main` 可读，不依赖切换 Git Tag。
3. **Git History + optional Tags**：归档仍通过 feature branch → PR → merge；Git 保留原始版本、移动与修改记录。Tag 只在重要项目里程碑使用，不作为日常归档的强制条件。
4. **原文保存**：被归档文件原则上以**完整原文**移动，尽量保持原相对目录层级（如 `docs/migration/a.md` → `docs/archive/2026-10-12/migration/a.md`）。不要为了适应新流程重写历史正文；解释写在该批次的 `README.md`。
5. **归档不等于删除知识**：重要的数据库事务、幂等、Manifest、Spark/K8s、数据 Contract、故障恢复等仍有效的经验，应先整理到当前有效的 Lessons/Runbook/Contract，确认无信息丢失后才能归档原文件。
6. **当前开发优先**：文档治理不能要求重新开展企业级 CI/CD 或重新验证已通过的 V8/V9 Runner 链路。不要以“清理全部历史文档”为平台业务开发的前置条件。
7. **不修改运行环境**：普通文档整理 PR 不改业务代码、冻结 Generator/Contract、Actions Workflow、Runner、RBAC、Kubernetes、数据库或存储资源。
8. **不要误判历史记录**：旧 Checkpoint 的 `NEXT` / `NOT_YET` 反映当时状态，不应直接修改历史正文；用当前 TASK 状态索引指向最新验收证据。

## 2. 文件处理决策

| 决策 | 操作 | 条件 |
|---|---|---|
| **KEEP** | 保留在当前目录 | 当前有效且仍被开发流程依赖 |
| **UPDATE** | 在原位置更新当前文档 | 仍是权威文件，但需对齐最新事实/规则 |
| **MERGE → ARCHIVE** | 先将独有且有效的知识并入权威文档，核对后移动原文 | 重复 Lessons、重叠 Runbook、历史经验汇总 |
| **ARCHIVE** | 原文移动到日期归档目录 | 已被替代的 Pilot、迁移设计、阶段性 Handoff、过期状态说明 |
| **DEFER** | 暂不移动，列出依赖和原因 | 引用未清、内容未审、Contract/冻结边界或仍在使用 |

**禁止**按文件名/日期一键清空 `docs/tasks/`、`docs/task003/`、`docs/handoffs/`、`docs/architecture/`；必须逐文件审查。未确认的文件默认为 **DEFER/KEEP**。

## 3. 每个归档批次的标准目录

```text
docs/
├── README.md                                 # 当前文档入口
├── development/
│   ├── PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md
│   └── DOCUMENT-LIFECYCLE-AND-ARCHIVE-v1.0.zh-CN.md
└── archive/
    ├── README.md                             # 归档总索引与使用说明
    ├── YYYY-MM-DD/
    │   ├── README.md                         # 此次归档清单、原因、替代文件、版本证据
    │   ├── migration/old-plan.md
    │   ├── runbooks/old-pilot.md
    │   └── handoffs/old-handoff.md
    └── YYYY-MM-DD-topic/
        └── README.md
```

这是目录规则示例，**不是要求每个仓库必须有相同业务子目录**。不要创建没有真实文件的空目录。

## 4. 归档批次 README 必填字段

每次重大调整在 `docs/archive/<batch>/README.md` 记录：

1. **归档原因与适用范围**：为什么调整、哪些当前规范取代了旧文档。
2. **来源基线**：仓库名、归档前 `main` 的完整 40 位 SHA、日期。
3. **逐文件映射**：原路径 → 新路径、KEEP/UPDATE/MERGE/ARCHIVE/DEFER、原因。
4. **替代权威文件**：新 Agent 应该阅读的准确相对路径。
5. **经验提炼清单**：MERGE 时说明哪些仍有效的独有知识移入何处，哪些只保留历史。
6. **引用检查**：旧路径引用搜索结果、已修复的当前文档引用、仍保留的历史引用和处理理由。
7. **验收结果**：Git 变更范围、文档/路径检查结果、是否触碰冻结源码、PR 编号、最终合并 SHA。合并 SHA 在合并后更新总索引或后续独立记录，**不得提前猜测**。
8. **阅读警告**：Archive 是历史背景，不是当前有效操作指令。

**归档后的原始正文默认不可变**。发现历史错误，优先在批次 README 添加说明，或在当前权威文件纠正，不回写旧文档。

## 5. 归档实施步骤（每次执行）

1. **盘点**：读取当前 `main` 文件树、最新规范、TASK Contract/Checkpoint、Lessons，列出逐文件分类和依赖；先给出候选清单，不直接移动。
2. **确认边界**：判断哪些是过时方案、哪些是冻结的业务证据、哪些技术经验需要提炼；列出所有被其他 Markdown/脚本/Workflow 引用的路径。
3. **新建 feature 分支**：在准确 `main` 基线工作；不要直接 Push 到受保护的 `main`。
4. **先 UPDATE/MERGE**：把仍有效内容写入当前权威文档，保留原意与适用范围；若不能证明覆盖完整，则保持 DEFER。
5. **再 ARCHIVE**：完整移动历史文档到 `docs/archive/<batch>/<原 docs 相对路径>`，创建批次 README。
6. **检查**：核对归档文件内容与原文一致（必要时比较 SHA/内容）、全部移动映射、当前文档链接、引用修复、最新 TASK 状态、Git diff。只改文档；不得误删 Contract/冻结文件。
7. **PR 审核与合并**：说明 KEEP/UPDATE/MERGE/ARCHIVE/DEFER 清单，检查后通过 PR Merge Commit 合并；不把 PR 创建当成已归档。
8. **验收**：从合并后的 `main` 核验归档路径和当前入口存在；在总索引记录批次 PR/Commit。出现失败时保留分支、修复后重新核验。

**避免移动时自动修改历史文件正文**：Git 可能将“移动 + 大改”显示为删除/新增，影响审计；移动和当前文档更新可以在同一个 PR，但应在审查中分开说明。

## 6. 新 Agent 的读取规则和冲突处理

1. 先读 `docs/README.md` 和 `docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md`。
2. 读当前 TASK 的 **Contract / 冻结边界**、最新真实 **Checkpoint / Closeout** 和相关 Skill/Lessons；按需阅读架构。
3. `docs/archive/` 只用于追溯历史决策、故障背景与旧版本内容；**不得从 Archive 恢复旧的操作要求来覆盖当前规范**。
4. 冲突按**领域权威**判定：开发流程以当前 Operations 为准；业务数据语义/冻结边界以当前 Contract 为准；任务进度以最新真实验收证据为准；运行代码以 Git 当前真实内容为准。不可简单以文档时间较新就覆盖 Contract。
5. 发现矛盾或遗漏时，先提出逐文件的修订方案与证据；不擅自重写历史记录。

## 7. 日常维护频率

- **每个 STEP**：更新必要的 TASK Checkpoint；有新坑才补 TASK Lessons；不强制归档。
- **每个 TASK**：更新当前状态索引；提炼跨 TASK 的经验；检查是否需要归档。
- **重大架构/流程调整**：创建日期批次、README、逐文件映射，执行本规范完整流程。
- **开发操作手册变更**：同步两仓库的正式规范；不因新增普通 TASK 自动升级版本。
- **本规范变更**：先审查影响，再以新版本 PR 更新两仓库；历史版本按同样规则归档。

## 8. 本次规范发布的边界

此文档仅确立**未来的整理规则**，不代表任何历史文档已移动、合并、删除，也不代表已完成旧路径引用检查。后续首次整理应另行做**完整文件级盘点与归档 PR**。当前 V8/V9 验证通过的开发模式继续有效。
