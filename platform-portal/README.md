# Platform Portal — 真实数据血缘与数据平台可观测性

本目录保存 **实际正在开发/运行** 的 Marquez、OpenLineage、专用数据库和后续 Portal 组件。业务 ETL 仍在原有 `airflow/`、`spark/`、`apps/` 与 `scripts/`，不搬家。

- `marquez/helm/values.yaml` — PostgreSQL14 外部数据库配置（**不存 Secret**）
- `marquez/kubernetes/deploy.sh` — 非破坏式、固定 upstream 版本部署入口
- `marquez/tests/verify.sh` — API/Web/PG14 真实验收
- `postgres/*.yaml` — 由已部署的 PostgreSQL 14 实际 YAML 保存的 Git 快照。**不代表重新部署**。
- `../docs/platform-portal/` — 统一文档（架构、计划、部署、验收、运维和历史归档）

当前 Marquez Namespace 固定 `dw-marquez`，PostgreSQL14 Namespace 固定 `dw-postgre14`；不接触 `dw-postgre` 中的 OMOP/Airflow 数据库。初期只有经 LAN/VPN 的原生 Marquez Web，**不是自定义网站**。
