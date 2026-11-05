## ADDED Requirements

### Requirement: Agent 启动状态必须以 OpenSpec Active Changes 为唯一具体任务权威

仓库导航 SHALL 将具体变更的 OPEN/DONE 任务维护在 `openspec/changes/<id>/tasks.md` 中。根 `AGENTS.md` 与 `PROJECT-STATUS.md` MUST NOT 维护平行的人工 CURRENT/NEXT 任务清单；前者仅为规则与任务路由，后者仅为兼容导航。长期架构、CODE Owner、操作安全仍归各自权威文档。

#### Scenario: Agent 开始 Warehouse F2 任务

- **WHEN** 新 Agent 需要继续 Warehouse Writer 开发
- **THEN** SHALL 经根 Agent 路由和 Fabric Warehouse README/CODE 找到现有 `fabric-omop-foundation` Active Change 的对应 F2 Tasks，且不得把历史 PROJECT-STATUS 当作实时 Warehouse Gold 验收

#### Scenario: Active Change 被归档

- **WHEN** 一个 Change 完成并从 `openspec/changes/<id>/` 迁至 `openspec/changes/archive/<date>-<id>/`
- **THEN** 动态 Active 索引 SHALL 不再把它列为待办，但历史 Tasks 与证据仍可在 Archive 查阅

### Requirement: OpenSpec 进度索引必须自动计算、只读且有失败边界

查询工具 SHALL 直接从当前 Git 工作树动态枚举 Active Changes 与 Tasks Markdown checkbox，输出稳定排序、OPEN/DONE 计数和第一个未完成任务，MUST NOT 写入业务状态文件或伪造执行成功。缺失/无法识别 Tasks 时 MUST 显式显示 UNKNOWN。

#### Scenario: 新任务新增到现有 Active Change

- **WHEN** 某个 Active `tasks.md` 增加一个未勾选的编号 Task
- **THEN** 下一次只读查询 SHALL 反映新的 OPEN 数量，无须人工编辑 PROJECT-STATUS

#### Scenario: Change 缺少任务文件

- **WHEN** Active Change 目录存在但缺少 `tasks.md`
- **THEN** 索引 SHALL 显示 UNKNOWN 而不是宣称 DONE

### Requirement: 状态改造不得破坏历史来源或共享 Runtime 边界

改造 MUST 保留原 PROJECT-STATUS 全文、原有可追溯 Markdown 相对链接以及实际 Run 结论，MUST NOT 改动可信安全门禁、现存业务源码或共享资源。

#### Scenario: 查询历史验收记录

- **WHEN** 使用者从旧 `PROJECT-STATUS.md` 链接进入
- **THEN** SHALL 能找到保存在同目录的原始历史快照，并明确区分历史记录与当前 OpenSpec Tasks
