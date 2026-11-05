# Local DP — OpenSpec Forward-Only Change Governance

> Governance policy adopted through [PR #696](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/696); legacy Person/Visit implementation and evidence were not rewritten and no Condition/other OMOP domain business runtime was developed or accepted.

## Purpose

本规范定义 Local Data Platform 的 OpenSpec Forward-Only 开发治理：不迁移或改写 Legacy TASK、已验收 Person/Visit、既有运行代码、合同和历史证据；后续新增业务域或实质性行为/配置变更统一由 Active OpenSpec 管理。该规范只约束开发过程，不代表任何新业务实体已经实施或获得共享运行环境写入授权。

## Requirements

### Requirement: Local DP 未来实质性变更仅用 OpenSpec 管理

从本规则正式合并之后，任何针对 Local DP 的新增业务域、行为/接口改变、实质性重构或运行配置变更 SHALL 在开发前绑定一个适当 Active OpenSpec Change，其 `tasks.md` 是唯一当前任务进度来源，PR 通过现有 Trusted Change Gate 检查。Agent MUST NOT 新建或继续更新 TASK/STEP Markdown 作为平行的 CURRENT/NEXT 权威。

#### Scenario: 开发新的 OMOP Condition Domain

- **WHEN** Agent 被要求继续扩展 Local DP 处理 `condition_occurrence`
- **THEN** SHALL 通过 Local DP README/CODE 找到现有 Source/Spark/OMOP/Airflow Owner，先查 Active OpenSpec（若无对应业务 Change 则创建），将历史 TASK005 仅作为设计参考，不沿用旧任务文件管理新的 OPEN/DONE

#### Scenario: 对现有 Local DP Runtime 配置做实质性修改

- **WHEN** Agent 计划调整已存在 DAG、镜像、SQL/Writer 行为或组件间 Contract
- **THEN** SHALL 根据实际影响绑定一个 Active OpenSpec Change，遵守原有代码归属和 Required Gate；OpenSpec 关联不自动授予共享 Runtime 操作权限

### Requirement: 旧 Local DP 实现、历史验收及有效合同必须原样保留

Legacy TASK001–TASK004、既有 TASK005 历史计划、现存 `task004_*` 代码/SQL/DAG、旧测试/文档、Batch/Run/PR 的 PASS/FAIL 原始证据 MUST 保留其追溯效力。仅因采用 OpenSpec MUST NOT 迁移、删除、重命名旧源码、复制另一套实现或重新宣布已验收 E2E 未验收。

#### Scenario: 需要复用 Person/Visit 逻辑

- **WHEN** Agent 为新的 OMOP 域核对已实现的 Person/Visit 和 Writer
- **THEN** SHALL 按现存 CODE.md 与真实 Source/Contract 定位并复用，经新的 Change 做明确范围的测试；旧文件原位保留，不建立 `task005` 新代码目录

### Requirement: 历史计划和迁移 Change 不得冒充新业务任务

旧任务文件及 `relocate-local-data-platform` Change SHALL 仅作为它们既定职责的记录。Condition/Drug/Procedure/Observation 等新业务 Change 的 OPEN/DONE SHALL 仅由其相应 Active Change 管理。新测试 MUST 使用 `.github/quality/tests/<system>/<component>/`，变更源码 Owner 后 SHALL 在同 PR 更新对应 CODE.md。

#### Scenario: 历史 TASK005 计划中出现旧目录约定

- **WHEN** Agent 读到 `tests/task005/` 或 `scripts/task005/` 的旧路径
- **THEN** SHALL 将其视为历史设计，不照搬到最新 main；根据现行 P1–P5 目录规则创建唯一功能命名源码/质量测试
