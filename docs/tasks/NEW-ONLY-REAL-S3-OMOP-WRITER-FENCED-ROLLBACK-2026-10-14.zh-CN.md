# TASK004 — NEW_ONLY v2 已存在 S3 Person 1 / Visit 812：真正 PG Writer Fencing 联合 ROLLBACK

> **2026-10-14 EDT — SUCCESS / 非业务 COMMIT。** [真实 Self-Runner Run 38554330163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38554330163) 成功完成受限 DB Function **持久安装/再验证**，并把真实 S3 Processing Parquet **Person=1 / Visit=812** 交给单个 PostgreSQL 事务中的 `cdm_writer` 权限执行 Person→Visit、前后两次 Claim 锁与票据校验、**显式 ROLLBACK**。后台没有重跑 Spark、没有更新 S3 READY、没有开启 Airflow 自动 Claim，也**没有发生 OMOP 业务 COMMIT**。TASK004 IN PROGRESS / TASK005 ON HOLD。

## 已经真正完成

1. **数据库持久化安装（纯行政 DDL，非业务 COMMIT）。** 新 `sql/landing_claim/writer_fence_v1_deploy.sql`：在 `omop` 中安装 `NOLOGIN/NOINHERIT task004_writer_fence_owner`、隔离 Schema、`task004_writer_fence.assert_active_claim(text,text,text,text,text,integer)` SECURITY DEFINER。固定 `pg_catalog, pg_temp` search_path，`FOR UPDATE NOWAIT` + `clock_timestamp()`，Owner/Attempt/Manifest/PROCESSING/expiry 严格拒绝；`cdm_writer` 只有受限 Function EXECUTE，无 Ledger 直接 SELECT/UPDATE；Function Owner 没有 CDM INSERT。函数只有在锁归属于 **同一 PG 事务** 的前提下才构成安全保护。DDL 脚本既可首次安装，也能在下次运行时**只检查现有权限**，对不一致/部分安装 Fail Closed。
2. **真正 NEW_ONLY v2 业务数据（不重跑 Spark）。** 读取先前已验收的 Immutable Manifest SHA `dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`，Batch `synthea-new-only-gh-38497355290`，真正 `health-processing` Patient/Encounter 两份已有 Parquet。Writer 计划由原版本化 `synthea-new-only-v1` 合同生成；1 Person / 812 Visit 解码、源键和指纹/Parent 校验及原 Existing Target Drift、Checkpoint、Person FK 均保留。
3. **重要 Claim 边界。** 真 READY Batch **仍然没有被正式 Claimed**。为了在绝不提交业务状态的约束下执行一次真正 Writer SQL，`omop_admin` 在该事务 **BEGIN 后插入暂时合成 Claim fixture**（匹配真实 Batch/SHA/URI、Owner/Attempt）。紧接着 `SET LOCAL ROLE cdm_writer`，以 `current_user=cdm_writer` 有效角色调用实际数据库 Function 拿到行锁，执行完整 Person/Visit SQL，并在最后调用同一个 Function 再检查租约。随后 SQL 强制 **ROLLBACK**，连合成 Claim fixture 一起清除，真正 READY 的 Claim=0。
4. **明确的限制。** `SET LOCAL ROLE cdm_writer` 证明 Writer **有效数据库权限/SQL 事务**，不代表 Writer Pod 已经使用自己的登录凭证独立执行完整 Claim/Writer，也不是一次真正的持久 Claim→COMMIT。此前候选 `apps/omop_writer/fenced_joint_rollback.py` 仍未绑定 Airflow；新一次性 `generate_fenced_s3_rollback_sql.py` 仅为安全验收工具，不能当成生产入库 executor。

## 真实执行和回滚证据

完成 Run：[38554330163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38554330163) SUCCESS（固定 Healthcare candidate SHA `638bf16e5e0390e11d5513d6aa039faa0e366d29`）。

```text
CLAIM_REGRESSIONS=26/26
WRITER_REGRESSIONS=33/33
FENCED_IMMUTABLE_S3_PLAN=PASS
FENCED_PG_BEFORE=PASS
FENCE_FUNCTION_DDL_INSTALL=ALREADY_PRESENT_VERIFY_ONLY
FENCE_DDL_DEPLOY_SAFETY=PASS
FENCE_DDL_PERSISTED=PASS
FENCED_REAL_S3_PERSON=1
FENCED_REAL_S3_VISIT=812
FENCED_REAL_SQL_NO_COMMIT=PASS
REAL_S3_PERSON_VISIT_SQL_GENERATED=PASS
TASK004_REAL_S3_FENCED_JOINT_PG_ROLLBACK=PASS
FENCED_REAL_PERSON_VISIT_ROLLBACK_TABLES_UNCHANGED=PASS
FENCE_INSTALLED_ROLE_ISOLATION=PASS
AIRFLOW_AUTO_CLAIM=NO
SPARK_RERUN=NO
S3_READY_MUTATION=NO
BUSINESS_COMMIT=NO
```

注意 Run 38554330163 的 workflow 主日志只输出最终 SQL marker 摘要；生成的含敏感源数据 SQL 文件放在 Runner 临时目录，独立读回后清理。不可把产生行号序列视作可回滚，`nextval()` 仍可能前进。

| 数据表/状态 | Before | After |
|---|---:|---:|
| `cdm.person` | 136 | 136 |
| `cdm.visit_occurrence` | 9391 | 9391 |
| `etl.person_id_map` | 136 | 136 |
| `etl.visit_occurrence_id_map` | 9391 | 9391 |
| `etl.landing_batch_ledger`（所有行） | 0 | 0 |
| 真实 Batch Claim | 0 | 0 |
| 真实 Batch Writer Ledger/Stage/Commit | 0/0/0 | 0/0/0 |

之前两个未完全成功的 Run：
- [38554101122](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38554101122)：纯 DDL **首次成功持久安装**，但 S3 SQL 生成 Pod 已结束，无法从 Completed Pod `kubectl exec` 提取文件；未运行业务 Writer。独立 PG 行数读回不变。
- [38554234906](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38554234906)：Pod 保持 Running，但 `runpy` 从镜像旧 `/opt/task004` 抢先导入历史 Plan，不识别 `synthea-new-only-*`；未运行业务 Writer。独立 PG 行数读回不变。
- 第三次固定挂载源码优先导入，`38554330163` 真 S3→PG Fenced Writer 完整 ROLLBACK PASS。严格遵守最多三次连续问题修复要求。

## 现在的 Demo 主线与暂缓项

**当前最重要 NEXT：** 设计受控一次真实 READY Claim→Writer 业务 COMMIT→独立 PG Reconciliation→同 Batch 再运行不重复；实际 COMMIT 需要用户另行明确授权，目前 **NO**。随后才串入 Airflow 定时自动 Claim + Writer，完成端到端批次 COMPLETED。实际 Claim 的事务边界应单独持久化后由独立 `cdm_writer` Pod 登录使用已安装 Function，不能把本轮事务内造出的 synthetic fixture 误当成正式 Claim。

**DEFERRED / FUTURE ENHANCEMENT**：两个 Writer 同时竞争、复杂 Lease Recovery / unknown-COMMIT 自动恢复，以及无限量批次队列分页等增强**不作为当前 TASK004 Demo 完成的阻塞条件**。但保持单 Writer、串行执行、合法 Lease、原有 Drift 防护与失败时不允许半批提交。

本轮未修改历史 S3 READY、不重新执行任何 Spark、无 Business COMMIT、不启用 Airflow 自动 Claim、不启动 Portal A4。TASK004 IN PROGRESS / TASK005 ON HOLD。
