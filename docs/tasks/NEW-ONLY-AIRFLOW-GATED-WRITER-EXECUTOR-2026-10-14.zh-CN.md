# TASK004 — Airflow NEW_ONLY Writer Executor 已接线（双闸门，未启用第三批业务提交）

> **2026-10-14 EDT。** 已将上轮成功的 NEW_ONLY `S3 READY→Airflow Discovery→Spark Person/Visit→immutable Handoff` DAG，接上**真实容器化原子 PostgreSQL Writer** KPO 及完成回读。该代码目前经过 CI 和真实 worker02 镜像启动验证，但尚未进行**第三个全新 S3 READY 批次**的 Airflow 自动 COMMIT 验收。不能将此阶段称作 TASK004 完全 CLOSED。前两个已提交批次 **Person 207 / Visit 21690 / Claim 2（两个 COMPLETED）** 保持不变，绝不可再次执行业务 COMMIT。

## 本轮新增能力与不可变镜像

- Airflow DAG `airflow/dags/new_only_omop_consumer.py` 中新增 `route_writer_authorization` Branch → `execute_new_only_writer` KubernetesPodOperator → `writer_committed_verified`。
- 仍旧 `schedule=None`、`is_paused_upon_creation=True`、`max_active_runs=1`、`retries=0`，原 Spark 只读/manual/完成批次跳过逻辑保留。
- 手工 DagRun `conf` 仅接受 base 4 个确切身份字段、可选 `spark_processing:true` 或**双启用** `spark_processing:true, writer_commit:true`；任何未知字段、Boolean 混淆或 schedule/backfill 都 fail-closed。
- 经过真实 Spark XCom 的 `NEW_ONLY_WRITER_HANDOFF_VERIFIED_NOT_AUTHORIZED` 严格 Plan/Manifest/URI SHA 校验后，分支才可以到 Writer；默认旧模式仍是 `writer_awaits_live_preflight`，而两个已经提交的 batch 永远不允许重新走 Writer。
- Writer 镜像 `ghcr.io/johnzhang-dataforge/healthcare-data-platform-new-only-omop-writer@sha256:dd0b0483ec01b05f1d072d65c9ab728b563cb063da0705564f3a03e23160fd6c`。由 `images/new-only-omop-writer/Dockerfile` 在已验证的 CDM runtime 上打包当前原子 Writer、真正 S3 Reader/PG 只读审计、Claim/Fencing SQL Renderer、Airflow Handoff 代码；全程 digest pin，不使用 `latest`。
- `apps/omop_writer/new_only_airflow_writer.py`：**先用 cdm_reader 真实只读查询 durable Claim/Stage/Checkpoint/source ID Maps**，COMPLETED 严格对账后 Skip；ABSENT 才重新 S3 GET Person/Visit、检查 fingerprints/父子关系和 source ID collisions，再进入完整单一 PG 事务：`omop_admin` 会话中 `SET LOCAL ROLE landing_claim_worker/cdm_writer`、3 次 Fencing、Person/Visit、row-by-row DB reconciliation、Claim COMPLETED、一次 COMMIT。之后必须由**全新 cdm_reader PostgreSQL Session** 读取持久状态；如事务响应模糊，**不重试 COMMIT**、只查 durable DB。
- 本方案是 Demo：Writer Pod 的独立 credential `omop_admin` 是高权限账号，本项目目前**没有**部署允许该 Pod COMMIT 的 Secret；生产环境应改为范围受限的 SQL 函数/专用最低权限账号后才能长期自动运行。

## 安全边界：尚未启用实际 COMMIT

除 Airflow 手工 Conf 双开闸门外，Writer Pod 还强制校验 `TASK004_WRITER_AIRFLOW_COMMIT_SELECTION=YES` 和 `TASK004_WRITER_MODE=COMMIT`，需要在 **dw-spark Namespace** 另外准备仅本独立 KPO 可用的 K8s Secret：

```text
name: task004-new-only-writer-commit
namespace: dw-spark
keys:
  enabled: "YES"
  password: <PostgreSQL omop_admin credential, never saved in Git>
```

**截至验收时这个 Secret 根本不存在**，从未把管理员 DB 密码添加到源代码/Workflow 环境日志，也没有开启 Airflow 自动 Claim。不要私自添加 Secret 来启用无人监督大范围提交。需要与具体第三批 NEW_ONLY 独立验收、明确 COMMIT 边界一起启动；这一轮的只读验收不会更改 PostgreSQL 任何业务行。

## 真实证据

- 新镜像真正构建/发布 [Healthcare GitHub Actions 38581579633](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38581579633) **SUCCESS**；固定 image digest 如上。CI Writer 安全测试通过。
- Self-Runner [38582267163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38582267163) **SUCCESS**：53 Landing +58 Writer = 111 组 Unit/Contract 回归；真实 dw-airflow Scheduler Python3 KPO `automount_service_account_token` API 支持检查 PASS；worker02 真实 K8s Pod 拉取该 digest，成功导入 Writer、S3 Reader、SQL Renderer Python 模块；部署所需 Secret 确认不存在；PG `READ ONLY` Before/After Person207、Visit21690、Claim2、两个已提交 Batch COMPLETED1 各自完全相同；Spark 没有重运行，没有任何业务 COMMIT。
- Writer 镜像初次构建 [Run 38580929111](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38580929111) 在专用测试文件尚未提交时没有找到测试，属于 CI 时序问题；随后 [38581235821](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38581235821) 与最终 [38581579633](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38581579633) 已 SUCCESS。

## 剩余步骤：真正宣布 TASK004 核心链路完成

1. 本 PR 合并 Main 后，**真实 Airflow GitSync** 加载新 DAG，正式 DagBag 无 ImportError/验证 14 Tasks、image digest、路由，再使用**已提交第二 Batch** 仅做 `COMPLETED → already_completed_no_replay`，不得触发 Spark/Writer。
2. 第三个**真正全新、Source ID 不与前两批冲突**的 NEW_ONLY S3 READY Batch，手工 Airflow conf 双 opt-in（并在受控环境部署单批次 COMMIT Secret），由 DAG 本身自动完成 Spark、Writer、COMMIT、独立 PostgreSQL Reconciliation，并验证重放安全跳过。没有这次实际 live COMMIT 就不能宣称全链路完成。
3. 第三批的初次成功后需要锁定并移除/禁用高权限临时 Secret，不允许留长期无人监督 root-like 自动写入；改为专用最低权限 Writer/Fencing 函数是后续生产化工作（不作为本 Demo 的复杂并发 blocker）。
4. 双 Writer 并发竞争/复杂不明提交状态恢复继续为 Future Enhancement；TASK005 ON HOLD、Portal A4 HOLD。

**本阶段工程判定：Airflow Writer KPO 已实现、打包、集群只读验收；真实 Main GitSync、新第三批 COMMIT 尚待最后验收。TASK004 IN PROGRESS。**
