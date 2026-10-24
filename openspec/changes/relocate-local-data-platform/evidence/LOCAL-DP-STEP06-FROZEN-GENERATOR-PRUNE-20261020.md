# TASK003 STEP06 历史源码生成器退役（2026-10-20）

> Local DP OpenSpec `relocate-local-data-platform`，Task **4.9 PARTIAL**。本记录仅针对两个**固定历史批次的一次性源码安装生成器**；正式源码、测试、恢复入口不删除。文中门禁均绑定本 PR 的 source SHA；实际是否合并由 GitHub CI 决定。

## 1. 范围、Source SHA 和可逆性

- 变更起始 Healthcare Main `7897263d2e165f9b2519094440026dfd99109ac9`、Self-Runner Main `4561f666d99e4fe1b014acac65332d5215b0c0c8`；创建清理分支时无其他 Healthcare Open PR。
- **移除**仅以下两个 `local-data-platform/scripts/task003/` Bash 生成器：

| 一次性历史生成器 | 原始 Git Blob SHA | 固定恢复链接 |
| --- | --- | --- |
| `06a4-prepare-visit-id-readonly-preflight-freeze.sh` | `0918b9888a173f2a6d03cbf8aa108236280cd1aa` | [Source at immutable pre-delete Main](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/7897263d2e165f9b2519094440026dfd99109ac9/local-data-platform/scripts/task003/06a4-prepare-visit-id-readonly-preflight-freeze.sh) |
| `06b4b-r1-prepare-visit-id-allocation-recovery.sh` | `b94c973d5678cedeb6090a88501ec9cb287b5a3c` | [Source at immutable pre-delete Main](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/7897263d2e165f9b2519094440026dfd99109ac9/local-data-platform/scripts/task003/06b4b-r1-prepare-visit-id-allocation-recovery.sh) |

这两个 Git Blob 均曾纳入 [94/94 Task003 Shell 冻结矩阵](LOCAL-DP-TASK003-SHELL-TRIAGE-20261019.md) 和独立 [原 393/393 备份核对](LOCAL-DP-BACKUP-BLOB-READBACK-20261019.md)，后续在主仓 Git 未发生变化；可通过上述固定 Git SHA 或独立 Healthcare-Specs 源码备份恢复。

## 2. 源码产物的独立当前 Git 比较

将两个 Bash 文件中精确的 `cat > "$WORK/..."`、`cat > "$STAGE/..."` 单引号 heredoc body 与**当前 Main**对应 Git 文件的完整 UTF-8 内容对比，**9/9 完全相同**（不是单纯目标文件存在）。

| 原生成器 | 受保护的当前 Git 已存在产物（全部保留） | 比较 |
| --- | --- | --- |
| STEP06A4 | `apps/task003/verify_visit_id_readonly_preflight.py`；`spark/contracts/processed/visit-id-readonly-preflight-v1.json`；`tests/task003/test_visit_id_readonly_preflight.py`；`scripts/task003/06a4-verify-visit-id-readonly-preflight.sh` | 4/4 byte-for-byte |
| STEP06B4B-R1 | `scripts/task003/06b4b-r1-reconcile-failed-visit-id-allocation.sh`；`apps/task003/verify_visit_id_allocation_recovery.py`；`scripts/task003/06b4b-r1-verify-visit-id-allocation-recovery.sh`；`spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json`；`tests/task003/test_visit_id_allocation_recovery.py` | 5/5 byte-for-byte |

另外，生成器还会输出当年 `docs/task003/TASK003-STEP06A-ReadOnly-Preflight.md` 与 `docs/task003/TASK003-STEP06B4B-R1-Allocation-Recovery.md`；这两个**历史文稿目标在当前 tracked Main 中不存在**，不作为当前业务源或测试依赖。原文稿 body 仍可从固定历史生成器读取，不宣称文稿已被保存在 Git 中。

STEP06A4 生成器写入旧宿主根 `/data/spark/healthcare-data-platform`，仅适用于旧的 `5799 Visit / 113 Person` 冻结上下文；STEP06B4B-R1 生成器写入同一旧根，内嵌 2026-10-10 **某次失败的 Visit ID Allocation** 的固定报告/Recovery 路径和预计状态，绝不应当在新的 Batch 上执行生成器来修复当前数据。恢复所需的正式运行脚本和测试**仍保留**。

## 3. 消费者与业务兼容

- 在本轮固定 Main Git 树中实际逐文件读取 **66/66** 高优先级主入口（Healthcare 工作流、Airflow 目录、Dockerfile、Task004 Shell、镜像 Shell），以及当前 Task003 **91/91** Shell；对两个被删除生成器的精确文件名进行静态查找：**157/157 文件无直接匹配**。这只能证明这些重点源码中没有直接字面调用；变量拼装、外部命令、全部 tests 及所有 Self-Runner Workflow **尚不构成完整动态消费者闭包**。
- 前轮任务中已实测新目录全链路 [Synthea READY #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)、[Airflow Helm GitSync #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)、[NEW_ONLY Writer+PG/同 Batch SKIP #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433)。上述实测均没执行 STEP06 冻结生成器，但**不等于证明所有旧恢复功能都测试过**。
- 本批无实际 Job/PG/S3/K8s 写入，也未重新跑过去已提交的业务 Batch。对这些旧生成器本身执行等价回放不安全也不必要；真正当前业务兼容依赖适用 CI 的 Image / DagBag / Writer Gate。
- 修改 OMOP 组件唯一 CODE.md，历史 task003 目录数字 32→30，退役来源链接指向固定 Git `7897263d2e165f9b2519094440026dfd99109ac9`；不移动或删除其 9 个正式产物，不调整活动业务身份。

## 4. 保留、HOLD 与退回原则

- **KEEP**：正式 Person/Visit/Writer、STEP06A4 preflight verifier、STEP06B4B-R1 recovery/verify、9/9 已经独立维护的源码 Contract 与回归测试。
- **HOLD**：真正会发起 Spark Job 的 `06b2-freeze-visit-business-key-snapshot.sh`，以及存在 SQL mutation、编排或外部消费者不明的 Task003 源码；本批不动。
- **Gate**：PR 最终 HEAD 的 OpenSpec、CODE Map、Docs Links、Airflow DagBag/Source、isolated images、CDM reader、Writer 回归应全部成功；否则保留 PR，不合并到 Main。
- 若某旧消费者仍直接使用此已退役生成器，可按上表从固定历史源码恢复，或把外部固定历史调用明确 Pin 在原 Commit；**不建议为了复活旧固定批次而在当前活跃 Main 重装原生成器**。本次不触发旧任务。
- Task 4.1、4.2、4.3、4.4、4.8、4.9、4.10 和 5 仍按 OpenSpec 任务原有状态继续，不因本批清理改成“全部完成”。

## 5. PR #315 元数据门禁修复历史

- 初始 PR 描述误写 `OpenSpec-Task: 4.9 (PARTIAL)`，不是机器要求的严格 `OpenSpec-Task: 4.9`；初始 [OpenSpec Change Gate Run #39452768608](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39452768608) 因 `Invalid OpenSpec task number` FAIL，**不是业务源码回归**。
- PR 描述已修正为独立一行 `OpenSpec-Task: 4.9`；直接 rerun 旧 Run 的失败 Job 仍使用原来的 `GITHUB_EVENT_PATH` 快照，故同样的 Invalid Task FAIL。此文档新提交将产生新的 `pull_request synchronize` Event，以正确 PR Body 与**新的最终 HEAD** 重新执行全套 CI；保留两次失败的诊断证据，不绕过 Gate。其余检查结果以新 HEAD 的最终 CI 为准。
