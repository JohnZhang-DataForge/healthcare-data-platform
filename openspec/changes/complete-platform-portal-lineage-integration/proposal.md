# Proposal

## Why

Local Data Platform 的 Synthea NEW_ONLY → SeaweedFS Landing → Airflow → Spark Person/Visit/Reconcile → OMOP PostgreSQL 业务路径已有独立真实 E2E 验收，但 `platform-portal/` 仅完成了 Marquez/PG14/Web 历史部署、Airflow A3 opt-in Probe，以及 Spark A4 部分 Smoke。业务级 Airflow ↔ Spark Job/Run ↔ Dataset 关联尚未成立；A4 历史 `unknown` Job 与零 Dataset I/O 不能标记为通过。

用户于 2026-10-24 选择优先交付 Portal，不等待 `task001`–`task004` / `stepNNN` 旧名称迁移或 Local DP 目录/架构重构。先基于现有稳定、已验收的开发业务运行身份接入可观测能力；未来重命名时应通过独立 Change 处理引用影响。

## What Changes

- 先核对当前 Portal 的 Marquez API/Web、独立 PostgreSQL 14、Service/Endpoint、现有 Airflow Provider 和 Spark Listener 配置；清楚区分仓库静态审查与 Live 只读读回。
- 保留 Marquez 官方 Web，先修复隔离 A4 Spark Job/Run 关联与**真实产生的**输入/输出 Dataset 血缘，保留原始失败记录。
- 对当前 `new_only_omop_consumer` DAG 采取 scoped/opt-in Airflow OpenLineage；对实际由控制容器创建的 Person、Visit、Reconcile SparkApplication 采用 per-job Listener，核对真实运行关联与数据集命名。
- 建立 `source_system + batch_id + manifest_sha256`、Airflow DAG/Run、Spark Job/Run 与 S3 输入输出的可核验关联；必要时通过独立只读 Ledger/PG 读回补充 Writer COMMIT 状态，不把 Spark 成功自动等同于 OMOP COMMIT。
- 以新且唯一的合成 Batch 进行受控真实 E2E / same-batch SKIP，验证原业务 Fencing、Claim、幂等和 OMOP 读回不回归；准确登记 SHA、Digest、DagRun、Spark Run、Marquez API 结果与 PG 证据。
- 完成后利用 Marquez 官方 Web 做内网演示。独立前端、匿名公网访问、认证代理和仪表盘如有需要，另行设计并评审。

## Capabilities

### New Capabilities

- `portal-runtime-health-verification`：基于当前资源的无破坏健康与元数据读回。
- `portal-business-openlineage-integration`：真实业务 DAG、Spark Job/Run 和实际 S3 Dataset 血缘可查询、可验证。
- `portal-batch-commit-observation`：提交状态由可信业务写入结果或独立只读 PG 证据支持，不允许推断成功。

### Modified Capabilities

不改变现有 NEW_ONLY 业务行为。旧 Task/Step 名称、DAG ID、镜像及 Postgres `etl.task004_*` 暂时保持原样；本 Change 仅允许完成可观测性所必需的局部代码/配置修改。

## Impact

可能影响：`platform-portal/marquez/`、`platform-portal/openlineage/{airflow,spark}/`、`local-data-platform/airflow/dags/new_only_omop_consumer.py`、SparkApplication 模板及创建它们的控制包装脚本/镜像、对应组件 CODE/Tests、相关受控 Self-Runner 验证入口。

**Explicit non-goals**：不实施 `modernize-legacy-task-code`、不移动 Local DP 目录、不改 Writer 事务/SQL schema、不清理 GHCR 或 PG/S3 旧数据、不加入 Kafka/Superset/OpenMetadata、不部署自研 React UI，不让 Portal 掌握业务写权限，也不公开 30999/API 到匿名互联网。

本 PR 首先交付 OpenSpec 设计与静态证据；它不修改 K8s/PG/Airflow/S3，也不代表 Portal 今日在线或 E2E 已通过。共享运行操作分别遵循 Safe Operations / Session Coordination、按资源取得明确授权并检查真实空闲状态。
