# Local DP 8 镜像重建、GHCR 发布与新 Batch E2E 验收证据

- 本地决策日：2026-10-20（美东）；GitHub Actions 日志 UTC：2026-10-21。
- OpenSpec 状态时间线：2026-10-20 初始 8 镜像 E2E 的 **4.11.5 HOLD**；2026-10-21 修复镜像最终真实 E2E 后 **4.11.2–4.11.5 DONE，4.11.6 OPEN**。下方原失败试验为修复前历史，不代表最新状态。
- 权威 8 镜像源码发布 Main：`a65a15d304045eb3edd673c086c2d6eacb85cf9e`。后续 Main `20a6449000fe10eac642ab2dbcef37976339572b` 只新增 Fabric 相关提交，二者之间无 `local-data-platform/` 变更；不能以 GitSync 提交 SHA 不相同冒充 DAG 内容漂移。
- 绝不将仅 Build PASS 误称 GHCR Published、PostgreSQL Commit 或真实 E2E PASS。

## 1. 源码与镜像发布

1. [Healthcare PR #339](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/339) 将三份子镜像的旧 `FROM ...@sha256` 改为 `ARG BASE_IMAGE`，4 份 DAG 使用开发 `:latest` + `Always`，并新增统一 5 基础 → 3 子镜像 Build Workflow。最终 PR CI PASS；[8/8 源码 Clean Build #39520399958](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39520399958) 成功，子镜像父层来自本轮构建。
2. 首次 Main 发布 [#39520825324](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39520825324) 构建/Smoke 8/8 PASS；只发布前五个项目镜像，第六个旧包名 `healthcare-synthea-new-only` 遇 `permission_denied: write_package`。无本轮 `:latest` 晋级；此为发布权限问题，不是源码 Clean Build 问题。
3. [Healthcare PR #342](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/342) 将三个子镜像更名为 Healthcare 专属 GHCR Package，保留旧包作历史回退。修复后 Main [发布 Run #39523510402](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39523510402) **SUCCESS**：5/5 基础 + 3/3 子镜像 Clean Build、8/8 Smoke、8/8 `:git-a65a15d304045eb3edd673c086c2d6eacb85cf9e` 发布、8/8 `:latest` 晋级。没有新增复杂发布系统。

### GHCR 已发布镜像与实际 Manifest Digest

所有行对应同一个构建 SHA `a65a15d304045eb3edd673c086c2d6eacb85cf9e`；均有同 SHA 的 `git-` 标签与 `:latest`。以下来自 Main 发布 Run 的真实 Push 输出（不是本地 Docker Image ID）。

| 镜像路径（统一前缀 `ghcr.io/johnzhang-dataforge/`） | Manifest Digest |
| --- | --- |
| `healthcare-data-platform-synthea` | `sha256:45227c376eba53b47ab3469c293b481bbf559c7a20685f1155a4d09b0f663e91` |
| `healthcare-data-platform-task004-runtime` | `sha256:f83af5224f2a17c902ed7ddec7833b25eb0f2a736e71f3b215833d18cb295098` |
| `healthcare-data-platform-task004-cdm-runtime` | `sha256:982400bd862dd89fc860053067689b9d52563e7d552b26dd813fdd0340e0cf04` |
| `healthcare-landing-discovery` | `sha256:95717d484fa41c845eebdf9d80d9fd8b68077c7a7128dd624199a340932bd53b` |
| `healthcare-landing-claim` | `sha256:541ae06763008fa57b1a9b01b3002dd906c9e40da3f75fefae27ac8e90a5d776` |
| `healthcare-data-platform-local-dp-synthea-new-only` | `sha256:6ce7d7320190603dcd103ccd7cb957d85c6f7bb2418e9faaa13b057b07565224` |
| `healthcare-data-platform-local-dp-landing-processing-v2` | `sha256:311849f5187f10b6ca7129aceca68d46d6eb2c0b784536479a5d32b5e5a91924` |
| `healthcare-data-platform-local-dp-omop-writer` | `sha256:f7904a5a5dd86c288bd369c7daddb8cb3d21c315c3e68e80ea2fe43dcd1c864f` |

## 2. 真实新批次验证（全 E2E 尚未 PASS）

[Self-Runner 一次性 E2E PR #171](https://github.com/JohnZhang-DataForge/Self-Runner/pull/171) **已关闭未合并**，以免更多 PR synchronize 意外重跑。所有独立临时 Jobs/诊断证据在 GitHub 历史 Run 中保留，不将临时测试 YAML 合入 Self-Runner Main。

| Run | 全新 Batch | S3 / Airflow / Spark | Writer / 状态 |
| --- | --- | --- | --- |
| [#39524035176](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39524035176) | 未生成 | 旧 `test_digest_runtime` 锁定历史 `FROM @sha256`，被新 `BASE_IMAGE` 设计触发的过时测试阻断；一次性 E2E 测试更新了校验 | 未运行 |
| [#39524177530](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39524177530) | `synthea-new-only-gh-39524177530`：19 Person / 2,961 Encounter | 新 Generator Pod 成功，S3 READY，源 ID 冲突检查 PASS；GitSync 实际 SHA `20a6449...` 与构建 SHA 不同（只有无关 Fabric 变更），旧测试因此 HOLD。后修正为**Scheduler 和 DAG Processor 两角色的 DAG 内容哈希逐文件相同** | 未运行 Writer |
| [#39524542198](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39524542198) | `synthea-new-only-gh-39524542198`：64 Person / 12,446 Encounter | 新镜像 Generator/S3 READY、Discovery、Spark Person/Visit/Reconciliation、Writer Handoff 均 PASS；两角色 GitSync 关键 DAG 内容核对 PASS | `execute_new_only_writer=failed`，完整 E2E FAIL |
| [#39525509725](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39525509725) | `synthea-new-only-gh-39525509725`：49 Person / 6,688 Encounter | 额外一次由同一 PR 中新增诊断文件意外触发；Generator/S3 READY、Discovery、Spark Person/Visit/Reconciliation、Writer Handoff 均 PASS | `execute_new_only_writer=failed`，确切堆栈未另行取得，完整 E2E FAIL |

### 已核实的 Writer Pod 身份与失败原因

[只读 Writer 诊断 Run #39525509790](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39525509790) 对第一个完整业务 Batch 的错误 Pod `task004-new-only-atomic-writer-6odfdbsw` 实际读取：

- Pod 镜像确为 `ghcr.io/johnzhang-dataforge/healthcare-data-platform-local-dp-omop-writer:latest`，**实际 imageID** 为 `sha256:f7904a5a5dd86c288bd369c7daddb8cb3d21c315c3e68e80ea2fe43dcd1c864f`，与本轮 GHCR 发布 Digest 一致。
- Python 调用路径 `new_only_airflow_writer.py → joint_s3_rollback.py → task004_cdm_dynamic_source.py → task004_cdm_dynamic_adapters.py`，在映射 `gender/race/ethnicity` 时明确抛出 `ValueError: BLOCKED=unknown_demographic`。
- 对该 Batch 只读查询 `etl.task004_batch_ledger` 得到 **0 行**，**不是一次完成的 Writer Commit**。诊断程序后续错误引用了不存在的 `etl.task004_person_stage` 表，因此诊断 Job 自身 FAIL；这不影响先前已实际取得的 Pod 日志、imageID 与 Writer Ledger=0 证据。Claim 读取值未可靠输出，不宣称全 PG 状态已完整审计。
- 新 Generator Pod 的 generate/validate/publish/verify/replay 阶段均报告 imageID `sha256:6ce7d7320190603dcd103ccd7cb957d85c6f7bb2418e9faaa13b057b07565224`，与本轮新 GHCR Manifest 一致。其他业务 Pod 的实际 imageID 未全部独立记录；DagBag `:latest`/Always 校验不能替代这一步。

**结论：镜像源码构建闭包与全部 GHCR 发布已通过，新的 Generator、Discovery 和 Spark 流程真实运行成功；Writer 因历史已记录的数据兼容缺陷而 FAIL，无法证明整链路 E2E、同 Batch SKIP 和 PG 零变化。** 随机 `unknown_demographic` 仍应单独立案修复；本镜像迁移不修改 Mapper、SQL 或 Writer 的业务语义，不盲目重放失败 Batch。Task 4.11.5 **HOLD/OPEN**；Task 4.11.6 历史 GHCR 清理 **HOLD/OPEN**，保留旧包和必要回退镜像，不触碰非项目镜像或业务数据。

## 4. 2026-10-21 修复后的真实 E2E 最终验收（取代第 3 节历史阶段的 HOLD；保留原 FAIL 记录）

- **Bugfix 源和发布**：Healthcare [PR #353](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/353) 最终 10/10 CI、Squash Main `b87be7df6d4985a16eb7dd426cae89c841ba9662`；基于该源的 [8/8 Clean Build / GHCR / latest Run #39549155963](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39549155963) SUCCESS。此前的 Digest 及旧映射缺陷不被冒称修复后结果。
- **旧失败 Batch 修复回归**：Self-Runner 临时 [PR #181](https://github.com/JohnZhang-DataForge/Self-Runner/pull/181)、[Run #39588544240](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39588544240) SUCCESS；历史真实 `synthea-new-only-gh-39524542198`，原 Handoff XCom、Person Parquet SHA `203f306d0c99b88caeaaca05ae310c7168e39ea997a716862965fedf4b7eff09`。旧 Writer 仍报 `unknown_demographic`，修复后实际 Pod imageID `sha256:6e35dda789802c1cb3a93df168d5755bdd4c222553809afff6d016fe69e9a15f`，`native → 8657`、Person=64/Visit=12446、`INVALID_DEMOGRAPHIC_ROWS=0`；PG 连接/提交 NONE/NO。只读回归不等于业务 COMMIT。
- **真正全新 E2E**：Self-Runner 临时 [PR #182](https://github.com/JohnZhang-DataForge/Self-Runner/pull/182) 的 [Run #39589050872](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39589050872) **SUCCESS**，原临时 PR 已关闭、未合并到 Runner Main。唯一新 Batch `synthea-new-only-gh-39589050872`；数据 **17 Person / 1816 Encounter**，S3 18/18 CSV READY/独立验证、再次相同请求 REUSE PASS；实际 Synthea Pod imageID `sha256:638d1295c1cac24979257dea90e1ffcbc858ee64e9b4a6b586fd4cde58998252`。
- **真实 GitSync 与 Writer Digest**：Scheduler Pod `dw-airflow-scheduler-65bb45c44-rzlqt`、DAG Processor `dw-airflow-dag-processor-654df59b6b-cgj4l` 的活动源码 SHA 均为 `b87be7df6d4985a16eb7dd426cae89c841ba9662`，4 份关键 DAG SHA256 与 Checkout 同字节；DagBag 和 KPO 的 `:latest` / `Always` 来源合同通过。原子 Writer 的短命成功 Pod `task004-new-only-atomic-writer-n5hmhz5i` 的实际 `imageID` 为新修复 Digest `sha256:6e35dda789802c1cb3a93df168d5755bdd4c222553809afff6d016fe69e9a15f`，`ACTUAL_FIXED_WRITER_IMAGE_ID=PASS`。不把未逐一读回的其它运行 Pod imageID 写成全部核验。
- **真实 DagRun / COMMIT**：`local-dp-fresh-newonly-39589050872` **success**，Spark Person / Encounter / Reconciliation、Handoff、Writer Auth、Atomic Writer、Writer Verified 均 success；`FRESH_NEW_ONLY_SPARK_PERSON_VISIT_RECONCILE_WRITER=PASS`。
- **独立数据库读回**：原始 Person=**377**、Visit=**50492**；COMMIT 后 Person=**394**、Visit=**52308**，准确新增 17 / 1816。Landing Claim=1、COMPLETED=1、Task004 Ledger=1、Batch Stage Person=17、Visit=1816、Verified Checkpoint=2、映射读回 Person=17 / Visit=1816；`FRESH_NEW_ONLY_INDEPENDENT_OMOP_PG_READBACK=PASS`。
- **同 Batch 安全重复**：`local-dp-fresh-skip-39589050872` **success**，Route 进入 `already_completed_no_replay`，Spark/Reconciliation/Handoff/Writer 全部 skipped，二次数据库读回与 COMMIT 后完全一致；`NEW_ONLY_SAME_BATCH_REPEAT_SKIP=PASS`、`NEW_ONLY_REPEAT_ZERO_PG_CHANGE=PASS`、`LOCAL_DP_FRESH_NEW_ONLY_REAL_E2E=PASS`；Airflow 原 DAG Pause 状态 `DAG_PAUSE_RESTORED=PASS`。

**结论：迁移 Task 4.11.5 DONE。** 镜像重建后的真实新数据闭环已由本轮修复镜像证明；历史随机失败仍作为缺陷证据保留，失败 Batch 没有历史业务重放或提交。下一步是 4.9/4.10 的历史文件和测试清理，**Merge Main 后必须再用新的 Batch E2E**；最后才依赖 4.11.6 的引用/恢复清单决定 GHCR 包版本是否可删除。未完成任务仍 OPEN，数据库/PVC、旧镜像和平台资源保持不动。
