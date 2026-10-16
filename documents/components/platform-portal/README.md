---
status: active
scope: platform-portal-component
last_verified: 2026-10-16
source_sha: 241944d0a6e0c222f2e862d4b79c4279bf7fd35b
---

# Platform Portal — OpenLineage + Marquez

> **ACTIVE 是指该组件的知识整理通过核对，并非完整业务血缘已上线。** 基线 Healthcare `241944d0a6e0c222f2e862d4b79c4279bf7fd35b`、Self-Runner `8f8cb877887540cbed697260c3e8154e218a49c7`；2026-10-13/14 的验收证据。本次未重新执行集群/Marquez 的 Live 探针。全局 CURRENT/NEXT 在 [PROJECT-STATUS](../../status/PROJECT-STATUS.md)。

## 1. 职责与结构

Portal 是旁路的**可观测性/数据血缘子系统**：收集 Airflow/Spark 产生的真实 OpenLineage Job / Run / Dataset 元数据并由 Marquez 展示。它不是业务数据处理引擎，不负责产生 Synthea、提交 PostgreSQL OMOP 或执行 Spark 业务加工。

```text
Airflow OpenLineage Provider（A3 Probe 实际事件 PASS）
Spark OpenLineage Listener（A4 独立 Smoke 部分 PASS）
    → Marquez API → 独立 PostgreSQL 14 (metadata)
                  → Marquez 原生 Web
未来 Person/Visit 完整业务数据集血缘（待设计与验证）
```

**当前源码所有权**：[源码入口](../../../platform-portal/README.md)；[`marquez/`](../../../platform-portal/marquez/helm/values.yaml) Helm/Services；[`postgres/`](../../../platform-portal/postgres/README.md) 独立 PG14；[`openlineage/airflow/`](../../../platform-portal/openlineage/airflow/README.md) Airflow Probe/配置；[`openlineage/spark/`](../../../platform-portal/openlineage/spark/README.md) 隔离 Spark 探针/静态测试。

- Marquez 0.51.1 复用 `dw-postgre14` PostgreSQL 14 元数据库，不触碰 `dw-postgre` PostgreSQL 17 OMOP 业务数据。Helm `postgresql.enabled=false`，API/Web ClusterIP。
- 独立 `marquez-web-lan` Web-only NodePort **30999**；Web 本身能代理 API，因此不是匿名只读 Portal。LAN/VPN/NAT/公网访问和备份恢复没有被当前证据证明。
- 当前是**Marquez 原生 Web**，不是自行编写的前端。Superset、OpenMetadata、Kafka 和自定义 UI 不属于已交付范围。
- 新源码仍以 `platform-portal/marquez/`、`openlineage/spark/` 等**组件+能力**命名，遵循 [强制命名规范](../../development/CODE-ORGANIZATION-AND-NAMING.md)；不创建 `taskNNN/stepNNN` 正式代码。

## 2. 可证实的阶段状态

| 阶段 | 实际验收 | 不能夸大的部分 |
| --- | --- | --- |
| Marquez + PG14 + Web | Marquez API/Web Ready、PG14 37 张元数据表、Web NodePort 30999、HTTP health / API proxy 读回 | 不是“当前在线”和完整网络访问/恢复验证 |
| A3 Airflow OpenLineage | opt-in Probe DAG 的真实 Task/Run 事件在 Marquez 中完成独立验收；Provider 2.17.0 | 不等于所有 Airflow 业务 DAG 与 OMOP Dataset 自动产生血缘 |
| A4 Spark 独立 Smoke | SparkApplication 真实 COMPLETED；3 行虚拟 CSV 聚合 PASS；Marquez 出现带 Spark facets 的 COMPLETED Run | 原整个 Workflow **FAILURE**，后续三次只读核验证实局部结果；应用 Job→Run 和 Dataset I/O 未通过 |

**A4 的关键未完成问题**：应用 Job `portal_a4_a438628542127` 的 `latestRun` 为空，真实完成 Run 在 `unknown` Job；`inputDatasetVersions=0`、`outputDatasetVersions=0`。既不能判定 root cause 已查清，也不能把孤立事件视为 Synthea→Spark→OMOP 完整血缘。首轮 Workflow 真实失败需要与后续局部成功**并列保留**。

**实证链接**：[部署和 30999 验证](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/validation.md) / [恢复成功 Run 38499838493](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499838493)；[A3 Airflow 验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/PORTAL-A3-AIRFLOW-OPENLINEAGE-REAL-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) / [只读 Run 38502940358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502940358)；[A4 Spark 验收与限制](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/A4-SPARK-OPENLINEAGE-REAL-SMOKE-2026-10-14.zh-CN.md) / [原失败 Run 38628542127](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38628542127) / [后续只读 Run 38629607225](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38629607225)。

## 3. 下一阶段仍是设计讨论（NOT APPROVED）

用户正在讨论**如何接入真正的业务 Spark**，本次不提前决定技术方案。需要逐项明确：

1. 先基于实际已保存的 OpenLineage Job/Run facets 只读分析 `unknown` 关联及名称规则；根因未定，不直接修改共享 Operator。
2. 确定 Dataset I/O 验证方式；若需要真实 Parquet/S3 输出，应设计**隔离的实验数据和权限**，明确对照验收，不允许手工伪造血缘事件。
3. 讨论对已验收 Person/Visit Spark 应用是 per-job Listener 还是其他非侵入接入方式，评估镜像、JAR、配置、资源与 TASK004 回归风险。
4. 业务 Airflow→Spark→Writer/OMOP 的边界关联在每段真实事件/Commit 被核实后才可展示；Airflow success、Spark Run 和 PG COMMIT 是不同证据。

这些是**待决问题，不是已授权执行的列表**。不触发新 SparkApplication、改业务 DAG、重放 TASK004、重装 Marquez/Spark Operator 或更新共有 Scheduler。

## 4. 维护、安全与迁移说明

任何 Self-Runner Live、ConfigMap/SparkApplication、共享 Airflow/Spark 修改必须先核对其他 Session/Job，按 [人工协作规则](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md) 取得明确的本次授权。Airflow Provider 初始为 opt-in，Scheduler 的独立配置更改与未来 Helm values 持久化还需单独评估。

[旧部署指南](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/deployment-guide.md) 和 [旧运维说明](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/platform-portal/operations.md) 在 STEP07 Runbook 迁移之前仍保留技术参考地位；其中旧“TASK004 尚未完成”的 CURRENT 已由 [最终验收](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md) 取代。
