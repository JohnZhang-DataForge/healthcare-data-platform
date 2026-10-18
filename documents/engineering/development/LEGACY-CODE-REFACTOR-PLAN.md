---
status: active
scope: legacy-code-refactor-plan
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Legacy Task-named Code — 依赖调查与渐进迁移计划

> **当前是源码整理清单及计划，不是已完成的代码搬迁。** 用户决定保留旧代码的历史命名，未来新增可维护代码必须使用**组件/功能名称**。任何迁移首先保护 NEW_ONLY Person/Visit 已验证的运行行为。

## 1. 静态目录清点（Main `2c85b485381a72425506829fd321d93b164a231d`）

| 目录 | Task 编号命名文件 / 全部文件 | 类型及可能归属 |
| --- | ---: | --- |
| `apps/` | **39 / 67** | Intake/Landing/Visit、CDM Runtime/Writer helpers |
| `airflow/` | **8 / 16** | Legacy DAG、PG Plan/Source/Adapter/SQL Renderer |
| `spark/` | **12 / 45** | Reconciliation、Person/Visit 旧 YAML Job |
| `sql/` | **10 / 14** | 已批准的 PG DDL、验证、入库 SQL |
| `scripts/` | **123 / 124** | 历史 STEP 实验、运行和回放脚本 |
| `images/` | **3 / 11** | 旧 Runtime Docker Build |
| `kubernetes/` | **5 / 12** | 历史 Job 模板、Control RBAC |
| `tests/` | **71 / 106** | 按开发 Milestone 组织的单元/合同测试 |

这是文件**路径静态清点**，不代表所有旧路径都是现行 Runtime 依赖。特别是 `scripts/taskNNN/` 许多是历史审计/恢复材料，没有必要仅为清零文件数量而搬动。

## 2. 关键依赖链（已查源代码）

- [`airflow/dags/new_only_omop_consumer.py`](../../../local-data-platform/airflow/dags/new_only_omop_consumer.py) 是当前真实验收 DAG；不可为了简洁改其 ID 后直接部署。
- [`images/new-only-omop-writer/Dockerfile`](../../../local-data-platform/images/new-only-omop-writer/Dockerfile) 的基础镜像为固定 `task004-cdm-runtime` digest，显式 COPY 多份 `task004_cdm_*.py` 到 **`/opt/task004/`**；`PYTHONPATH` 和 `ENTRYPOINT` 也使用该路径。
- 当前 Writer Python 和 PG 仍引用 `etl.task004_batch_ledger`、`etl.task004_batch_stage`、`etl.task004_batch_commit`、`task004_writer_fence.assert_active_claim()` 等持久化接口。它们并非只需替换显示名称的文档字符串。
- 早期版本因覆盖基础镜像中部分旧 `task004_cdm` 模块而遭遇 `BLOCKED=batch_id`，最终通过协调版本 COPY 修复；见 [最终验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。
- Batch ID/Manifest URI/Contract Version/Claim/Checkpoint/镜像 Digest 等是不可变身份/持久化协议；**绝不批量替换 task 字符串**。

## 3. 未来真正重构代码的阶段

| 阶段 | 迁移单位 | 必备证明 |
| --- | --- | --- |
| R1 | **所有新功能**直接采用组件目录。例如 Condition `spark/apps/condition/` / `apps/omop_writer/condition_writer.py`（仅在真正开发时创建） | 新增路径/类/DAG ID 命名检查 + 功能相关单元测试 |
| R2 | Legacy 中可独立测试的 Manifest、Plan/Adapter、共同 Validation | 新/旧同输入输出与失败 Gate 一致；先保留薄适配入口 |
| R3 | Spark reconciliation、Airflow glue | DagBag/Import、Contract、Spark 静态或受控 Runtime；保持已验收 DAG ID，部署变更单独批准 |
| R4 | Docker COPY/Base Image、Writer SQL 与持久化接口 | 完整依赖清单、版本化镜像 Digest、负向/幂等测试与受控 Runtime 数据读回，不无故重跑旧 COMMIT |
| R5 | 确认不再使用的旧脚本/模板/测试 | 链接、Workflow/Run、历史证据仍可追溯；弃用必须有明确迁移记录 |

**执行限制**：每个阶段小 PR；优先新代码兼容调用旧接口而不是反过来；未验证前旧入口保留。历史 Task/Step 可以出现在追踪文档、测试证据和旧文件中，不能成为新的正式代码路径。参见 [统一命名规范](CODE-ORGANIZATION-AND-NAMING.md)。

## 4. 本轮的完成边界

**已完成（合并后）**：新命名强制规范、PR 新增路径 Gate、模块文档、Legacy 依赖/阶段计划；**未执行**：任何 `task004` 模块 Rename、Airflow DAG/ID 更新、Docker Image rebuild、K8s/PG/Blob/Azure Runtime 操作。TASK004 的已验收业务事实保持不变。
