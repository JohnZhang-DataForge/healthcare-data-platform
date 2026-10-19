# TASK004 Runtime Build Context 修复与发布 HOLD

2026-10-19；OpenSpec Change `relocate-local-data-platform`，Task 4.3。基线 Main `d0447d52d70a593503b6b8e26bd5b14db19a7261`。

- Workflow 从旧根目录源码访问切换到 `local-data-platform/`，Context=`./local-data-platform`、file=`./local-data-platform/images/task004-runtime/Dockerfile`；Dockerfile 里相对 Context 的 COPY 不变，容器内 `PROJECT_ROOT` 维持。
- 旧的 `scripts/task004/06a-prepare-unified-runtime-image.sh` 会生成 Dockerfile、Entrypoint、Workflow 和测试文件，已有路径逻辑与新 Repo Root 不一致。停止在 CI 中执行此源码重建器，改为只读 Shell syntax 与静态 Source Test。**未删除、未执行历史生成器**。
- 原 Workflow 监听 `main` 和 `feature/**` Push，结合 `packages: write` / `push: true` 构成未经请求的 GHCR 发布风险。此轮变更为仅 `workflow_dispatch`，保留人工发布入口但不调用。需要将来单独批准可自动发布的策略。
- 不修改 Writer、PG、K8s、S3、Airflow、Spark 或 Batch 身份。CI 基础静态验证与单测、Clean Build、镜像 Digest、Entrypoint Smoke、真实 DAG 验证等证据须分别以 PR HEAD 记录；本文件不声称任何运行 PASS。
- 4.1、4.2–4.4、4.8 继续 OPEN，Task 4.9 HOLD。Synthea PR #251 仍独立 Draft，不并入此 PR。
