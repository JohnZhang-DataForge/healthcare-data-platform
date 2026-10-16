# Healthcare Data Platform — 文档新入口

> **状态：ACTIVE（新文档治理入口）** · 2026-10-16 · **阶段：Pre-OpenSpec Documentation Rebuild**
>
> 本目录逐步建立经代码、Contract、真实验收核实的项目知识。**目前并非所有模块都已迁入**，不能把这里暂缺的文档理解为功能不存在或已经通过验收。

## Agent 必读入口

1. [AI/Agent 开发与安全规则](development/AGENT-RULES.md) — 当前通用 AI 操作约束。
2. [文档治理与渐进迁移规则](development/DOCUMENTATION-GOVERNANCE.md) — 当前文档的唯一权威、证据、冲突、迁移门槛。
3. [迁移进度与顺序](migration/MIGRATION-STATUS.md) — 明确哪些模块迁移完毕、哪些仍依赖旧资料。

**最小读取策略**：先读本页和必要规则，再按任务读取有关代码、Contract、测试、部署配置及证据；避免一次性加载旧 `docs/` 全量 Markdown。

## 两套目录的过渡边界

| 位置 | 当前职责 |
| --- | --- |
| `documents/` | 新治理规范及**已完成审核并在迁移表标记为 ACTIVE 的**架构、模块和运维知识 |
| [`docs/`](../docs/README.md) | Legacy：旧架构、状态、Runbook、Task 计划、已验收证据的迁移来源；未迁移领域仍须按需查阅 |
| [`contracts/`](../contracts/README.md) | 具体行为合同和数据 Schema 等以当前 Git 源码与有效 Contract 为准，不因文档搬迁而改写 |
| `openspec/`（未来） | **尚未初始化**；下一阶段管理需求 Specs / Changes，不取代 `documents/` 的实现与运维知识 |

旧 `docs/` 存在互相矛盾的日期快照；不得仅按文件名中的 CURRENT 或文件创建日期认定事实。对代码/运行状态的陈述必须标明 **Source SHA 与对应验收证据**。有不一致时先记录，停止未经核实的权威切换。

## 已知项目基线（迁移上下文，不是新一轮实时探针）

- [仓库根 README](../README.md) 描述已验收的本地 Synthea → S3 Landing → Airflow → Spark Person/Visit → PostgreSQL OMOP 路径。
- TASK004 NEW_ONLY Person/Visit 实际 E2E 和同批次 SKIP 有[最终验收证据](../docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)；该结论不代表其他数据域或所有并发/恢复场景已验收。
- [Condition TASK005](../docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 处于可做 STEP00 只读预检、尚未完成业务入库的状态；开发前再次核对最新 Main 和授权。
- Azure/Fabric、Portal 各自有独立实施与证据状态，不得以“有 Terraform Plan”“有 Spark Smoke”推断全部功能已部署或所有血缘已完成。

## 为什么不直接重写全部文档？

我们采取 **逐领域分析 → 核对源码/运行证据 → 消除矛盾 → 新建简洁文档 → 审核切换权威** 的方式。现有历史证据不批量覆盖，不修改 `docs/` 正文来伪造一致性。

迁移完成后：`documents/` 管理实际架构、开发方法、运维知识及证据索引；引入 OpenSpec 后，由 `openspec/specs/` 管理可验证行为要求，`openspec/changes/` 管理后续设计/功能变更；避免两套内容重复成为权威。
