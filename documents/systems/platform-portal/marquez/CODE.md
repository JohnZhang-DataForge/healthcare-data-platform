---
status: active
scope: portal-marquez-source-map
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
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

**依赖**：PG14 持久化组件由 [Postgres CODE](../postgres/CODE.md) 管理；Airflow Provider 与 Spark Listener 仅向 Marquez API 发送真实 OpenLineage，分别由 [Airflow CODE](../airflow/CODE.md)、[Spark CODE](../spark/CODE.md) 管理。版本/Ready/接入情况以单次 Run 证据为准，不等于实时探针。

[系统 CODE](../CODE.md) · [验收限制](../README.md) · [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。
