# Synthea NEW_ONLY — 独立 v2 不可变 Publisher 已实现但 READY 发布保留安全门槛（2026-10-13 EDT / 2026-10-14 UTC）

> **本轮真实通过：Publisher 代码 + 42 单元测试 + 完整内存 S3 上传/读回/重放仿真 + 真实 worker01 冻结 CSV v2 Draft 验证 + 真实镜像构建推送 + 正式发布安全拒绝。** **未向真实 SeaweedFS 发布任何 v2 READY；Airflow Consumer 运行中版本仍未升级。** TASK004 IN PROGRESS；TASK005 ON HOLD。

## GitHub / 运行证据

- Healthcare [PR #102](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/102) merged，main squash `97b229a83022037d0360e6da40a8c07be68b7ecd`。
- Self-Runner [PR #88](https://github.com/JohnZhang-DataForge/Self-Runner/pull/88) merged，main squash `4d7ee65c8c9d05cf759d00b0776df8575e92913f`。
- 真实 [Self-Runner Run 38492827750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38492827750) 两个 Job 均 SUCCESS：`Ran 42 tests`，`NEW_ONLY_V2_PUBLISHER_UNIT_SUITE=PASS`，`NEW_ONLY_V2_PUBLISHER_IN_IMAGE_SMOKE=PASS`，`NEW_ONLY_V2_PUBLISHER_PUSH=PASS`，`NEW_ONLY_V2_REAL_FROZEN_CSV_DRAFT=PASS`，`NEW_ONLY_V2_PUBLISHER_NOT_RELEASED=PASS`，`NEW_ONLY_V2_S3_READY_PUBLISHED=NO`，`POSTGRESQL_MUTATION=NO`。
- 新 GHCR 专用 image **真实 RepoDigest**：
```text
ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:4a456ee4f186bcfdcf5e22c6477ac92ce32941ca4bae9ba685b0b1a2ca3840c5
```
- 真实 worker01 Job 装载 `synthea-new-only-state` PVC 以**只读**方式验证已生成的 `gh-38489944582`，得出 Person=70 / Encounter=11487，准确构建 v2 Draft，但这批原本属于严格 v1，18 CSV 全非空；此动作不伪称实际存在 v2 零行辅助批次。
- 当前两个**真正的 v1 S3 READY** 仍是 `synthea-new-only-gh-38484300008`（73 Person/12159 Encounter）和 `synthea-new-only-gh-38489944582`（70 Person/11487 Encounter），原 Manifest 及 SHA 保持不变。

## 本轮实际开发

```text
apps/synthea/new_only/publish_v2_verified.py
apps/synthea/new_only/verify_v2_ready.py
apps/synthea/new_only/entrypoint.py     # add explicit --phase validate-v2/publish-v2/replay-v2/verify-v2
images/synthea-new-only/Dockerfile       # include new v2 modules
tests/synthea_new_only/test_publish_v2_verified.py
tests/synthea_new_only/test_verify_v2_ready.py
Self-Runner: .github/workflows/synthea-new-only-v2-immutable-publisher.yml
```

- 从 `frozen_request()` 读取已存在的 params/validated marker + 真实原始 18 CSV，重新运行 `audit_local()`，检查每个文件 schema、header、row shape、SHA256 和记录数与不可变 `validated.json` 一致；Person、Encounter 必须正数，另外 16 辅助表 `row_count=0` 可有非空 header-only CSV。每文件最多 512MiB、合计 2GiB，避免超出当前单请求内存界限。
- v2 Manifest 带 `manifest_version=2.0`、`synthea-new-only-*`、contract path + 精确 SHA、固化 seed / clinician seed / reference date / Synthea commit、18 文件的真实 SHA256 和文件尺寸，整个 Manifest 经已经测试的 `validate_v2_manifest()` 再验证。
- v2 Publisher 复用历史 `S3Client` 的签名访问，但**不**调用 v1 的 `publish_batch`，更没有更改原 v1 `row_count > 0` 规则。S3 历史 Source ID + PostgreSQL READ ONLY source key 预审是发布前单独的验收门槛；无 PG 写权限。
- 独立 v2 上传算法的**单元测试使用内存 Fake S3**，涵盖 18 CSV 上传、全部对象 SHA256 GET、最后写 `manifest.json`、从 S3 重放复用 `REUSE_EXISTING` 且 SHA 完全相同；已有 Manifest 缺失 Payload、覆盖冲突、读回 SHA 漂移、缺少预审标记或原始 CSV 被修改等情况全部拒绝。
- `verify_v2_ready.py` 支持从真实 v2 READY 的 Discover / Resolver 返回身份与 Manifest SHA、同冻源 Person/Encounter 数量对比，再逐一读取 18 个 S3 对象计算 SHA；本轮使用 Fake S3 执行此闭环。
- **生产发布明确 Fail Closed**：v2 Contract 中 `consumer_compatibility` 仍是 `NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY`。真正执行 `--phase publish-v2` 时，必须首先检测到它成为 `V2_RUNTIME_CONSUMER_DEPLOYED_READY`，否则 `BLOCKED:NEW_ONLY_V2_V2_RUNTIME_CONSUMER_NOT_DEPLOYED`、绝不进入 S3 PUT。这在 worker01 真 Job 经预期阻断检验 PASS。不能通过仅设置 `NEW_ONLY_PG_SOURCE_AUDIT=PASS` 假装 Consumer 已上线；旧 Writer Drift Guard 不动。

## 下一轮必须完成的闭环

1. **实际 Airflow Consumer v2 Runtime 升级与回归**：为已经运行的 Landing Discovery/Resolver 做独立可部署 runtime 镜像/代码 pin；验证 73、70 两个原 v1 Manifest 保持可识别、新 v2 16 header-only 测试 Manifest 能正确解析、非法 Contract 继续隔离；Claim 仍 `NO`，PostgreSQL 不变。
2. Consumer 升级且**真实 Live 验收**后，才能在新的版本化合同修订中将 `consumer_compatibility` 变为 `V2_RUNTIME_CONSUMER_DEPLOYED_READY` 并重建 digest，进行真实 v2 首次不可变发布测试。
3. 通过真正的新独立 `gh-<run_id>` NEW_ONLY Request 产生合法空辅助 CSV（**不能人为删除现有真实 CSV 冒充 Synthea 生成**），再次通过真实 S3+PG 历史 Source IDs 只读预审；以 v2 发布 18 object -> 全量 GET 校验 -> 最后 Manifest READY -> 独立 Discovery/Resolver + 18 GET -> 同 Batch 重放 SHA 完全相同。原 Main 手工 Workflow 若零行仍 `HOLD_V2_CONSUMER_REQUIRED`，在上述兼容性验证前不得解除。
4. Writer 版本化 Batch ID、事务内 Existing Target Drift、正向 PG ROLLBACK / COMMIT、Airflow Claim/Spark 自动新批处理尚未验收；`synthea-update-only` 和 `synthea-mix-data` 仍 DESIGN ONLY。

**状态：NEW_ONLY_V2_PUBLISHER_CODE=PASS，FAKE_S3_IMMUTABLE_UPLOAD_READBACK_REPLAY=PASS，REAL_WORKER01_FROZEN_CSV_V2_DRAFT=PASS，REAL_V2_S3_READY=NO，AIRFLOW_V2_RUNTIME=NOT_DEPLOYED，PG_DML=NO，TASK004=IN_PROGRESS。**
