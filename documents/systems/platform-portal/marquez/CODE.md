---
status: active
scope: portal-marquez-source-map
last_verified: 2026-10-25
source_sha: b92ccc9b7976e740d9dd77994a0725b115693705
---

# Marquez — CODE / 源码导航

> 下表直接链接 Git 中实际存在的源码；**运行有副作用**，文档审查不能作为调用脚本许可。职责与当前证据见 [README](README.md)。

| Git 文件 | 功能及副作用 |
| --- | --- |
| [`helm/values.yaml`](../../../../platform-portal/marquez/helm/values.yaml) | 官方 Marquez Helm values；禁用 chart 内 PG，使用外部 PG14/Secret，服务 ClusterIP |
| [`kubernetes/deploy.sh`](../../../../platform-portal/marquez/kubernetes/deploy.sh) | 受控 Runner 上的真实部署脚本；前置 PG14/Storage/30999 冲突门禁，可创建 Namespace/Secret/Helm 对象 |
| [`kubernetes/recover-web.sh`](../../../../platform-portal/marquez/kubernetes/recover-web.sh) | 已 Ready Marquez Web 的受控恢复；可执行 `kubectl apply` NodePort Service，不是纯只读 |
| [`kubernetes/web-nodeport.yaml`](../../../../platform-portal/marquez/kubernetes/web-nodeport.yaml) | `dw-marquez/marquez-web-lan` NodePort **30999**；仅 Web，不应视为公网授权 |
| [`tests/verify.sh`](../../../../platform-portal/marquez/tests/verify.sh) | 真实 K8s/PG/HTTP 检查，含临时 port-forward；不属于离线单元测试 |
| [`tests/inventory_readonly.py`](../../../../platform-portal/marquez/tests/inventory_readonly.py) | 固定目标、指定 context、只执行 `kubectl get` 的运行资源只读盘点；**不是** HTTP/PG SQL/lineage 健康证明 |
| [`tests/test_inventory_readonly.py`](../../../../platform-portal/marquez/tests/test_inventory_readonly.py) | 纯离线测试：命令白名单、context fail-closed、资源状态及错误信息保护 |
| [`tests/verify_business_lineage.py`](../../../../platform-portal/marquez/tests/verify_business_lineage.py) | 对固定内网 Marquez 执行有界 HTTP GET，按精确 Batch 和三个 Spark Application 查询真实子 Run、DatasetVersion、两级 Parent；分别报告严格业务血缘和物理 RDD Action 生命周期，明确 Writer durable COMMIT / PG17 / SKIP **必须独立核对**，不伪造 Action COMPLETE，也不修改 Marquez 或 Writer |
| [`tests/test_verify_business_lineage.py`](../../../../platform-portal/marquez/tests/test_verify_business_lineage.py) | 纯离线回归：读取和写入 DatasetVersion 同一性、Reconcile 终态、Spark Action/Application 精确 Parent、Airflow→Spark 真实 Task Run ID、错误 Batch、HTTP off-host fail-closed |

**P6 演示/运维导航**：[官方 Marquez Web 内网演示与固定 Batch 只读查询](SHOWCASE-RUNBOOK.md)；独立受控 GET-only [Run #40218701308](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218701308)，Artifact 包含 K8s/HTTP/API/Lineage 四类验证；没有新增或变更本组件的真实部署脚本、Helm、镜像、业务逻辑或应用测试源码。浏览器级可视化尚需人工实机确认。

**依赖**：PG14 持久化组件由 [Postgres CODE](../postgres/CODE.md) 管理；Airflow Provider 与 Spark Listener 仅向 Marquez API 发送真实 OpenLineage，分别由 [Airflow CODE](../airflow/CODE.md)、[Spark CODE](../spark/CODE.md) 管理。版本/Ready/接入情况以单次 Run 证据为准，不等于实时探针。

[系统 CODE](../CODE.md) · [验收限制](../README.md) · [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。
