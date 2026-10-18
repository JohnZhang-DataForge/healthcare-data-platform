---
status: reviewed
scope: openspec-g0-baseline-audit
last_verified: 2026-10-18
source_sha: f79871f4ff4a793aa30f5d1f4e3a52656ecfeb50
evidence:
  - https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/209
  - https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.3
---

# OpenSpec G0 — 只读基线与前置条件审计

> **G0 RESULT: COMPLETE — STATIC READ-ONLY AUDIT.** 只证明截至 2026-10-18 本文所列的 GitHub 基线、文档/CI 现状、官方公开发布信息已核对；**不表示目标 Runner 的 Node/npm 已实际检测，不表示已安装 CLI、初始化 OpenSpec、执行 GitHub Workflow 或部署业务服务**。执行环境版本与 CLI 输出须在 G1 单独捕获后才能判定 G1 PASS。
>
> [G0–G7 唯一实施计划](OPENSPEC-IMPLEMENTATION-PLAN.md) · [OpenSpec Readiness](OPENSPEC-READINESS.md) · [开发命名规范](../development/CODE-ORGANIZATION-AND-NAMING.md)。

## 1. Git 事实基线（固定 SHA）

| 核对目标 | G0 实际观察 | 后续动作 |
| --- | --- | --- |
| Healthcare 仓库 | \`JohnZhang-DataForge/healthcare-data-platform\`，\`main\` SHA \`f79871f4ff4a793aa30f5d1f4e3a52656ecfeb50\` | G1 开始前再次读取最新 Main |
| Self-Runner 仓库 | \`JohnZhang-DataForge/Self-Runner\`，\`main\` SHA \`93ab72edd97d42ad77a371bb7c1365989ae97fd5\` | G4 接力测试前重新核对 |
| Healthcare 未合并 PR | 只读 GitHub PR 查询：0 | 新 PR 不应复用旧 Bootstrap |
| Self-Runner 未合并 PR | 只读 GitHub PR 查询：0 | 本次不改 Runner |
| 原 OpenSpec PR #164 | **CLOSED / NOT MERGED**；旧 config 引用了已失效的 \`docs/\` | 绝不直接合并或恢复 |
| [方案 PR #209](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/209) | **MERGED**；实施计划处于 Main | 本计划为阶段权威 |
| \`openspec/config.yaml\` | Main 只读获取结果 \`404 NOT_FOUND\` | **尚无已初始化 OpenSpec 的证据**，G1 才执行官方 Init |
| \`data-platform/README.md\` | Main 只读获取结果 \`404 NOT_FOUND\`；物理迁移未启动 | G5 先审 Change、G6 才允许迁移 |
| 旧 \`docs/README.md\` | Main \`404 NOT_FOUND\`，历史记录由冻结 Git Snapshot 提供 | 不恢复旧目录或旧上下文 |

固定历史基线链接：[Healthcare Main](https://github.com/JohnZhang-DataForge/healthcare-data-platform/commit/f79871f4ff4a793aa30f5d1f4e3a52656ecfeb50) · [Self-Runner Main](https://github.com/JohnZhang-DataForge/Self-Runner/commit/93ab72edd97d42ad77a371bb7c1365989ae97fd5) · [旧 PR #164](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/164)。

## 2. 官方 OpenSpec / Node / CLI 静态核验

**核对时的候选固定安装版本**：\`@fission-ai/openspec@1.14.3\`。官方 [v1.14.3 Release](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.3) 在 2026-10-17 发布；官方 [package.json](https://github.com/Fission-AI/OpenSpec/blob/v1.14.3/package.json) 声明 \`engines.node >=20.19.0\`。候选版本并非本次实际安装结果，也不表示目标 Runner 的 Registry 能成功拉取。

| 预定 G1 只读/受控检查 | 核对状态与理由 |
| --- | --- |
| \`node --version\`、\`npm --version\` | **G1 必做**：在真正用于 Init/Validate 的执行环境核对。现有业务 Runner 的 Node/npm 实装版本**未核实** |
| \`npm view @fission-ai/openspec@1.14.3 version engines --json\` | **G1 必做**：实际 Registry 可获取性检查，不能仅凭 GitHub Release 假定 npm 可达 |
| \`openspec --version\` | **G1 安装之后执行**，记录实际版本；此轮没有安装或执行 |
| \`openspec init --tools none\` | 官方支持的非交互式最小初始化候选；优先避免自动生成大量 Agent 插件文件，**不可搭配 \`--force\`** |
| \`openspec schemas\`、\`openspec validate --all --strict\` | 官方 CLI 支持，G1 根据生成的实际项目内容观察输出和 Exit Code |
| \`openspec validate --archived\` | G3 后续可作为归档完成任务检查；**与业务 E2E 读回不同** |
| Change \`.openspec.yaml\` 中 \`skip_specs: true\` | 官方针对纯 Refactor/Tooling/Docs Change 支持；G5 使用时须以 G1 固定版本验证 |

官方依据：[Installation](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/start/installation.md)、[Setup](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/start/setup.md)、[CLI](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)、[Release v1.14.3](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.3)。

**环境决定：**G1 推荐使用可审计的独立 GitHub-hosted \`ubuntu-latest\` CI 工作流，通过 \`actions/setup-node\` 明确选择 Node 22，并固定 OpenSpec 包版本；若选择已有 Self-Runner，先执行实际 Node/npm 只读检查，不能照搬宿主机的假定配置。GitHub Actions \`ubuntu-latest\` 的实际预装版本不能替代明确版本固定。安装/初始化的证据在 G1 保存，不在 G0 伪造。

**Agent 集成决定：**G1 先走 \`--tools none\` 的标准根目录 \`openspec/\`，G2/G4 再根据实际 Agent 工具选择受支持的命令/Skills，避免在 G1 把所有工具集成都生成进仓库。仓库原有 \`AGENTS.md\` 继续是 Agent 权威入口。

## 3. 实际命名与 CI 现状

- [命名规范](../development/CODE-ORGANIZATION-AND-NAMING.md) 与根 [AGENTS.md](../../../AGENTS.md) 已强制新增维护代码采用**组件/功能**命名，拒绝新 \`taskNNN/stepNNN\` 源码路径，保留已验收的 Legacy Runtime 身份。
- 现有 [Component Code Naming Workflow](../../../.github/workflows/code-component-naming-check.yml) 在 \`pull_request\` 使用 \`ubuntu-latest\`、Python 单测、CODE Map 校验和 [新代码命名检查器](../../../scripts/quality/check_new_code_names.py)。
- **确证缺口**：上述 Workflow 的 \`pull_request.paths\` 和 Checker 的 \`ROOTS\` 均**没有 \`data-platform/**\`**；检查器使用 \`git diff --no-renames --diff-filter=A\`，纯历史移动可能被归为新增文件。**G3** 必须增加覆盖与严格限定的 Legacy 搬迁例外正/负测试；**G6** 才准真实移动。
- [PR #209](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/209) 对应的 [Documentation Relative Links Run #39136532662](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39136532662) **conclusion=success**，这证明已有文档链接 CI 可用于本次仅文档 PR 的静态验证，**不等于 OpenSpec CLI PASS**。
- 本次审查只发现现有命名 Workflow 依赖 Python；**尚无已实施的 OpenSpec CLI CI**。G3 才增加 \`openspec validate\` 检查，并锁定 Node/CLI 版本。

## 4. Self-Runner 复用与待修兼容

- [Generic Task Executor](https://github.com/JohnZhang-DataForge/Self-Runner/blob/93ab72edd97d42ad77a371bb7c1365989ae97fd5/.github/workflows/generic-task-executor.yml) 运行于 \`dw-runner-set\`，执行 **Self-Runner 自己仓库中**受控脚本，不能把它当成可任意执行 Healthcare 代码的通用 Runner。
- [Cross Repo Healthcare PR Readonly V4](https://github.com/JohnZhang-DataForge/Self-Runner/blob/93ab72edd97d42ad77a371bb7c1365989ae97fd5/.github/workflows/cross-repo-generic-pr-v4.yml) 虽绑定 Healthcare 准确目标 SHA，却仍包含 \`test -f healthcare/docs/BASELINE.md\`。该 \`docs/\` 已退出 Main，**旧 Workflow 不能不检查就用作 G4 新的通用 OpenSpec 验证**。G4 应选择受控的新验证路径或单独修复该检查，并跑真实 CI。
- [Azure Infra Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/93ab72edd97d42ad77a371bb7c1365989ae97fd5/.github/workflows/azure-infra.yaml) 使用 Self-Runner 并显式 Checkout Healthcare \`main\`；它包含有副作用的 Apply 选项，不属于 G0/G1 OpenSpec Bootstrap 的可复用静态步骤。
- 未查证 G1 目标执行环境的 Node 实装版本、npm Registry 网络通达性、OpenSpec 是否全局安装；必须由 **G1 真实命令** 给出结论。

## 5. G0 结论、风险与下一步

**G0 静态基线与冲突审查 = PASS / COMPLETE**：已记录两仓准确 SHA、PR/目录状态、官方候选版本与 Node 下限、当前文档/命名 CI、Self-Runner 已知兼容风险；没有使用已过时的 PR #164。

G1 入场条件：

1. 从实施时最新 Main 新建独立 Bootstrap 分支（防止 G0 文档合并后的 SHA 漂移）。
2. 在被选中的**实际执行环境**核实 Node ≥20.19.0、npm、\`@fission-ai/openspec@1.14.3\` Registry 可用；固定实际版本、执行输出。
3. 使用官方 CLI Init 建立仓库根目录 \`openspec/\`，核查 \`config.yaml\`、\`specs/\`、\`changes/\` 和意外生成文件；不导入旧 \`docs/\`，不修改 \`data-platform/\`、Self-Runner 或业务源码。
4. 经独立 PR、静态 CI 和人工可审核证据后，才能宣布 G1 完成。G2/G3/G4、G5、G6、G7 **均未开始**。

**本次操作边界：**只读 GitHub 及官方资料审计；允许提交该文档/实施状态记录，**无** OpenSpec 安装、Cloud/K8s/PG/S3/Airflow/Spark 操作或业务批次重放。
