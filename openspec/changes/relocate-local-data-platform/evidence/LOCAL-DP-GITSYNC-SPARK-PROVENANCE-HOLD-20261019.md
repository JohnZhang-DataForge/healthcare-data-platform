# Task 4.4 — GitSync / Spark 来源闭包现状与 HOLD（2026-10-19）

基线 Main `d55bfabcfc7d7d00b21002b78a9e4a83a3a0a97b`；OpenSpec `relocate-local-data-platform`。本证据只读，不运行 Airflow、SparkApplication、Kubernetes、PG、S3 或 Writer。

## 已有已验证层级

- Airflow 3.2.2 DagBag 隔离 Parse：PR #261 / Run #39295887624 SUCCESS；测试环境补了 `psycopg[binary]==3.2.12`，DAG 源自 `local-data-platform/airflow/dags` 的只读挂载。此结论仅适用于 GitHub-hosted 临时容器，不等于部署集群实际加载路径。
- Synthea / TASK004 Runtime Clean Build 与只读 Smoke：PR #256 / Run #39293879916 SUCCESS；Runner 本地 Image ID，不是 GHCR 镜像发布 Digest。
- `local-data-platform/airflow/dags/task004_processing_pipeline.py` 定义 `task004_processing_pipeline`、`schedule=None`，仍 pin 历史控制镜像 Digest；`new_only_omop_consumer.py` 同样为手动 `schedule=None`。不改变 Batch 身份或镜像 pin。

## 仍需证实的真实来源

1. 当前集群 Airflow Helm Release 的 GitSync `repo`、`ref/rev`、`subPath`、DAG Folder 路径及实际同步 Git SHA（要求只读检查配置和 Pod 挂载，不重启部署）。确认没有旧根 `airflow/dags` / 第二份可扫描 DAG 导致重复加载；不得凭历史 YAML 假定当前 GitSync 配置。
2. `local-data-platform/spark/manifests/task004/person-visit-reconciliation.yaml.tpl` 使用 `mainApplicationFile: local:///opt/spark/app/reconcile_person_visit.py`，Driver 和 Executor 只读挂载 ConfigMap `__CONFIGMAP_NAME__`。必须对实际渲染 YAML、ConfigMap data SHA 与固定 Git 源 Blob 做一一核对；模板存在不代表当前 Pod 执行的 Python 与 Git 一致。
3. `local-data-platform/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl` 同样通过只读 ConfigMap 将 `synthea_encounter_adapter.py` 挂载到 `/opt/spark/app/`，须独立核对渲染器与 ConfigMap 的真实数据源。
4. 冻结历史 `.github/workflows/task004-airflow-step03e-main-runtime-pin.yml` 仍包含原根 `airflow/dags/...`，但仅对原特定 feature Branch 生效；不能直接推断新 Main 当前 DAG 已采用旧路径，也不能在无验证下全局批量替换历史引用。

## 安全边界和结论

Git Source / ConfigMap 模板层核对为静态事实。真实 GitSync checkout、Airflow Pod 读取位置、Spark ConfigMap SHA、Spark Driver import `__file__` 以及 GHCR Digest 目前未作现态验证：**4.4 PARTIAL；Task 4.9 HOLD**。下一步先建立有固定 SHA/环境标识的只读探针，再决定是否需要运行态验证授权。不得触发 DAG Run、SparkApplication、Batch/Writer 或 historical replay。
