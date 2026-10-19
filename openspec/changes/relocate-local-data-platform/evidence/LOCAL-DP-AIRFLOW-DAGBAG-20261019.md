# Airflow 3.2.2 DagBag Isolated Parse — 待 CI 验证

2026-10-19，基线 Main `50721124e0fab5914e6677e43ec6a63b914d646e`，OpenSpec Task 4.4。

新增 PR Workflow `.github/workflows/local-dp-airflow-dagbag-parse.yml`：在 GitHub-hosted Runner 上以 `apache/airflow:3.2.2` 临时容器、无网络与只读 DAG 挂载执行真实 `DagBag`；不启动 Scheduler / Webserver、不运行 DAG Task、不连接 K8s、PG 或 S3。Airflow Kubernetes Provider 可用性尚未确认，若镜像缺失则 FAIL/HOLD，必须有明确的新测试策略而不能降级为伪通过。现有 `local-dp-airflow-source-preflight.yml` 仅 AST/compile PASS，不能替代此检查。

任何通过仅代表固定代码与该镜像依赖下的离线 DAG Parse；实际 Helm/Composer GitSync 绑定目录、SparkApplication 与运行中 DAG 源路径均尚未验收。任何业务 Writer 不得执行；Task 4.9 HOLD。
