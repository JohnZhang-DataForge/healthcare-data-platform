# Design

## 1. 单一事实来源：forward-only 切换而非历史迁移

1. 根 `AGENTS.md` 是强制入口；[Data Platform README](../../../documents/systems/data-platform/README.md) 是 Local DP 组件和下钻路由，系统组件的 `README.md` 解释长期能力，`CODE.md` 是唯一真实代码 Owner 图。
2. Local DP 下一次新增 Condition / Drug / Procedure / Measurement / Observation 等领域时先审计当前 main/开放 PR，查 Active OpenSpec 是否已有同一功能；存在则沿用，否则先建立 **一个新业务 Change**（如 `local-omop-condition-occurrence`）。同一 PR 将确切 OpenSpec-Change/Task 写入 PR Body、更新该任务，复用已验证的旧函数/Contract。不要另起 `TASK006.md` 管开发进度。
3. `openspec/changes/relocate-local-data-platform/` 原有遗留清理、相容性/E2E 和 Archive 任务保持原始职责，不掺入新 Condition；历史 `docs/tasks/TASK-005-...` 保留在 Git 固定 SHA，仅作为技术参考，不是当前 Active Tasks，也不授予写入权限。
4. 历史已部署的 `task004_*` Python/DAG/SQL 函数、镜像 COPY、持久化身份、冻结合同和先前 PASS/FAIL 证据不改动。新功能按组件命名，代码写到已有 Owner 根目录，不为 OpenSpec 新造一套执行框架。
5. 新测试只能放 `.github/quality/tests/<system>/<component>/`；组件源文件的每次新增/移动/删除均与同一 PR 的唯一 `CODE.md` 同步。完整安全规则仍由原 [Safe Operations](../../../documents/engineering/operations/SAFE-OPERATIONS.md) 等持有。

## 2. Agent 真实走法（Condition 仅作示例，不启动开发）

`AGENTS.md` → `documents/systems/data-platform/README.md` → `spark/README.md` / `omop/README.md` → 对应 `CODE.md` → 已存在的 Person/Visit/Manifest/Writer 实际源及 Contracts → 查 `openspec/changes/` 目标业务 Change（缺失则新建）→ 有界开发、测试、PR/CI、授权后独立 Runtime 读回。

- Source / Manifest：`local-data-platform/contracts/synthea/v3.3.0/csv-contract.json` 和已验收 Landing owner。
- Pure Spark Canonical/Candidate/DQ：`local-data-platform/spark/apps/<domain>/`。
- SQL/Commit：`local-data-platform/apps/omop_writer/`，绝不未经授权复用已 COMMIT 批次。
- Orchestration：`local-data-platform/airflow/dags/`，现存 `new_only_omop_consumer.py` 不应未经回归擅改为另一业务模式。
- Tests：`.github/quality/tests/data-platform/<component>/`，不是旧 `tests/task005/`。

## 3. 历史 Condition 参考的可用性边界

[固定 Git 历史 TASK005 计划](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 记录 source `conditions.csv`、稳定 occurrence key、Person/Visit 映射、Vocabulary、null / duplicate、rollback / replay 等候选要求；它明确为历史设计，不是已实施或现行 OpenSpec。Agent 必须在新的 Change 中从当前真实代码/Contract/Runtime 审计后采纳仍正确的部分；不能将旧 TASK005 中过时的路径、状态或直接 PG mutation 作为命令。

## 4. 检查和回退

- 仅本次 OpenSpec 与导航类 Markdown 发生变化；Git compare 保证 `local-data-platform/`、受保护 policy、legacy baseline 与任何 Runtime config 不变。
- 现有 Required Trusted OpenSpec、OpenSpec CLI strict、CODE-map/naming、Docs Links CI 正常 PASS；保留历史及所有相对/固定链接。
- 归档 Change 前需 PR 合并和独立 main 读回；Current Spec 只采纳已发布的治理行为，不将未实施 Condition 写为已实现。回滚文档只需 Git revert。
