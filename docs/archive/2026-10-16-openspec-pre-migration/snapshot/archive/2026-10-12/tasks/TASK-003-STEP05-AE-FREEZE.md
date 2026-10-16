# TASK-003 — STEP05A–E 验收冻结记录

验收日期：2026-10-09。本文件是历史验收快照，不代表以后环境中的任务已自动完成。

## 范围与结论

- STEP05A：APPROVED Encounter Raw 上下文与本地证据验证 PASS。
- STEP05B：PostgreSQL 只读数据库基线 CAPTURED，检查验收 PASS。
- STEP05C：创建 `etl.visit_occurrence_id_map` 结构及序列，重跑 REUSED；没有分配任何 Visit ID。
- STEP05D：S3 远程 manifest/DQ 字节哈希及血缘验证 PASS。
- STEP05E：Spark 实际 Raw Parquet 预检 PASS，SparkApplication COMPLETED。

本次 Raw Encounter 共 5,799 条，唯一键 5,799，关联 Person 共 113；Person 已入库 113 行。

STEP05A–E 结束时，`cdm.visit_occurrence` 和 `etl.visit_occurrence_id_map` 均为 0 行。

STEP05E 没有写 S3、没有写 PostgreSQL，也没有分配 ID；尚未发布 Processed Visit。

## 固化源码的重建入口

- STEP05A：`scripts/task003/05-prepare-visit-omop.sh` → `05a-verify-visit-omop-input.sh`
- STEP05B：`05b-prepare-visit-db-baseline.sh` → `05b-inspect-visit-database.sh`
- STEP05C：`05c-prepare-visit-id-map.sh` → `05c-create-visit-id-map.sh`
- STEP05D：`05d-prepare-visit-remote-metadata.sh` → `05d-verify-visit-remote-metadata.sh`
- STEP05E：`05e-prepare-visit-raw.sh` → `05e-validate-visit-raw.sh`

正式 Python、SQL、YAML、测试由这些 prepare Shell 生成并与正式源码一致性核对。

正式源文件进入 Git；`runtime/`、原始数据、运行配置、Secrets 和临时修复 Shell 不进入 Git。

## 验收证据（runner01 本地）

- A：`runtime/reports/task003/step05/input.Kj4lPk/input-context.json`
- B：`runtime/reports/task003/step05/database.dNYYFx/baseline.json`
- C：`runtime/reports/task003/step05/id-map.Ll7g3e/run-state.json`
- D：`runtime/reports/task003/step05/remote-metadata.JPmdc6/run-state.json`
- E：`runtime/reports/task003/step05/raw-preflight.b7bMSF/run-state.json`
- SparkApplication：`visit-raw-check-20261009t175910z-2051155`

上述证据不在 Git 中。仅 clone 源码不能恢复已发布 S3 对象、数据库内容或历史运行证据。

从零重建必须先部署基础平台、完成上游 TASK-001/TASK-002/TASK-003 STEP03–04，并依次执行相关正式 Shell；整链干净环境恢复尚未验收。

## 下一步

从 STEP05F 开始开发 OMOP Visit Candidate 映射与 Processed 发布门禁；随后单独验收 Stage、稳定 ID 分配、事务 UPSERT、数据库对账及幂等重跑。

不得将 STEP05E 的 PASS 误写成 Visit 已入库。
