# Portal P5 — 全新 Batch E2E 执行登记（2026-10-25；非最终验收）

> 状态：**IN PROGRESS / 未验收**。本页只记录在 GitHub 可独立核对的执行事实与安全边界。不能将 Workflow 步骤 SUCCESS、Airflow Task SUCCESS 或 Spark Application COMPLETED 直接视为 PostgreSQL17 Writer 原子 COMMIT。最终结论须补充原始 Artifact、独立 PG17 Readback、同 Batch SKIP 和 Marquez GET，随后另行审查 OpenSpec 勾选。

## 源代码、控制入口和协调范围

- Healthcare 固定源 SHA：`95f480078da622178f4fa7b68d986d8e05a91ae9`。当前变更只补充审计文档；**不**改 Person/Visit/Reconcile、Spark Listener、OpenLineage 版本、镜像、Airflow DAG 或 Writer。
- Self-Runner Workflow 的固定 helper SHA：`401f4ad379f48412d3028d596ecbcdb549ccc8f7`。工作分支 `feature/portal-p5-fresh-batch-e2e-20261025`，执行源 HEAD `d255fd0f8504a696aaca47a10ba39f81001a5572`；审核入口 [Self-Runner PR #292](https://github.com/JohnZhang-DataForge/Self-Runner/pull/292)。
- 真实 Run：[Self-Runner #40208104106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106)，`push` 触发、`run_attempt=1`，Workflow `Portal P5 Fresh Batch Full E2E and Design A Lineage`。运行期实际约束由自身的 `concurrency: local-dp-shared-new-only-e2e-exclusive`、Run 前 Kubernetes/Airflow/PG17/S3 Read-only Gate、明文限定运行参数和 Fencing/Claim 规则共同约束；**这不是跨所有 Session/CLI 的全局原子资源锁**。
- 此批次的预期唯一身份：`synthea-new-only-gh-40208104106`（来自 Workflow 源码中的 `GITHUB_RUN_ID`），非历史 P4 Spark-only Batch；S3 Manifest URI/SHA256 等真实值必须从本 Run 的 Artifact 和只读读回取证，不从名称推导。

## 实际失败保留：前一尝试

- 原始 [Run #40207853132](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40207853132) **FAILURE**，不能改写为 PASS。[PR #292](https://github.com/JohnZhang-DataForge/Self-Runner/pull/292) 记录：Generator Pod 使用了当前受批准 Digest `sha256:31b65605df694f6d3743822bec7a6236a9fcd6ce946bd0bfa7f904bd53fe4da6`，但生成后第二条过期历史 Digest 断言错误地拒绝了它。修复仅去掉该过期断言，保留真实 imageID 与当前固定 Digest 的一致性检查。
- 该原始 Run 的候选 `synthea-new-only-gh-40207853132` 仅在 PVC 内留下生成产物，**未做** prepublish/publish、S3 READY 或 Consumer/Writer Trigger；原 DAG paused 状态恢复，临时 Job/Secret 清理。这些是 PR 中记录的现场调查，不应夸大为本轮重新完成的独立 PG/S3 审计。
- 后续新 Run 在自己的只读 Preflight 检查失败候选的 Claim/Ledger 为零，不重放、覆盖或删除该候选。另见原独立只读 [Preflight #40207289577](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40207289577)。

## 正在执行的第二次真实独立 Batch（已观察到的 GitHub 步骤结果）

截至本次初始 GitHub Jobs GET，Run #40208104106 的以下步骤已经标记 **SUCCESS**：

1. Healthcare/Self-Runner exact SHA、Synthea 与 Writer/Airflow/OpenLineage 的源代码单元/契约检查。
2. Kubeconfig 配置和**本 Run 内**即时只读 Preflight；K8s Namespace、Airflow 活动运行、PG17 Claims、镜像/GitSync Gate 均由脚本 fail-closed 守护。
3. Airflow scheduler + dag-processor 双角色 GitSync 内容与 Writer Secret/DAG 解析检查。
4. 暂停 Consumer 并核对无冲突 DagRun。
5. 用新 Request 生成独立 100 人目标 Batch；历史 S3/PG 身份碰撞预检与 READY 发布。
6. Fresh READY Manifest 与输入行数的独立检查；准备业务执行时的无 Secret 观测与校验步骤。

随后 `Real Airflow Spark atomic Writer COMMIT, independent PG17, same-batch SKIP` **in_progress**；`Independent Marquez GET, exact DatasetVersion ParentRun and Writer evidence correlation`、最终 PG17 Readback、DAG pause restore、Artifact 保存 **pending**。**当前没有足够证据判定最终 PG17 COMMIT、SKIP 或 P5 Lineage PASS**。GitHub 在 Run 未结束时不能提供完整 Job Logs/Artifact 的情况不应解释为错误或成功。

## 第二次 Run 最终结论（2026-10-25T15:50Z 后独立核验）

- 原 [Run #40208104106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106) 的 **Workflow 总结果 = FAILURE**。不能重标 SUCCESS。其原始 [Artifact #12605147240](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208104106/artifacts/12605147240) 包含 `pg-before.txt`、`pg-after.txt`、`pg-final-always.txt`、`airflow-commit.json`、`writer-handoff.json`、`images.jsonl` 与 Synthea READY 证据，允许独立交叉复核。
- 实际失败点：Writer Step 完成 Airflow/PG17 后调用 `verify_runtime.py`，在读取 `spark-apps.jsonl` 时抛出 `FileNotFoundError`。原 `capture.py` 有生成此文件的代码，但运行时**未产生可读文件**；Artifact 中只有 `images.jsonl`，不能推断 Spark App 未运行。该缺口发生在同 Batch SKIP 触发之前，后续 Marquez GET 步骤因此 SKIPPED；并非 Writer COMMIT 失败。
- 独立 PG17 读回：`PERSON_TOTAL:1294 → 1394`，`VISIT_TOTAL:184814 → 200556`；`BATCH_CLAIM=1`、`BATCH_COMPLETED=1`、`BATCH_LEDGER=1`、`BATCH_STAGE_PERSON=100`、`BATCH_STAGE_VISIT=15742`、`BATCH_CHECKPOINT=2`（Person、Visit 各 1）、`BATCH_PERSON_MAPPED=100`、`BATCH_VISIT_MAPPED=15742`、`VISIT_ORPHANS=0`、`ACTIVE_CLAIMS=0`。`pg-after.txt` 与失败后**独立再次只读**的 `pg-final-always.txt` 数字及 8 组内容/Map/Ledger/Stage/Checkpoint MD5 指纹一致。
- `airflow-commit.json` 显示 `portal-p5-commit-40208104106` 的 DAG 与所有 Person/Visit/Reconcile/Writer 任务 SUCCESS；日志明文标记 `TASK004_NEW_ONLY_WRITER_RESULT=COMPLETED`、`PG_RECONCILIATION=PASS`、`NO_SECOND_COMMIT=PASS`。Writer 已经将 **100 Person + 15,742 Visit** 实际持久化，**绝不可对这一 Batch 重新启动 COMMIT 或整条 Fresh E2E Workflow**。
- Manifest 真值：`s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-25/batch_id=synthea-new-only-gh-40208104106/manifest.json`，SHA256 `cad0a79c1f536e5d3fed0e732c2b2da4cc7af48c89355c6fa95f0b380042130e`。真实 V2 Pod Image Digest 为 `sha256:42d6d087de4dfecf35c51bf84461fddea9635506ed73b6a59f7de8c44d8e775d`（至少 Person/Visit，见 Run 的 Image Evidence）。
- 异常退出后 `Restore original DAG pause state` SUCCESS：`P5_FINAL_DAG_PAUSED=True`、`P5_FINAL_ACTIVE_CONSUMER_RUNS=0`；最终 PG Readback / 证据上传 / Kubeconfig 清理步骤均 SUCCESS。不构成全局 Pod 已全部释放的推断。
- 补证入口：[Self-Runner GET-only #40209504539](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40209504539)，专门针对**已提交** Batch，使用精确源 SHA/已知 ParentRun UUID/PG17 Readback，仅 GET Marquez + Airflow 只读查询，**无** `airflow dags trigger`、Spark/Writer/S3 写入；该入口的结果与同 Batch SKIP 仍分别需要真实验收。原 P5 Run 的总体 FAILURE 不因补证而删除或覆盖。

## 尚须满足的独立验收矩阵

| Gate | 现场要求 | 本登记状态 |
| --- | --- | --- |
| P5 6.1 安全/版本/运行独占 | 运行窗口所有门禁及最终资源归属可复核 | Preflight Step SUCCESS；最终资源释放未核验 |
| P5 6.2 COMMIT | 唯一 Batch READY、3 个 Spark Application、Writer Transaction、PG17 Person/Visit 新增行数、Ledger/Checkpoint、FK/Map 独立 Readback | **OPEN** |
| P5 6.3 SKIP | 同一 Manifest 的第二个 DagRun 跳过 Spark/Writer；提交前后 PG17 表/ID Map/Ledger/Checkpoint 指纹零变化 | **OPEN** |
| P5 6.4 Marquez | GET 的真实 Airflow ParentRun UUID、Spark App→Action、数据输入输出 DatasetVersion 与 Writer Run、独立 PG17 提交事实同批对应 | **OPEN** |
| P4 5.4 Writer 可信状态关联 | 不仅依赖 Spark COMPLETE；对齐真实 Airflow Writer、PG17 durable state、Batch/Manifest SHA | **OPEN** |

设计 A 的 P4 物理 RDD Action START-only/RUNNING 已知观测缺口保持独立披露；不伪造 COMPLETE，不用 `business_edges_gate` 代替 PG17 状态，不将原 `business_dataset_gate=INCOMPLETE` 改成 PASS。OpenLineage 1.47.1/1.54.0 已知行为参见 [ADR](../../../../documents/architecture/design/OPENLINEAGE-SPARK-RDD-ACTION-LIFECYCLE-DECISION.md)。

## 接管、安全退出和下一步

- 旧会话中断 **不表示** Run/Pod/PG 已空闲。此文档记录时 Run #40208104106 仍在进行，**不再触发第二个 Batch/Workflow、不手动 Replay、不取消它**；本审计文件不做任何共享 Runtime 操作。
- 等 Run 取得最终 `conclusion` 和已保存 Artifact 后：逐项查 `pg-before/after/skip`、`writer-pg17-gate.json`、`marquez-report.json`、`p5-acceptance.json`、Airflow/Spark 应用和最终清理；核对精确 Manifest SHA 与源 SHA。发生 FAILURE 或 UNKNOWN COMMIT 时先核验 PG17 Claim/Ledger/Checkpoint，**不要盲目重试**。
- 仅在各项真实验收通过后，才于专门 PR 勾选 5.4/6.1–6.4 并同步 Current 文档。失败 Run 保留原始结论与证据。
