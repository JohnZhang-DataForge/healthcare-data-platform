# Marquez 路线 A — A0 版本兼容与 NodePort 网络安全只读验收 Closeout

**执行日期**：2026-10-13 EDT / 2026-10-14 UTC  
**阶段**：A0 第二轮 / Compatibility & Security Audit  
**综合状态**：**只读检查闭环 PASS；直接部署 A1/A2 = HOLD（发现真实兼容风险和入口风险）**。  
**正文权威**：[路线 A v3.0](./MARQUEZ-OPENLINEAGE-IMPLEMENTATION-PLAN-v3.0.zh-CN.md) → [A0 第一轮验收](./MARQUEZ-A0-READONLY-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) → 本文。**不能用本文的 Workflow SUCCESS 替代 Marquez 实际迁移/运行通过**。

## 1. 真实 GitHub / Self-Runner 证据

- 已经合并的 Healthcare 业务 SHA（本轮 Runner 固定 checkout）：`f89ed12b2cb051b8296ce2c1ab7e8cba9676d19f`，TASK004 的 NEW_ONLY digest 和两个真正 S3 READY Batch 有各自单独的证据；本轮没有重复生成/重新发布。
- 上游 Marquez source 固定到 [Commit `180f37b22387146187af1ef0279e3ee1d1ccd789`](https://github.com/MarquezProject/marquez/tree/180f37b22387146187af1ef0279e3ee1d1ccd789)；所有上游文件只下载/静态审计，**没执行 Marquez 或 DB migration**。
- **[Self-Runner Run 38491060185](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38491060185) SUCCESS**，全部 job steps PASS。受控 Push-triggered `.github/workflows/marquez-a0-compatibility-network.yml` 精确 source SHA `11bece9af656137d6e2ae4da1fbe7a5954513fba`。
- [Self-Runner PR #86](https://github.com/JohnZhang-DataForge/Self-Runner/pull/86) MERGED，Main merge SHA `0e7c8911f0f853d90a409dc791d2c600e1d4c6c5`。Artifact: `marquez-a0-compatibility-network`（只含筛选后的配置与计数，无 Secret）。
- 受控操作：`kubectl get` 和 Pod 内 `df`（只读）、PostgreSQL `BEGIN TRANSACTION READ ONLY` + `ROLLBACK`、固定 SHA 上游文本检查；没有 `kubectl apply/create/delete/patch`，没有新数据库、PVC、Kubernetes Service 或 S3/DAG/Writer 作业。最终 `KUBERNETES_MUTATION=NO`，`POSTGRESQL_MUTATION=NO`，`MARQUEZ_DEPLOYED=NO`。

## 2. PostgreSQL 17 和 Marquez Flyway：实质性阻塞

| 证据 | 核实值 | 技术含义 |
|---|---|---|
| worker03 运行 PostgreSQL | **17.11**（170011），连接 **18 / 100** | 真 PG 只读重查，不代表迁移可用 |
| Marquez 上游 [`api/build.gradle`](https://github.com/MarquezProject/marquez/blob/180f37b22387146187af1ef0279e3ee1d1ccd789/api/build.gradle) | **`org.flywaydb:flyway-core:8.5.13`** | 此版本发布时间早于 PG17 |
| Flyway 官方 [release notes](https://documentation.red-gate.com/flyway/release-notes-and-older-versions/release-notes-for-flyway-engine) | **10.20.0（2024-10-16）新增 PG17 支持** | 旧版 8.5.13 不能当 PG17 正式兼容方案 |
| Marquez 上游 [`MarquezApp.java`](https://github.com/MarquezProject/marquez/blob/180f37b22387146187af1ef0279e3ee1d1ccd789/api/src/main/java/marquez/MarquezApp.java) | 启动必调用 `DbMigration.migrateDbOrError(...)` | 不得假设启动开关会跳过 Flyway 检查 |
| Marquez [`DbMigration.java`](https://github.com/MarquezProject/marquez/blob/180f37b22387146187af1ef0279e3ee1d1ccd789/api/src/main/java/marquez/db/DbMigration.java) | 先 `flywayFactory.build` / `hasPendingDbMigrations`；新的空库遇到待迁移仍可能运行 `migrate()` | `migrateOnStartup=false` **不是**规避 PG17 兼容问题的安全手段 |
| 上游 Chart | `0.51.1`（主分支 `Chart.yaml`） | 不等于“在 PG17 已成功运行”的 Live 结果 |

**判定**：`PG17_WITH_UNMODIFIED_MARQUEZ=BLOCKED_FOR_DEPLOYMENT`；这意味着**不能直接选择 worker03 PG17 + 原版 Marquez、允许自动 migrate**。这个 BLOCKED 是版本/源码静态审计结论，并未在 worker03 运行失败迁移，更没有改写既有数据库。

**建议保持用户的 PostgreSQL 复用优先级，不立即额外安装第二个 PostgreSQL：**

1. **NEXT P1：隔离的 PostgreSQL 17 兼容性 PoC**。使用固定 Marquez 版本源码，在独立测试环境重新构建与 PG17 兼容的 Flyway 依赖（**至少有官方 PG17 支持的版本，并核对 `flyway-database-postgresql` 插件/Java API 改动**）。仅对一次性独立测试库执行 Marquez 全量 migrations；验证 API 启动、Web API、schema version、重启、重放、失败恢复。测试数据库不可是 `omop`/`airflow`，也不得未经另一轮授权直接在 worker03 创建或修改真实 `marquez` DB。
2. PoC 真 PASS 且 resource/extension/权限/connection footprint 安全以后，才考虑在**现存 PostgreSQL 实例上**新建独立 `marquez` 数据库 + 非超管角色 + Secret，再上 A1。Marquez 的 DB 迁移和 API 版本必须有一致测试证据/固定镜像 digest。
3. 如果 PoC 无法安全复用 PG17，才研究**独立、与 Marquez 实测兼容且仍受维护的 PostgreSQL 镜像/实例**。旧 PostgreSQL 版本不能因为 Flyway 能启动就忽略安全补丁/支持期限。
4. **严禁**在生产 OMOP 上试跑 `migrate`、修改 `omop`/`airflow` schema、关掉 Existing Target Drift 或将只读检查认作真实 Marquez 成功部署。

## 3. NodePort 30999 与内网权限模型：三层结论

### 3.1 真实集群静态/只读网络证据

| 实测项 | 结果 | 判断 |
|---|---|---|
| Kubernetes Nodes Ready | 4 | PASS |
| `30999` Service collisions | **0** | 端口未被现有 Service 使用；未创建 NodePort |
| Node `InternalIP` | 4 | 只记录数量，避免日志公开内网地址 |
| Node `ExternalIP` | **0** | 不等于没有 NAT/外部端口映射 |
| 全球可路由 Node IP | **0** | 不等于对互联网不可达 |
| NetworkPolicy 对象总数 | **0** | 不能假设存在有效内网 egress/ingress ACL |
| `dw-marquez` Namespace | **不存在** | 仍未部署 |
| kube-apiserver Pod | 1 | 已见控制面 Pod |
| 显式 `--service-node-port-range` | **NOT VERIFIED** | 默认 30000–32767 只是预期，未证明当前集群使用默认 |
| 主机防火墙 / 上游路由器 NAT / 用户 LAN/VPN | **NOT VERIFIED** | NodePort 暴露安全 Gate 继续 HOLD |

### 3.2 Helm Chart 与 Web Proxy 源码发现

上游 [`chart/templates/web/service.yaml`](https://github.com/MarquezProject/marquez/blob/180f37b22387146187af1ef0279e3ee1d1ccd789/chart/templates/web/service.yaml) 和 [`chart/templates/marquez/service.yaml`](https://github.com/MarquezProject/marquez/blob/180f37b22387146187af1ef0279e3ee1d1ccd789/chart/templates/marquez/service.yaml) **均读取 `.Values.service.type`**。简单地修改 Chart 全局 `service.type=NodePort` 可能**同时**把 Web 和未经鉴权的 API 变成 NodePort，违反已经批准的“内部 API / 只让受控 Web 走 30999”架构。

上游 [`web/setupProxy.js`](https://github.com/MarquezProject/marquez/blob/180f37b22387146187af1ef0279e3ee1d1ccd789/web/setupProxy.js) 确实把浏览器同源路径 **`/api/v1`、`/api/v2beta`** 代理到 `MARQUEZ_HOST:MARQUEZ_PORT`。**即使仅 Web Service 是 NodePort，访问 30999 的浏览器也能通过 Web Proxy 向 API 发送请求**，不是自动的只读授权/只读 API。

### 3.3 下一步明确网络设计（待独立验收）

- **部署时保持官方 Chart `service.type=ClusterIP`**，API/Web 内部 Service 独立保留；另建**专用且只有 Web selector 的 NodePort Service**，显式 `nodePort: 30999`，绑定真实 Web targetPort。新专用 Service 的 selector 先由 Helm render 核实，避免意外命中 API Pod。
- NodePort 只能允许经过核实的 **trusted LAN/VPN** 访问，外层防火墙和路由器 NAT 状态必须有**独立有效证据**；单看 Node ExternalIP=0 不可视为“安全暴露证明”。不部署额外公开前端，但必要的鉴权/访问限制是基础安全控制。
- 若最终要让招聘经理**无需 VPN 匿名公网只读浏览**，当前原生 Web+Proxy 架构无法仅靠 NodePort 实现：须另起设计评审，选真实只读 API 网关/代理/鉴权策略；本轮和初期开发都不开放匿名互联网。
- 开放前实测 Web `/healthcheck` 与 Job/Dataset/Run 浏览器侧 API 请求，同时确认后端 API Service 仍无 NodePort；如任意 Gate 未证明则 `NODEPORT_EXPOSURE=HOLD`，允许内部 ClusterIP/端口转发验证而不放行外部端口。

## 4. 资源与磁盘核验（不能误解 PVC 配额）

- worker03 的 `postgres-local` PVC Request/Capacity 仍为 **50Gi Bound**（A0 前一轮）；本轮 PG Pod 路径 `df -Pk /var/lib/postgresql/data` 报文件系统 `total=306453440 KiB`、`used=21755444 KiB`、`available=269058036 KiB`。
- **这只是 PG Pod 内路径的底层可见文件系统数值**，LocalPath PVC 容量不一定是真实 quota，不能用本轮 `df` 数值声称 PostgreSQL 50Gi PVC 就有 256Gi 可用，也不能把它视为已经完成磁盘 IOPS、备份、增长率及真实峰值验收。
- PostgreSQL 17.11 连接 `18/100`，为此刻读数，不是峰值；未创建 `marquez` DB 或 Role。若复用必须限制 Marquez connections/threads，不占用 OMOP Writer 正常事务预算。

## 5. 安全/任务状态

- `A0_COMPATIBILITY_AUDIT=PASS` 是 **发现、确认、记录真实部署阻塞**，不是批准 A1/A2。
- `PG17_UNMODIFIED_MARQUEZ_DEPLOY=BLOCKED`（Flyway 8.5.13 vs PG17 版本兼容）；`30999_PUBLIC_ACCESS=HOLD`（Web 代理 API，且未验证防火墙/NAT）。
- `MARQUEZ_DB_CREATED=NO`、`MARQUEZ_DEPLOYED=NO`、`K8S_MUTATION=NO`、`PG_MUTATION=NO`。
- 新完成的独立 `NEW_ONLY` 真实 S3 READY 的演示仍可做后期真实数据集来源，但 **Airflow 新 Batch Claim、PG Writer 真 COMMIT 尚无验证**；TASK004 IN PROGRESS，TASK005 ON HOLD。

## 6. 下一轮推荐的有界开发闭环

**P1：Marquez + PostgreSQL 17 隔离兼容性 PoC**，仍遵循 GitHub + Self-Runner：

1. 冻结 Marquez Chart/API/Web/JDK/JDBC/Flyway 的 exact upstream SHA/依赖；修改 Flyway 必须是**单独可追溯的构建**，不能暗改官方二进制。
2. 为 PG17 构建具 PG17 支持的 Flyway/驱动并审核兼容 API；对**隔离、可销毁的测试 Postgres 17** 执行真实 Marquez 全量迁移、启动及健康接口验证。测试环境不能接触主线 OMOP/airflow 数据；不复制原数据库或 Secret。
3. 真 PoC PASS 后才能决定能否复用 worker03 的 **同一个 PostgreSQL 实例、但独立 `marquez` DB**；否则先确定一个仍在受支持期内的独立数据库技术方案。PoC 产生的业务外 Demo 测试事件必须标注 `TEST`、不可冒充真实 Synthea 血缘。
4. 并行继续评审网关 LAN/VPN 和 NodePort Service 渲染，但**尚不开放 30999**。
5. 每轮最多 3 次失败，闭环验收和文档更新后才能进入正式 A1/A2。维持 `CLAIM_ENABLE=NO`、Writer Existing Target Drift、TASK005 ON HOLD。

**结论：完成了真正的 A0 静态上游/真实集群结合验收，证明现在不能安全直接安装原版 Marquez 到 PostgreSQL17 并公开 30999。下一轮应解决独立兼容 PoC，而不是盲目创建数据库。**
