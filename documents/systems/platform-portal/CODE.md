---
status: active
scope: platform-portal-source-map
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Platform Portal — CODE / 源码总导航

> 系统级 CODE 只负责**唯一所有权与入口**，逐文件源码导航在对应子组件 `CODE.md`，职责、验收范围在 [系统 README](README.md)。仓库当前源文件位置已静态核对，不表示 Kubernetes/Marquez 今日在线。

| 组件 | 代码实际所有者 | 唯一 CODE 来源 | 运行与修改边界 |
| --- | --- | --- | --- |
| Marquez API/Web | [`platform-portal/marquez/`](../../../platform-portal/marquez/) | [Marquez CODE](marquez/CODE.md) | Helm/部署与 NodePort；改变真实服务必须单独批准 |
| PostgreSQL14 metadata | [`platform-portal/postgres/`](../../../platform-portal/postgres/) | [PostgreSQL14 CODE](postgres/CODE.md) | YAML 为历史快照；Retain PVC，不得作为重建指令 |
| Airflow Provider/Probe | [`platform-portal/openlineage/airflow/`](../../../platform-portal/openlineage/airflow/) · [`airflow/dags/platform_portal_openlineage_probe.py`](../../../local-data-platform/airflow/dags/platform_portal_openlineage_probe.py) | [Airflow CODE](airflow/CODE.md) · [Data Platform Airflow CODE](../data-platform/airflow/CODE.md) | Probe DAG 由 Airflow DAG 运行路径拥有，Portal 文档负责观测职责；共享 Scheduler 调整有副作用 |
| Spark Listener/Probe | [`platform-portal/openlineage/spark/`](../../../platform-portal/openlineage/spark/) | [Spark CODE](spark/CODE.md) | 离线模板/静态测试与隔离 Smoke，**非生产 Person/Visit 应用** |
| OpenLineage Blob Relay Consumer | [`platform-portal/openlineage/blob-relay/`](../../../platform-portal/openlineage/blob-relay/) | [Consumer entry](../../../platform-portal/openlineage/blob-relay/consumer.py) · [Mock tests](../../../platform-portal/openlineage/blob-relay/tests/test_consumer.py) · [protocol/limits](../../../platform-portal/openlineage/blob-relay/README.md) | Offline committed Blob → existing Marquez; no live PG14/POST permission |\n| Portal Web / Exporter / Control / Infra | [`platform-portal/portal/`](../../../platform-portal/portal/) | [Portal CODE](portal/CODE.md) | P0 Schema、Mock 和合同测试已实现，其余组件未部署；公网发布需单独审查 |

**跨组件数据边界**：Marquez 接收真实 OpenLineage Job/Run/Dataset 事件，不创建 OMOP 业务数据。`dw-postgre14` PG14 为元数据数据库；`dw-postgre` PG17 为本地业务库。Airflow 真实 Producer/Consumer、Spark Person/Visit 与 OMOP Writer 的实际源码仍属于 [Data Platform](../data-platform/README.md)，不迁入 `platform-portal/`。

**安全**：不要直接运行部署/恢复/探针类 `*.sh`，只读查询与会修改 Scheduler/Service/Secret/StatefulSet 的代码必须分别评估；详见 [Operations 安全规则](../../engineering/operations/SAFE-OPERATIONS.md)。新 Portal 源码的新增/删除/移动必须在同一 PR 同步对应的组件 CODE；当前文档迁移不更新任何实际脚本/镜像/Manifest。

**历史证据**：[Marquez 验证](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) · [A3](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) · [A4](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)。A4 原失败和后续只读部分 PASS 须并列陈述。
