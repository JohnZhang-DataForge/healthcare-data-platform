# Marquez 部署与恢复 Runbook

> **真实 LIVE STATE**：Marquez API/Web 1/1 Ready，`dw-postgre14/marquez` 迁移 37 表，`dw-marquez/marquez-web-lan` 30999 Service 已创建；[实际验收](./validation.md)。不用重复运行 Helm 安装来验证 Web NodePort。网络访问控制与备份演练仍是独立运维门槛。

**部署仓库源代码：**
- `platform-portal/marquez/helm/values.yaml`
- `platform-portal/marquez/kubernetes/deploy.sh`
- `platform-portal/marquez/tests/verify.sh`
- `platform-portal/postgres/` 为已部署 YAML 的**只读记录**，不得重新安装数据库。

**固定依赖**：Marquez 0.51.1 官方 annotated tag 对应 commit `27a4a1357d9078bc4e6738524dfe5ba9d77aa2df`；Helm v3.17.3 sha256 验证；用户现有 PG14 14.24。图表源码从官方 GitHub tarball + `helm dependency build` 取得，`https://marquezproject.github.io/marquez` 不是可用 Chart index，之前已得到 404。

**安全步骤**：Runner 固定完整 Healthcare commit SHA；先 `bash -n`/Helm render，验证 `postgresql.enabled=false`、2 个 ClusterIP service 和外部 PG14 Service DNS；再确认 `dw-postgre14` Pod/PVC/Service/DB；复用 `dw-marquez/marquez-db` Secret（仅由已有 Secret 在 Runner stdin 复制生成，不打印或入 Git），执行 `helm upgrade --install`。运行时只应改 `dw-marquez`；绝不清理 `dw-postgre14` PVC/PV，禁止对 `dw-postgre` 执行 SQL 或 Helm。

**验收顺序**：部署/rollout Ready → PG14 `flyway_schema_history` 和业务元数据表存在 → API 本地端口转发 HTTP GET → Web 本地 HTTP、同源 `/api/v1` → （网络许可后）单独 Web NodePort 30999 Service。不能拿 `helm status deployed` 单独当完整成功。

**失败恢复**：先保存 Runner Run、准确 SHA、Helm 状态、Pod Events；别删除 PG Pod/PVC/PV；没完成的 Deployment 可按 Helm revision 回滚，但不能执行 PostgreSQL migration down/cleanup 作为一般恢复；重新执行只在新一轮授权时触发。Namespace `dw-marquez` 和 Secret 可以保留复用。
