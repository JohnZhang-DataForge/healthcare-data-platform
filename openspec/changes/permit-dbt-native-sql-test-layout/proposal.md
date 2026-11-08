# Proposal — Allow reviewed dbt singular SQL tests in the source tree

## Why
此前已采用的 Fabric dbt 标准工程要求 `azure-fabric/dbt/hl7-canonical/tests/`，但 Main 中受保护的 `.github/quality/scripts/check_repository_layout.py` 将所有源码目录 `tests/` 拒绝。该脚本本身受 GitHub Ruleset 的自保护检查限制，不能通过普通功能 PR 偷偷修改、复制/关闭或跳过。用户已明确授权在保持保护的前提下允许 dbt 原生 SQL Tests。

## What Changes
- 严格白名单：仅 `azure-fabric/dbt/hl7-canonical/tests/.gitkeep` 和该目录中规则命名的 singular `*.sql`（含子目录），其他 dbt 项目、Python/JS、YAML、README 或别的源码 tests 继续拒绝。
- 在受保护 checker 中保留历史 baseline 逻辑、CODE Map / Native Item 约束，增加上述源路径精确检查。
- 添加正反向单元测试以及无凭据、PR-head 的离线策略测试 Workflow，避免误报或放宽后不自知。
- 本治理 PR **需要经过独立管理员维护窗口**；仓库当前 Main 自保护 Gate 按设计会拒绝修改该策略文件。验证后再由管理员按正式流程短暂放行受保护策略的部署、立即恢复 GitHub Ruleset，并检查新 Main 受信任 Gate 的正反 PR 行为。

## Capabilities
### Modified Capabilities
- `repository-quality-layout`: 为单个明确 dbt Core 项目的原生 SQL Singular Test 引入精确所有权例外，其余测试仍集中管理。

## Impact
不触及正式 dbt 模型、Local DP 代码、Fabric Native Items、Azure/Blob/Silver/Gold 或任何共享运行环境。不改变历史冻结清单，不允许未经批准的其他 dbt Project。独立于 `govern-fabric-dbt-project-layout` P3 新工程实现。
