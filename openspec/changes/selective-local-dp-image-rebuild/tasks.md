# Tasks — Selective Local DP single-image rebuild

> STATUS: ACTIVE / CODE & CI PENDING / NO IMAGE PUBLICATION AUTHORIZED BY THIS CHANGE.

## 1. Design / safety

- [x] 1.1 核对最新 Main、所有 8 个 Dockerfile、父子镜像映射、现有 8 镜像 Workflow 的自动 Main 发布副作用，以及 P2 PR #416 的冲突范围；保留现有镜像名/Writer/Task ID。
- [x] 1.2 定义固定 `image`、`operation`、可选 `parent_digest` 参数与 fail-closed 发布门槛；本 Change 仅批准源码/PR，不授权 GHCR 实际写入。

## 2. Implement and test

- [x] 2.1 实现单镜像手工 dispatch Workflow 和参数选择器；只构建一个镜像，按需 pin 已存在父镜像 Digest，no-network smoke，发布动作显式区分。
- [x] 2.2 调整原 8 镜像 Workflow 为 manual-only，阻止变更 Airflow DAG / Main push 自动发布全部 `:latest`；不删除原全量手动能力。
- [ ] 2.3 补充纯离线正向/负向合同测试和组件 CODE 导航；PR CI 全绿、合并 Main 并记录 HEAD 与 Run。

### 当前代码候选（尚未合并/未执行镜像）

- Healthcare Main Base: `8e075bca130429c261a0f2cf245daef83ba8eebf`；并行 PR：Portal P2 #416、Synthea P2 #418；本轮使用独立分支。
- 单镜像 Workflow 与固定镜像映射、离线正反测试已经提交候选；旧 full-build Workflow 候选改为手动触发。待绑定 PR HEAD 的 CI PASS 和合并 Main 后才算启用。
- 不触碰 DAG、task004、Writer、K8s 或 PG；本 Change 尚未执行 workflow_dispatch，GHCR 发布与 latest 晋级均为 NONE。
- Portal PR #416 需要待本次变更合并后再次确认 Main Push 不再自动启动 8 镜像发布；共享运行状态及并行 PR 仍需独立协调。

### 本 PR 可追溯静态证据

- PR [#419](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/419) 初始代码 HEAD `d51b77376950355fae0b553e744a7383a810f0b5`；静态 [Single Image Policy Run #40096943455](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40096943455) SUCCESS、**8/8** 选择/权限/父依赖/负向测试 PASS；同 Run 的 Manual Build Job 明确 SKIPPED（无 Docker、Registry Mutation）。[OpenSpec Strict #40096943415](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40096943415)、[Trusted #40096943433](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40096943433)、[Change Gate #40096943396](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40096943396)、[Docs Links #40096943423](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40096943423)、[Code Naming #40096943451](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40096943451) 均 SUCCESS。后续文档 Commit 会改变 PR HEAD，需要以最终 HEAD 的 CI 为准，不沿用旧 Run 做最终 HEAD 验收。
- 2.1/2.2 对应静态源码完成；2.3 的最终 HEAD CI、合并 Main/启用状态尚待证实。不将 PR 静态成功等同实际单镜像构建/发布验证。

## 3. Manual runtime verification

- [ ] 3.1 获得精确选中 image/operation/parent、当前 Main/并行 GHCR Writer 与消费者的协调授权后，先手动 `validate`，核对只产生目标镜像、无 Registry 更改。
- [ ] 3.2 如果用户独立批准 publish/promote，精确记录 GHCR target package/唯一 tag/digest、其他 7 包无覆盖、受影响运行 Pod imageID 及必要发布后读回；任何步骤结果不明 HOLD。
- [ ] 3.3 更新真实 Run/Artifact/证据，确认 Portal PR #416 Merge 不再触发自动全 8 build/promote；满足范围后再决定 Archive。
