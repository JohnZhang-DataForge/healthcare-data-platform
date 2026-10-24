---
status: active
scope: airflow-orchestration
last_verified: 2026-10-16
source_sha: badd7b400212ca7302f9ccd216c074359720d5a9
---

# Airflow — 消费、调度和业务路由

> **组件说明入口**：了解职责与系统关系读本页；要定位、添加、删除或修改实际 DAG / Python 源码，请直接阅读 **[CODE.md：Airflow 源码导航](CODE.md)**，不再通过 `airflow/README.md` 二次跳转。全局 CURRENT/NEXT 见 [Project Status](../../../engineering/status/PROJECT-STATUS.md)。

## 已验证的 GitSync 新目录部署（2026-10-20）

原 Helm `dw-airflow` 的 `dags.gitSync.subPath=airflow/dags` 在 Git 物理迁移后失效，导致旧路径下 DAG 缺失和 DagRun 排队。[Self-Runner 实际修复 Run #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924) 已对原 Release 采用 `--reuse-values --atomic --wait` 的 Helm Upgrade；实际 Scheduler 和 DAG Processor 的 `core.dags_folder` 都验证为 `/opt/airflow/dags/repo/local-data-platform/airflow/dags`。所需最小 Helm 叠加配置由 [开发工具配置 CODE Map](../../../engineering/development/CODE.md) 单一维护，配置文件为 [`helm-gitsync-postmove-values.yaml`](../../../../local-data-platform/config/airflow/helm-gitsync-postmove-values.yaml)。只能配合现有 Release 的 values 使用，不得把该片段作为新的完整 Airflow 安装配置；真实业务 E2E 与其 PG 幂等验收分别记录，不能由 Helm PASS 自动推导。

**职责**：Airflow 根据可信 Batch 身份完成 Discovery、只读 Claim 检查和受控任务路由；通过 KubernetesPodOperator 调度 Spark / Writer，并组织 Person/Visit Reconciliation。Canonical 转换留在 Spark，PostgreSQL 事务由 OMOP Writer 执行，不在 DAG 内重复实现领域逻辑。

**当前已验收范围**：手工 `new_only_omop_consumer`（`schedule=None`、`max_active_runs=1`、14 Tasks）、显式 `spark_processing` / `writer_commit` 与 Secret/Claim Gate；已完成 Batch 被路由到 `already_completed_no_replay`。独立 Discovery 周期性扫描 READY，不代表自动 Claim 或业务 COMMIT。

**未来方向与兼容**：新增 DAG 应按功能命名（如未来 `condition_omop_consumer`）；当前 Legacy `task004_cdm_*.py` 仍与 Image COPY、Import 和 PG/Writer 兼容约束相关，不能为了整理文档而重命名或删除。实际源码清单、测试与相关 Contract 均在 [CODE.md](CODE.md)。

**操作边界**：需要同一批次的 `batch_id`、`manifest_uri`、`manifest_sha256`；不因 DAG Parse/GitSync/Task SUCCESS 就声称数据库提交成功，也不在 Writer 状态不明时盲目 Retry/Clear。详细 Gate 见 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。

**历史验收证据**：[TASK004 NEW_ONLY Person/Visit Final E2E](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。该证据只证明对应日期与 Source SHA 下的流程，不代表其他业务域或当前环境持续在线。
