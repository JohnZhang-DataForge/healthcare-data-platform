# Synthea NEW_ONLY 第一个真实 v2 READY 全流程实测 — 2026-10-13 EDT / 2026-10-14 UTC

> **最新权威状态：FIRST_REAL_NEW_ONLY_V2_S3_READY=PASS；REAL_AIRFLOW_V2_DISCOVERY_XCOM=PASS；IMMUTABLE_REPLAY=PASS；CLAIM_ENABLE=NO；SPARK_NOT_TRIGGERED；POSTGRESQL_MUTATION=NO。** `TASK004 IN PROGRESS`，`TASK005 ON HOLD`。本报告覆盖此前过期的“v2 Publisher/Reader 尚未启用、v2 尚无真实 READY”的断言。

## 已合并 Main 和真实执行证明

- Healthcare 生产代码 [PR #107](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/107)，merge `01c73518fd1174772ce82f816284dcaa85e02326`。新增不可变参数化 population=1..100（只在创建全新请求时可设 `NEW_ONLY_TARGET_POPULATION`，冻结后不得改变），新增 `contracts/synthea/new-only/ready-publication-policy-v1.json` 和 fail-closed v2 Publisher 发布门槛，不修改既有 v2 CSV Contract 的原始字节，也不影响任何旧 v1 Resolver/Writer。
- Self-Runner 实施验收 [PR #91](https://github.com/JohnZhang-DataForge/Self-Runner/pull/91)，merge `6b7f0ead8e5fd59f3d14f9dec00d4fdd4124f494`。此三个新 Workflow 是**特定已冻结第一批的不可变实测流程**，不是未来每次运行都会生产 1 人的新通用入口。
- **[Run 38497355290](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497355290)** SUCCESS：45 个 NEW_ONLY 测试 + 29 Landing Discovery 测试 PASS；新版独立 NEW_ONLY image build/push + 容器内政策验证；真实 Synthea v3.3.0 在 `dw-synthea/worker01` 创建全新唯一 `gh-38497355290` Request，Person **1**、Encounter **812**、18/18 CSV，`synthea-new-only-state` PVC 永久保存冻结参数、校验标记和原始 CSV。没有人为制造/删改历史 CSV。
- 正式 NEW_ONLY image 不变 digest：
```text
ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:050a9dcdfb1b95791e2664b85d692152408a473201e2e73a2420f8349167a21f
```
- **[Run 38497549237](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497549237)** SUCCESS：读取**已冻结**原始 1 Person/812 Encounter 实际 CSV，v2 逐表/header/SHA 验证，恰有 **1 个辅助 CSV 为合法 header-only 零行**；扫描过去真实 SeaweedFS S3 所有相关 Person/Encounter source hashes 无交集；PostgreSQL `BEGIN TRANSACTION READ ONLY` 重审 136 个历史 Person key、9391 个历史 Visit key，同源碰撞数均 **0**，本 Batch 的两个 ETL/Claim Ledger 记录数均 **0**；这两个独立 Gate 验收 PASS 后才允许发布。
- 真实 S3 首发结果 `PUBLISH_MODE=PUBLISHED_NEW`，18 原始 Payload 全部 PUT/GET/SHA256 通过；最后才写 `manifest_version=2.0` / `status=INTAKE_VERIFIED` 的 `manifest.json`，再做独立 v2 Discovery/Resolver/18 GET 校验；后续同 Request `PUBLISH_MODE=REUSE_EXISTING`，没有覆盖任何 Payload 或 Manifest，SHA256 完全相等。
- **[Run 38497724825](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38497724825)** SUCCESS：运行中 Airflow scheduler 实际 GitSync/ DagBag 使用新版只读 v2 Discovery 镜像，人工触发一次真实 `landing_batch_discovery` 无参数 DagRun，**真正从 TaskInstance XCom 取得新 v2 Batch 与完全相同的 Manifest SHA256**，不只是另一只临时 Reader Pod。 `scan_ready_manifests/evaluate_batch_claims/authorize_processing_replay` 为 success，`spark_patient/spark_encounter/spark_reconcile/verify_spark_processing` 均 `skipped`，`CLAIM_ENABLE=NO`，PG DML 0。

## 首个真实 v2 READY 精确标识

```text
generation_request_id=gh-38497355290
batch_id=synthea-new-only-gh-38497355290
generation_mode=NEW_ONLY
target_population=1
person_rows=1
encounter_rows=812
source_csv_files=18/18
genuinely_header_only_auxiliary_csv_files=1
manifest_version=2.0
manifest_status=INTAKE_VERIFIED
s3_uri=s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38497355290/manifest.json
manifest_sha256=dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80
first_publication=PUBLISHED_NEW
same_request_replay=REUSE_EXISTING
independent_readback=18/18 PASS
real_airflow_xcom_manifest_match=PASS
postgresql_mutation=NO
```

## 现在是两个 v1 + 一个 v2 独立 READY

| Manifest | Person | Encounter | 版本 | 状态 |
|---|---:|---:|---|---|
| `synthea-new-only-gh-38484300008` | 73 | 12159 | v1 | READY，旧 Manifest SHA `66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9` |
| `synthea-new-only-gh-38489944582` | 70 | 11487 | v1 | READY，旧 Manifest SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256` |
| `synthea-new-only-gh-38497355290` | 1 | 812 | **v2** | **READY，真实含 1 个零行辅助 CSV**，Manifest SHA `dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80` |

三份均是真正独立、不同 Batch ID 的真实数据；本轮没有修改此前任何已 READY 数据。

## 为什么不用直接修改老 v2 CSV 合同的“未部署”标记

Airflow 实际 Consumer 的独立只读镜像已经固定 `contracts/synthea/new-only/csv-contract-v2.json` 内容及 SHA256：

```text
contract_sha256=d7118f4bc3306d74911e609b4f0a41b9340ba9a60acaa69174063d5025ad1249
deployed_reader_image=ghcr.io/johnzhang-dataforge/healthcare-landing-discovery@sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924
airflow_reader_live_acceptance_run=38496119114
```

合同内 `consumer_compatibility=NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY` 是之前预部署历史标记，**不应直接编辑原合同的一个字节**，否则其 SHA 变化而旧 Reader 拒绝新 Manifest。现在**真正的发布授权状态**由单独、受版本控制的 `ready-publication-policy-v1.json` 表达；此新 Policy 经代码明确核验：固定已部署 Reader image digest、成功真实 DagRun、原 CSV Contract SHA、NEW_ONLY/v2 Manifest/只读 Claim 与 PG 禁止写入范围。没有 Policy、伪造镜像或 SHA、错误版本均 fail-closed。**不能把旧字段当成尚未完成 v2 Reader 部署的现状**，也不能为了消除历史字段而改动当前 v2 合同 SHA。

S3 和 PG Source ID 防撞审计是**发布前只读筛选**，不能替代未来 Writer COMMIT 时受控事务内的 Existing Target Drift/Fencing 检查。

## 下一步（不要重新生成或重新发布上述批次）

1. **通用独立 NEW_ONLY Workflow 分支升级**：Self-Runner Main 现有通用 `Synthea NEW_ONLY - Run New Independent Request` 仍 pin 之前旧的只支持 v1 的源码和 digest。下一阶段应将它版本化到本轮正式 v2 image 并规范参数/Request 身份、审计和 v1/v2 选择。任选 1..100 人真实合法零行辅助 CSV 可发 v2，其余可维持严格 v1；不要运行本报告中的一次性固定 Request 证明工作流生成新批。
2. **Airflow Consumer 后续 Claim / Spark / PostgreSQL Writer**：虽真实 v2 READY 已被 Airflow XCom 发现，当前 **Claim=NO**，没有 Spark 处理这个 v2 Batch，也没有写 `cdm.person` / Visit / OMOP；后续应独立扩展 Writer 支持 `synthea-new-only-*` 并做读写隔离、Claim fencing、事前事中 Existing Target Drift、ROLLBACK 正例及授权 COMMIT，保留历史 `task004-airflow-*` 行为。
3. `synthea-update-only`、`synthea-mix-data` 仍是 DESIGN ONLY；OpenLineage/Marquez 属平行开发，不得混为此轮产出。

**结论：真实 v2 Landing 生产/校验/发布/重放/Airflow 只读发现闭环已经完整 DONE；TASK004 整体尚未结束，因为动态 NEW_ONLY Airflow→Spark→PostgreSQL Materialization 尚未获批也未实现。**
