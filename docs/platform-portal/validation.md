# Portal — 实际验收记录（Live 证据总览）

> **A4 最新真实 Smoke**：[A4 实际 Spark Smoke 与 Marquez Run Closeout](./A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md)：Run 38628542127 整体 **FAILURE**，但实际 SparkApplication `COMPLETED` + CSV 聚合 PASS；后续 [38629218047](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629218047)、[38629414644](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629414644)、[38629607225](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225) 三次**只读 SUCCESS**：Marquez `healthcare-platform-spark-probe` 真实 Job `portal_a4_a438628542127` + `unknown` 下真实 `COMPLETED` Spark Run 及 `processing_engine` facets。ConfigMap / SparkApplication / Pod 均已清除。**不代表 Spark Job 与 Run 的完美挂接或 Dataset Lineage 已完成**。

> **A4 TASK1 旧轮仅 Static（随后 A4 Smoke 已执行，见上方）**：[Spark Agent 静态开发方案](./A4-SPARK-OPENLINEAGE-STATIC-PLAN-2026-10-14.zh-CN.md)。GitHub-hosted Ubuntu 静态测试验证源码/YAML 结构；在该 TASK1 静态阶段**没有 A4 实际 SparkApplication、没有 Marquez Spark Job/Run 证据**，因此 A4 Live 严格为 HOLD，TASK004 COMMIT/Secret 不受影响。

> **并行开发期间的 Live Gate**：另一个 TASK004 Session 正在开发 Spark。Portal A4 的实际 SparkApplication、OpenLineage Agent 集群部署/测试 **HOLD**，直到先问用户是否已暂停/释放共享 Spark/Airflow 运行，再只读检查无未结束 Job/Workflow。**本次仅提交 Portal 文档，不占用 Self-Runner、不运行任何集群任务**。详见 [Session 人工协调规则](./SESSION-COORDINATION-POLICY.zh-CN.md)。

> **A3 最新 PASS**：两次实际 Portal Airflow DagRun，两种 Task Job 各 2 条 Marquez COMPLETED Run。[A3 实际 Airflow→Marquez Closeout](./PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [Run 38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358)。没有启用 TASK004 Claim/Writer，OMOP PostgreSQL17 未修改。

## 2026-10-13 EDT / 2026-10-14 UTC — Marquez 原生 API/Web + Web 30999 LIVE PASS

**验收已完成**。证据分为两次真实 Runner 执行，而非将失败 Run 改写成 SUCCESS：

1. [Marquez Helm + PostgreSQL14 Schema Run 38499534795](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499534795)：完整工作流最后 **FAIL**（原 Python 动态拼 NodePort JSON 语法问题），但日志真实返回 `MARQUEZ_HELM_RENDER_NO_BUNDLED_DB_NO_NODEPORT=PASS`、Release `marquez` `STATUS: deployed`、API/Web `1/1 Ready`、PG14 `MARQUEZ_SCHEMA_TABLE_COUNT=37`、`MARQUEZ_SCHEMA_MIGRATION=PASS`。两个 Service 均为 ClusterIP，未触碰 `dw-postgre`。
2. **[Web-only NodePort 修复与实测 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493)：工作流 SUCCESS**，固定 Healthcare SHA `175a9af8f1e5e2f7864896d96643e5c72f691429`；事前检查现存 Deployment 与 PG14 37 表 `PASS`，Web selector Gate `PASS`，创建 `dw-marquez/marquez-web-lan` Service `nodePort:30999`，EndpointSlice Ready，Web `/healthcheck` PASS、经 Web Proxy GET `/api/v1/namespaces` **HTTP 200**。API Service 仍保持 ClusterIP；`OMOP_POSTGRES17_AND_TASK004_MUTATION=NO`。
3. [Chart + Script 静态核验 Run 38499336014](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499336014)：SUCCESS，官方 Chart 0.51.1 Render 只有两项 ClusterIP API/Web、`postgresql.enabled=false`，没有第三个 DB 或 NodePort。

**真实状态**：Marquez 0.51.1 API + Web（Deployment 1/1），数据库 `dw-postgre14/marquez` 上 37 张元数据表，Web-only Service 30999 已创建，Web HTTP / API Proxy Gate PASS。原有 PG14 Retain PV/PVC 原样保存，未重装数据库。

**不应误报**：Runner 的端口转发与 Kubernetes Endpoints PASS 不等于个人电脑浏览器、局域网路由器/NAT/防火墙配置已测试，`INTERNET_NAT_REACHABILITY=NOT_VERIFIED`。**该 Marquez 部署验收轮次当时**尚未发送 Synthea / Airflow / Spark / Writer 真实事件；随后 **A3 Airflow Provider 已独立验收 PASS**，但 Spark / Writer 未接入；仍未测试 PG14 重启持久化或备份恢复。任何 Source-to-OMOP 成功 lineage 仍不能显示为业务 COMMIT。

旧阶段原下一轮 A3 已经完成。**现阶段 A4 仅允许静态开发；实际 Spark Agent Live 等人工协调后运行**，再考虑 Writer 真正成功的业务证据。LAN/VPN 外部入口访问控制仍须单独核实。

---

## 已确认

- PostgreSQL14 `dw-postgre14`：用户实测 Postgres 14.24，DB/Role 均 `marquez`；50Gi `postgres-marquez` Retain PVC，worker03 原路径 `/data/postgres-marquez/...`；EndpointSlice 服务 5432 已连 Pod。**未进行重新安装**。
- 上轮 [Run 38497309444](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497309444)：确认 PG14 版本、Port 30999 空闲，创建 `dw-marquez` Namespace 与独立 DB Secret。**没有创建 Marquez API/Web**。
- [Run 38497221548](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497221548) 失败：Runner 缺 Helm。
- [Run 38497309444](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497309444) 失败：错误的 Chart index URL 404。
- [Run 38497455412](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497455412) 失败：Bash 文本生成破损，安装没有开始。

## 后续仍未验收

Marquez API/Web、PostgreSQL14 schema、Web-only 30999 和 A3 Airflow Provider 的**真实 Job/Run**已有独立成功证据。**A4 Spark Agent、S3/Parquet 真实 Dataset Lineage、Writer 真 COMMIT 证据、Airflow Helm 配置持久化、外部 LAN/NAT 访问和 PG14 备份恢复**仍未完成；不得把本阶段无业务数据 DAG 的 Run 冒充 Synthea→OMOP 完整血缘。

历史证据：见 [历史归档](./archive/2026-10-13/README.md)。
