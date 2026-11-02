# Design — Fabric Git-native Notebook onboarding

## Source of truth and deployment

- `healthcare-data-platform/main` 的 `azure-fabric/workspaces/healthcare-omop/` 是现有 Workspace Git Folder 根目录。已证实的发布链为 Healthcare Push → Dispatch → Private Self-Runner OIDC → Status → UpdateFromGit → 真实定义读回；新 Notebook 不走“Portal 手工建 + 导出”，也不走“REST 创建空 Notebook + updateDefinition”的历史失败路线。
- 当前业务 Notebook `nb_fhir_ingest` 和 Pipeline `pl_fhir_ingest` 是固定身份的现存 Item，继续使用原来的 exact allowlist/remote Modified/local-only serialization 语义验证；新创建路径**不可**使这两个 Item 的变更校验变宽。
- 新 Notebook 第一阶段仅接受 Workspace Git 根级 `nb_<slug>.Notebook/.platform` + `notebook-content.py`，名字、类型、唯一 logicalId 由仓库声明；不得复用现有 logicalId，也不得在 Fabric Workspace 已有同名同类型物理 Item 时盲目创建。
- 要求 Notebook 为 Fabric Native `.py` 格式、有 PySpark kernel 和被验证的 `env_healthcare` 逻辑绑定；仅声明资源、不执行任何代码。任何关联的 New Pipeline/Environment/Lakehouse、Delete、Workspace 修改、冲突、不明附带文件必须 HOLD。
- Fabric `Get Status` 的 `remoteChange=Added` 代表新增资源（Microsoft REST 枚举），不是 `Created`；新 Item 的 `fileChanges` 可能包含 `.platform`、`notebook-content.py`；其余字段/冲突按未知失败关闭。
- `UpdateFromGit` 不能仅选择某一条变更，会同步当前提交下的全部变更。因此如果 Git status 含有未批准的另一个 Item，必须 **整批 HOLD**；每次只做一次无重试 POST，未知 ACK 则独立只读审计。
- POST 后独立查验 Workspace 创建的同名唯一 Notebook、实际原生 `.py`、正确 Environment 映射和代码 Cell；还要保持原业务 Notebook/Pipeline 的 HALT 读回；验证失败按 UNKNOWN，不盲目二次提交。

## API vs Git semantics

Microsoft 文档规定，UpdateFromGit 会对缺失的 Git Item 创建 Workspace Item；REST GetStatus ChangeType=`Added`。这与 REST Notebook Create/UpdateDefinition 是**两个独立路径**，不可混为一谈。参考：
- https://learn.microsoft.com/en-us/fabric/fundamentals/understand-best-practices-fabric-cicd
- https://learn.microsoft.com/en-us/rest/api/fabric/core/git/get-status
- https://learn.microsoft.com/en-us/rest/api/fabric/core/git/update-from-git

## Evidence gates

1. 代码/文档 OpenSpec Change、PR 与主分支 Required CI。
2. 本地/CI 反例：冒名、复用 logicalId、非 Notebook、删除、冲突、Workspace 同名、混杂未允许 Item、重复提交、篡改代码/Environment、无凭据 Runner 路径。
3. 独立可信运行：新增一个无数据访问的测试 Notebook Git 定义 → Git main → 自动 Dispatch → Self-Runner 单次 Git Update → GetDefinition 严格读回 → 明确清理（需要独立安全 Gate）或保留为开发资产。此 Gate 未完成前标记 `LIVE_NEW_NOTEBOOK_UNVERIFIED`。
4. 现有 `nb_fhir_ingest` 的实际 Spark/业务 ETL 验收是另一个 Change；本 Change 不解除 HALT。

## Failure and rollback

对不明状态返回 HOLD，保留准确 Git SHA/Run/预检与读回报告。不能通过自动删除或覆盖已有业务资源恢复状态；如确实要回滚新 Item，必须确认精确身份和影响范围，再由独立审批执行。先只改代码与测试时，不制造 Fabric 云端资源。
