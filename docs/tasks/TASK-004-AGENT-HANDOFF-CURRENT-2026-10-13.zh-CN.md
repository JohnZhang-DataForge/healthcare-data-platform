# TASK004 Agent 交接与唯一 NEXT — 2026-10-13

> **2026-10-13 READONLY AUDIT 已收尾，此前“唯一 NEXT = 修复 PYTHONPATH”已过时。** 新增[只读 Source ID 审计 Closeout](TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md)：[Run 38435544614](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38435544614) **SUCCESS**，23/23 Source ID 在 mapping 中已存在；与目标 Person 完全一致 0、内容不同 23、全新 0、dangling 0；失败批次 ledger/stage/commit 0/0/0；CDM Person/Visit 总数 136/9391；数据库无业务写入。Self-Runner [PR #69](https://github.com/JohnZhang-DataForge/Self-Runner/pull/69) merged SHA `9c2ad3ce33b5c3a877608defbbdcd25118978c15`。**下一轮只讨论并验证 Synthea Seed / Reference Date / Source ID 的批次隔离设计**（同 Seed 导致漂移仅为原因假设）；需另行授权任何新批次、ROLLBACK、Writer COMMIT。**本文件下方第3/5节仍为交接时历史断点，不是当前 NEXT。TASK004 IN PROGRESS；TASK005 ON HOLD。**


> **CURRENT / 权威增量交接。新 Agent 从 `docs/README.md` 进入后首先阅读本文件；历史 TASK-STATUS / Plan / Closeout 中的旧 NEXT（例如 STEP04A / STEP04B）均被本文件的当前进度取代。不要从头重新实施 STEP04A–04F。**

## 1. 用户目标与开发方法

真正的 TASK004 完成标准：一次 Airflow DAG 自动触发 Synthea → Landing → Spark Person/Visit → 共同批次 PostgreSQL OMOP Person + Visit → DB reconciliation，并对同一 batch/manifest 的重新执行保证逻辑幂等、恢复验证。TASK005 Condition **ON HOLD**。

**开发约束**：以 GitHub 为代码/文档唯一来源；Healthcare feature 分支、Self-Runner Actions/ARC 验证真实结果、PR → protected main；每轮一个有意义的代码+实测+证据闭环，≤3 次失败后停止调查，不允许以 Workflow 被预期拒绝视为业务成功。无需让用户本地手工执行 shell；不擅自修改冻结历史数据，不直接推 main。每轮准确区分源码测试/容器构建/集群测试/DB COMMIT。

## 2. 已经完成并验证，不要重做

- STEP04C/D/E **固定历史批次** PostgreSQL Person/Visit COMMIT+重放+联合核对通过。历史 `task004-airflow-task004-step03e-38324111846`（Person 23，Visit 3592）；CDM 既有总量 **Person=136、Visit=9391**；该批次 ledger 为旧合同版本，不能将它当作新的 dynamic-v1 批次重写。
- STEP04F 动态 Plan、S3 Manifest SHA + 一份 Parquet 检查、Person/Visit canonical→OMOP Adapter、PG SQL Builder（默认 ROLLBACK）、Airflow 6-task DAG **解析成功但尚未实际串接入库**。
- 独立 CDM Runtime：实际 SeaweedFS 读取 Person/Visit、镜像构建/GHCR 发布；read-only `cdm_reader` 与 insert-scoped `cdm_writer` 凭据分别存放 `dw-spark/task004-cdm-reader-db`、`dw-spark/task004-cdm-writer-db`；PG Role 权限核实，独立 Runtime 只读 SELECT 成功；合成 Person 事务借由真实 Runtime ROLLBACK 成功，确认没留下 ledger/stage/map/CDM 数据。
- 已发布 S3→Writer ROLLBACK 桥接镜像：`ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e`。CLI：`--plan-file <json> --rollback-from-s3 person|visit`，无 COMMIT 参数；另有 `--validate-source`、`--validate-postgres`、`--rollback-entity/--rollback-rows-file`。K8s worker02、`dw-spark`。
- 历史批次用于新 Writer 时被 `BLOCKED:LEDGER_DRIFT` 拒绝 **安全门禁 PASS 而不是写入成功**（Self-Runner 38430437561）。
- **2026-10-13 新 Synthea 完整流程实测 SUCCESS：** Airflow `task004_processing_pipeline`，新批次 `task004-airflow-task004-step03e-38431103586`，Synthea v3.3.0，2026-10-13 ingest；Landing 发布→Person 23 / Visit **3588** Processing→Reconcile；[Self-Runner run 38431103586](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38431103586) SUCCESS；Self-Runner PR #68 / Healthcare PR #67 已合并。
- **新批次动态 Person Writer ROLLBACK 尚未成功**：[run 38432556422](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38432556422) 接入真 S3/PG 后在 `BLOCKED:EXISTING_TARGET_DRIFT` 处中断。此验证 Workflow FAILURE，未进入预定独立 readback。不要绕过此门禁，更不要执行 COMMIT。可能因新旧批次默认 Synthea `seed=20261012` / `clinician_seed=20261012` 相同、参考日期变更而发生 source_id 重合、Person Payload 不同；**目前只是待验证假设**。

## 3. 最近一次排查的精确断点（NEXT）

目标是仅用 SELECT 计算 **新批次 23 个 Person ID**：
(1) 新 ID 个数；(2) 已存在且目标 OMOP 完全一致个数；(3) 已存在且目标不同个数；(4) 映射存在但 Person 目标丢失个数。只输出汇总数字，不输出任何患者标识。还要独立核实失败批次 `etl.task004_batch_ledger/stage/commit` 是否为 0、Person/Visit 总数是否仍为 136/9391。

目前代码尚在 **Self-Runner 未合并 feature 分支** `feature/task004-person-readonly-audit-20261013`，SHA（创建交接前）`bfad7e9b604006bc6d514bc5afabb9769732df2b`：
- `task004/smoke/read_only_person_overlap.py`
- `.github/workflows/task004-person-readonly-audit.yml`

[Run 38434861465](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38434861465) **FAILURE**，实际 Kubernetes Job 超时后报 `ModuleNotFoundError: No module named 'task004_cdm_materialization_plan'`。脚本以 `python /code/audit.py` 启动，从 ConfigMap 挂载脚本；CDM 镜像中模块位于 `/opt/task004`，而 `sys.path` 只有 `/code`。**最小修复**：在 `read_only_person_overlap.py` 顶部、其余 `from task004_...` 导入前加 `import sys; sys.path.insert(0, "/opt/task004")`，或在 Job 环境设置 `PYTHONPATH=/opt/task004`。推荐只改测试 Job 的 `PYTHONPATH`，镜像和 PostgreSQL 权限不需要变。

**注意：** 上次运行用了 `kubectl wait --for=condition=complete` 超时 240 秒，却未及时发现 Job 已 Failed，导致不必要的等待。修改为有限时间同时查询 Failed/Complete 状态并早停；失败时显示最近 25 行 Pod 日志（不得打印 secret/PHI）；成功后按 `READONLY_PERSON_RECONCILIATION=PASS` 等 marker 验收。只重新触发同一个只读审计一次，失败再查原因，不要重复启动 Synthea/Airflow 或 Writer。

脚本核心：读取新 batch 的固定 SeaweedFS Landing Manifest、发现唯一 Person/Visit Processing Parquet path，通过 `task004_cdm_dynamic_source.read()` 转换 23 Person OMOP row，用 `cdm_reader` 的严格 READ ONLY transaction 逐条 SELECT `etl.person_id_map` / `cdm.person`，使用 `to_jsonb(p) IS NOT DISTINCT FROM to_jsonb(jsonb_populate_record(NULL::cdm.person, payload||id))`（与真实 Writer 一致）比较，按四类 aggregate 并输出独立 DB readback。Secret 取自现有 `dw-spark-s3-secret` + `task004-cdm-reader-db`，无 CREATE/GRANT/INSERT/COMMIT 业务写入（只读事务的结束 COMMIT 不等于业务写入）。

**边界：** 有可能验证后 23 个 Person source_id 全部存在且内容不一致；只有实际成功 SELECT 才能下结论。若 overlap+drift 成立，分析 Synthea Seed/Reference Date/Business Key 政策，优先设计**新的独立 Seed 批次**或有明确版本化规则，不覆盖既有 Person，不取消 drift gate。用户之前要求单轮小闭环和≤3 次测试循环，完成排查后单独规划新的 Synthea 批次与 ROLLBACK。**不立即开新批次、不启用 writer COMMIT、不触发 Airflow 数据库写入。**

## 4. 关键证据与当前 Repo 状态

| 验收 | Self-Runner / Healthcare Actions | 结果 |
|---|---|---|
| 独立 reader PG service + CDM Runtime | 38425638192 | PASS |
| cdm_writer scoped role & rollback | 38427294423 | PASS |
| CDM Runtime standalone synthetic rollback | 38429423958 | PASS |
| S3→Writer historical ledger rejection | 38430437561 | expected rejection PASS |
| **new Synthea + Spark Airflow** | **38431103586** | **PASS, 23/3588** |
| fresh S3→Person dynamic SQL | 38432556422 | **FAIL, EXISTING_TARGET_DRIFT** |
| latest source ID readonly investigation | **38434861465** | **FAIL, Python import** |

Healthcare main **截至交接前** `0b54b4ca42f5a1dd53d7afdbcf678dc316357378`（须重新查询最新 SHA）；Self-Runner main 亦须实时查询。历史文档多次记录不同 SHA，**不要当成今天的 HEAD**。

已完成文档：
- `docs/tasks/TASK-004-STEP04F-FRESH-SYNTHEA-AIRFLOW-SOURCE-PASS.md`
- `docs/tasks/TASK-004-STEP04F-FRESH-PERSON-TARGET-DRIFT-BLOCKER.md`
- `docs/tasks/TASK-004-STEP04F-S3-WRITER-ROLLBACK-INTEGRATION.md`
- `docs/tasks/TASK-004-STEP04F-CDM-RUNTIME-WRITER-ROLLBACK-CLOSEOUT.md`
- `docs/tasks/TASK-004-STEP04E-JOINT-DB-RECONCILIATION-CLOSEOUT.md`
- `docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md`（开发操作手册）

## 5. 下一 Agent 第一轮验收要求

**本轮唯一 NEXT：修复只读审计模块路径 → Self-Runner GitHub Actions 在 K8s 读取真 S3 + PostgreSQL SELECT → 取得四类 Person overlap 数字与失败批次 DB residual → 记录文档、PR 合并。** 若再失败，按工具日志查明原因、控制迭代次数。完成前不得将 STEP04F 标注为完成，也不能开始 TASK005。

特别提醒：不要声称 `38434861465` 已成功或用户取消；它以 FAILURE 结束，失败原因已从真实 Job 日志核实。
