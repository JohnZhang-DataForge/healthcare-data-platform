# Proposal

## Why
Healthcare main → Fabric Native Notebook/Pipeline 自动同步已由 Self-Runner Run #41311994774 实证。唯一 Shared Wheel `healthcare_data_engine-0.1.0-py3-none-any.whl` 已在 Git 与 Fabric staging 可见，但发布生效和 Notebook 环境绑定尚无证据。已有只读 Run #41263018957/#41263182097 的 staging=True、published HTTP 404、publishDetails.state=Success，不能以历史 Success 推导最新 Wheel 生效。

## What Changes
- 将 Wheel 源代码/确定性构建、Git Native Environment staging、发布操作、Published Libraries、Notebook Environment 绑定和实际 Spark import 划分为独立验收门禁。
- 以 Microsoft Fabric 稳定版 Environment API（`beta=false`）只读复核，并保留 HTTP 404 的官方 `EnvironmentLibrariesNotFound` 和 API/权限异常两种可能；不从状态文本或文件名推导内容 SHA。
- 先设计和验证只读预检；之后独立评审并授权 Environment Publish/绑定及非写入 runtime smoke。禁止自动携带执行数据作业授权。
- 不重复 Git 更新/OIDC/Service Principal 既有工作，不引入第二 Wheel 或自制 Fabric I/O 层。

## Capabilities

### New Capabilities
- `fabric-environment-wheel-release`: 单一发布制品的可追溯、分级、失败关闭验收。

### Modified Capabilities
- `ingest-fhir-to-fabric`: P2 Native 环境运行时门禁在本 Change 通过前继续 HOLD，不修改其原有运行保护。

## Impact
本 Change 可审阅、验证并合并 **OpenSpec/只读检查**；明确不直接授权 `staging/publish`、Notebook/Environment 绑定更改、Spark Session、Pipeline Run、paid Capacity 或 Bronze/Silver Delta 写入。GitHub `main` 是唯一源码权威，所有云操作必须有独立、可追溯的执行证据。
