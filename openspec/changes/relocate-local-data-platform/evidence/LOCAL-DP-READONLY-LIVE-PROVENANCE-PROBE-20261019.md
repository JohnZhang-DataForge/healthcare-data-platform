# Task 4.4 — 可选择执行的只读来源探针

2026-10-19；基线 Main `34165485cd145ad4bbf7e46bc397d73022474e13`。脚本：`local-data-platform/scripts/quality/read-only-gitsync-spark-provenance.sh`。

本 PR 只交付探针，不执行探针，不访问任何连接集群。要求操作人员显式设置 `KUBE_CONTEXT`、`AIRFLOW_NAMESPACE`、`SPARK_NAMESPACE`、`SPARK_CONFIGMAP`、`EXPECTED_SPARK_FILE`、`REPORT_DIR`，在固定 Git SHA checkout 下运行；确保身份具备相关命名空间资源的只读 get/list 权限。脚本仅允许 `kubectl get pods/configmap -o json`，不会使用 exec、apply、create、patch、delete，不触发 Airflow 或 Spark。

示例命令（此处仅示例；先核实当前上下文/ConfigMap，切勿猜名称）：

```bash
export KUBE_CONTEXT='approved-readonly-context'
export AIRFLOW_NAMESPACE='dw-airflow'
export SPARK_NAMESPACE='dw-spark'
export SPARK_CONFIGMAP='actual-rendered-configmap-name'
export EXPECTED_SPARK_FILE='local-data-platform/spark/apps/task004/reconcile_person_visit.py'
export REPORT_DIR='/tmp/local-dp-provenance-verified'
bash local-data-platform/scripts/quality/read-only-gitsync-spark-provenance.sh
```

报告会保存原始 Pods JSON 与 ConfigMap JSON 到操作者指定的目录，可能包含敏感配置和非 Secret 的环境变量值。**报告不得提交仓库或上传聊天，须在授权隔离位置保存、按最小权限清理。** 公开输出只显示容器名、DAG mount、环境变量名称以及 Spark ConfigMap 指定 key 与 Git 文件的 SHA256 匹配。脚本并不校验 GitSync 实际 checkout SHA、DAG 扫描/导入来源、Pod 镜像 Digest 或 driver `__file__`，不得因部分 PASS 就宣布 4.4 完成。

空值、缺少资源或 SHA 不相符必须 HOLD；不得自行修复在线配置、删除历史脚本、重放 Batch 或触发运行 Task。4.9 HOLD。
