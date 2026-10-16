# Platform Portal — 架构

```text
synthea producer (worker01) → SeaweedFS S3 READY manifest
                                 ↓
Airflow 3.2.2 (OpenLineage Provider 2.17.0 已安装)
                                 ↓
Spark Operator / PySpark (worker02) →  Parquet
                                 ↓
Python Writer → OMOP PostgreSQL17 (dw-postgre; 业务库不可改)
            │             │
            └─ 真实 OpenLineage event（依次接入，不伪造完成的边）
                         ↓
Marquez API (dw-marquez, ClusterIP) ↔ marquez PostgreSQL14 (dw-postgre14)
                         ↑
Marquez Web (dw-marquez, ClusterIP) → 单独 LAN NodePort 30999
            [Web 本身代理 /api/v1 和 /api/v2beta；不是只读 API]
```

- 仅部署 **Marquez 官方原生 Web UI**，不开发单独前端。未来的 Superset / Portal UI 是预留方向，不在本次验收。
- Marquez 依赖 **独立、已持久化** PostgreSQL14（namespace `dw-postgre14`，DB/role `marquez`），不需要修改 PostgreSQL17 业务数据库，也不新建 PostgreSQL Pod。
- Web 与 API 必须分属 Kubernetes ClusterIP Service；若需要 30999，必须创建仅选择 Web Pod 的独立 Service，不得把官方 Helm Chart 的共享 `service.type` 改为 NodePort。
- Web 反向代理可访问 API，因此 NodePort 不是原生匿名只读门户；LAN/VPN、NAT、firewall 保护不可省略。
- Producer/Writer 成功状态与 PostgreSQL COMMIT 必须来自真实事件/验证；不得用测试事件冒充业务 Lineage。

[全阶段设计与旧 A0 版本检查](./implementation-plan.md)。
