# Fabric Environment Wheel Release

## ADDED Requirements

### Requirement: Separate source, staging, publish and runtime acceptance
系统 MUST 独立报告 Shared Wheel 的可重现构建 SHA256、Fabric staging 文件名、published libraries、Notebook Environment 绑定和实际 Spark Session import。名称相同或历史 Publish Success 不得自动提升其它门禁为 PASS。

#### Scenario: Source Wheel is in staging but not demonstrably effective
- **GIVEN** Git main Wheel 内容 Hash 经 CI 验证且 staging 列表包含目标文件名
- **WHEN** Published Libraries 返回 HTTP 404 或库未列出目标文件
- **THEN** Publish 和 Notebook runtime SHALL 保持 HOLD，不得触发 Notebook 或 Delta 写入

### Requirement: Stable official Environment APIs and fail-closed error handling
只读诊断 SHALL 使用正式版 `beta=false` 的 staging/published libraries API，验证 Workspace/Environment 固定身份、分页、schema 和 HTTP 状态；`404` MUST NOT 被误写成“未执行过 Publish”，亦不能解释成目标 Wheel 已生效。

#### Scenario: Historical publish success followed by published 404
- **GIVEN** `publishDetails.state=Success` 但 `GET /libraries?beta=false` 返回 HTTP 404
- **WHEN** 计算当前 Wheel 有效状态
- **THEN** 报告 SHALL 保留历史 publish 成功及当前 published 未能核实的两个独立事实

### Requirement: Publish and Notebook execution require separate approval
仅构建/审阅/GET 不等于真实环境发布许可。任何 `staging/publish`、Notebook 环境更改或 Spark Session 运行 SHALL 受独立授权和审查，并验证副作用边界。不得更改当前 HALT、安全参数或触发 Bronze/Silver/Gold 数据写入。

#### Scenario: Read-only P3 preflight on a trusted runner
- **GIVEN** 使用既有绑定到 Self-Runner/main 的安全 OIDC 只读工作流
- **WHEN** 收集 Environment 与 Notebook 元数据
- **THEN** 不得调用 Publish、UpdateDefinition、Run Notebook 或业务数据 I/O；输出不含 Secrets、Wheel 原始字节或 Notebook 正文

### Requirement: Validate package compatibility with the selected Fabric Spark runtime
当前运行目标 Runtime 2.0 SHALL 与 Wheel `Requires-Python`、Spark/PySpark 和依赖版本相容。源代码可在 Python 3.13 导入不等于可安装 Wheel：版本声明、构建文件及实际运行时测试 MUST 单独验证。若现有 `requires-python = ">=3.10,<3.13"`，Python 3.13 发布 SHALL 被阻断。

#### Scenario: Wheel excludes the target Runtime 2.0 Python
- **GIVEN** Environment `runtime_version: 2.0` 要求 Python 3.13
- **WHEN** Git 唯一 Shared Wheel 的 `Requires-Python` 上限小于 3.13
- **THEN** 系统 MUST 标记发布阻断，并要求通过新的、可追溯的兼容性发行版；不得以旧 Wheel 的 Python 3.11 测试或云端 Staging 名称作为兼容证明
