# Airflow Landing Discovery v2 Reader — 真实部署与 Claim NO 验收（2026-10-13 EDT / 2026-10-14 UTC）

> **实际运行中的 Airflow Landing Reader 已使用包含 strict NEW_ONLY v2 Manifest Contract 的新镜像，GitSync、DagBag、真实无参数 DagRun、Claim Guard 与 Spark skip 实测成功。** 仍保持 `CLAIM_ENABLE=NO`、`CLAIM_ALLOWLIST=""`。本轮**没有** S3 v2 READY 发布、Synthea 新病人生产或 PostgreSQL Person/Visit 写入。TASK004 IN PROGRESS，TASK005 ON HOLD。

## 已合并的源码与不可变执行证据

- Healthcare [PR #104](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/104) merged Main squash SHA `a6b87497497fb1b1367c0646e3410a24ed4f7ec3`；Self-Runner [PR #89](https://github.com/JohnZhang-DataForge/Self-Runner/pull/89) merged Main squash SHA `a0f4efb4770caef80dd1b0ebb9637ddf18c56638`。
- 官方仓库自身有发布权限的 [Healthcare GHCR 构建 Run 38495502204](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38495502204) SUCCESS，29 discovery tests PASS；使用现有 `healthcare-landing-discovery` GHCR Package 重新发布而不是覆盖旧 digest：
```text
ghcr.io/johnzhang-dataforge/healthcare-landing-discovery@sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924
```
- 使用等价相同 Scanner 源码、独立新 image 包的 [Self-Runner Run 38495328517](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38495328517) SUCCESS：offline Discovery 29 tests + v2 contract 4 tests，worker02 真实 S3 上 `synthea-new-only-gh-38484300008` 73 Person 和 `synthea-new-only-gh-38489944582` 70 Person 的真实 v1 Manifest SHA 都能在 XCom preview 中匹配，`processing_authorized=false`、`database_mutation=false`。
- 正式 GHCR Image [Self-Runner 38495856841](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38495856841) SUCCESS：worker02 由 Airflow 实际 `task004-control-runtime` ServiceAccount 直接拉取这个精确官方 digest；没有注入临时 `imagePullSecrets` 或短期 Actions Token，成功验证容器内 v2 CSV Contract 存在。
- **运行中 Airflow [Self-Runner 38496119114](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38496119114) SUCCESS**：
  ```text
  AIRFLOW_V2_GITSYNC_EXACT_SOURCE=PASS
  AIRFLOW_V2_REAL_DAGBAG_IMAGE=PASS
  AIRFLOW_V2_CLAIM_DISABLED=PASS
  AIRFLOW_V2_REAL_DAG_TRIGGER=PASS
  AIRFLOW_V2_REAL_DAGRUN_STATE=success
  AIRFLOW_V2_SCAN_CLAIM_GUARD=PASS
  AIRFLOW_V2_SPARK_NOT_TRIGGERED=PASS
  AIRFLOW_V2_RUNTIME_READONLY_DAG=PASS
  AIRFLOW_V2_CLAIM_ENABLE=NO
  POSTGRESQL_MUTATION=NO
  ```
  Airflow scheduler 内源文件 SHA 与 Main 精确一致；DagBag 真正加载了 `landing_batch_discovery`，其扫描 task `image` 等于上面的官方 digest；Claim task 的 Kubernetes `env_vars` 真解析后为 `CLAIM_ENABLE=NO`、Allowlist 空。

## 真 DagRun 的 TaskInstance 结果

| Task | 真 Airflow 实测状态 | 说明 |
|---|---|---|
| `scan_ready_manifests` | success | v2 Reader 镜像读取 SeaweedFS S3；只读 XCom |
| `evaluate_batch_claims` | success | PostgreSQL Claim Guard 检查，Claim=NO |
| `authorize_processing_replay` | success | 对没有显式 Replay 授权的无参数 DagRun 返回不授权 |
| `processing_only_gate` | success | ShortCircuit 使业务处理任务跳过 |
| `spark_patient` | skipped | 没有启动 Spark |
| `spark_encounter` | skipped | 没有启动 Spark |
| `spark_reconcile` | skipped | 没有启动 Spark |
| `verify_spark_processing` | skipped | 没有生成处理结果 |

无需更改 Airflow Helm Chart、Scheduler 镜像或 ServiceAccount。更新的是 GitSync DAG 中固定的 `DISCOVERY_IMAGE`，同时独立的 `images/landing-discovery-runtime/Dockerfile` 加入 `validate_new_only_v2_manifest.py` 及精确 `csv-contract-v2.json`。

本轮新增 `tests/landing_discovery/test_v2_airflow_reader.py`，测试 v1+v2 Manifest 并行发现、非法 v2 quarantine、v1 全非空合同未放宽、Claim=NO。旧 `resolve_verified_landing_file.py` 的 v1 分支未改；v2 版本只对显式 `manifest_version=2.0` / `synthea-new-only-*` 激活。

## 注意的 GHCR / 运行历史

- Self-Runner 尝试向原 GHCR Package 推送时曾返回 `write_package` 拒绝；这是包级权限，而非源代码缺陷。通过**持有现有 Package 发布权限的 Healthcare 自身** `build-landing-discovery-image.yml` SUCCESS 解决。早期临时独立 `healthcare-landing-discovery-v2` 包仅用于测试，不是运行中 Airflow 所引用的镜像。
- 一次 KPO 离线验收脚本曾在 Pod 完成后 `kubectl exec` 失败；更正为在 Pod 完成前输出 XCom 摘要并从 Logs 验证，最终 worker02 完成 SUCCESS。另实际 DagBag 读取 KPO `env_vars` 时最初把 Kubernetes `V1EnvVar` 列表误认为 dict，修正断言后真实 DagRun SUCCESS；没有改动 Airflow 生产任务或业务数据。
- Airflow 的 cron 仍配置每 15 分钟；本轮验收**确实人工触发**一个普通无参数 DagRun，并没有单独证明新版部署后某个自然 cron 的新 DagRun。

## NEXT — NEW_ONLY 真实 v2 S3 READY（不要重做 Airflow Reader）

1. **版本化批准 v2 发布**：当前 `contracts/synthea/new-only/csv-contract-v2.json` 的 `consumer_compatibility` 仍是 `NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY`，`apps/synthea/new_only/publish_v2_verified.py` 仍严格 BLOCK。必须在下一轮经过合同审查，显式更新到 `V2_RUNTIME_CONSUMER_DEPLOYED_READY`，重建正式独立 NEW_ONLY Publisher digest，并让更新后的 Publisher 和已部署 Reader 真实核对 exact contract SHA。
2. **生成真正合法空辅助 CSV 的 NEW_ONLY 批次**：全新 `gh-<run_id>` Request、worker01 `dw-synthea` Retain PVC 持久化、真实运行 Synthea v3.3.0；绝对不能篡改既有 73 或 70 人数据模拟空表。选择合法小人口 Profile 时需要先版本化定义参数合同、保证请求不可变、回放幂等。
3. **真实预发布源键审计**：重审当前 SeaweedFS 历史 Source IDs、真实 PG Person/Visit source maps、existing Batch Ledger；源码与 Manifest 都必须和原始冻结请求绑定，S3/PG READ ONLY 源键检查不能替代 Writer COMMIT 时事务锁。
4. **真实不可变 READY**：上传 18 CSV（允许仅合法辅助表 `row_count=0`）→ 全量 S3 GET/SHA256 → 最后发布 v2 `INTAKE_VERIFIED` Manifest → 已部署 Airflow v2 Reader 真实只读发现（Claim=NO）→ 独立 v2 Resolver/18 S3 对象回读 → 同请求 `REUSE_EXISTING` 幂等重放、SHA 完全相同；验收后才把 REAL_V2_S3_READY 标记为 PASS。
5. **不要启动其他模式/Writer**：`synthea-update-only` / `synthea-mix-data` 仍 DESIGN ONLY；Writer 旧 `task004-airflow-` Batch ID 和 `BLOCKED:EXISTING_TARGET_DRIFT` 完全不变，Spark/PG ROLLBACK 正例和动态 COMMIT 尚待独立批准。

**权威状态：AIRFLOW_V2_READER_DEPLOYED=LIVE_PASS，V1_S3_BACKWARD_COMPATIBILITY=LIVE_PASS，CLAIM=NO，NEW_ONLY_V2_PUBLISHER_CODE_STAGED=PASS，REAL_V2_READY=NO，DYNAMIC_POSTGRES_COMMIT=NO，TASK004=IN_PROGRESS。**
