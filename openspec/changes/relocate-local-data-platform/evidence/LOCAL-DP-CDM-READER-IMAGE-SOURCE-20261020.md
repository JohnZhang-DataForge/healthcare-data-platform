# Local DP 4.2 / 4.3 — CDM Reader 镜像构建入口兼容与审批边界

> 2026-10-20 EDT；基线 Healthcare Main `bd54a2e9927d12e2214c4538941be9a39c0d4c48`。本轮只更改 `.github/workflows/task004-cdm-pg-read-publish.yml`、OMOP CODE 导航和对应 OpenSpec 证据。本文实施说明不代替最终 PR HEAD 的真实 CI。

## 根因与最小修复

在原本用于历史 feature 分支的 `.github/workflows/task004-cdm-pg-read-publish.yml` 中，Docker build 使用 `context: .`、`file: images/task004-cdm-runtime/Dockerfile`，测试和 Python 编译引用迁移前的 `tests/task004/`、`apps/task004/` 和 `airflow/dags/`；但当前业务源码已移动至 `local-data-platform/`。原 `push` 发布 Job 无独立审批门槛，故不作为 Main 当前有效安全发布入口。

本次将 **这一条**历史兼容的 CDM Reader Workflow 改成两个分离的 Job：

1. PR `validate-source`：Checkout 不变的 PR HEAD；以 `local-data-platform/` 为唯一本地 Docker Context 检查 **7 个 Docker COPY 输入**存在、相应仓库旧根文件不存在、Python AST 可解析、CDM 非 root 和 Entrypoint 声明未漂移。镜像 `FROM python:3.12-slim-bookworm` **不是 Digest Pin，明确记录 `CDM_BASE_IMAGE_DIGEST=NOT_PINNED`**，不能将本地构建 ID 充当上游 OCI 固定 Digest。
2. PR 在 GitHub Runner 上 `docker build --pull --no-cache` 构建本地临时镜像（不接触 Registry Publish），再以 `--network none --read-only`、不调用 CDM 业务 Entrypoint 的方式检查 4 个 `module.__file__` 均来自镜像内 `/opt/task004/`。运行原有 `test_step04f_cdm_runtime_packaging.py`、`test_step04f_cdm_postgres_readonly.py`、`test_step04f_cdm_writer_runtime_rollback.py`、`test_step04f_dynamic_pg_writer.py` 和 `test_step04f_s3_writer_rollback.py` Mock/静态回归。测试可能渲染 `COMMIT` 文本，仅在进程内检查 SQL 字符串，**不连接/提交数据库**。
3. GHCR Publish Job `build-and-push` 只允许 `workflow_dispatch` **且显式 `publish_approved=true`**，且必须先通过 `validate-source`。原 feature Push 自动发布入口删除；保留已使用过的 image repository、`git-<sha>` Tag 语义、SHA256 Digest 输出。此 PR **不触发**任何 Dispatch/Publish。

## 同一镜像的其他历史消费者

另有 `.github/workflows/task004-cdm-rollback-image.yml`、`.github/workflows/task004-s3-writer-rollback-image.yml`、`.github/workflows/task004-step04f-cdm-ghcr-publish.yml` 三条历史限定 feature 分支的旧根 Publish Workflow 同样引用 `images/task004-cdm-runtime/Dockerfile`，**本 PR 不改变或自动触发它们**。这些未审阅的固定历史工作流仍只能视为 **Legacy/HOLD**，不能因为这一个 Reader Gate PASS 就推断 4.2/4.3 全面完成、也不能无证删除/批量替换它们。

Dockerfile、业务 Python/SQL、Airflow DAG ID、已部署容器、历史 Batch/Claim、现有发布镜像 Digest 均不变。只有这个指定 PR HEAD 的 CI Success 才能证明被测试的旧根/COPY/Build/Import/Mock 子门禁；不是 GitHub GHCR 发布、Kubernetes 运行时安装、PG/S3 真实恢复或 E2E。4.2/4.3 **PARTIAL**，4.9/4.10 HOLD，批准删除为 0。

## 待记录真实验收

对最终 PR HEAD 要求至少 `CDM_SOURCE_GATE=PASS`、`CDM_COPY_COUNT=7`、`CDM_CLEAN_BUILD=PASS`、`CDM_IMAGE_IMPORT_GATE=PASS`、`CDM_OFFLINE_REGRESSION=PASS`，专用 GHCR 发布 Job 必须 `SKIPPED`，所有适用 Required Checks SUCCESS。记录实际 Run URL、来源 SHA、本地临时 Image ID 和单测数量；不能凭源码存在先写 PASS。
