# Local DP 4.3 — GitHub 隔离镜像构建 Gate

日期：2026-10-19。源 Main `8b1572fac479b670e9270690240dac67972df52e`；Change `relocate-local-data-platform`。

本 PR 新增独立 `.github/workflows/local-dp-isolated-image-build.yml`。两个 Matrix Job 分别对 `synthea`、`task004-runtime` 进行 Clean Build（`docker build --pull --no-cache`，仅 Runner 本地 Image），检查 Docker COPY 对应的 canonical 文件存在，容器以 `--network none` 执行 `--help` / `version` 以及文件存在性 Smoke。没有 GHCR 登录、Push、Self-Runner Dispatch、集群、数据库、对象存储动作。Synthea Smoke 不生成患者数据；TASK004 Smoke 不执行 generate-publish/person/visit/reconcile。

此 Workflow 只对当前 PR/显式手动运行，`permissions: contents: read`。Build 可能下载公开依赖与 Synthea 上游源代码；它不是离线验证。只认当前 SHA 两个独立 Job 的实际结果，不能以 workflow 已创建判断 PASS。Image ID 是 Runner 本地标识，不是 GHCR digest；仍需核对 Python module.__file__ / DAG / Spark 的后续来源门禁。三个 TASK003 历史生成器仍 HOLD。
