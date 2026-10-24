# Design

## Implementation boundary

- `workflow_dispatch.image` 是静态枚举的 8 个现有镜像组件（5 base + 3 child）；**不接受用户提供的 Dockerfile 路径、package、命令或任意 Shell**。来源和正式 GHCR package 通过测试覆盖的 `local_dp_single_image_plan.py` 固定映射。
- `workflow_dispatch.operation` 固定为 `validate`（默认，仅 Docker build/no-network smoke）、`publish`（仅推送含 Git SHA/Run/Attempt 的不可复用 tag）、`promote-latest`（先推唯一 tag，再明确覆盖选中镜像的 `:latest`）。
- Publish/Promote 仅在 `refs/heads/main` 且用户明确选择时允许；PR 事件只有 offline unit/static job，不执行 Docker build、GHCR login 或任何发布。
- 子镜像父依赖：`synthea-new-only -> healthcare-data-platform-synthea`；`landing-processing-runtime -> healthcare-data-platform-task004-runtime`；`new-only-omop-writer -> healthcare-data-platform-task004-cdm-runtime`。允许仅对这 3 个子镜像输入精确格式的 Digest；若省略，则将当前 parent `:latest` 的 RepoDigest 固定后作为 Docker `BASE_IMAGE` 注入。父镜像更新不自动传播给子镜像，需手动分别构建。
- 8 个现有 Dockerfile、BUILD context `local-data-platform` 与原 GHCR 包名均不变。单镜像构建 `--pull --no-cache` 并使用已绑定的 SOURCE SHA；成功的固定路径无网络 smoke 才允许 publish。Writer 额外做离线 Python import。使用 `docker push` 得到实际 Digest，GitHub Job Summary 记录选中包、SHA、父 Digest、Run ID、运行模式与是否发布。
- 保留旧 full-build Workflow 主体，只让其 `on: workflow_dispatch`；它是显式全量发布途径，不再因 Main push/PR 自动触发。因 PR #416 的 DAG 变更不应引发全 8 :latest 晋级，其 Merge 需等待本变更已合并且明确审查 workflow 触发行为。

## Safety / gate

- 无任何 K8s/Airflow/S3/PG 实时操作；单镜像手动发布或 `:latest` 晋级仍需按 Safe Operations 和 Session Coordination 核对并行镜像发布/运行消费者。
- GHCR token 仅来自 Actions `GITHUB_TOKEN`，不得显示凭据；只有手动构建 Job 拥有 packages write，PR 静态 Job contents read。
- 保留 Parent Digest 记录。新增唯一 tag 名 `git-<40sha>-run<runid>-a<attempt>` 以避免覆盖以前 run；`:latest` 仅在显式 promote 时更新。无法删除/自动清理既存 package；不重启 Pod、不刷新 Airflow 发布环境。
- Failure fail-closed：参数不符、错误 Ref、父 Digest 不存在、Smoke 失败均不推送 `:latest`；如果 `:latest` 更新失败须以 Registry/实际 Pod imageID 只读确认，不盲重试。

## Acceptance

1. PR 静态检查覆盖 8 个正向选择、未知镜像、发布非 Main、非法 Digest、base 不允许父 Digest、子镜像 parent 映射、旧 full-build 无自动触发。
2. GH Actions YAML Parse/Trusted Change Gate、Docs Links 等必需检查成功；PR 不触发镜像构建或 GHCR 写。
3. 仅合并后用户手工分开验证 `validate`、`publish`、`promote-latest`；没有真实 dispatch 之前状态仅 STATIC PASS，不能写入 Runtime PASS。

## Addendum: independently tested candidate before latest promotion

- 单镜像 Workflow 允许 `validate|publish`，默认 Release Tag `portal-v1.0`，只接受保守的 `<component>-v<major>.<minor>[.<patch>]` 格式。构建与 Smoke 后，如明确 `publish`，分别推唯一 Run tag 和候选 Tag，**永不推 `latest`**。存在候选 Tag 时拒绝覆盖（并发构建由 release 并发组协调，但仍需独立 GHCR 读回以识别 registry 竞态）。
- 新 Workflow `local-dp-image-promote-tested.yml` 为单独人工入口；默认 `verify-candidate`，必须传候选 Tag + 已测试 `sha256` Digest，下载候选并匹配 RepoDigest、使用 Digest 做 no-network Smoke，不推 Tag。
- `promote-tested` 需额外提供 Review/Run 证据 URL（记录引用不等于自动证明已通过 E2E），再次执行上述校验，再次核对候选 Tag 未变化，才 `docker pull PACKAGE@sha256` 并对**同一个 Digest** 赋予 `:latest`；全程不运行 `docker build`。最终记录 GHCR Push Digest 并要求与测试 Digest 完全一致，否则标记为需要 Registry 人工取证的失败，不自动重试。
- 两个单镜像 Workflow 与旧手工 8 镜像 Workflow 使用同一 GitHub Actions 并发组 `local-dp-image-ghcr-release` 串行执行；未涵盖其它仓库/手工 Docker CLI 的并行写，因此执行前仍必须遵守 Session Coordination。
- 仅现有 8 镜像允许候选构建/晋级。`new_only_omop_consumer.py` Airflow 实际经 GitSync 读取，`portal-v1.0` 镜像标签不会替换或隔离 DAG，不能把它当作 Portal P2 OpenLineage Runtime/E2E 测试。这个差异必须在门户上线步骤单独验证。
- 默认不执行任何手动 GHCR 发行或业务部署。`publish` 和 `promote-tested` 是不同有副作用操作；当前用户只请求先发布 candidate，未批准晋级 `:latest`。

## Current mode override — Local development latest; staged candidate remains optional (2026-10-24)

此节是最新有效开发决定，覆盖上述候选默认路线，但不删除历史设计与审计记录。

- `operation=validate` 仍默认；`publish-latest` 仅在手工 Main dispatch 允许，和候选 `publish`、独立 `promote-tested` 并存，**不依赖候选 Tag 切换**。符合当前 GitSync/KPO/DAG 引用 `:latest`、`Always` 的开发环境合同。
- 单镜像 `publish-latest` 先按固定 Dockerfile Clean Build 和无网络 smoke，推独一无二 SHA/Run 标签，拉取现有该包 `:latest` 并解析旧 RepoDigest；在覆写前必须以 `pre-latest-run<id>-a<attempt>` 标签发布旧镜像，且核对 Digest 一致。之后只更新选中包 `:latest`，新 Digest 必须与不可变 SHA/Run tag 相同；重新 Pull Registry 验证。上游父 Digest 仍按既有方案锁定，**不**自动更新子/兄弟镜像。
- 如果旧 Digest/回退镜像不可达，或者备份 Push 失败，阻止覆写 `:latest`；如更新后读回不一致，标记失败并人工只读排查 Registry 状态，不自动回滚或盲重试。已有 Pod imageID/业务 DAG 不被此 workflow 修改。
- 仍然只允许 `workflow_dispatch` 做实际 Build/Publish，PR 执行离线 Policy；不部署 Scheduler、不写入 S3/PG/Writer。其它 Repo/手工 Registry 操作不受 Actions concurrency 保护，实机发布前必须核对共享资源。
- Portal P2 的 GitSync DAG opt-in 不封装进上述任何八个镜像；变更 DAG 无需重构镜像，不意味着 GitSync Merge 后无需受控验证。P3/P4 Listener 与 Writer 如修改应用代码，只构建受影响的现有镜像并检验 parent-child 传播。实际 E2E 需要准确 imageID 和 fresh Batch/Marquez/PG 独立 Readback。
