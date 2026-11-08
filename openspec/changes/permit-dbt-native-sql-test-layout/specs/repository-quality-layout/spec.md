## MODIFIED Requirements

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
