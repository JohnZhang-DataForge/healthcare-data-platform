# Design — Agent 启动导航与 OpenSpec 状态单一来源

## 1. 权威边界

1. **AGENTS.md** 只提供必须即时遵守的安全约束与任务路由，固定简短；不保存 Batch、Run、旧 Fabric 实验历史。
2. **Active OpenSpec** `openspec/changes/<slug>/tasks.md` 是尚在实施的唯一任务状态，`proposal.md`/`design.md` 与 `specs/` 是批准的需求/方案。任务状态以合并后的实际文件为准；独立 PR/Run/读回负责验收。
3. **Current Spec** `openspec/specs/` 只说明已采纳且有验证的行为；已经 Archive 的 Change 只作历史追溯，不再作为当前待办。
4. **System README/CODE** 仍然是长期职责、实现入口及源码所有者的权威；OpenSpec **不会取代**架构、合同、运维或真实代码。
5. **PROJECT-STATUS.md** 只保留兼容入口和动态查询命令，不维护任务/状态复制；原内容完整保存在同目录 `PROJECT-STATUS-HISTORY-20261105.md`。历史资料不被冒充为最新事实。

## 2. 自动查询设计

`.github/quality/scripts/active_openspec_index.py` 是只读 CLI：
- 从给定 `--repo-root` 下的 `openspec/changes/` 枚举直接子目录，排除 `archive` 和隐藏目录，按名字稳定排序；
- 从每个 `tasks.md` 的 Markdown 复选框中统计完成/未完成的编号任务；只展示第一个 OPEN 任务的简短文字，确保不读取完整旧的证据入 Agent 上下文；
- 输出 GitHub/Markdown 可用的相对链接，或者 JSON；缺失 Tasks 显式报告 `UNKNOWN`，不可当作 DONE；无 Active Changes 为正常状态；
- 仅使用 Python 标准库、只读文件；不调用云端 API/GitHub Actions，不写回 `PROJECT-STATUS`、不修改 OpenSpec 本身。GitHub 网页访问可直接浏览 `openspec/changes/`。
- 随任务文件合并而自动变化，**无额外定时任务或文件同步**。PR CI 对其行为做隔离单测、真实 checkout smoke。

## 3. 迁移与安全

- 减少根 Agent 启动字数，但绝不移除代码唯一归属、OpenSpec Change Gate、未经授权不得进行部署/数据写入、未知 COMMIT 先只读核实、Fabric Native 限制、Notebook 必读 Runbook、命名及测试目录规则。
- 现有指向 `PROJECT-STATUS.md` 的外部链接继续有效（兼容 Redirect/Router），系统文档中的架构/验收陈述仍需 SHA 与 Run 依据。
- 原历史文件仅作为冻结快照，放在相同目录维持原有 Markdown 相对链接语义；修改文件名不改写旧事实，不承诺里面的历史 CURRENT 是现在仍有效的结论。
- 不新造 OMOP tasks 内容，也不删除 OpenSpec 证据；OMOP 当前 Source-only/NOT GOLD_COMMITTED 边界保持。
- 新 Workflow 用 `pull_request` + hosted runner + `contents: read`，不接触任何 Secret/Fabric/Runner；现有可信 Required Checks 原封不动。

## 4. 退出条件和回滚

- 新索引能在真实 Git checkout 上列出 Active Changes，跳过 Archive；单测覆盖排序、复选框、空目录、缺失任务、安全只读行为。
- AGENTS → 组件 README/CODE → Active OpenSpec/Tasks → 对应代码/测试的阅读路径清晰可操作。
- 历史 snapshot 全文保留、旧 PROJECT-STATUS 路径仍可访问、所有受影响文档链接及 OpenSpec strict CI PASS。
- GitHub 正常 Required Checks、附加只读索引 CI PASS；最终 PR protected merge 后独立读回 main。若检查失败保持 Change Active。回滚用 Git revert；不触碰 Runtime。
