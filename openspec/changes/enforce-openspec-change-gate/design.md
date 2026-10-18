# Design

## Context

2026-10-18 GitHub Main 基线：`a082273b0de98b201aa5adee30dd397e5d40082f`。当前 `.github/workflows/openspec-validation.yml` 仅执行 CLI schema/context、`openspec validate --all --strict` 和临时正负示例；**并不**验证 PR 是否关联 Change。旧 PR #225 的 Component Naming 失败仍成功合并，说明不能仅依靠当前普通 CI 绿灯来声称 Main 的合并安全门已生效。已确认分支报告 `protected: true`，但读取 REST `branches/main/protection` 返回 403；无法核实 required checks/管理员 bypass 状态。

## Decision

### A. 验证器与触发

在 `.github/quality/scripts/check_openspec_change_gate.py` 建立可离线单测的 Python 策略。输入严格限定为 PR 事件正文、Base/Head Git SHA、Git Diff 的路径清单，以及 PR Head 工作树中相应 Change 内容。只有普通字符串/文件校验，不执行任何来源于 PR Body 的 Shell 指令。

`.github/workflows/openspec-change-gate.yml`：`pull_request` 不设置 `paths`，采用 GitHub-hosted `ubuntu-latest`，只读权限，checkout 精确 PR HEAD、`fetch-depth: 0`，读取 `github.event_path`，对 base/head 比较，运行检查器及单元测试；**不会**触发 Self-Runner、数据库/云端、集群/部署。

现有 OpenSpec Static Validation 持续验证官方 Schema / Change 格式，Change Gate 只处理**必有 Change 及 PR 关联**，二者都必须通过。

**受信任执行基线的分阶段上线**：首次 PR #230 负责将 Checker/测试/新 Workflow 正式加入 Main；它的 `pull_request` 工作流会从本次 PR Head 执行代码，**还不具备对恶意自修改 PR 的安全防护**。在 Checker 先进入 Main 后，单独跟进将 Gate 改为 `pull_request_target` 中执行 Base Branch 的受信任 Checker 和单测，HEAD 仅作为只读 Checkout/Data 输入，`contents: read` 并禁用凭据持久化，不执行 HEAD 仓库源码。最终再考虑 Required Check；绝不把过渡态的单次 PASS 当成已解决自修改绕过风险。

### B. 实质性变更与豁免

默认所有改动都需要 Change。仅当 PR Body 有单独一行 `OpenSpec-Exemption: docs-only`，且修改文件**全部属于** `README.md` 或 `documents/**/*.md/.mdx`，且未修改以下治理/架构/状态敏感区时豁免：
- `documents/architecture/**`
- `documents/engineering/**`
- 任意 `**/CODE.md`，以及 `documents/README.md`（导航和工程入口）

其它文件包括 `local-data-platform/**`、`azure-fabric/**`、`platform-portal/**`、`.github/**`、`AGENTS.md`、`openspec/**`，以及根级运行路径，**不得**申请 docs-only 豁免。假冒的小型文档变更以改动路径判定，正文声明不具有超越路径事实的效力。该策略只能进行路径级而非语义级审查，仍需人工 Review。

### C. 关联 / 同步 / 生命周期

开发 PR 须且仅须一行 `OpenSpec-Change: <kebab-case>` 和一行 `OpenSpec-Task: <n.n>`。要求引用的 Change 为 HEAD 下 `openspec/changes/<id>/` 并包含 `.openspec.yaml`、`proposal.md`、`design.md`、`tasks.md`；至少一个正式任务与 PR Body 的 Task 编号完全匹配，`tasks.md` 在本 PR Diff 中有变化，强制同步进度。不能凭空关联 Archive/不存在/空任务列表。

Archive 专用 PR 可引用 Head 下 `openspec/changes/archive/YYYY-MM-DD-<id>/`，但必须是从 Base 下同 ID Active Change 归档而来、不能包含非文档代码改动，且所有正式任务已打勾（禁止误提前完成）。Archive 的 `tasks.md` 必须在 PR Diff 中被移动，并应留下归档证据。Archive 仅是仓库文档生命周期，不自动代表 Runtime 验收。

同一 PR 如果是对 Change 的 Proposal/Design 先行提交，同样需要 Task 记录和 `tasks.md` 更新；不要求对应业务代码已存在。后续每个实施 PR 都必须更新对应 Tasks。过往本地平台变更仅按真实证据继续受 `relocate-local-data-platform` Change 跟踪。

### D. 测试和真实性分级

验证器单元测试包含：有效新建和已有 Change、无关联、重复声明、不合法 slug、恶意路径、丢失/空 tasks、未更新 tasks、虚假 docs-only 例外、允许纯 README/组件 README 豁免、归档成功与不完整归档拒绝、0 变更拒绝、路径安全。

GitHub Action 的成功表示“PR HEAD 符合静态 Change 关联规则”，**不等于**业务代码、Runtime 或已部署。只有把新 Job（`OpenSpec Change Gate / require-change`）设置为 Main Ruleset/Branch protection 的 Required Status Check，并保证不被有权限者绕过，合并失败阻断才具备持续约束；如果 API 无权限，必须明确留出管理员操作项及验证步骤，不能宣称已经设定 Required。

### E. 回滚 / 风险

脚本或分类策略造成误拒绝时先更新同一个治理 Change 和单测，再在精确 HEAD 重新验证；不得将 `paths` 过滤或 broad wildcard 例外作为临时放行手段。对误通过应增加负向测试并复验。禁止为了让 CI 变绿把 `OpenSpec-Change` 伪造到无文件的目录。

## Verification

- Python 标准库 `unittest` 全量质量工具测试及新正负用例。
- PR 确切 HEAD：OpenSpec CLI 1.14.3 `validate --all --strict`，新 Change Gate，Component Code Naming，Documentation Relative Links 均适用。
- 检查 PR Diff 不包含业务源码、集群或云修改。
- Main 合并之后只读核查新的 Workflow/检查器及 docs 已存在；单独核实分支保护规则，不以 Merge Success 或 GitHub branch `protected` 代替 Required 的实测。


### F. Trusted-base hardening and 2026 public-repo policy

第一阶段 #230 的 PR Head 脚本验证保留为普通非特权检查。第二阶段新增只读 `OpenSpec Trusted Change Gate` 使用 `pull_request_target`，来自仓库默认分支的 workflow/Checker/Test 属于受信任代码，PR Head 单独 checkout 到 `candidate/`，仅用 Git Diff 与 `Path.read_text` 当作**数据**检查；禁用 checkout token 持久化、限制 `contents: read`、不能从候选分支运行任何命令或模块。`--repo-root` 指向独立候选目录，防止基线检查器误扫 Base Tree。

安全限制：`pull_request_target` 有提升执行上下文，必须确认不运行 untrusted source；若 GitHub 策略阻止此事件，**不能取消策略以换取假成功**。GitHub 于 2026-10-18 公布的 [Securely using pull_request_target](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target) 指出公开仓库默认事件策略将于 **2026-11-02** 强制；管理员需要审查仓库/组织 Actions Policy 是否允许该安全用法。无法核实权限时，此项作为未完成部署门，原普通 Change Gate 保留运行，但不声称防止恶意 PR 自修改。
