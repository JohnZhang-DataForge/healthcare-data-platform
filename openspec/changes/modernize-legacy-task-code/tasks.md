# Tasks — Clean Slate Task/Step Naming Migration

> **2026-10-22 方案切换 / 全新规划**：用户确认旧 Local DP PG/S3 仅为可再生 Synthea 开发业务数据，可以放弃全部历史业务状态；新库/新 DAG/新镜像先独立验证，验收后才退役旧资源。以下任务**替代 2026-10-18 只保留外部契约的渐进 R2–R5 计划**；旧实施从未开始，不能复用其“完成”记号。当前本 Change **只规划、不修改业务代码或运行环境**。

## 1. Specification and decision

- [x] 1.1 基于 Healthcare Main `b99c5e8d4f3e5e4481facde3f7196569645125fb` 和 Self-Runner Main `79464c92cf244508d81c99fc25be9cd90820bad1` 只读审阅现有 Task 命名、迁移/E2E 历史证据、OpenSpec 治理；修订 Proposal / Design / Delta Specs / Tasks，明确 Clean Slate、风险与保留范围。本项仅表示方案**已形成**，不表示审查通过或实施。
- [ ] 1.2 本规划 PR 的最终 HEAD 通过 OpenSpec Strict、Trusted Change Gate、文档链接等适用 CI 并合并 Main；记录 PR/HEAD/Run。**本阶段结束后才开展实施 PR。**

## 2. Exact dependency and rename inventory — implementation pending

- [ ] 2.1 冻结执行时最新双仓 Main SHA；全量扫描 Healthcare Local DP 和 Self-Runner 的文件路径、文本、动态 import/调用、Workflow/dispatch、Docker、DAG/Task/XCom、SQL、K8s/GHCR/Portal 消费者；产出 exact `old→new` 映射和名称冲突/可恢复决议。
- [ ] 2.2 用只读 Live inventory 判定 PG17 当前实际业务 DB/Schema/Table/View/Function/Role/Sequence/Claim/Writer Ledger，S3 Bucket/Prefix、DAG ID/DagRun、K8s 和 GHCR 消费者，标出**受控可重建**与**无权删除/未知**。不能只靠静态 grep 推断资源可删。
- [ ] 2.3 选择并证明 Path A（隔离的新 PG 业务数据库 + 新 S3 Prefix）或 Path B（停旧后排他原地业务 Reset），冻结新的组件、函数、表、镜像、DAG 和 K8s Resource 名称；禁止旧新 Writer 访问同一非隔离 CDM/ETL/Batch。
- [ ] 2.4 审查受影响的 Security/RBAC、SQL 初始化次序、Fencing/幂等/Claim 语义、应用连接参数及 Portal/Lineage 引用，形成可执行但**不自动执行**的清单，声明实际部署/Reset 的授权边界。

## 3. Component-first code / contracts — implementation pending

- [ ] 3.1 在 `local-data-platform/` 现有层级内统一重命名 Task/Step 维护代码、Python/import、Shell、SQL 和 107 测试的适用路径/断言；保持独立业务逻辑/Contract 和负向测试。历史证据、OpenSpec Tasks 与 Airflow 原生 `task_id` 不纳入机械替换。
- [ ] 3.2 修改全部 8 镜像 Dockerfile/Entrypoint/COPY/PYTHONPATH、父子镜像 Build 与 GHCR 新名称；更新 Healthcare 与 Self-Runner 所有当前消费者，保证无遗漏旧运行标识。
- [ ] 3.3 新命名的 Airflow DAG/Python helpers、SQL Schema/bootstrap/GRANT、K8s Job/RBAC/SA、S3/Batch 资源配置接通；旧 DAG 切换前暂停，不允许双自动调度及旧新同时提交相同业务。
- [ ] 3.4 同步对应 Synthea/Landing/Airflow/Spark/OMOP `documents/systems/data-platform/*/CODE.md`、测试和正式导航；对历史文件仅保留 Git 固定版本的证据引用，不保留运行时兼容壳作为完成条件。

## 4. Build / Merge / Fresh-state deployment — implementation pending

- [ ] 4.1 最终实施 PR HEAD 的所有适用 CI PASS：OpenSpec、Naming/CODE、Docs、DagBag、Unit/Contract、Writer Native Race/Multi-Parquet/Fencing/Claim/Discovery exact-selection，以及 8/8 无旧项目镜像层 Clean Build、Import、Entrypoint、父子镜像对应；代码 PR 合并 Main。
- [ ] 4.2 明确运行窗口并核对其它 Session/Run、当前 DagRun/Writer/Pods/DB/S3 所有权；取得具体操作范围的授权；只在已确认的业务对象范围内准备隔离新业务 DB 或执行排他 Reset。
- [ ] 4.3 以新 DDL 从空状态初始化 CDM/ETL/Ledger/Claim/Checkpoint/Sequence/Grants、生成新唯一 S3 Prefix/Manifest，部署新 DAG/K8s 及 8 镜像、捕获实际 GitSync SHA 与 Pod imageID/Digest；原 PG 实例、Airflow、SeaweedFS、K8s 基础设施保留。
- [ ] 4.4 至少 **2** 个独立新 Synthea Batch 全链路实际 COMMIT/PG+S3 独立读回/同 Batch SKIP 和零 PG 变化，覆盖 Writer 失败闭锁与关键边界，并实测新 DAG 定时 Discovery；真实 Run/Manifest/Digest/SHA 在 Task 中登记。

## 5. Retire OLD dev state only after acceptance — implementation pending

- [ ] 5.1 在新系统 E2E PASS 且无旧消费者时，生成精确的旧 PG 业务对象、旧 Airflow DAG 元数据、旧 S3 Prefix、旧 K8s/GHCR 镜像/Workflow 的 **DELETE allowlist**；新对象及基础设施、Marquez/PG14、Airflow Meta DB 整库、Secrets/PVC、Fabric/Azure/Portal 不得误删。
- [ ] 5.2 完成独立受控旧业务资源退役，逐项验证旧入口不存在、当前新入口可运行；新 Batch 数据不得随旧表/旧 S3 清理被连带清除。记录真实删除对象和剩余 HOLD/历史手动消费者。
- [ ] 5.3 完成删除后新业务 Batch、必要调度和隔离/幂等回归，核对无旧 Task/Step runtime 标识进入新发布包，或为特殊保留情况写出明确 Exception。

## 6. Closeout / Archive — implementation pending

- [ ] 6.1 同步项目状态、业务/组件 CODE Map、真正采用的 Current Specs、双仓准确 Main、全部 PR/CI/Runtime/PG/S3 读回及删除后证据；历史失败、旧 Git SHA 与 Run 不覆盖。
- [ ] 6.2 复核 `relocate-local-data-platform` 尚未关闭的独立范围，在真正完成所有适用任务后单独 Archive 本 Change；未实施或未知项不可提前勾选。

**失败边界**：CI/Build 失败不发布新 `:latest`；E2E 失败不删除旧资源；未知 COMMIT 停止同 Batch 重跑；旧系统先暂停、后删除；共享资源占用或归属不明时 HOLD。用户接受“旧合成数据可丢弃”不等于任何未枚举 PG/S3/PVC 都可销毁。
