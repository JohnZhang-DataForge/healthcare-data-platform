# Local DP 第三批 STEP06 冻结源码生成器清理（2026-10-20）

> OpenSpec Change: `relocate-local-data-platform` / Task **4.9 PARTIAL**。仅删除固定 2026-10-09/10 历史 Context 使用的一次性 Shell **安装生成器**，不清理运行/恢复/验证/Contract/Unit Tests、不改业务身份/执行路径或任何 K8s/S3/PG 状态。

## Frozen source / recovery

Healthcare Main source base: `689a00732edfbf68fffa1581b96389ba81a3b443`。Self-Runner audited Main: `4561f666d99e4fe1b014acac65332d5215b0c0c8`。这些脚本原始 Blob 已记在 [原 Task003 94/94 Shell 静态盘点](LOCAL-DP-TASK003-SHELL-TRIAGE-20261019.md) 与 [原 393/393 独立源码备份](LOCAL-DP-BACKUP-BLOB-READBACK-20261019.md)，与本轮删除前 Main 的 SHA 一致；Git 历史和 Healthcare-Specs 私有独立备份可用于精确恢复。

| 退役的一次性生成器（`local-data-platform/scripts/task003/`） | 原 SHA | 原文件冻结版本 | 正式产物 |
| --- | --- | --- | ---: |
| `06a5-prepare-readonly-runner-snapshots.sh` | `e04115aae10b5c718512780befd390966e395379` | [immutable Git source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/689a00732edfbf68fffa1581b96389ba81a3b443/local-data-platform/scripts/task003/06a5-prepare-readonly-runner-snapshots.sh) | 3/3 |
| `06b3-prepare-visit-id-pre-mutation-gate.sh` | `22600a22243fa36ae1765ce35a448be39e37e75a` | [immutable Git source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/689a00732edfbf68fffa1581b96389ba81a3b443/local-data-platform/scripts/task003/06b3-prepare-visit-id-pre-mutation-gate.sh) | 7/7 |
| `06b4c-prepare-committed-visit-id-mapping.sh` | `18428bddc4e17b22ef301cc0895605cb8552526d` | [immutable Git source](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/689a00732edfbf68fffa1581b96389ba81a3b443/local-data-platform/scripts/task003/06b4c-prepare-committed-visit-id-mapping.sh) | 5/5 |

## Formal outputs preserved, exact byte comparisons

逐个读取上述三个生成器的 `cat > "$STAGE/..."` 单引号 heredoc 内容，与当前 Main Git `local-data-platform/` 下的相同相对路径正式源文件**全字节内容比对**；结果 **15/15 MATCH**。下列受维护文件未在本 PR 修改或删除：

**`06a5-prepare-readonly-runner-snapshots.sh`（3/3）**：
- `local-data-platform/scripts/task003/06a1-visit-id-allocation-baseline-discovery.sh`
- `local-data-platform/scripts/task003/06a2-plan-visit-id-allocation.sh`
- `local-data-platform/scripts/task003/06a3-reconcile-visit-business-keys.sh`

**`06b3-prepare-visit-id-pre-mutation-gate.sh`（7/7）**：
- `local-data-platform/scripts/task003/06b1-build-visit-id-mutation-contract.sh`
- `local-data-platform/scripts/task003/06b2-freeze-visit-business-key-snapshot.sh`
- `local-data-platform/apps/task003/verify_visit_id_pre_mutation_gate.py`
- `local-data-platform/scripts/task003/06b3-verify-visit-id-pre-mutation-gate.sh`
- `local-data-platform/spark/contracts/processed/visit-id-mutation-contract-v1.json`
- `local-data-platform/spark/contracts/processed/visit-business-key-snapshot-v1.json`
- `local-data-platform/tests/task003/test_visit_id_pre_mutation_gate.py`

**`06b4c-prepare-committed-visit-id-mapping.sh`（5/5）**：
- `local-data-platform/scripts/task003/06b4b-r2-corrected-visit-id-allocation.sh`
- `local-data-platform/apps/task003/verify_committed_visit_id_mapping.py`
- `local-data-platform/scripts/task003/06b4c-verify-committed-visit-id-mapping.sh`
- `local-data-platform/spark/contracts/processed/visit-id-allocation-result-v1.json`
- `local-data-platform/tests/task003/test_committed_visit_id_mapping.py`

STEP06A5、STEP06B3、STEP06B4C 原 Shell 包含固定的旧宿主目录 `/data/spark/healthcare-data-platform`、冻结 Run ID 和旧静态校验要求。运行旧生成器可能尝试在旧 Root 安装源码或再次操作旧环境；本次不执行。

## Caller scope and CI / operational safety

- 从固定 Main 实际逐个读取 **66/66** 高优先级入口（Healthcare GitHub Actions Workflows、DAG、Dockerfile、Task004 Shell、镜像 Shell）、**89/89** 当前 Task003 Shell，以及 Self-Runner 当时 Main 中 **16/16** 关联 OMOP/Visit/Healthcare Workflow；精确扫描这三个待退役文件名：**171/171 未发现直接字面调用**。历史审计和文档/Source CODE Map 引用不当作活动消费者；变量拼接、外部 Runner、冻结镜像、其余 Test 的间接加载未彻底排除，不能冒称整个消费者图完全关闭。
- OMOP `documents/systems/data-platform/omop/CODE.md` 同步删去三条当前活跃源链接，历史 Task003 标题 **30→27**；插入 immutable Git Blob 恢复链接。所有正式验证 Shell、S3 读取、OMOP ID allocation、数据库 rollback/recovery、Contract 和回归测试仍保留。
- 之前新的 NEW_ONLY Synthea→S3→Airflow→Spark→Writer→PostgreSQL E2E 已真实 PASS：[Generator #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)、[Airflow GitSync Helm #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)、[NEW_ONLY/CDM+Idempotent Skip #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433)。这些 Run 没有执行已退役的旧生成器，不把它们视为全历史功能已复验。
- 本批 Git PR 无业务数据修改；合并前以**最终 HEAD** 的 GitHub Actions 进行 OpenSpec Change/Static、CODE Map、Relative Links、source provenance、Airflow DagBag、isolated image/Writer/CDM tests 的实际验收。若存在真实回归则停留在 PR 上修复或从 fixed source 恢复，不绕过 Gate。
- **HOLD**：`06b2-freeze-visit-business-key-snapshot.sh`、`06b4b-r2-corrected-visit-id-allocation.sh` 等具有 S3/K8s 或数据库副作用的**正式运行脚本**以及没有完成活动消费者证明的其他历史模块仍留在树中。
- 此次只是 Task **4.9 局部**完成，4.1/4.8/4.10 和 Archive 不因此打勾。历史 393 Blob 备份数量不能冒充本轮剩余追踪文件数。

