# Healthcare Data Platform — TASK004 Current Agent Handoff（2026-10-13 EDT / 2026-10-14 UTC）

> 以当前 GitHub Main、[NEW_ONLY v2 S3+Airflow 验收](SYNTHEA-NEW-ONLY-FIRST-REAL-V2-S3-READY-AIRFLOW-2026-10-13.zh-CN.md)、[NEW_ONLY Writer 身份只读验收](OMOP-NEW-ONLY-WRITER-IDENTITY-V1-READONLY-LIVE-2026-10-13.zh-CN.md) 为准。旧的“Generator DESIGN ONLY / 尚无 READY”状态已失效，完整老交接归档：docs/archive/2026-10-13-new-only-writer-identity/TASK-004-AGENT-HANDOFF-BEFORE-WRITER-IDENTITY.zh-CN.md。TASK004 IN PROGRESS / TASK005 ON HOLD。

## 已完成、不要重做

NEW_ONLY Synthea v3.3.0 worker01 Retain PVC，冻结随机 Request 参数、1–100 人、源身份双侧只读防撞、immutable S3 READY + Replay 均通过实际运行。真实独立 READY 共 3：
- v1 synthea-new-only-gh-38484300008：73 Person / 12159 Encounter；Manifest SHA 66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9
- v1 synthea-new-only-gh-38489944582：70 Person / 11487 Encounter；SHA be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256
- v2 synthea-new-only-gh-38497355290：1 Person / 812 Encounter / 18 CSV（1 auxiliary header-only）；Manifest SHA dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80

真实证据：Generate [38497355290](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497355290)、S3 Publish+Replay [38497549237](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497549237)、Airflow 实际 v2 XCom [38497724825](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497724825)。Reader 已部署。不能编辑 v2 原 CSV 合同 SHA、S3 READY、既有 PVC。

## 消费现状

- airflow/dags/landing_batch_discovery.py + apps/landing_claim/：每 15 分钟扫描、真实 PG Claim Guard 已接线；**CLAIM_ENABLE=NO**、allowlist 空、尚无持久自动 Claim。现有 Ledger 事务 ROLLBACK 真实验收 [38468961485](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38468961485)；25-item preview 上限、Heartbeat/过期 Lease/unknown COMMIT 尚有缺口。
- airflow/dags/landing_spark_processing.py：历史 Batch 手动 Spark Processing+Reconcile 8 tasks PASS [38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452)，没有对新 NEW_ONLY v2 完成真实 Spark。
- apps/omop_writer/、airflow/dags/task004_cdm_dynamic_*：旧 Writer 真 S3 source→PG 历史 Source-ID 内容漂移拦截 PASS [38479591382](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38479591382)，不是成功 ROLLBACK 正例。
- NEW_ONLY Writer 身份版本：Healthcare PR #109 + Self-Runner PR #92 / [Run 38500077292](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38500077292) 53/53 tests、真实 PG READ ONLY PASS。新版本 writer_identity_version=synthea-new-only-v1 必须显式指定；原 task004-airflow-* 无版本合同保持，Existing Target Drift 保留，NEW_ONLY COMMIT 被拒绝。**此代码尚未作为新 Writer image 部署**。
- 最后 PG 实测：Person=136、Visit=9391、Claim=0；v2 Batch Claim/Legacy/Stage/Commit 均 0。

## 下一轮按依赖推进

NEXT-A：选真实 v2 1 人 812 Encounter Batch，开展单次人工明确授权的 Spark Processing-only 真实 Airflow DagRun、精确 Manifest SHA、S3 Parquet+XCom readback。禁止启用自动 CLAIM，禁止 PG 写入，禁止改旧 READY。

NEXT-B：绑定实际 Person/Visit Processing URI + manifest hash，独立新版 Writer digest，实际 PG Reader 安全门槛、joint Person/Visit 事务 ROLLBACK 正例。现有单实体 SQL 独立 BEGIN/ROLLBACK 且 Visit 依赖 Person VERIFIED，不能仅运行两个 rollback Job 当作完成全批 ROLLBACK。

NEXT-C：新增单事务 claim token / lease fencing、锁与并发/失败恢复、Source ID + Existing Target Drift 事务复查，之后受控真实 COMMIT 和独立 DB reconciliation / COMPLETED / repeated replay。

NEXT-D：启用单批 Airflow 自动 Claim→Spark→Writer，治理 preview=25 安全上限、Heartbeat 和自然 Cron；通用 NEW_ONLY 新 Request workflow 的 v1/v2 镜像版本化选择另外收尾。UPDATE_ONLY、MIX_DATA、TASK005 均 ON HOLD。

## 规则

GitHub Main 唯一正式业务权威；feature branch→PR→Self-Runner Workflow→实际日志及 K8s/PG readback→Merge→docs 更新。单轮一个有效小闭环，修复上限三次，不动历史 READY / PVC / Secrets / Legacy Ledger，禁止没有实测证据便宣称 COMMIT/ROLLBACK 成功。