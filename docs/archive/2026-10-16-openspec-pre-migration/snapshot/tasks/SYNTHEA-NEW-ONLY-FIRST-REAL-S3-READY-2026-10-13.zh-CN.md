# Synthea NEW_ONLY — 首个真实不可变 S3 READY 批次闭环（2026-10-13 EDT / 2026-10-14 UTC）

> **NEW_ONLY 已通过真实「现存 PVC 数据 → 严格 v1 18 CSV → S3 payload 最后 Manifest → v1 Discovery + 全量读回 → 幂等重放」PASS。** 这代表第一个实际 READY 的 NEW_ONLY Batch，**不等于**独立新请求自动定时生成已部署、Airflow Claim 已开放、Spark 已自动消费、PostgreSQL ROLLBACK 正例或 COMMIT 已完成。TASK004 IN PROGRESS / TASK005 ON HOLD。

## 权威 GitHub 与 Self-Runner 实际证据

- Healthcare [PR #93](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/93)：真实验收 PR commit SHA `a504309aa1694e9733b40956350477484b90428b`，合并 Main squash SHA `2a708a25879685e6bb542c35f89f0e85214ac9a7`。
- Self-Runner [PR #83](https://github.com/JohnZhang-DataForge/Self-Runner/pull/83)：合并 Main squash SHA `61b005eda59af23e9044472f0cc5d88a230e6e5b`。
- 实测 [GitHub Actions Run 38488453236](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38488453236)：完整 Job `SUCCESS`，所有测试、先验身份审计、后续四阶段执行及 replay 全部 PASS；无重试循环。
- 现存 producer 请求由 [首次生成 Run 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008) 在 worker01 `dw-synthea` 创建、已经持久化；本轮**没有**重新执行 Synthea 生成人员。

## 发布的数据与精确不可变身份

```text
generation_mode=NEW_ONLY
generation_request_id=gh-38484300008
batch_id=synthea-new-only-gh-38484300008
person_rows=73
encounter_rows=12159
validated_csv_count=18/18
csv_total_bytes=119147940
csv_all_nonempty=YES

source_synthea_version=v3.3.0
source_date=2026-10-13
landing_ingest_date_UTC=2026-10-14
manifest_uri=s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38484300008/manifest.json
manifest_sha256=66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9
manifest_version=1.0
manifest_status=INTAKE_VERIFIED
```

注意：`source_date` 是原生成请求参考日期，而 `ingest_date` 是 S3 发布时的 UTC 日期；2026-10-13 EDT 当晚等于 2026-10-14 UTC。不能把两者强行改成相同一天。Manifest SHA 在首次上传、独立读回及 replay 完全相同。

## 实际验收顺序（完整成功循环）

1. **安全重审，无变更**：Git checkout 精确 SHA、NEW_ONLY 单元测试；只读重新扫描既有 SeaweedFS 源身份 CSV，PG `BEGIN TRANSACTION READ ONLY` 分别扫描 136 条 Person / 9391 条 Visit 已映射 Source Keys；对应当前 73/12159 Source IDs 重合 **0**；Ledger/Claim 无该 Batch。
2. **Strict v1 Validator**：在 worker01 `dw-synthea` 临时 Job 中，以 **只读** PVC `synthea-new-only-state` 装载 frozen `params.json`、`validated.json` 和 18 CSV；核查参数 SHA、Person ID 摘要、所选固定 Synthea 版本、实际 Person/Encounter rows；沿用**完全未修改**的 `contracts/synthea/v3.3.0/csv-contract.json` 严格校验 18 文件的完整 header / row / SHA256。当前批全为非空，所以合法落在既有 v1 协议中。额外以可选 `source_parameters` 记录 `generation_mode=NEW_ONLY` 和 `generation_request_id`，通过旧 v1 Publisher/Resolver 兼容门槛。
3. **独立 S3 immutable Publish**：此阶段之前不产生 S3 Manifest；使用已验证既有 v1 Publisher（不修改它），仅允许首次空 Batch 前缀上传、冲突时拒绝覆盖；18 CSV 按实际 SHA 上传、S3 GET 逐文件校验；**只有全部 18/18 回读成功最后 PUT `manifest.json`**，其状态为 `INTAKE_VERIFIED`、`PUBLISH_MODE=PUBLISHED_NEW`。
4. **独立 v1 Discovery + Resolver + 18 对象再读**：由第二个只读 Job 经 S3 API 调用现有 `scan_ready_batches.discover_ready_batches()`、`resolve_verified_landing_file.validate_manifest()`，重新 GET Manifest 比对上面完整 SHA，检查 73 Person、12159 Encounter 计数，并 GET 全部 18 对象独立计算 SHA256，返回 `NEW_ONLY_INDEPENDENT_S3_READBACK=18/18`。
5. **同一 Request Replay**：第三个短命 Job 仍从同一个只读 PVC 参数+CSV 构建完全相同 v1 draft，由老 Publisher 的严格内容核对返回 `PUBLISH_MODE=REUSE_EXISTING`；没有覆盖或创建第二个 Manifest；再次输出**相同** `66b6e79...` SHA。
6. 以上每个临时 Job 成功后删除；短命 ConfigMap 在整轮验收后清理；`synthea-local` Retain SC/PVC/PV、源 CSV 和新 S3 READY 批次保留。

## 新增可复用开发资产

```text
apps/synthea/new_only/publish_v1_verified.py
apps/synthea/new_only/verify_v1_ready.py
kubernetes/manifests/synthea/new-only/publish-v1-job.yaml.tpl
tests/synthea_new_only/test_publish_v1_verified.py
Self-Runner: .github/workflows/synthea-new-only-v1-s3-publish.yml
```

业务采用 `NEW_ONLY` 独立 CLI，不调用 `images/synthea/entrypoint.sh` 重新生产，也不依赖 Airflow。正式 NEW_ONLY 镜像仍待构建/发布 digest：本轮使用原有 digest-pinned Synthea 基础镜像，通过临时 ConfigMap 注入独立的新 Publisher 与验证工具。Self-Runner pin 精确 Healthcare feature SHA，已合并 PR 上正式源码供持续维护。

## 下一阶段（不得把 READY 当成 OMOP 完成）

1. **真正可反复运行的独立 Generator 镜像和发布器**：将 `generate_new_only.py`、`publish_v1_verified.py`、校验器封装到 `synthea-new-only` 独立 digest-pinned 镜像，Job/CronJob 独立管理 request identity 和发布幂等恢复；当前 Workflow 只是**固定 Batch 的实测和发布工具**，不是任意新 request 的自动生产流程。
2. **小人口 V2 Consumer 版本兼容**：当前 73 人的全部 18 CSV 非空，旧 v1 能无改动接收；但随机 1..100 人可能生成仅 header 的辅助 CSV，新的 `csv-contract-v2.json` 尚标 `NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY`，必须升级/版本化 Landing Resolver/Discovery 才能安全发布这些批次，不得静默放宽旧 v1 或丢弃辅助文件。
3. **Consumer（读取侧）**：独立 Airflow 现有 v1 Discovery Core 已发现 READY，实际 **Airflow 定时 DagRun** 是否对这一个新 Batch 产生对应可观察的 XCom/Ledger/Claim Guard 仍未专门核验。保持 Claim 默认关闭；不能声称 Spark 自动新 Batch Processing 已成功。
4. **Writer Versioned Batch IDs**：旧 Writer 仍只接受 `task004-airflow-`，新 `synthea-new-only-` 等三种名字必须显式版本兼容；现有 `BLOCKED:EXISTING_TARGET_DRIFT` 必须完全保留。然后做真实 S3→Spark Processing→Person→Visit PostgreSQL **ROLLBACK 成功正例**，只在完整 DB 事务级 Claim Fencing、Reconciliation、幂等/UNKNOWN-COMMIT 策略通过后才考虑独立授权 COMMIT。
5. `synthea-update-only`、`synthea-mix-data` 仅命名冻结 / DESIGN ONLY，禁止在本阶段混入业务代码；TASK005 仍 ON HOLD。

**权威当前事实：NEW_ONLY_LOCAL_GENERATE=PASS，NEW_ONLY_S3_READY=REAL_PASS，NEW_ONLY_S3_REPLAY=REAL_PASS，AIRFLOW_NEW_BATCH_AUTOCONSUME=NOT_PROVEN，OMOP_DYNAMIC_COMMIT=NOT_DONE，TASK004=IN_PROGRESS。**
