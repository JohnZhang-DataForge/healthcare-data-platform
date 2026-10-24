# Proposal

## Why

现行 `.github/workflows/local-dp-image-rebuild.yml` 在 Main 任意 Airflow DAG 源码变动后会执行 8 镜像 clean build、推送 8 个 GHCR SHA tag 并覆盖 8 个 `:latest`。当前 Platform Portal P2 只修改 `new_only_omop_consumer` 的 OpenLineage opt-in，GitSync 即可读取代码；自动 8 镜像发布既昂贵又增加跨 Session 运行镜像漂移风险。用户要求新增一个可手动传参、仅重构指定单个镜像的 Workflow。

## What Changes

- 新增 `local-dp-image-rebuild-single.yml`：通过 `workflow_dispatch` 的固定 image choice 选取现存 8 镜像之一；`operation=validate|publish|promote-latest` 默认 `validate`，明确区分构建、推送唯一 tag 与更改 `:latest`。
- 父子镜像严格映射；子镜像固定使用父镜像不可变 Digest，可通过合法 `sha256:<64 hex>` 参数指定；默认只读解析现有父镜像 `:latest` 的真实 RepoDigest，绝不隐式连带构建父镜像。
- 复用既有 Dockerfile/业务镜像标识和 smoke；仅在 Main 手动 publish，使用含 SHA/Run/Attempt 的唯一追踪 tag；无自动 K8s/Airflow/S3/PG 部署。
- 旧 8 镜像 Workflow 保留为**显式手动全量构建**，关闭 `push` 和 `pull_request` 自动触发，避免改 DAG 后自动发布全套 `:latest`；原逻辑和镜像名不重构。
- 新增离线参数解析/负向单测、PR 静态 Gate，同步开发工具 CODE，提供准确风险与 Run 证据。

## Capabilities

### New Capabilities

- `local-dp-selective-image-rebuild`：固定白名单、单次一个镜像、父镜像依赖与发布动作可审计。

### Modified Capabilities

- `local-dp-full-image-build-trigger`：全 8 镜像 Workflow 从自动发布变为显式手动请求。

## Impact

只修改 GitHub Actions、源码映射、离线构建选择器及测试；沿用既有 8 个 Dockerfile、镜像包名、legacy task004 标识。不改 Portal DAG PR #416、Writer 事务、RBAC/Secret、部署配置。构建与 GHCR 发布属于后续**独立人工 dispatch**，本 PR CI 不发布任何镜像。
