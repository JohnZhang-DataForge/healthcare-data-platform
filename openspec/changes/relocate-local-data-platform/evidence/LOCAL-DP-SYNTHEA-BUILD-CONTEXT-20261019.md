# Local DP 4.3 — Synthea Image Build Context 修复（尚待验证）

固定基线：Healthcare Main `6c8fa670f0e9266d77070719589f898154f7230f`，OpenSpec `relocate-local-data-platform`，日期 2026-10-19。

## 改动边界

- 修复 `.github/workflows/build-synthea-image.yml` 中五条业务源码 path filter，指向 `local-data-platform/`。
- 更改 docker/build-push-action 的 Context 为 `./local-data-platform`、Dockerfile 为 `./local-data-platform/images/synthea/Dockerfile`。
- 保留 Dockerfile 内相对于 Context 的 `contracts/`、`apps/`、`images/` COPY 源文件路径和容器内部路径、标签、Synthea pinned source commit。
- 同步 `test_synthea_ghcr_workflow.py` 的 Context、Dockerfile 与 Trigger 断言，不删除单元测试和 Contract。
- 原历史 `01-prepare-synthea-generator-image-source.sh` 直接使用宿主路径及源码生成逻辑，绝对不能执行来覆盖 Git canonical source；其下游生成文件一致性需在后续审计验证。

## 尚未通过的 Gates

此次路径修复不证明 Docker Clean Build、GHCR Digest、Entrypoint Smoke、实际来源或动态调用闭包。该 Workflow 在 `main` push 时自动运行并带 `packages: write` 和 `push: true`；**合并此 PR 可能触发 GHCR 真实发布**，因此在发布策略确认前保持 Draft/HOLD，不把 CI 静态 PASS 当作运行验收。Task004 Runtime 构建和其旧生成器仍另需单独处理。4.2–4.4 及 Task 4.9 未完成，业务 Writer、K8s、PG、S3 均不触碰。
