# Portal 运维、安全与恢复

> **A3 运行时配置风险**：Airflow OpenLineage Provider 到 Marquez 已真实联通（[A3 实际 Airflow→Marquez Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)），但当前是 `kubectl set env` 更新 Shared Scheduler Deployment。将来执行 Airflow Helm upgrade 前，必须把 `TRANSPORT`、`NAMESPACE`、`SELECTIVE_ENABLE=True`、`DISABLE_SOURCE_CODE=True` 持久化纳入权威 Helm Values 并回归验收；否则新 Pod 可能丢失本轮配置。不应默认为 TASK004 DAG 开启血缘采集。

> **当前注意**：NodePort `30999` 已创建。由于原生 Web 同源代理 API，这并非只读门户；Kubernetes Node 无 ExternalIP 但家庭路由器 NAT 和防火墙未审计。务必仅在受控 LAN/VPN 内访问，不要配置公网端口转发。真实数据血缘需 A3 以后接入，当前 API HTTP 200 只是服务健康，不代表有实际业务 lineage。

- PostgreSQL14：`dw-postgre14/dw-postgre14-database-0`，PVC `dw-postgre14-data` 50Gi、StorageClass `postgres-marquez` Retain，实际目录在 worker03 的 `/data/postgres-marquez/`。Retain 并不等于 DB 备份，且与其他目录共享底层文件系统；建议另建立 `pg_dump -Fc`、定期恢复测试、磁盘空间阈值。
- Secret：源 `dw-postgre14/postgres-secret`，目标 `dw-marquez/marquez-db`；禁止跨 Namespace 直接 secretKeyRef，禁止密码写入 Git、日志或 Helm values。
- Marquez：API/Web 的 ClusterIP 仅用于集群内；`marquez-web-lan` 30999 只能在确认本机 LAN/VPN/firewall/NAT 后为可信用户开放。原生 Web 代理 API，请勿当匿名只读网页发布。
- 故障：保留 pg14 StatefulSet、PV、PVC，不得以 `helm uninstall` 清理 DB，不直接修改 `dw-postgre` 的 OMOP 与 Airflow。API 不健康先查 rollout/events、Secret Key 名、JDBC DNS、Flyway Schema History。
- Git：Deploy/Validate 与证据由 exact-SHA Self-Runner 运行，失败 3 次自动暂停，避免无界重试；完成验收才合并 PR。
