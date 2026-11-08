## MODIFIED Requirements

### Requirement: 现存旧测试与新测试应采用渐进迁移规则

质量策略 SHALL 对现有 Local DP、Portal 和 Shared Engine 测试采用精确存量基线；默认新自动化测试 MUST 放在集中 Quality 目录。唯一新增例外是经正式批准的 `azure-fabric/dbt/hl7-canonical/tests/` 中的 dbt 原生 singular `*.sql` 和根级 `.gitkeep`；其它源码目录与非 SQL 测试仍 SHALL 被拒绝。不得因此关闭既有回归测试。

#### Scenario: dbt 的标准 singular SQL Test
- **WHEN** 新增 `azure-fabric/dbt/hl7-canonical/tests/assert_unique_patient.sql` 或 `tests/.gitkeep`
- **THEN** 在受保护检查器已更新的前提下，路径准入 SHALL 通过，dbt 实际测试仍应由正式 Workflow 独立运行。

#### Scenario: 非授权的 source-local tests
- **WHEN** 新增 `azure-fabric/dbt/hl7-canonical/tests/test_helper.py` 或其它 dbt Project 的 `tests/.gitkeep`
- **THEN** 受保护检查 SHALL 拒绝该路径，不能用 dbt 名义将 Python 自动化测试迁入业务源码区。

#### Scenario: Shared Engine 旧测试回归
- **WHEN** 开发者修改现有 `shared-data-engine/tests/test_fhir_r4_contract.py`
- **THEN** 现有回归 SHALL 仍按之前可用的构建入口运行，且不会因为 Fabric 专项治理而触发旧文件物理搬迁

#### Scenario: Fabric 测试变更后遗漏 Workflow 引用
- **WHEN** 一个 Fabric 测试从旧目录迁至 `.github/quality/tests/` 而工作流依旧在旧目录 `unittest discover`
- **THEN** 依赖与测试发现检查 SHALL 失败或标记 HOLD，不得把空测试收集集当作 PASS
