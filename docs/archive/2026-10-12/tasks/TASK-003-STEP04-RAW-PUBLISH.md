# TASK-003 Step04 — Canonical Encounter Raw 发布验收

状态：发布 PASS；同 run 恢复重跑 PASS；本步骤源码冻结。
TASK-003 整体尚未完成；下一业务步骤为 OMOP Visit mapping。

- Batch：`synthea-20261005-pop100-atlanta`
- Processing run：`encounter-20261008T234726Z-1658454`
- Raw run：`encounter-raw-20261009T005128Z-1681690`
- Raw 状态：`APPROVED`
- Raw 行数：5799；唯一键：5799
- Raw data：`s3://health-raw/canonical_version=v1/entity=encounter/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/run_id=encounter-raw-20261009T005128Z-1681690/data/`
- Raw manifest：`s3://health-raw/canonical_version=v1/entity=encounter/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/run_id=encounter-raw-20261009T005128Z-1681690/manifest.json`
- Manifest SHA256：`778ae7513c4b2d5dbf16c711fd9f09f1c3c933d94327a42d927199d2aba74171`
- DQ：`s3://health-raw/canonical_version=v1/entity=encounter/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/run_id=encounter-raw-20261009T005128Z-1681690/dq/result.json`
- DQ SHA256：`8a36c23bc302b1080d27c197e6c451c6efd8cbd6069c9a2cbce786e8199dfcf8`
- 原 Spark 作业已完成，Canonical gate 和 Raw readback 通过。
- DQ、manifest 均完成上传回读；manifest 最后发布。
- 同 run 重跑复用两份 metadata，哈希不变，Raw 对象未重写。
- PostgreSQL 写入：无；Phase3C 修改：无。

## 验收路径与修复

首次运行完成 Spark/Raw 写入后，空对象列表检查错误地要求 KeyCount=0，
拒绝了实际的 {"RequestCharged": null} 响应。
已修复正式 Python，并同步正式 prepare Shell。
通过 --resume-run 完成 metadata 发布，再次续接验证幂等。
本次验收未另起新的 Spark run 重做整个九段流程。

## 永久运行方式

前置：TASK-001 和 TASK-003 Step03 已验收，平台依赖与模板已安装。
先执行 scripts/task003/04-prepare-canonical-encounter-publish.sh 生成本步骤源码，
再执行 scripts/task003/04-publish-canonical-encounter.sh 发布新 run。
已有 run 使用同一 runner 的 --resume-run RUN_ID 入口。
恢复需要保留该 run 的本地证据、诊断对象清单及原 SparkApplication/driver 日志。

## 本地验收证据

- `runtime/reports/task003/step04/encounter-raw-20261009T005128Z-1681690/run-state.json`
- `runtime/reports/task003/step04/encounter-raw-20261009T005128Z-1681690/replay-check-20261009T011330Z-9iIM2t/validation.json`
- `runtime/reports/task003/step04/encounter-raw-20261009T005128Z-1681690/replay-check-20261009T011330Z-9iIM2t/replay.log`

runtime 原始日志与数据不随源码提交。
TASK-003 reset 已安装，dry-run 与实际清理通过；仅清理本任务 Python 缓存。
Step03/04 报告文件 SHA256 不变，血缘与恢复证据保留。
Reset 源码：`scripts/task003/00-reset-task003.sh`；SHA256：`310ac173fba6171de6d13f3ca6a69edb7dbc614ece84b648bfc96e2702f3259a`。
验收清单：`runtime/work/task003-reset-check.SQZpRO/evidence.sha256`。
源码提交与远端同步状态以 Git 日志及远端分支为准。

## 冻结源码 SHA256

| 文件 | SHA256 |
|---|---|
| `scripts/task003/04-publish-canonical-encounter.sh` | `4c8bcdcb3cdae7d55ef158a25e273e5c494d5a908e5420cf9e7c467f6621f817` |
| `scripts/task003/04-prepare-canonical-encounter-publish.sh` | `26490241bb3aaf4fa368a03947c9f1c22e089d5904728a0a4571ceeeb3986548` |
| `scripts/task003/04-resume-canonical-encounter-publish.sh` | `256fd87d56c605ba9851fe8b3ad350416e6b04714cc8e1518c698e1a8d346f28` |
| `apps/task003/build_encounter_raw_evidence.py` | `122829030e0d1def7cf8b71b13a6f8a7d3fc503610b035c48b21b75d7a210f73` |
| `apps/task003/resolve_encounter_raw_resume.py` | `4de8ed1acaaa342e777140bc7c79a1f50828de1f1cb0babdfbe2de5d710e187c` |
