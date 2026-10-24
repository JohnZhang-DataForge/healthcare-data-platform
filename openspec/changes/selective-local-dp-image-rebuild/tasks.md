# Tasks — Selective Local DP single-image rebuild

> STATUS: ACTIVE / CODE & CI PENDING / NO IMAGE PUBLICATION AUTHORIZED BY THIS CHANGE.

## 1. Design / safety

- [x] 1.1 核对最新 Main、所有 8 个 Dockerfile、父子镜像映射、现有 8 镜像 Workflow 的自动 Main 发布副作用，以及 P2 PR #416 的冲突范围；保留现有镜像名/Writer/Task ID。
- [x] 1.2 定义固定 `image`、`operation`、可选 `parent_digest` 参数与 fail-closed 发布门槛；本 Change 仅批准源码/PR，不授权 GHCR 实际写入。

## 2. Implement and test

- [ ] 2.1 实现单镜像手工 dispatch Workflow 和参数选择器；只构建一个镜像，按需 pin 已存在父镜像 Digest，no-network smoke，发布动作显式区分。
- [ ] 2.2 调整原 8 镜像 Workflow 为 manual-only，阻止变更 Airflow DAG / Main push 自动发布全部 `:latest`；不删除原全量手动能力。
- [ ] 2.3 补充纯离线正向/负向合同测试和组件 CODE 导航；PR CI 全绿、合并 Main 并记录 HEAD 与 Run。

## 3. Manual runtime verification

- [ ] 3.1 获得精确选中 image/operation/parent、当前 Main/并行 GHCR Writer 与消费者的协调授权后，先手动 `validate`，核对只产生目标镜像、无 Registry 更改。
- [ ] 3.2 如果用户独立批准 publish/promote，精确记录 GHCR target package/唯一 tag/digest、其他 7 包无覆盖、受影响运行 Pod imageID 及必要发布后读回；任何步骤结果不明 HOLD。
- [ ] 3.3 更新真实 Run/Artifact/证据，确认 Portal PR #416 Merge 不再触发自动全 8 build/promote；满足范围后再决定 Archive。
