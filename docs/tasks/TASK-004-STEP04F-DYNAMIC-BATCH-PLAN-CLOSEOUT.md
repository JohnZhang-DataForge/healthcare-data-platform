# TASK004 STEP04F — Dynamic Batch Materialization Plan / Airflow 验收

**本轮验收：动态批次计划已接入现有 DAG，实际 Airflow Scheduler DagBag PARSE PASS。数据库自动写入还未接入。**

## 本轮工程闭环
- 不破坏现有 `generate_publish → [person,visit] → reconcile → cdm_load_preflight`。
- 新增 `cdm_materialization_plan` PythonOperator，位于 `cdm_load_preflight` 下游，直接读取其 XCom 的动态批次信息。
- 单一生产模块 `airflow/dags/task004_cdm_materialization_plan.py` 跟随现有 `gitSync` 同步，与 Airflow DAG 同目录，不依赖 runner 本地文件。
- 校验 Manifest SHA、batch_id/source_version、Person/Visit URI、原始文件日期跨来源一致性、entity 归属、record counts。源发生漂移、路径欺骗、多个 batch 混合时 fail-closed。
- 根据完整输入生成稳定 `plan_sha256`；两个 plan 对比不一致会拒绝 replay。
- 输出明确 `load_order=[person,visit,db_reconcile]`、`database_mutation_authorized=false`、`PLANNED_AWAITING_LOADER_VALIDATION`。**此 plan 不会触发任何 INSERT，也不等于给新批次授权数据库写入。**

## 实测证据
- [Self-Runner 38397075712](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38397075712) **SUCCESS**；固定 Healthcare feature SHA `27b931a3d1f77898276fde2e720a9bda9163c858`。
- 测试：8 个 dynamic contract 单元用例 + Airflow Python 语法验证、真实 Airflow scheduler 内的 DagBag 导入、六个 task_ids 和任务依赖顺序检查。
- `REAL_AIRFLOW_DAG_PARSE=PASS`、`CDM_WRITE=NO`。
- 没有触发新 DAG Run、没有部署新版镜像，没有更改 `omop` Person/Visit、没有新增数据。

## 下一步关键阻断
1. 新运行批次需要通用的 **动态 Person/Visit Loader**（当前 `step04c_person_*` / `step04d_visit_*` 仍是锁定历史批次的脚本，不得直接用它们读取新批次）。
2. Runtime Image 需要验证并固定包含所需 Python 依赖（boto3/pyarrow 或受控的替代读取路径）、PG 连通性、最小权限数据库凭据与镜像不可变 digest。
3. Airflow XCom 必须驱动任务参数，Person DB Load → Visit DB Load → 独立 DB Reconciliation，并分别记录事务提交/未知结果恢复；新批次正式写库需要审核写入范围。
4. STEP04G 才能执行真正的 Airflow 完整链路 replay/idempotency、失败注入与并发控制验证。TASK005 ON HOLD。

**STEP04F 第一轮 Handoff + 第二轮 Dynamic Batch Planning 已通过；自动数据库入库尚未完成。**
