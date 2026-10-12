# Healthcare Data Platform — 当前 TASK 状态与下一步（2026-10-12）

> **CURRENT STATUS / MAINLINE AUTHORITY**。本文件描述唯一正式业务主线的当前状态。Self-Runner / ARC 测试期产生的真实运行证据可以证明既有代码是否运行成功，但测试期间新增的业务实现不会自动成为主线已验收功能。**不得将未来计划或 test-period candidate 当成 MAINLINE PASS。**

## 已验证 / 下一步

| 范围 | 当前主线状态 | 当前动作 |
|---|---|---|
| TASK001 | 历史冻结的 Landing / batch 基线 | 不重跑、不改冻结文件 |
| TASK002 | Person V2 历史回归与冻结基线 | 不擅自修改 |
| TASK003 | **COMPLETE / CLOSED**：Canonical Encounter → Raw → Processed Visit → ID mapping → OMOP CDM | 只读参考实现 |
| TASK004 — Synthea | **PASS** | 已验收 |
| TASK004 — Resolver/Control | **PASS** | 已验收 |
| TASK004 — Person | **PASS** | 已验收 |
| TASK004 — Visit | **PASS**：2459 行 | V8 对既有主线 `05e` 的真实 runtime validation，接受为主线 PASS |
| **TASK004 — Batch Reconciliation** | **CANDIDATE / NOT MAINLINE ACCEPTED** | **NEXT：审查 V9 candidate；正式 adopt/modify + 重新按主线流程验证** |
| TASK004 — Airflow orchestration | **NOT YET / BLOCKED BY MAINLINE RECONCILIATION** | Reconciliation 正式主线 PASS 后再开始 |
| Azure/Fabric/dbt/MLflow 等 | 后续分阶段设计 | 不阻塞当前 Batch MVP |

**TASK004 overall status = IN PROGRESS。**

## 主线连续性结论

原主线文档 checkpoint：

```text
5c8677e2c46bea6eda0576d4c63c2612f599ff1a
```

当时已完成：

```text
Phase 9 control runtime  PASS
Standalone Person        PASS
```

### V8 Visit

- target Healthcare SHA：`40f9c37a303b95330a503ba69b99e5fc7014aca6`
- Self-Runner Actions Run：`38250467965`
- 执行入口：`scripts/task004/05e-run-visit-canonical.sh`
- `5c8677...` → `40f9c37...` 之间只有文档变化，没有 Healthcare 业务代码变化
- `05e-run-visit-canonical.sh` 在 checkpoint、V8 target、当前 main 的 Git blob 均为：

```text
afc25d47e32497334f3988d7568d9d5bd0aca4e8
```

接受的 runtime 结果：

```text
EXPECTED_ROWS=2459
CANONICAL_ROWS=2459
PROCESSING_READBACK=PASS
POSTGRESQL_MUTATION=NO
RESULT=PASS
```

因此 Visit = **MAINLINE PASS**。

### V9 Batch Reconciliation

V9 新增了：

```text
scripts/task004/05f-reconcile-person-visit.sh
spark/apps/task004/reconcile_person_visit.py
spark/manifests/task004/person-visit-reconciliation.yaml.tpl
tests/task004/test_person_visit_reconciliation_source.py
```

历史运行证据真实存在：

- negative policy run `38251924029`
- pre-merge run `38251984921`
- Healthcare PR #16 tested HEAD `d1f97ecdf864048ff142fd878b6cd5eb72cf5cd6`
- merge commit `ae949f4fe3d2e81c0b43f3b27c8b4478b88a8459`
- post-merge run `38252497171`
- post-merge tested Healthcare main `32a72b2941979fcb20b6d6fd0953b7a87760cdc7`
- observed result：20 Patient / 2459 Encounter / 0 orphan

但是：

```text
historical runtime PASS
!=
mainline acceptance
```

当前这组实现属于 **candidate implementation**。

## 当前 Reconciliation candidate

```text
CODE_EXISTS=YES
HISTORICAL_TEST_RUN_PASS=YES
MAINLINE_REVIEWED=NO
MAINLINE_ACCEPTED=NO
MAINLINE_CHECKPOINT=NO
```

详细边界见 `TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md`。

## 下一位 Agent 如何开始

1. 读取 `../README.md`、本文件、Candidate Status、Operations、Skill 和通用 Lessons。
2. 读取 candidate 的 4 个业务文件以及 V9 historical evidence。
3. **不要先重写 reconciliation**；先 review candidate 的输入、lineage、row/unique、FK/orphan、mutation contract、Spark lifecycle、failure retention、cleanup、future Airflow compatibility。
4. 明确结论：`ADOPT_AS_IS` 或 `MODIFY_BEFORE_ACCEPTANCE`。
5. 使用当前正式开发方式：Healthcare feature PR → exact HEAD SHA → Self-Runner fixed request/workflow → ARC real runtime → evidence → merge → checkpoint。
6. Reconciliation MAINLINE PASS 后，才将 Airflow 改为 NEXT。

## 冻结与安全

- TASK001–TASK003：task-level frozen。
- TASK004 已验收阶段：Synthea / Landing / Resolver / Control Runtime / Person / Visit = frozen baseline。
- TASK004 Batch Reconciliation：**candidate，不属于 frozen accepted baseline**。
- TASK004 整体：**IN PROGRESS**。
- 历史 Checkpoint / Closeout 的当时事实不追溯修改；当前状态由本文件解释。

## 相关文档

- `TASK-003-FINAL-CLOSEOUT.md`
- `TASK-004-PHASE9-CLOSEOUT.md`
- `TASK-004-BATCH-RECONCILIATION-CANDIDATE-STATUS.md`
- `../archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md`
