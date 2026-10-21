# Local DP 一次性清理实施及业务验收操作清单（2026-10-21）

> OpenSpec Change: `relocate-local-data-platform` · Tasks **4.9.7–4.9.10**；本文件是**已经批准策略的具体执行清单，不是删除/构建/运行已经完成的证据**。规范事实与历史验收参见 [Tasks](../tasks.md)、[Design](../design.md) 和 [旧集中清理证据](LOCAL-DP-TASK003-CONSOLIDATED-RETIREMENT-20261020.md)。执行前必须以**实际最新 Main** 重取 SHA/消费者，不能机械套用本文冻结基线。

## 目标、范围和成功定义

- **目标**：将当前 `local-data-platform/` 中已确定无用的历史 C/D 文件**一次性删除**；不逐文件开展运行验证，以**最终 PR 静态/构建验收 + 合并 Main 后真实 3 新 + 2 旧 Batch 全链路**验证已覆盖的 NEW_ONLY Person/Visit 业务。
- **方案冻结源（编写时，不代表执行时）**：Healthcare Main `7f046afd4d627c5f5b5995129ebe371d9a9bb4c9`，Self-Runner Main `29094515eeb84f79a89c34061e55becd96e7d9ad`；2026-10-21 清点为 Local DP **363 tracked、90 Shell（TASK003 60）、107 tests**，且历史 PR #332 已删九个一次性安装 Shell，19/19 正式产物与 17/17 HOLD 均保留。此数字随 Main 变更时要重新计算。
- **当前真实业务基线**：[完整入库 02/03 #39653021301](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39653021301) 和 [2 旧 SKIP + 1 新全业务 E2E #39679393354](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39679393354) PASS。后一轮新 Batch 100 Person / 15,326 Visit，PG Person 694→794、Visit 96,133→111,459，最后两者是**对应 Run 的历史读数**，不是下次预期总数。
- **正式成功**：删除 PR 全部适用 CI、8/8 Clean Build PASS、合并后 8/8 镜像 GHCR 发布并固定 Digest；两个旧 COMPLETED Batch 真正 SKIP/零写入；**三个不同的全新随机 Batch** 各自完成 COMMIT、独立 PG/Manifest 读回、同 Batch SKIP 且零变化；恢复原 DAG pause 状态。缺任何一项则 Task 4.9 不能 CLOSED，旧 GHCR 不能退役。
- **不在本轮做**：更改业务 Mapper/SQL/Schema、重命名旧 DAG/Batch/镜像标识、Azure/Fabric/Portal 代码和资源、旧数据重置、删除 PG/PVC/S3、按目录整批删 `tests/`、清理所有节点缓存。

## E0. 前置检查和一份 DELETE allowlist — Task 4.9.7

1. 冻结执行时 **Healthcare Main SHA、Self-Runner Main SHA、当前 open PR 和在途 Actions/共享 Airflow/Spark/Writer 任务**；确保并行 Fabric 工作没有修改本轮业务目录。预检未知/冲突 → HOLD，不占用共享 Writer。
2. **只做一次**：以双仓隔离 checkout 的 `git ls-files -s` / 当前 Tree 为权威，复用 [原 818 文件审计](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39479335467) 与 [PR #332](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/332) 结论，跨所有当前 Workflow、Docker COPY/Context、DAG/动态导入、Spark/K8s、测试、脚本、正式源码生成产物及可能手工恢复用途，完成一次批量增量依赖检查。无需逐个文件运行脚本。
3. 形成一份冻结的 `file-inventory.tsv` / `cleanup-delete-allowlist.txt`（作为 PR 内 evidence 或 CI Artifact，注明全部路径的 Blob SHA、Owner、类别、现行消费者和恢复 Git SHA）。允许删除的每个文件必须是**已可替代/无独立职责/无实际动态及手动安全消费者的 C/D**；当前有效 DAG/运行器、SQL、Tests/Contracts、Manifest/Writer Fencing/人工 Recovery、未知 E **KEEP/HOLD**。无高置信候选则**不强行删除**，转向收尾。
4. 单独标出 Git 历史可恢复的删除文件及它们生成的、必须继续存在的正式输出。确认 **19/19 历史正式产物、17/17 原 HOLD** 的现状；任何新证据变化需先更新决策，不能直接延用“历史保留就是今天仍无引用”的推论。

**E0 Gate**：存在确定的逐路径显式 DELETE allowlist、可恢复 SHA、KEEP/HOLD 及影响组件列表，**无运行写入**。不要求逐文件动态 E2E。

## E1. 一个 PR 完成全部清理 — Task 4.9.8

1. 由**最新 Main** 建一个 `chore/local-dp-cleanup-one-pass-<date>` 分支；只用精确 allowlist 路径删除（例如 `git rm -- <明确的文件>`，**不使用 `rm -rf` / 删除整个 Task 目录**）。一个 PR 删除全部候选，不再拆 2–6 文件 PR。
2. 同一个 PR 更新受影响的 `documents/systems/data-platform/<component>/CODE.md`、必要的 Workflow/导航/负向旧路径断言、不可变 Git 恢复链接、`openspec/changes/relocate-local-data-platform/tasks.md`，提交完整删除清单与前后文件数量。保留源代码和配置的现行行为；遇到有效引用，转 KEEP/HOLD，不为提高删除率引入业务重构。
3. **PR 最终 HEAD 必过**：Documentation Links、Trusted Change Gate、OpenSpec Strict、Component Naming/Source Map、DagBag parse、Spark Manifest Source/Provenance，适用 Synthea/Landing/Writer/PG 单元与合同、已知 Native Race（包括不合法值拒绝）、多 Parquet（包括跨片重复/丢片/空片）、Airflow exact selection/旧 25 预览界限的正负回归。
4. 使用现有 [8-image Workflow](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/main/.github/workflows/local-dp-image-rebuild.yml) 在**最终 PR HEAD** 做 **5 基础 + 3 子镜像** `--pull/--no-cache` Clean Build；子镜像引用**同一次 Run 新建的父镜像**，核验 Docker COPY、容器 `module.__file__`、Entrypoint/Smoke 和本轮 SHA。PR 分支只构建/测试，**不对 GHCR 发布或声称 Live**。若清理路径没有命中 Workflow `pull_request.paths`，须通过同 PR 的 OpenSpec Tasks 改动保证有效触发，或者明确手动 `workflow_dispatch` 做等价检查；不得认为没触发等于 PASS。
5. 所有适用检查在**最终 HEAD** PASS，且 PR diff 只有明确 DELETE allowlist + 必要 CODE/docs/测试适配、无并行 Local DP 冲突 → **Squash Merge Main**，记录 **删除前 Main SHA、PR HEAD、合并后 Main SHA**。不要把 PR 分支 8/8 Build 当成合并后业务 E2E。

**E1 Gate**：CI/Contracts/DagBag/8 镜像 Clean Build PASS，PR Merged；业务 E2E = NOT_RUN。

## E2. Main 镜像发布及部署来源确认 — Task 4.9.9 的前置门

1. 合并后重新取 `main` 的完整 40 位 SHA，确认不包含新的、未经审核的 Local DP 并行提交。**关键触发细节**：`.github/workflows/local-dp-image-rebuild.yml` 的 **Main `push.paths` 不包含单纯的 `scripts/task003/**` 或 OpenSpec 文档**，故不能依赖“删除 PR 合并后自动发布”。确认 Main 最新正确后，在 **Main 上明确 `workflow_dispatch` 该现有 Workflow**。
2. 从该次 Main Run 核实 5 个独立镜像 + 3 个子镜像 **8/8 Clean Build / Smoke / immutable `:git-<main-sha>` GHCR Push / `:latest` 晋级成功**。记录全部 GHCR repository/version/Digest 与三条子镜像实际父镜像关系。现行源码对应的 8 个 Package：`healthcare-data-platform-synthea`、`healthcare-data-platform-task004-runtime`、`healthcare-data-platform-task004-cdm-runtime`、`healthcare-landing-discovery`、`healthcare-landing-claim`、`healthcare-data-platform-local-dp-synthea-new-only`、`healthcare-data-platform-local-dp-landing-processing-v2`、`healthcare-data-platform-local-dp-omop-writer`。
3. 验证 Scheduler **与** DAG Processor 的 GitSync 工作树实际同步到**合并后 Main 的业务源码**（允许 Git 管理提交前沿推进仅无业务差异的变更时记录比较证据），DAG ID `new_only_omop_consumer`、`schedule=None`、Task Graph/关键 DAG 文件 hash 正确；真实 Pod `imageID` 与本轮发布的有效 Generator/Processing/Writer Digest 对齐。仅 GHCR Tag 存在不算 Live 已加载。
4. 操作共享环境前确认当前没有其他活动 DagRun / SparkApplication、未知 Writer transaction/Lease/Claim。保存原 DAG paused 状态并确保故障/成功都恢复；使用原 Workflow 的独占 `concurrency` 与实际集群只读占用检查（GitHub concurrency **不能**防止别的会话直接调用 kubectl）。

**E2 Gate**：合并 Main SHA、已发布 8 个 Digest、真实 Scheduler/DAG/Pod 对应来源与资源独占均可证；未满足则 **HOLD，绝不先跑新业务写入**。

## E3. 业务强验收：2 旧 SKIP + 3 新完整 COMMIT — Task 4.9.9

复用 [已通过的 Self-Runner 临时 PR #208](https://github.com/JohnZhang-DataForge/Self-Runner/pull/208) / [Run #39679393354](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39679393354) 的 Kubeconfig/PG/Writer/Fail-closed 验收逻辑，将其改为**同一个受控串行 Job 的 2 OLD + 3 FRESH**；无需长期新增业务 Workflow。Job 必须固定 Healthcare 合并 Main SHA、已发布镜像 Digest 和运行环境，每个阶段成功才进入下一个；错误停止生成下一批并恢复 DAG pause。

| 顺序 | 输入 | 必须通过的断言 |
| --- | --- | --- |
| T1 — OLD-02 | `synthea-new-only-gh-39630497311-02`（100 Person/15,400 Visit；已 COMPLETED） | Manifest SHA/Claim=COMPLETED，DagRun success 且 `already_completed_no_replay=success`，Spark Person/Visit/Reconcile、Writer 均 `skipped`；PG Person/Visit 总数及本 Batch Ledger/Stage/ID Map/Checkpoint **执行前后完全一致**。 |
| T2 — OLD-03 | `synthea-new-only-gh-39630497311-03`（100 Person/13,237 Visit；已 COMPLETED） | 同 T1，**再次触发只允许 SKIP**，绝不重置 Claim 或重复 COMMIT；PG 零变化。 |
| T3 — FRESH-01 | 新唯一 Request ID/Batch ID | 严格依照下方 FRESH 清单全流程 PASS。 |
| T4 — FRESH-02 | **不同**的 Request/Batch/Manifest | 严格依照下方 FRESH 清单全流程 PASS，前批已结束且无活跃 Writer。 |
| T5 — FRESH-03 | 第三个**不同**的 Request/Batch/Manifest | 严格依照下方 FRESH 清单全流程 PASS，不能复用前两批数据以凑“三次”。 |

**每个 FRESH Batch 全部检查（不因第一次成功而省略）**：

1. **输入**：在 Worker01/当前发布 Generator `imageID` 上生成真实随机 Synthea；独立的 Request、Batch ID、Manifest SHA，输出 **18/18 必需 CSV**，Person/Encounter 行数动态读取且必须大于零；对 S3 历史 Source IDs 与 PG 已有 Source IDs 做冲突检查。
2. **Landing**：首发新的 immutable S3 READY Manifest；校验 18/18 对象/hash/数目，复用相同 Request 再次验证 `REUSE_EXISTING`（不得覆盖），Manifest URI/Hash 保持不变。
3. **Airflow & Spark**：将 exact Batch/Manifest 参数传给 `new_only_omop_consumer`；必须命中该 Batch（不依赖预览 25/100 上限）；Person、Visit、Reconcile Task `success`，运行 SparkApplication 成功、写入分片整体符合合同；记录真实 Generator/Processing/Writer `imageID`，多 Part 若本次出现必须完整读取，不出现时保留多 Part 独立合同测试作为覆盖。
4. **Atomic Writer & Readback**：Writer DagRun `success`，Claim `COMPLETED=1`、Ledger=1、Stage Person/Visit 数量、ID Map、Reconciliation、Checkpoint（历史成功场景为 2）与 Manifest 行数一致；独立 PostgreSQL 会话核对 `cdm.person` 与 `cdm.visit_occurrence` **净增量分别恰等于该批独立 Person/Encounter 数**、Person/Visit FK、来源键无重号；不能仅凭 DAG SUCCESS 推断已经 COMMIT。
5. **第二次同 Batch**：新 DagRun 但**完全相同 Manifest URI/SHA**，必须走 `already_completed_no_replay`；Spark 和 Writer 任务均 `skipped`，独立 PG 前后快照 `diff` **零变化**，Claim attempt/Stage/Map/Checkpoint 不增长。这里的二次 SKIP 是新批自身的幂等回归，与 T1/T2 旧批复测分开计数。

**E3 Gate**：5/5 输入测试全绿，其中新业务 **3/3** 真正 COMMIT + 读回 + SKIP、旧批次 **2/2** SKIP + 零 PG 变化；没有未处理的并发或未知事务。每个测试保留 `RUN_ID, BATCH_ID, MANIFEST_URI/SHA, EXPECTED_PERSON/VISIT, PG_BEFORE/AFTER, CLAIM/LEDGER/STAGE/MAP/CHECKPOINT, POD_IMAGE_ID, FRESH/SKIP_DAGRUN, RESULT`。

## E4. 故障处置与关闭 — Tasks 4.9.10、4.11.6、5.x

- **任何 Stage FAIL、Writer COMMIT UNKNOWN、PG 对账失败**：当前 Batch 标记 HOLD，**立即停止后续 Fresh 写入及 GHCR 退役**；只读核对 Airflow TaskInstance/SparkApplication/Pod/Manifest/Claim/Lease/PG 事务+实际行数。先区分删错依赖、旧业务数据映射缺陷（如历史 Native Race）、分区读取、环境/竞态，再进行明确的最小修复，必要时以保留的删除前 Main SHA 做 Git revert 并重新构建/测试。未知 COMMIT 不允许盲目重跑；Git revert 不会回滚已提交的 PG/S3。
- **随机覆盖局限**：新 3 批可能都不产生 `native`、多 Parquet 或 Discovery 大于 25 的情形。因此对应 Unit/Contract/模拟分区/Discovery 边界测试必须持续 PASS；手工灾难恢复未做专项测试的脚本**不得删除**。本方案不宣称覆盖所有 OMOP 域、UPDATE_ONLY、Condition、灾难恢复或故障注入。
- **全部 PASS 后**：把真实 3+2 Run/Manifest/PG/Digest/回退记录写回 `openspec/changes/relocate-local-data-platform/tasks.md` + 项目状态；对可证明完成的 4.1、4.7、4.8、4.9、4.10 依实际证据逐项更新。随后**单独**执行 4.11.6 旧 GHCR Package/Version 消费者及保留 Digest 核对，不清理基础镜像、节点/缓存/PVC、PG/S3；最后 5.1–5.3 条件全部满足才 Archive。临时 Self-Runner 验收 PR 留永久评论和 Run 证据后关闭不合并。

## 最简执行顺序（每个箭头是一道明确 Gate）

```text
Current Main/Self-Runner SHA + active-runtime guard
  → one-shot inventory / explicit DELETE C/D allowlist + KEEP/HOLD
  → one Healthcare cleanup PR (delete all eligible + CODE.md + OpenSpec)
  → final HEAD CI / contracts / DagBag / 8 clean builds all PASS
  → squash merge Main
  → Main workflow_dispatch for 8-image rebuild + GHCR publish
  → verify published digests / live GitSync / Pod imageID / no competing jobs
  → old Batch02 SKIP and zero DB change
  → old Batch03 SKIP and zero DB change
  → new Batch01 generation → READY → Spark → Writer COMMIT → PG → repeat SKIP
  → new Batch02 generation → READY → Spark → Writer COMMIT → PG → repeat SKIP
  → new Batch03 generation → READY → Spark → Writer COMMIT → PG → repeat SKIP
  → persist evidence / Closeout → obsolete GHCR retirement → Archive
```
