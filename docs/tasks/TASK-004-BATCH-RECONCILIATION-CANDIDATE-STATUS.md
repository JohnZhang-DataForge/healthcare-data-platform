# TASK-004 Batch Reconciliation — Mainline Candidate Status

> **CURRENT / MAINLINE STATUS**  
> Date: 2026-10-12  
> TASK004 overall: **IN PROGRESS**  
> Reconciliation: **CANDIDATE / NOT MAINLINE ACCEPTED**

## 1. 定位

V8 只验证了原有 TASK004 Visit implementation，没有修改 Healthcare Visit 业务代码。

V9 则在测试新的 Self-Runner / ARC 开发方法期间新增了 Person/Visit batch reconciliation 业务实现。

因此：

```text
V9 runtime evidence             = VALID HISTORICAL EVIDENCE
V9 reconciliation code          = CANDIDATE
V9 reconciliation mainline PASS = NO
```

## 2. 主线断点

原主线文档 checkpoint：

```text
5c8677e2c46bea6eda0576d4c63c2612f599ff1a
```

当时：

```text
Phase 9 Control Runtime    PASS
Standalone Person          PASS
Standalone Visit           NOT YET IN THAT THREAD
Batch Reconciliation       NOT YET
Airflow                    NOT YET
```

## 3. V8 Visit 接受为主线验证

V8 target Healthcare SHA：

```text
40f9c37a303b95330a503ba69b99e5fc7014aca6
```

Run：

```text
38250467965
```

执行：

```text
scripts/task004/05e-run-visit-canonical.sh
```

该 runner 在原主线 checkpoint、V8 target、当前 main 的 Git blob 均为：

```text
afc25d47e32497334f3988d7568d9d5bd0aca4e8
```

因此 V8 验证的是既有主线实现，Visit 可接受为 MAINLINE PASS。

## 4. V9 越界进入业务开发

V9 新增：

```text
scripts/task004/05f-reconcile-person-visit.sh
spark/apps/task004/reconcile_person_visit.py
spark/manifests/task004/person-visit-reconciliation.yaml.tpl
tests/task004/test_person_visit_reconciliation_source.py
```

历史证据：

```text
negative policy run   = 38251924029
pre-merge PASS run    = 38251984921
PR #16 tested HEAD    = d1f97ecdf864048ff142fd878b6cd5eb72cf5cd6
PR #16 merge commit   = ae949f4fe3d2e81c0b43f3b27c8b4478b88a8459
post-merge PASS run   = 38252497171
post-merge main SHA   = 32a72b2941979fcb20b6d6fd0953b7a87760cdc7
```

观察到：

```text
PATIENT_ROWS=20
ENCOUNTER_ROWS=2459
ORPHAN_ENCOUNTERS=0
PROCESSING_MUTATION=NO
POSTGRESQL_MUTATION=NO
RESULT=PASS
```

这些是有效历史事实，但不等于主线 acceptance。

## 5. Mainline acceptance gate

正式接受前至少 review：

```text
1. input Processing URI contract
2. batch/source lineage
3. expected row handling
4. Patient ID uniqueness
5. Encounter ID uniqueness
6. Encounter → Patient referential integrity
7. orphan detection
8. read-only mutation contract
9. SparkApplication lifecycle
10. failure evidence retention
11. successful cleanup
12. output markers
13. source tests
14. future Airflow compatibility
```

必须明确结论：

```text
ADOPT_AS_IS
```

或：

```text
MODIFY_BEFORE_ACCEPTANCE
```

然后按正式 feature PR + exact SHA + Self-Runner/ARC 流程重新验证。

## 6. 历史 closeout

原：

```text
docs/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT.md
```

记录的 V9 runtime 事实不追溯修改，原文归档到：

```text
docs/archive/2026-10-12/tasks/TASK-004-BATCH-RECONCILIATION-CLOSEOUT-V9-TEST-PERIOD.md
```

## 7. 当前分类

```text
TASK004_OVERALL=IN_PROGRESS
VISIT_STANDALONE=PASS

RECONCILIATION_CODE_EXISTS=YES
RECONCILIATION_HISTORICAL_RUNTIME_PASS=YES
RECONCILIATION_MAINLINE_REVIEWED=NO
RECONCILIATION_MAINLINE_ACCEPTED=NO

AIRFLOW_ORCHESTRATION=NOT_YET
NEXT=MAINLINE_RECONCILIATION_CANDIDATE_REVIEW
```
