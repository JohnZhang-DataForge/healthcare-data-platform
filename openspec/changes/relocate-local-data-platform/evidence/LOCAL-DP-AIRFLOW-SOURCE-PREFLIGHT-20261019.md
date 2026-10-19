# Task 4.4 — Airflow 源码静态预检（不冒充 DAG Parse）

基线 Main：`c73522b85cc4cd4c7dd3db69b91c72540c0d83fd`，2026-10-19，Change `relocate-local-data-platform`。

从 Git Tree 只读确认 `local-data-platform/airflow/dags/` 包含 15 个 Python 源文件；其中 `task004_processing_pipeline.py` 的静态 dag_id 为 `task004_processing_pipeline` 且 schedule=None；`new_only_omop_consumer.py` 的 dag_id 为 `new_only_omop_consumer` 且 schedule=None。发现冻结历史 Workflow `.github/workflows/task004-airflow-step03e-main-runtime-pin.yml` 仍引用旧根目录 `airflow/dags/... `，仅在特定 feature 分支 Push 触发。此类历史路径和冻结 Image SHA 必须另案认定，不能盲目批量改写。

新增 PR 源码-only Gate 对 DAG Python 文件做 AST/compile 和静态 dag_id 重复检查，**不导入 Airflow，不调用集群、DB、S3、Writer，不执行任何 DAG**。此检查不能确认 Airflow 3.x import/API 兼容、DagBag Parse、GitSync checkout 唯一来源、实际 DAG/task dependency 或 SparkApplication source。4.4 继续 OPEN；失败最多三轮，保持 HOLD。
