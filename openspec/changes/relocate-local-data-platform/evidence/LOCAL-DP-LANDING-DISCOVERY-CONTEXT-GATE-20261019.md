# Local DP 4.2 / 4.3 — Landing Discovery 新目录镜像来源

> 2026-10-19 · 基线 Main `6a49fa760086867b2961ff9f22bde9e7def3af18`，OpenSpec Change `relocate-local-data-platform`。**本文件为 PR 验证计划，未把未完成 CI 当成 PASS。**

- 只调整 `.github/workflows/build-landing-discovery-image.yml` 现行入口：源码 Trigger Paths 映射到 `local-data-platform/`；Docker Context `./local-data-platform`；Dockerfile 的五项原 Platform Root 相对 COPY 及容器内的绝对运行路径保留。
- 停止原来 Main Push 自动 GHCR 发布。PR 仅执行 `validate-source` 的无发布本地 `docker build --pull --no-cache`、COPY 存在性检查、镜像中模块的 `__file__` Import 检查以及两组以假 S3 为输入的现有 Discovery/Runner 单元测试；`build-and-push` 仅允许显式 `workflow_dispatch`，此轮绝不触发。
- 通过 `docker run --network none --read-only` 和源码只读挂载测试，不执行镜像默认 Entrypoint、Airflow DAG、SparkApplication、历史生成器或访问 K8s/PG/S3。构建可从公网读取固定 Docker/PyPI 依赖，不推送镜像。
- 不改任何业务代码、批次身份、历史导入接口、Chart/Helm、资源状态或 CODE.md 既有职责；本 PR 只涉及 Landing Discovery。Landing Claim 已在 PR #270 完成相应独立 Gate，OMOP Writer 仍未修复。
- 合并前必须检查 PR 最终 HEAD 的独立 Local Clean Build、模块来源和单元测试、OpenSpec/Docs/Component/Trusted CI PASS 与 GHCR 发布 Job `SKIPPED`。记录本地 Image ID（非 GHCR Digest）；未通过不得将 Task 4.3 标为完成。4.9/4.10 继续 HOLD。

## 第一轮真实 PR Gate 证据（最终 HEAD 尚待复核）

- PR [#271](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/271)，源 HEAD `756829341eba01c2493224ef43c74cd9715bc8b3`，Run [#39337678147](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39337678147)。
- `Landing Discovery clean build and read-only offline tests (no publish)` **SUCCESS**，手动 `Publish Landing Discovery image` Job **SKIPPED**。本地 Image ID `sha256:ff02e0898b4980d19d58519785314a317e278b33693632aaf6539afe9e2c26af`，非远程 GHCR Digest。
- `PACKAGED_MODULE` 已确认三项路径：`/opt/healthcare/landing_discovery/run_airflow_scan.py`、`/opt/healthcare/landing_discovery/scan_ready_batches.py`、`/opt/healthcare/task004/resolve_verified_landing_file.py`。
- `test_scan_ready_batches.py` 8/8 PASS，`test_run_airflow_scan.py` 3/3 PASS；共 11/11。测试容器 `--network none` 且不运行默认 Entrypoint。结果标记 `KUBERNETES_PG_S3_ACCESS=NOT_PERFORMED`。
- 该真实 Build 只证明 GitHub-hosted 临时容器在该 HEAD 上的构建/Import/离线合同；不证明当前集群镜像、GitSync/DAG 扫描、Spark 实际 ConfigMap、PG/S3 业务链路或旧脚本可删除。本证据编辑后仍须以最终 PR HEAD 检查全套 CI，4.9 HOLD。
