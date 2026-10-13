# TASK004 STEP04F — Airflow CDM Handoff Preflight (第一轮)

**完成的范围：将无数据库副作用的 CDM handoff 校验任务接入现有 `task004_processing_pipeline` DAG。尚未实现真正的 Airflow 自动 Person/Visit INSERT。**

## 已完成
- 原有 `generate_publish → [person,visit] → reconcile` 处理链保留不变。
- 在 `reconcile` 下游追加 `cdm_load_preflight` PythonOperator，按当前 DAG XCom 而不是固定历史批次检查 Manifest SHA、source version、真实 batch_id、Landing URI、Person/Visit Processing URI 和行数。
- 纯 Python 模块 `airflow/dags/task004_cdm_preflight_contract.py` 输出 `HANDOFF_VERIFIED_NOT_LOADED`，字段 `cdm_write_permitted=false`。绝不使用历史批次常量去加载 DAG 当前批次，更不会调用早先固定批次 STEP04C/D 写库脚本。
- `tests/task004/test_step04f_airflow_handoff.py` 覆盖正确输入、批次不匹配、manifest 错误、丢失 XCom、行数类型错误和 DAG dependency。

## 验证证据
- [Self-Runner Run 38396121007](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38396121007)：**SUCCESS**。
- GitHub-hosted Python 单元测试和 DAG 语法检查 PASS。
- ARC Runner 在实际运行的 Airflow scheduler Pod 内，从 GitHub 指定 SHA 将两个 DAG 文件导入隔离临时目录，通过 Airflow `DagBag` 加载检查：`REAL_AIRFLOW_DAG_PARSE=PASS`，所有五个 task_ids 存在，依赖顺序校验 PASS；`CDM_WRITE=NO`。
- 未触发新的 DAG Run，未修改已有 Person/Visit 数据，未生成新 Synthea 文件。

## 仍需完成才算 STEP04F
1. 现有 TASK004 runtime image 只带 processing/control 脚本和 kubectl，没有正式安装此批次 Person/Visit Python DB Loaders 所需的 boto3、pyarrow，也没有 DAG 所需的动态 batch/URI 读写接口。**不得将现有固定批次 Loader 硬连到当前 Airflow run。**
2. 增加基于 XCom 的 **动态 batch** Loaders 和 batch ledger 的事务契约，按上游 XCom URI 校验 immutable Manifest 与源内容。相同新批次 DAG replay 不得再生成一批不同 Synthea 输入。
3. 最小权限 PostgreSQL 写入运行账户、S3 凭据注入与 runtime image digest 构建/扫描/固定；避免将 Secrets 打印到日志。
4. 在 Airflow 中 Person DB Load → Visit DB Load → Joint DB Readback 顺序依赖、只允许已验证的处理产物进入 Stage；先只读 Dry Run、再授权范围内执行受控新批次真实 COMMIT。
5. STEP04G 执行整条 DAG 的重放、失败注入和恢复验收；TASK005 保持 ON HOLD。

**本轮状态：AIRFLOW HANDOFF PREFLIGHT VERIFIED；Airflow DB Materialization IN PROGRESS。**
