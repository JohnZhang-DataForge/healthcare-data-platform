# Local DP OpenSpec 4.2 / 4.3 — NEW_ONLY Writer 构建入口单组件兼容性

> **2026-10-20 EDT，独立实施步骤；不更改已验收 Writer 业务源码、批次和父镜像 Digest。** 起点 Healthcare Main `7d30a50c3a91eba542a40a0684d290020730dec4`；以下首次 CI 实证绑定 **实现 HEAD** `021f832b3e2a62c65373fb69b372afe73a7b0c55`，本次回填证据后还须对**最终 PR HEAD** 重新检验适用 CI，不能跨版本宣称 PASS。

## 发现与修复范围

在正式 [Writer Workflow](../../../../.github/workflows/build-new-only-omop-writer.yml) 中发现现行 `workflow_dispatch` 与三个历史 feature-branch `push` 入口仍以仓库旧根 `apps/`、`tests/`、`images/` 为源码和 Docker 构建上下文；迁移后文件仅在 `local-data-platform/`。该旧行为不应被描述为当前可用的 NEW_ONLY Writer 发版验证。

本 PR 仅修改该工作流、OMOP CODE 导航和 OpenSpec 状态/证据：

1. 用新的受限 `pull_request.paths` 替代三条旧 feature Push；源码路径指向 `local-data-platform/`，测试 Runner 固定到 PR HEAD。只有 `validate-source` 在 PR 跑；工作流无自动 GHCR 登录/Push。
2. `validate-source` 基于 `local-data-platform` 读取 Dockerfile `COPY` 的每一个输入，要求都存在且旧仓根同名输入不存在；核对已冻结的上游基础镜像 Digest 保持不变；然后在 GitHub-hosted 临时 Docker 中执行 `--pull --no-cache` 本地 Clean Build（不 Push）。
3. 镜像内通过 `--entrypoint python`、`--network none`、`--read-only` 检查 Writer/计划/PG Renderer 的真正 `module.__file__`，且强制来自 `/opt/task004`，不执行业务 Writer Entrypoint。
4. 通过不联网、只读源码挂载运行 `test_new_only_airflow_writer_runtime.py` 和 `test_new_only_writer_identity.py`（原有 Mock/Fixture 单测；它们不允许访问持久数据库或 S3）。
5. 原 `build` 发版 Job 保持了历史镜像名称、Git SHA Tag、Dockerfile、已有发布后 Mock Smoke 的业务合同，但 **只有** `workflow_dispatch` 且显式 `publish_approved=true`、先前 `validate-source` 成功才允许 GHCR 登录/Push；本轮绝不调用 Dispatch。

## 不变接口与验收边界

- 原 `local-data-platform/images/new-only-omop-writer/Dockerfile` 保留当前 COPY 相对 `local-data-platform/` 布局及 `ENTRYPOINT ["python","/opt/task004/new_only_airflow_writer.py"]`。
- 继续固定上游基础镜像 `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e`，不重建/替换已发布 Parent 镜像。
- 不改 Airflow DAG ID、已经批准的 Batch/Manifest/Claim/PG Writer；不做新的 Kubernetes/KPO/DAG/SparkApplication、PG/S3 写入或已完成批次 Replay。
- 即使本轮 PR 的 Docker Build/Import/Unit PASS，也**仅**建立其确切 PR HEAD 的静态/测试/本地构建证据：GHCR 发布 Digest、在共享 Airflow 上的 Writer 容器环境、真实 PG/S3 事务和综合 4.2–4.4 均 `NOT_VERIFIED`。

## 出口

以本 PR 的最终 HEAD 为准记录真实 CI 中以下子门禁：`WRITER_SOURCE_GATE`、`WRITER_CLEAN_BUILD`、`IMAGE_IMPORT_GATE`、`WRITER_OFFLINE_TESTS` 及 GHCR publish Job 必须 `SKIPPED`。失败即 HOLD，绝不绕过 CI 直接发布/删除历史文件。4.2/4.3 仍 OPEN，4.9/4.10 HOLD，批准删除仍为 0。


## 已执行的真实隔离 CI（实现 HEAD）

- [Healthcare PR #296](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/296)；[NEW_ONLY Writer 专项 Run #39395014874](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39395014874)，Job `NEW_ONLY Writer isolated clean build and regression (no publish)`：**SUCCESS**，工作流输出 `SOURCE_SHA=021f832b3e2a62c65373fb69b372afe73a7b0c55`。
- `WRITER_COPY_SOURCE_COUNT=13`、`WRITER_SOURCE_GATE=PASS`；所有 Docker `COPY` 输入在单一 `local-data-platform/` Platform Context 找到，旧仓根没有同名回退源。
- **本地 Clean Build PASS**：`docker build --pull --no-cache`，临时本地 `LOCAL_IMAGE_ID=sha256:a8dbdf3fbafdfe000f7b3031e0bf5f6248a71c6ccf2afd89c756de13ab09da9b`；这是 GitHub-hosted Runner 的 *本地镜像 ID*，**不是 GHCR 发布 Digest / Kubernetes 生效镜像**。
- 无网络隔离容器 `IMAGE_IMPORT_GATE=PASS`，真实模块 `__file__`：`/opt/task004/new_only_airflow_writer.py`、`/opt/task004/build_s3_rollback_plan.py`、`/opt/task004/task004_cdm_dynamic_pg_writer.py`，3/3 均为镜像路径，业务 Entrypoint 未调用。
- Writer Runtime 7/7、Writer Identity 7/7，总 **14/14** 离线 Unit/Negative 测试 PASS；`WRITER_OFFLINE_TESTS=PASS`。运行容器 `--network none --read-only`、无实际 DAG/Spark/PG/S3 操作。
- 相同 PR Run 中原发布 Job `build` **SKIPPED**，`GHCR_PUBLISH=NOT_PERFORMED`，没有 GHCR 登录/Push。后续手工发布属于另一项需明确审批的动作。
- 单组件 4.2/4.3 的 Build/Import/Unit 子门禁成功，但全部工作流/外部历史消费者和 shared-runtime 并未闭合，**Task 4.2/4.3 不打勾；4.9/4.10 HOLD，删除 0**。
