# 已部署 PostgreSQL14 Git 快照 / 不触发自动重装

以下 YAML 按 2026-10-13 用户实际已部署的配置归档；**不是预期新建或覆盖 PG14 集群的 Manifest**。数据库 Namespace `dw-postgre14`；worker03 label `workload=compute`；StatefulSet `dw-postgre14-database`、DB/User `marquez`、Service `dw-postgre14`，PVC `dw-postgre14-data`；StorageClass `postgres-marquez`，PV Retain。原始 master01 文件目录 `/data/postgre14-marquez/`，Git 仓库路径不是其自动同步副本。

**重要外部依赖**：LocalPath Provisioner `local-path-config` 须含 `postgres-marquez` 指向 worker03 `/data/postgres-marquez` 的 nodePathMap；此外 `dw-postgre14/postgres-secret` 具有 `POSTGRES_USER`、`POSTGRES_PASSWORD` 和 `POSTGRES_DB`，**密码不进入 Git**。

PostgreSQL14 当前已经运行且持久化，**不执行重新 apply/replace/delete**，修改前需单独迁移审查及数据备份。
