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

## 4. Candidate tag release / digest-bound promotion — portal-v1.0

> 本轮用户确认：先构建并仅发布 `portal-v1.0`，在不改变业务 `:latest` 的情况下测试；只有确认合格以后再将**完全相同 Digest** 的已测试候选晋级为 `:latest`。这是两个不同的操作，不允许构建即晋级或在晋级时重构；本 OpenSpec Change 保持 Active。

- [x] 4.1 再核对 Main 与当前 Portal P2 PR #416 的源码承载方式：Airflow `new_only_omop_consumer.py` 由 GitSync 加载，**不是**上述 8 个镜像之一。因此为镜像增加 `portal-v1.0` 不能隔离验证 OpenLineage DAG 本身；还需独立隔离 GitSync/DAG 或受控运行环境。任何一个镜像的候选发布都不构成 Portal E2E 验收。
- [x] 4.2 扩展原单镜像 Workflow：手动 `image` + `validate/publish`，候选标签 `release_tag=portal-v1.0`（可扩展按组件版本号）；删除一次性 `promote-latest` 构建+晋级路径；仅 `publish` 推唯一 Run tag + 候选标签，不能覆盖 `:latest`。
- [x] 4.3 新增 `local-dp-image-promote-tested.yml`：`verify-candidate`（默认，只读下载固定 Digest 并独立离线 Smoke）与 `promote-tested`（显式验收证据引用，候选 Tag/Digest 一致、无 Docker build 才晋级同一个 Digest 的 `:latest`）。手工 Workflow 的统一并发组与正/反向离线 CI；更新 Developer CODE 与 Delta Spec。
- [ ] 4.4 PR 最终 HEAD CI、合并/Main 读回；注明候选运行和 Registry 发布是否真的发生，不把静态测试标为真实发布。
- [ ] 4.5 核对具体 `image`/PACKAGE 后才进行带有副作用的 `portal-v1.0` GHCR 发布；绑定 exact Main SHA、Run、推送的真实 Digest。事前读取其他活跃 Build/Session，未协调者 HOLD。**禁止**在此步骤触碰 `:latest`、共享 K8s/Airflow/S3/PG。
- [ ] 4.6 以候选 Digest 在隔离环境完成实际业务/Portal 验收，保留可审计验收证据；仅在用户批准的后续独立 `promote-tested` 行为中将同一个 Digest 晋级 `:latest`。晋级之后还需检查业务实际使用的 imageID，不能将 Tag 变化当作 Pod 已自动使用新版本。

**当前风险/待协调**：`portal-v1.0` 只是一份候选镜像 Tag，不代表 Portal DAG GitSync 已隔离；用户未选中具体 8 镜像中的哪一个，因此不会猜测目标 GHCR Package 或推送任意镜像。上述实现变更可以走源代码 PR/CI，实际 publish/promote 分别需精确目标和资源预检。

## 5. Current Local-dev `latest` simplification — supersedes candidate default for Portal

> 2026-10-24 最新决定：Local 开发使用已有 DAG/KPO 的 `:latest`，不为 `portal-v1.0` 来回调整镜像引用；可选候选及 Promote 流程**保留**，但不是当前 Portal P2/P3/P4 的必经路径。上述第 4 节为历史已实现候选能力和原有待验收项，不能当作本轮唯一默认开发路线。

- [x] 5.1 只读确认 Main 与 Portal P2 PR #416、现有 8 镜像依赖、Airflow GitSync + KPO `:latest` 引用和 Always 策略；记录新 Pod 使用新镜像、已运行 Pod 不自动更新的事实。
- [x] 5.2 增加原 single-image Workflow 手工 `publish-latest`：仅该包新镜像 SHA/Run tag，先镜像旧 `:latest` 到 unique rollback tag 并核验旧 Digest，再 Push 新 latest 并 Registry Readback；原 `validate`（默认）、候选 `publish`、可选 promote-tested 保留。非 Main / PR 不发布。
- [x] 5.3 同步 8 镜像边界负向/正向 Policy Test、Developer CODE、OpenSpec 与 Portal Change 设计。
- [ ] 5.4 PR 最终 SHA CI/合并/Main 读回证据；静态/离线测试不等于 GHCR Push 成功。
- [ ] 5.5 仅在后续具体源码要求重建时，核实精确受影响 `image` / parent Digest、活动 GHCR/Session/Pod/Writer 状态，单独授权手动 `publish-latest`；本次变更不触发 Workflow Dispatch，不修改业务正在使用的标签。
