# Marquez / OpenLineage A0 — Kubernetes + PostgreSQL READ-ONLY 实测 Closeout

**日期**：2026-10-13 EDT / 2026-10-14 UTC  
**范围**：路线 A [v3.0 实施规划](./MARQUEZ-OPENLINEAGE-IMPLEMENTATION-PLAN-v3.0.zh-CN.md) A0 的首个**真实集群环境/容量/版本审计闭环**。  
**结论**：**A0 CORE READ-ONLY EVIDENCE = PASS；A1/A2 DEPLOYMENT READINESS = HOLD（兼容、安全网络和浏览器 API 路径未完全核验）**。没有部署 Marquez、没有创建 DB、没有设置 NodePort。本文件**不批准 A1/A2 修改集群**。

## 1. 正式证据与测试边界

- 精确固定 Healthcare Main 源码 SHA：`a69bb97f674a20ada6b8b69d1fb25ba5cf374b88`（当时路线 A v3.0 方案合并 SHA）。后续 Main 并行前进不会改变这轮测试结论；实施前必须再次读取最新 Main。
- Self-Runner 最终 workflow HEAD SHA：`2a1ddccfe849411f63c1383e0d9aa66458deca30`，受控 push 触发 `.github/workflows/marquez-a0-readonly.yml`。
- [首次真实 Run 38490355553](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38490355553)：SUCCESS；版本 package 汇总逻辑未正确显示，故不把它当完整 package 结果。
- **[最终真实 Run 38490452257](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38490452257)：SUCCESS**；修复 package 汇总，并增加 worker01–03 节点调度资源请求/限制读回，未超过三轮。
- [Self-Runner PR #84](https://github.com/JohnZhang-DataForge/Self-Runner/pull/84) **MERGED**，Merge SHA `e507850d1ddc628a3e7e38dc8ccb65b41f837045`。
- Run Artifact：`marquez-a0-readonly-report`（仅经筛选的资源、版本、端口、SQL 汇总；不采集 Secret 或医疗 CSV）。完整实时原始证据在上述 Github Actions Run 日志。

两轮都在既有 `dw-runner-set` 中执行，只运行 Kubernetes GET/DESCRIBE/TOP、可选 Pod 内 Python 版本查询，以及 PostgreSQL **`BEGIN TRANSACTION READ ONLY` ... `ROLLBACK`**。没有 `kubectl apply/create/delete/patch`、数据库 DDL/DML、S3 上传或 DAG/Writer 调用。**`KUBERNETES_MUTATION=NO` / `DATABASE_MUTATION=NO`。**

## 2. 运行时 Kubernetes / NodePort

| 事实 | LIVE 值 | 验收解释 |
|---|---|---|
| Kubernetes Nodes | 4/4 Ready（master01、worker01、worker02、worker03） | PASS |
| worker01 allocatable | CPU 5600m，Memory 23877341575 bytes | 只代表可调度分配额 |
| worker02 allocatable | CPU 5600m，Memory 23877333793 bytes | 只代表可调度分配额 |
| worker03 allocatable | CPU 5600m，Memory 23877349357 bytes | 只代表可调度分配额 |
| NodePort 30999 | 现有 Services 使用数 0，`IN_USE=False` | **未被占用 PASS**，不等于端口外部可达或受保护 |
| API server `--service-node-port-range` | `NOT_VERIFIED`（未从现有 static pod 参数读到） | 默认范围 30000–32767 仅可作设计参考，不能当成当前集群实测 |
| K8s metrics-server / `kubectl top nodes` | `NOT_AVAILABLE` | 实时 CPU/RAM 压力尚无可用指标 |
| dw-marquez | 当前 0 Pod（**Namespace 本身是否存在未核验**） | 未部署 Marquez |
| SparkApplications | 本次可读取 27 个 CR 记录；最近五个声明 Spark `3.5.7` | 不等于 Spark Agent 已安装 |

从 `kubectl describe node` 的 **Allocated resources** 汇总：

| Node | CPU requests | CPU limits | Memory requests | Memory limits |
|---|---|---|---|---|
| worker01 | 850m (15%) | 1 core (17%) | 1094Mi (4%) | 2248Mi (9%) |
| worker02 | 1275m (22%) | 4350m (77%) | 1990Mi (8%) | 4808Mi (21%) |
| worker03 | 1150m (20%) | 2500m (44%) | 1490Mi (6%) | 9504Mi (41%) |

**解释**：调度资源请求看起来有余量，但**不是**当前实际使用率；没有可靠的实时 `top` 与 worker03 磁盘剩余空间/IOPS、PostgreSQL 连接峰值，所以 Marquez 的具体 request/limit、DB 池大小仍要在 A1/A2 前审查。禁止把节点总内存等同于剩余空闲。

## 3. 真实 Airflow / Spark / PostgreSQL 版本

| 项目 | LIVE 值 | 来源与限制 |
|---|---|---|
| Airflow | **3.2.2** | Scheduler 真实 Python distribution |
| `apache-airflow-providers-openlineage` | **2.17.0，已安装** | **A3 不必从零安装 Provider**；是否配置/启用/成功发事件仍未证实 |
| `openlineage-python` | **1.47.1，已安装** | 不等于已发送事件 |
| Kubernetes Airflow Provider | **10.17.1** | 真实 Scheduler 查询 |
| Spark Operator | **2.5.2** | 工作负载控制器 image tag |
| SparkApplication | **3.5.7** | 现存 Spark CR 的 `spec.sparkVersion`；Spark Driver JDK/Scala、OpenLineage Spark Agent 是否存在需另查 |
| PostgreSQL | **17.11**（version_num=170011） | 真实 DB 本机只读 SQL |
| PostgreSQL `max_connections` | **100** | 实测 |
| PostgreSQL 查询时当前连接 | **18** | 单点瞬时值、非历史峰值 |
| PostgreSQL 可连接数据库合计空间 | **2,656,298,009 bytes**（约 2.66GB / 2.47GiB） | 不代表磁盘真正空闲量 |
| `marquez` DB / `marquez` 或 `marquez_app` Role | **0 / 0** | 尚未创建 |
| PostgreSQL PVC | `dw-postgre/dw-postgre-data`，`50Gi`，Bound，StorageClass `postgres-local` | 实际卷使用率未测 |
| Synthea PVC | `dw-synthea/synthea-new-only-state`，`5Gi`，Bound，StorageClass `synthea-local` | Demo 不复用它 |

**潜在好消息**：OpenLineage Airflow Provider **已经随现有 Airflow 镜像安装**。下一轮应优先核对 Airflow 配置状态和到 Marquez API 的连通方案，不要为了安装已存在的 Provider 盲目替换 Airflow 3.2.2 镜像。

## 4. 上游 Marquez 版本调查（不是运行时验收）

阅读 [Marquez 官方 Chart.yaml](https://github.com/MarquezProject/marquez/blob/main/chart/Chart.yaml) / [values.yaml](https://github.com/MarquezProject/marquez/blob/main/chart/values.yaml) 时，Main 示例目前标记 **Chart 0.51.1、backend/web image 0.51.1**，其配置区分 backend 默认端口 5000、admin 5001、Web 3000，且可禁用 bundled PostgreSQL；GitHub `releases/latest` API 所返最新标记 Release 为 **0.50.0（2024-10-24 发布）**。**Chart Main 候选值不等于已验证并推荐的部署版本**，0.50.0 Release 和 chart Main 值也并非同一种“版本已经对齐”的证据。

**A1/A2 前必须单独确认**：
1. Marquez 后端镜像与数据库迁移工具是否真的支持 PostgreSQL **17.11**；官方 Chart 的 Helm 依赖、需要的 PostgreSQL schema/extension、角色/DDL 最小权限及升级/回滚风险。
2. 0.51.1 Docker image / Web image / 对应 Chart 是否真实可拉取、支持现有 K8s 和独立 DB；不要拿未知镜像对运行中的 OMOP PostgreSQL 自动 migrate。
3. Web 浏览器如何访问 API，是否使用 HTTP reverse proxy/API base URL；不要将未经鉴权的 API 随 Web 一并开放到公共网络。
4. **30999** NodePort 的服务范围、apiserver nodeport range、主机防火墙、路由/NAT、LAN/VPN 访问控制。未实际证明之前 `NETWORK_ACCESS_GATE=HOLD`。
5. Spark 3.5.7 的 JDK/Scala、Listener version、Spark Operator Application Config 是否能兼容 pin 版本，以及避免侵入 TASK004 的注入策略。

## 5. A0 验收判定及下个最小闭环

| Gate | 状态 |
|---|---|
| Exact Healthcare SHA + Runner 业务隔离 | **PASS** |
| Nodes/Services/PVCs/Controllers + Port 30999 未占用 | **PASS** |
| Airflow 真实 Provider 版本 | **PASS** |
| PostgreSQL 真实版本与只读容量/连接快照 | **PASS** |
| Nodes 调度资源 requests/limits | **PASS（非实时利用率）** |
| Marquez + PostgreSQL 17 版本兼容/镜像固定 | **NOT VERIFIED** |
| Web UI → API 真实浏览器请求 | **NOT VERIFIED** |
| 防火墙/NAT/VPN 的 NodePort 曝露安全 | **NOT VERIFIED** |
| 真实 OpenLineage 事件/Marquez 服务 | **NOT RUN** |
| PostgreSQL DDL / K8s 服务创建 / OMOP Mutation | **NO** |

**A0 核心只读技术审计闭环已完成，A1/A2 的部署前许可继续 HOLD。**

**NEXT = A0 后半部兼容性/网络访问 Gate**（另一轮只读/离线验证）：选择 pin 的 Marquez backend/web/chart，研究 PostgreSQL 17 + Flyway 迁移兼容性和 UI↔API 路由；检查实际集群 NodePort 范围及 LAN/VPN 入口、worker03 磁盘余量或监测能力。明确 PASS 后才做 A1：独立 `marquez` DB/Role/Secret。A1 再 PASS 后才做 A2：`dw-marquez` + Marquez API/Web + NodePort 30999。当前仍不开发额外前端、Superset、OpenMetadata 或 Kafka。

**TASK004 仍独立开发，`CLAIM_ENABLE=NO` 保持，Existing Target Drift 未绕过。Writer 正向 ROLLBACK/COMMIT 没有在本 Demo 轮运行；TASK005 ON HOLD。**
