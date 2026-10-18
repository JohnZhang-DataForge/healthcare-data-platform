---
status: active
scope: platform-portal-system
last_verified: 2026-10-18
source_sha: ad39ed608c699ea3f30b74bd4bc331733d462e99
---

# Platform Portal — OpenLineage + Marquez 可观测性子系统

> **本系统唯一 README 总入口。** Portal 是**旁路数据血缘/运行观测系统**，不是业务 ETL、OMOP 数据库 Writer 或自研前端；实际展示界面是 Marquez 官方 Web。组件代码定位见 [CODE.md](CODE.md)；全项目 CURRENT/NEXT 以 [PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md) 为准。以下运行结论来自 **2026-10-13/14 历史验收**，不是本次部署或当前在线探针。

## 系统结构与数据边界

```text
Airflow OpenLineage Provider → (A3 真实事件通过) ─┐
                                                     ├→ Marquez API → PostgreSQL 14 元数据
Spark OpenLineage Listener → (A4 隔离 Smoke 部分通过)┘                ↓
                                                           Marquez 官方 Web

真实 Person/Visit 业务 DAG → Spark → OMOP 的 Job/Run/Dataset 全链路：尚未验收
```

Marquez 使用 `dw-marquez` 的 API/Web 与独立 `dw-postgre14` PostgreSQL14 元数据库；**不得触碰** `dw-postgre` PostgreSQL17 的 OMOP 数据。初期 Web 通过 `marquez-web-lan` 的 NodePort **30999** 在受控网络内验证；Web 可以代理 API，**并非匿名只读公网服务**。LAN/VPN/NAT/浏览器外部可达性、备份恢复和持续健康均不能仅凭旧验收得出结论。当前没有自建 Portal UI，也没有交付 Superset、OpenMetadata、Kafka。

## 组件总导航

| 组件 | 说明与源码导航 | 真实源码/配置 | 职责及限制 |
| --- | --- | --- | --- |
| **Marquez** | [README](marquez/README.md) · [CODE](marquez/CODE.md) | [`marquez/`](../../../platform-portal/marquez/) | Helm 配置、API/Web、受控恢复、验证；没有独立自研 UI |
| **PostgreSQL14** | [README](postgres/README.md) · [CODE](postgres/CODE.md) | [`postgres/`](../../../platform-portal/postgres/) | 独立 Marquez metadata 持久化；Git YAML 是历史已部署快照，不是重装指令 |
| **Airflow OpenLineage** | [README](airflow/README.md) · [CODE](airflow/CODE.md) | [`openlineage/airflow/`](../../../platform-portal/openlineage/airflow/) · [Probe DAG](../../../local-data-platform/airflow/dags/platform_portal_openlineage_probe.py) | A3 opt-in Provider 真正的 Task/Run 事件验证；不等于业务全 DAG |
| **Spark OpenLineage** | [README](spark/README.md) · [CODE](spark/CODE.md) | [`openlineage/spark/`](../../../platform-portal/openlineage/spark/) | A4 隔离真实 Smoke 有部分完成的证据；完整 Job↔Run / Dataset I/O **未通过** |

## 已验证结果、保留的失败事实

| 领域 | 有界的历史验收 | 不可扩大解释 |
| --- | --- | --- |
| Marquez / PG14 / Web | API/Web Ready、独立 PG14 **37 张元数据表**、NodePort 30999、HTTP health/API proxy 读回 | 不是今天的网络连通性/集群健康证明 |
| A3 Airflow | opt-in Probe DAG、两项 TaskInstance success、真实 Marquez Job/Run 读回；OpenLineage Provider 2.17.0 | 不证明生产所有业务 DAG、Person/Visit Dataset |
| A4 Spark | 隔离 SparkApplication COMPLETED、3 行 CSV 聚合、Marquez 中含 Spark facets 的 COMPLETED Run | 原 Live Workflow **FAILURE**；后续只读核验验证局部成果，完整映射/输入输出 Dataset 仍失败 |

**A4 的已知阻断事实**：应用 Job `portal_a4_a438628542127` 的 `latestRun` 为空，完成 Run 被挂在 `unknown` Job；`inputDatasetVersions=0`、`outputDatasetVersions=0`。不能宣称根因已解决或完整业务血缘成功，更不能将原失败工作流结果改写为成功。

**固定历史证据**：[Marquez 部署、服务及 30999 验证](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) · [恢复 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493) · [A3 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) · [A3 只读 Run 38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358) · [A4 Closeout](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md) · [A4 原失败 Run 38628542127](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) · [A4 后续只读 Run 38629607225](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225)。

## 下一阶段：仅设计讨论，不代表部署授权

真实业务 Spark OpenLineage 接入方式尚未确定。需要先对现有 Job/Run facets 做只读溯源，调查 `unknown` 命名与关联；随后设计有边界的 Dataset I/O 验证，评估对 Person/Visit 实际 Spark、JAR、镜像、Operator 与 Airflow 的影响，保证不回归已验收的 Writer/Claim/Fence。**不要伪造 lineage event、无授权触发 SparkApplication、重跑冻结批次或改共享 Scheduler。**

本次迁移**只移动经核对的知识、整理源码索引**；`platform-portal/` 下运行相关文件未更改。需要触碰 Kubernetes、PostgreSQL、Airflow、Spark、网络或 Secrets 时，先遵循 [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md) 和 [Session Coordination](../../engineering/development/SESSION-COORDINATION.md)，不能从本文件推断执行许可。

**继续阅读**：[系统 CODE](CODE.md) · [Marquez](marquez/README.md) · [Postgres14](postgres/README.md) · [Airflow](airflow/README.md) · [Spark](spark/README.md) · [总体架构](../../architecture/SYSTEM-OVERVIEW.md)。
