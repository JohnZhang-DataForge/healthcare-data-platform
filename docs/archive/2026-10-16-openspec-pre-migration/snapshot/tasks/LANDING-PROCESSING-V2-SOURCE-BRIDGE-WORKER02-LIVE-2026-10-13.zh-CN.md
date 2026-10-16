# Landing Processing v2 源解析桥接 — worker02 真实验收

> **2026-10-13 EDT / 2026-10-14 UTC：v2 SOURCE BRIDGE REAL S3 PASS、v1 COMPAT PASS。** Healthcare PR #112 + Self-Runner PR #93。最终实际 Self-Hosted Runner [Run 38503213376](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38503213376) SUCCESS；**SPARK_APPLICATION=NO，CLAIM_ENABLE=NO，POSTGRESQL_MUTATION=NO，S3_MUTATION=NO**。TASK004 IN PROGRESS，TASK005 ON HOLD。

## 本轮发现和改动

原已验收的控制镜像 `healthcare-data-platform-task004-runtime@sha256:8d55a150...` 早于独立 Synthea NEW_ONLY v2 Reader 合同。虽然当前 Healthcare Main 的 Resolver 有 v2 分支，但原固定运行镜像缺少 `validate_new_only_v2_manifest.py` 与其 SHA 固定的 CSV Contract，因此**不能直接把旧控制镜像用于 v2 Spark**。

使用新的功能名 `images/landing-processing-runtime/Dockerfile` 做 **immutable additive layer**，依赖旧固定 digest、不覆盖旧镜像，额外打包已验收的现行 Resolver、v2-only Validator 与完全相同的 `csv-contract-v2.json` 原始字节；合同 SHA 保持：

`d7118f4bc3306d74911e609b4f0a41b9340ba9a60acaa69174063d5025ad1249`

新版正式镜像精确 digest：

`ghcr.io/johnzhang-dataforge/healthcare-landing-processing-v2@sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937`

**没有修改 v1 合同、原 v2 合同、任何已发布 READY Manifest/Payload，也没有触发 Synthea Generator、Airflow Claim 或 Spark Application。**

## 测试与真实证据

第一次 Self-Runner [Run 38502593628](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38502593628)：Hosted build/Push + v2 真实 source readback 均通过，worker02 返回 v2 Patients 1、Encounters 812、Manifest SHA 精确匹配。最后 v1 73 人回归失败，仅因为 Workflow 错将 S3 发布 UTC 日期填为 `2026-10-13`；实际不可变 URI 的 `ingest_date=2026-10-14`，S3 404 属测试路径错误，未修改源数据；原 Workflow 的等待逻辑还导致 5 分钟后才报告错误。

第二次 [Run 38503213376](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38503213376) **build / live 全 SUCCESS**：
- 严格 `tests/landing_discovery` 34/34 + `test_v2_consumer.py` 4/4，共 38/38 PASS；镜像内 v2 Contract SHA PASS；
- 新镜像真正从 worker02（`dw-spark`）Pod 使用受限 S3 Secret，按固定 batch/Manifest URI/SHA 读取 SeaweedFS；
- v2 `synthea-new-only-gh-38497355290`：`V2_PATIENT=1`、`V2_ENCOUNTER=812`、`V2_MANIFEST_SHA=PASS`；
- v1 `synthea-new-only-gh-38484300008`：`V1_BACKCOMPAT_73=PASS`，其实际 ingest_date 是 `2026-10-14`；
- `REAL_WORKER02_V2_SOURCE_BRIDGE=PASS`，无 PG DML / Claim / S3 写入；工作流失败检测已改为 Job failed 即 Fail Fast。

## 下一步（不能把本轮标为 Spark PASS）

**NEXT**：版本化更新 Airflow 手工 NEW_ONLY v2 Processing-only 选择门槛，保留历史批次 `SKIP_LEGACY_BATCH` 分支，只在显式 `processing_only` 且 `new_only_processing_probe` 双开、READY+完整 Manifest SHA、Claim NO + `OBSERVED_ONLY` 条件下允许验证新的批次；固定使用本轮新镜像 digest，并处理 `task004_cdm_preflight_contract.py` 旧 `task004-airflow-*` 约束。实际触发一次 Airflow DagRun → Spark Patient/Encounter → Reconcile → 真 S3 Processing Parquet XCom，回读 Person 1 / Visit 812、检查 PG 无变化。

后续使用该真实新批 Processing URI，设计 Person→Visit 在同一事务内成功 ROLLBACK、再 Claim token fencing / COMMIT / Reconciliation。不得把只读 Source Bridge 误称完整 Spark、成功 Writer ROLLBACK 或 COMMIT。
