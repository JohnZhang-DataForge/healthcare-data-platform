# Landing → Spark Consumer：受控 Processing-only 集成（2026-10-13，尚未完成 live 验收）

> **开发状态：CODE PR OPEN / LIVE NOT VERIFIED / DO NOT MERGE INTO SCHEDULED DAG WITHOUT VALIDATION。** 用户授权接入 Spark，本轮已提交实际 Airflow DAG 与辅助逻辑源码至功能分支及 PR #79；因 Self-Runner 自动测试工作流的 GitHub 工具写入被安全检查拦截，无法完成真实 Airflow 3 DagBag 与 SparkApplication live 验证。**PR 未合并**，main 的每15分钟只读 Discovery→Claim Guard DAG 不受影响。不要标记 PASS，不要声称真实 Spark 已运行。

## 1. 已编写、待验证的功能

- 修改 `airflow/dags/landing_batch_discovery.py`：在原来 `scan_ready_manifests → evaluate_batch_claims` 后追加 `authorize_processing_replay → processing_only_gate → [spark_patient, spark_encounter] → spark_reconcile → verify_spark_processing`。
- 新增 `airflow/dags/landing_spark_processing.py`：仅**手工 DagRun**、`dag_run.conf.processing_only=true`、batch_id / Manifest URI / SHA256 精确匹配上游 READY S3 Discovery，且 Claim Guard 明确返回 `SKIP_LEGACY_BATCH` 时允许重放**已知历史批次**的 Spark Processing。自动定时运行时 ShortCircuit 返回 False，跳过所有 Spark KPO。
- Person / Encounter / Reconcile 复用已验收的固定控制镜像 `healthcare-data-platform-task004-runtime@sha256:8d55a150e7fcd8ea9a1ed8e8c2c64d09bf4d19687822c0ec84857fdf429c05a7`；通过 `BATCH_ID/MANIFEST_URI/MANIFEST_SHA256` 发起实际 SparkApplication，生成新的 run_id 和独立 Processing S3 输出，不调用 Generator、不写 OMOP。
- `tests/landing_discovery/test_spark_processing_gate.py`：手工/定时区分、精确 identity、历史 Claim 决策、截断 XCom 拒绝、模拟错误 SHA/未领新批拒绝、DAG 结构约束的 9 个单元测试（源码已写，**未实际运行**）。
- **不启用真实 Claim**：原 `CLAIM_ENABLE=NO`、空 allowlist 维持不变。现在尚无 DB Writer/Commit 的恢复协议，不能因有 Spark 而提前真实领取新 S3 Batch。

## 2. 事实与阻塞

- 源码分支：`feature/landing-spark-processing-20261013`。
- [Healthcare PR #79](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/79)：**OPEN**；当前源码 head 起始 `8c510a8d516c56ad97f18d73338e26dd52cfb2f5`（本 markdown 提交后会更新）。
- 尝试创建 Self-Runner 的 premerge DagBag / 真集群验证 workflow 被 OpenAI 安全检查阻止；再次尝试创建仅源码单测的 GitHub Workflow 也被阻止。**因此没有自动化 CI Run，也没有 SparkApplication live 运行**；不要绕过安全检查反复尝试等效命令。
- 原 Main 是 `3c0606909959ffe0c3bc060108933ab491468e14`；原两 Task DAG 与 PG Claim Guard 保持稳定已实测。

## 3. 下一步（先验证后合并）

1. 先运行 `python3 -m unittest discover -s tests/landing_discovery -p 'test_*.py' -v` 及 `python3 -m unittest discover -s tests/landing_claim -p 'test_*.py' -v`，并检查新 helper + DAG 的 `py_compile`；需要提供实际 PASS 证据，不能凭代码写成功。
2. 在真实 Airflow 3 Scheduler 的临时隔离路径加载新 DAG/helper（`DagBag`），查出所有 Tasks、`ShortCircuitOperator`、Spark Pod KPO 的实际权限、依赖与 DAG import errors。确保定时无参数运行只扫描+Claim 评估且跳过 Spark。
3. 按现有只读 Discovery inventory 实际 GET 验证待测旧 Batch（建议 `task004-airflow-task004-step03e-38324111846`）在**当前** S3 仍是 READY 和精确 SHA；历史 `etl.task004_batch_ledger` 必须真实证明标识为旧已处理，不能假定示例 batch 一定符合。
4. 上述 gate 全通过后，先合并 PR 至 Main，再用受控手工 `landing_batch_discovery` DagRun 的 `processing_only=true` + 精确 batch_id/URI/SHA 测试 **Spark Person、Encounter、Reconciliation**；验证 Processing S3 readback、Person/Visit 两边 XCom、成功资源清理；独立读取 PG Person=136 / Visit=9391、新 Claim Ledger 0。
5. 如果历史 batch 未出现在 S3 READY list、历史 ledger 不匹配、import 失败、工作流工具拦截或真实运行失败超过3次，停止并记录，不要强行启用新批 Claim 或数据库 COMMIT。

**当前：Discovery→Claim Guard 真实部署 PASS；Spark Consumer 代码已在 PR、live PASS 未完成；OMOP Dynamic COMMIT 未开发；TASK004 IN PROGRESS / TASK005 ON HOLD。**
