# Local DP 4.2 / 4.3 — Landing Claim 镜像来源迁移小批次

> 2026-10-19 · 实施起点 Healthcare Main `22c98426e72517b70d59b3396c943ce383b9a62a`，关联 Active OpenSpec Change `relocate-local-data-platform`。本证据只覆盖 Landing Claim 这一组件，不能推广到 Landing Discovery、OMOP Writer、GitSync/Spark 或业务 E2E。

## 修复范围和发布安全

- `.github/workflows/build-landing-claim-image.yml` 的旧根 `apps/`、`tests/`、`images/` 入口改到 `local-data-platform/`；Docker build context 固定 `./local-data-platform`，Dockerfile 内 COPY 源相对于 Platform Root，保持容器绝对运行路径、Claim/Lease/Fencing 行为和镜像名不变。
- 移除旧 `push(main)` 自动 GHCR 发布触发；PR 只执行 `validate-source`，`build-and-push` 严格限定 `workflow_dispatch` 且依赖前置验证通过。本轮**不会手工 dispatch**，不登录 GHCR、不推送镜像。
- PR 的临时 GitHub-hosted Runner 执行 `docker build --pull --no-cache`，收集**本地** Image ID，不是远端 GHCR digest；`docker run --network none --read-only`，挂载源码只读，执行已有三组 Claim/Lease/Fencing 单测，绝不执行默认 Claim Entrypoint 或连接 PG/S3/K8s。
- 不修改 Claim / Writer 业务代码、冻结 Batch 身份、持久数据、历史 Shell、仓库内其他镜像流程或运行系统。

## 验收和 HOLD

本 PR 建立时尚**未**取得 PR HEAD CI 结果。通过标准：Main 最新基线无冲突、OpenSpec / Trusted Change / Component / Docs 检查适用项 PASS，Landing Claim 容器本地 Clean Build 与三组离线单测均 PASS、发布 Job SKIPPED，合并后核对 Main SHA。完成后只将 **Landing Claim 构建兼容**标记为已验证，不将整体 4.2/4.3 标记完成。

需单独开展：Landing Discovery / OMOP Writer 的旧路径发布入口修复；真实 GitSync / Spark ConfigMap 只读来源证明；消费者间接闭包与 4.1/4.8 最终清理 Gate。因此 **4.1、4.2、4.3、4.4、4.8 OPEN；4.9/4.10 HOLD；获准删除 0**。失败遵循同一问题三轮后停止并在 PR 评论记录 HOLD。

## 第一轮实际 PR 验证（本次记录后仍须检查最终 HEAD）

- PR [#270](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/270)，初始 HEAD `7f4329b005bd2b34292ef37183de9a0c2b152a79`。
- [Landing Claim Build Run #39336793115](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39336793115)：`validate-source=SUCCESS`，`Publish Landing Claim image (manual dispatch only)=SKIPPED`；`CLEAN_BUILD=PASS`、`CLAIM_FENCING_OFFLINE_REGRESSION=PASS`、26/26 tests passed。
- 临时 Runner 本地镜像 ID：`sha256:bf6a5b33c45a3d03e8ba47b67fd6628c777d9dba6db0ce5a457fdb0cc87ee479`；**不等于 GHCR 发布 Digest**。无网络容器测试结果为 `KUBERNETES_PG_S3_ACCESS=NOT_PERFORMED`。
- 首轮 OpenSpec Change / Trusted Gate 因 PR Body `OpenSpec-Task: 4.2, 4.3` 格式不合规范失败；已更正为单值 `OpenSpec-Task: 4.3`，随后 Trusted Gate 重新 SUCCESS。此任务状态/证据提交将再次触发适用 PR Checks，以最终 HEAD 的成功结果为合并条件。**不掩盖原始 Gate FAIL**。
