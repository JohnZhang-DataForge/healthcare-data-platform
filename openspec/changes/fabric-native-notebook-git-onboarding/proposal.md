# Proposal

## Why

现有 Healthcare `fabric-git-deploy.yml` 只匹配固定的 `nb_fhir_ingest` 和 `pl_fhir_ingest`；Self-Runner `fabric_git_auto_update.py` 只接受两个固定 Item 的 `remoteChange=Modified`。增加任何新 Git-native Notebook 时，即便 Dispatch 成功，部署仍会 fail closed。这与 Git 是唯一源码权威、无需 Portal 手工创建的已批准目标不一致。

## What Changes

- 让 Healthcare main 上原生 Notebook 的新增/修改（根级或未来文件夹）触发可信的私有 Runner Dispatch，沿用不可变 commit SHA 和 main-only OIDC 约束。
- Self-Runner 增加独立、严格的 `remoteChange=Added` Notebook onboarding：来自 main 的真实 Git Native `.platform` + `notebook-content.py`、唯一 logicalId、Workspace 无同名资源、单次 UpdateFromGit、独立原生定义与身份读回；既有两个业务 Item 的固定保护与本地 serialization guard 不放宽。
- 明确新 Notebook 的根级 Git Native 格式为首期支持范围；新增 Fabric 文件夹/任意新 Item 类型不自动写入。
- 增加正/反例离线测试、文档与真实云端验收 Gate，避免“Workflow 触发 = 已创建”的错误结论。

## Capabilities

### New Capabilities
- `fabric-native-notebook-git-onboarding`: 无需 Portal 先建、从 Git 原生声明创建新 Notebook 的受审部署能力。

### Modified Capabilities
- `ingest-fhir-to-fabric`: 原业务 `nb_fhir_ingest`、`pl_fhir_ingest`、`env_healthcare` 维持既有 HALT 和 pin，新增 Notebook 不自动执行数据作业。

## Impact

涉及 Healthcare Git Dispatch workflow 和 CI、Self-Runner guarded Git updater 和 CI、Azure/Fabric Notebooks CODE/Runbook。目标云端变更仅允许 Git-native 新 Notebook 的创建，**不执行 Notebook/Pipeline，不发布 Environment，不改写 Delta、Blob 或业务记录**。无新增资源的离线验证不能冒充创建 E2E。
