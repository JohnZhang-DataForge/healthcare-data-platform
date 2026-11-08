# Repository Quality Layout Specification

## Purpose

记录已在 Healthcare 主仓库采用并通过 P1–P5 代码/离线测试治理验收的目录所有权规则、可信 PR 门禁与历史路径例外边界；不表示真实 Fabric/OMOP 运行时验收。

## Requirements

### Requirement: 维护源码、测试、文档与 Fabric Git Item 必须有可验证的唯一所有权

对 Healthcare 仓库中的新文件，仓库治理规则 SHALL 区分业务源码、自动化测试、质量检查脚本、人类技术文档、OpenSpec 变更，以及 Fabric 原生 Git Item 的不同所有权。规则 MUST NOT 把普通 Warehouse SQL 源码伪装成 Fabric Workspace 的 Native Warehouse Item。

#### Scenario: Agent 新增业务测试

- **WHEN** 变更新增一个用于测试 Azure Fabric Writer、Notebook 或 OpenLineage 的自动化测试文件
- **THEN** 检查 SHALL 要求文件位于 `.github/quality/tests/azure-fabric/` 中对应组件分类，且有可发现的测试入口

#### Scenario: 保存 Workspace-only Warehouse 的正式 SQL

- **WHEN** 变更维护现有 Fabric Workspace 的 OMOP DDL/Writer 源码
- **THEN** SHALL 维护 Writer Python 在 `azure-fabric/warehouse/` 的业务归属，以及受控 DDL/Schema 在 `azure-fabric/deployment/warehouse/` 的部署资产归属；不得自动创建 `*.Warehouse/` 的 Git Native 项

### Requirement: 源码区新说明性文档必须被拒绝

仓库治理规则 SHALL 将新增人类阅读的组件说明性 README、CODE、ARCHITECTURE 等文档路由至 `documents/`，但 MUST 保留仓库根 README、已批准 Agent 指令、机器可读格式以及受控存量迁移例外。

#### Scenario: 开发者在 Warehouse Writer 下新增 README

- **WHEN** PR 新增 `azure-fabric/warehouse/omop-foundation/writer/README.md` 或同类说明性 Markdown 文件
- **THEN** 静态 Gate SHALL 输出违规路径与目标文档 Owner，并拒绝该新增行为

#### Scenario: 编辑尚未迁移的历史源码文档

- **WHEN** PR 仅合法更新一个被精确冻结的历史 README 且未创建新违规路径
- **THEN** 静态 Gate SHALL 允许此过渡操作，直到独立文档迁移 PR 完成并清除该例外

### Requirement: 现存旧测试与新测试应采用渐进迁移规则

质量策略 SHALL 对现有 Local DP、Portal 和 Shared Engine 测试采用精确存量基线；不授权批量搬迁旧项目测试。新增自动化测试 MUST 采用集中 Quality 路径。**唯一已获准例外**为 `azure-fabric/dbt/hl7-canonical/tests/` 中命名合规的原生 singular `.sql` 文件或根 `.gitkeep`；其余源码 `tests/`、Python/JS 测试及其它 dbt 项目仍须被拒绝。迁移期间不得关闭原有测试保障来强行通过 CI。

#### Scenario: 正向 dbt 原生 SQL 测试路径
- **WHEN** PR 为 `azure-fabric/dbt/hl7-canonical/tests/` 新增合规 singular `*.sql` 或根 `.gitkeep`
- **THEN** 受保护目录检查 SHALL 接受；这不替代真实 dbt 运行测试。真实治理 PR [#816](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/816) 已证明 `.gitkeep` 正向路径成功。

#### Scenario: 负向非法源码测试路径
- **WHEN** PR 添加 `azure-fabric/dbt/hl7-canonical/tests/test_helper.py` 或其他未经审批项目的测试目录
- **THEN** 受保护检查 SHALL 拒绝，并阻止合并。真实负向 PR [#817](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/817) 已返回 `RULE=new-test-outside-quality`，未合并。

#### Scenario: Shared Engine 旧测试回归

- **WHEN** 开发者修改现有 `shared-data-engine/tests/test_fhir_r4_contract.py`
- **THEN** 现有回归 SHALL 仍按之前可用的构建入口运行，且不会因为 Fabric 专项治理而触发旧文件物理搬迁

#### Scenario: Fabric 测试变更后遗漏 Workflow 引用

- **WHEN** 一个 Fabric 测试从旧目录迁至 `.github/quality/tests/` 而工作流依旧在旧目录 `unittest discover`
- **THEN** 依赖与测试发现检查 SHALL 失败或标记 HOLD，不得把空测试收集集当作 PASS

### Requirement: 目录准入 Gate 必须被真实可信的 GitHub 保护执行

结构检查 SHALL 通过受信任的 PR 入口识别不符合规则的新路径，且必须证明其在 main 的 Required Check 中真实生效。检查 MUST NOT 执行来自不可信 PR 的 Python 或 Shell 作为自身合规判定机制。

#### Scenario: 违规文件被 PR 阻止

- **WHEN** 受控负向 PR 新增源码目录说明 README、新测试子目录或伪 Fabric 原生 Item
- **THEN** 可信结构检查 SHALL 失败并说明具体规则，且 GitHub 合并状态必须被 Required Check 阻止

#### Scenario: 检查脚本存在但是未列为 Required Check

- **WHEN** PR 中的脚本与测试全部 PASS，但 GitHub Ruleset 不要求该检查或无法核实
- **THEN** 整改 SHALL 保持 HOLD/NOT_ENFORCED，不得报告治理已经完成

### Requirement: 文档和测试迁移不得变更生产数据或部署定义

本 Change 的实现 SHALL 只触碰 Git 文档/测试/质量规则和必要的开发辅助入口；必须保护 Fabric 原生 Item 定义、OMOP Warehouse 的已有资源身份、历史已验收批次、临床映射及生产数据。结果 MUST 明确区分代码/CI 验收与真实业务 Runtime 验收。

#### Scenario: 迁移测试但触及原生 Notebook/Pipeline

- **WHEN** 计划中的目录整理需要修改 `nb_fhir_ingest.Notebook/notebook-content.py`、`pl_fhir_ingest.DataPipeline/pipeline-content.json`、其 `.platform` 或环境 Wheel
- **THEN** 实施 SHALL 停止并请求独立获批的业务变更，不得把部署源文件改动包进目录清理 PR

#### Scenario: 仅有 OpenSpec 方案合并成功

- **WHEN** 本 Change 的计划 PR CI 成功并合并 main，但目录 Gate 与测试/文档迁移尚未实施
- **THEN** 状态 SHALL 明确保持 `PLAN_APPROVED / IMPLEMENTATION_OPEN`，不得报告 15 个测试或 8 份 README 已整改完成

### Requirement: 冻结的历史例外基线不得使已删除路径重新获得豁免

源码目录存量豁免 MUST 同时要求路径列于 P1 的 185 条不可变精确历史清单，并且该路径**确实存在于当前 PR base Git tree**。不得把单纯存在于历史清单视为新文件豁免，也不得为了归档本 Change 而临时关闭 GitHub Required Checks。有效例外数量由交集计算，不是永久固定数值。

#### Scenario: 退役 Fabric 文件试图重新引入

- **WHEN** PR 新增已从 base tree 删除、但仍列于历史清单中的 `azure-fabric/notebook-development/README.md` 或旧 `tests/test_notebook_offline.py`
- **THEN** 可信 Gate SHALL 按新增源码文档或新增测试违规拒绝，并由 Required Check 阻止合并

#### Scenario: 仍存在的 Local DP 历史文件合法维护

- **WHEN** PR 仅修改一个同时位于历史清单和 PR base tree 的既有 Local DP 测试，且没有其他违规变更
- **THEN** 布局 Gate SHALL 不因其历史测试目录而拒绝该文件；未来若该文件被删除，则同一旧路径重新引入不再享有该豁免
