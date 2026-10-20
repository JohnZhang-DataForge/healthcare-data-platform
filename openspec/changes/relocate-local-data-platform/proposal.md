# Proposal

## Why

本地 Kubernetes 数据平台原先的业务源码散布于 Healthcare 仓库根目录。已经批准的命名试点 `adopt-local-data-platform-naming` 只决定了未来统一使用 `local-data-platform/`，不包含实际搬迁。2026-10-18 用户随后批准将源码独立备份到 Healthcare-Specs，并允许在完成运行调试前将目录迁移合并到 Main。实施时直接使用 GitHub PR，**没有事先建立正式的 OpenSpec Change**。

本 Change 为已经实施的结构变动提供**事后追溯管理入口**，并把剩余运行兼容修复与验收纳入可接续的 Tasks；绝不将此前 PR 描述为经过事前 OpenSpec 评审。

## What Changes

- 记录原始源码固定 SHA、Healthcare-Specs 私有独立备份、393 个业务文件的来源与校验结果。
- 追溯 Main 已完成的三次合并：PR #225 业务源码物理搬迁、PR #226 文档源码链接与 CODE Map 对齐、PR #227 全仓质量工具移入 `.github/quality/`。
- 保持 `documents/systems/data-platform/` 作为文档组件导航；明确 `local-data-platform/` 才是本地业务**源码**根目录。
- 将尚未完成的 Python Import、Airflow/DAG GitSync、Docker COPY/构建上下文、Spark、Actions/Runner 及独立 E2E 的验证作为未完成任务，不声称此前已运行通过。
- 标记 PR #225 当时的组件检查失败与运行切换风险，不隐瞒历史 Gate。
- 修正必要的事实状态入口，使新 Agent 不再误判“业务源码尚未搬迁”。
- **2026-10-18 用户新增批准的后续范围（计划，尚未清理）**：在新路径兼容验收中进行逐文件依赖清点；识别并分批移除已证实不再被当前业务、构建、CI、部署或有效回归测试使用的一次性 Shell、实验 Probe、过期测试/生成器及重复实现。删除不等于已完成；先证明可恢复、无有效间接依赖且测试保护不退化。

### 2026-10-20 最新补充：集中清理，不改变业务语义

在已成功的 NEW_ONLY 真实 E2E 和七批历史安装器退役之上，将余下 26 个 TASK003 **历史审计候选**集中分类，统一由 Runner 双仓 Checkout 完成一次只读依赖/完整生成产物审计，并在候选明确为 C/D 且无活动或独立恢复消费者时，集中由一个后续 PR 删除；A/B/E 保留或 HOLD。**未在本方案 PR 中批准或实施任何删除**。删除前与拟删除版本后分别跑来源与 SHA 明确的全新 Batch E2E/独立 PG-S3 Readback/同 Batch SKIP；若无法证明候选 PR 真实被 Airflow/Spark/镜像运行，停止有风险删除、不得冒充验收。不是所有零引用文件都无用，也不以 Git 文件修改时间作为判断依据。详见 [集中清理决策与验收门](evidence/LOCAL-DP-CONSOLIDATED-CLEANUP-PLAN-20261020.md) 和本 Change Task 4.9.1–4.9.5。优先一次清理并尽快收尾；无足够高置信候选则直接结束清理，保留明确 E/HOLD。不涉及 Fabric、Portal、业务 Writer/Fencing 合同或 OLD_ONLY/MIXED 新增支持。

### 镜像重建优先（2026-10-20）——新增实施目标，尚未执行

用户确认调整：**先让全部 8 个 Local DP 应用镜像从当前 Git 重新构建、发布、在真实新 Batch 上完成 E2E；随后集中清理历史 Shell/测试**，不再用多轮旧文件审计阻断镜像重建。修改代码时移除 Airflow DAG/Kubernetes 业务镜像及 Dockerfile 父镜像中的**历史 Digest 硬编码**；开发环境统一使用项目 GHCR 镜像名和 `:latest`，新 Pod 拉取策略为 `Always`；子镜像采用 `ARG BASE_IMAGE` 注入本轮刚构建的父镜像。继续使用既有 GitHub Actions、Self-Runner、GHCR，不新建复杂发布管理系统。

保留不可变 `:git-<sha>` 发布标签、镜像实际 Digest 与新 Pod `imageID` 作为自动化验收/回滚证据；所有适用检查通过后才更新 `:latest`。8/8 镜像发布并经过新 Synthea → S3 READY → Airflow/Spark → Writer → 独立 PG/S3 Readback → 同 Batch SKIP 验收后，清理无活动或回滚引用的旧**业务镜像**，不提前删唯一恢复版本或无关基础镜像。已记录的随机 Writer `unknown_demographic` 等业务缺陷继续独立追踪，不在本轮改 Mapper/SQL/业务合同。

**本次 PR 只调整本 OpenSpec 的 Proposal/Design/Tasks**；没有实际修改 Dockerfile、DAG、Workflow、镜像、集群或数据，也不声称构建/发布/E2E 已成功。新顺序以 [Design 4C](design.md) 和 [Tasks 4.11](tasks.md) 为准，旧历史清理计划仍保留事实记录但在执行优先级上让位。


## Capabilities

### New Capabilities

无。本 Change 追踪已有源码**位置重构**及其未完成的兼容/验证，不新增可观察业务能力。

### Modified Capabilities

无已批准的业务语义修改。保留 NEW_ONLY Person/Visit、Batch/Manifest/Claim/Fingerprint、Writer/Fencing、DAG ID 等协议与行为不变量。采用 `skip_specs: true`；运行测试不通过或未来行为需要更改时另建相应 Delta Spec/Change，不提前将目标行为写成 Current Specs。

## Impact

- 已改变（历史事实）：仓库 `apps/`、`airflow/`、`spark/`、`images/` 等本地业务根目录移动到 `local-data-platform/`；根目录 `scripts/quality/`、`tests/quality/` 移至 `.github/quality/`，根级这两个目录已退出 Main。
- 已改变（历史事实）：`documents/` 的有效源码链接更新；仓库级 CODE Map 检查器和相关 CI/测试已适配。
- **尚未证明**：生产/实验集群中运行的 DAG、GitSync、镜像及 Spark/PG/S3 全链路已适配新路径。目录内容 Blob 一致、文档链接 CI PASS 不等于运行 E2E PASS。
- 历史追溯建档 PR **只改 OpenSpec/事实性状态文档**；不执行构建、K8s、Airflow、Spark、PG、S3、Azure、Terraform，也不回放已经完成的批次。**当前清理方案 PR 亦仅改本 Active Change 的 Proposal/Design/Tasks，不删除源码或运行测试。** 后续删除必须独立审查和验证。
- 最终 `local-data-platform/` 保留有效业务源码，以及业务构建、测试、Contract、部署和维护必需的工程文件；**不以“只剩业务 Python”为目标**。有效单测/合同/回归测试、可恢复性与安全门禁不能因为文件含 `taskNNN` 就删除。
- 迁移前的独立 393 文件备份只覆盖固定历史 SHA；后续新增/改动文件删除前还需比对当前 Blob、核对 Git 历史的固定 Commit 和按需独立增量备份。业务记录、数据库对象与 GHCR 镜像 Digest 不因 Git 清理而自动可恢复。
- OpenSpec Change Gate、PR 强制绑定、分支保护和合并后状态自动同步属于**下一轮独立治理修复**，不在本 Change 中悄悄启用。
