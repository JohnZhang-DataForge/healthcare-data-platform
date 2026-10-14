# Portal 运维、安全与恢复

- PostgreSQL14：`dw-postgre14/dw-postgre14-database-0`，PVC `dw-postgre14-data` 50Gi、StorageClass `postgres-marquez` Retain，实际目录在 worker03 的 `/data/postgres-marquez/`。Retain 并不等于 DB 备份，且与其他目录共享底层文件系统；建议另建立 `pg_dump -Fc`、定期恢复测试、磁盘空间阈值。
- Secret：源 `dw-postgre14/postgres-secret`，目标 `dw-marquez/marquez-db`；禁止跨 Namespace 直接 secretKeyRef，禁止密码写入 Git、日志或 Helm values。
- Marquez：API/Web 的 ClusterIP 仅用于集群内；`marquez-web-lan` 30999 只能在确认本机 LAN/VPN/firewall/NAT 后为可信用户开放。原生 Web 代理 API，请勿当匿名只读网页发布。
- 故障：保留 pg14 StatefulSet、PV、PVC，不得以 `helm uninstall` 清理 DB，不直接修改 `dw-postgre` 的 OMOP 与 Airflow。API 不健康先查 rollout/events、Secret Key 名、JDBC DNS、Flyway Schema History。
- Git：Deploy/Validate 与证据由 exact-SHA Self-Runner 运行，失败 3 次自动暂停，避免无界重试；完成验收才合并 PR。
