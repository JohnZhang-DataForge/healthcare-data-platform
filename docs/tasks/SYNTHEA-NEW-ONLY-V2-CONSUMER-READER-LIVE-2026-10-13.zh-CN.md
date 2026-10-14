# NEW_ONLY v2 Consumer Reader — 严格空辅助表兼容验收（2026-10-13 EDT / 2026-10-14 UTC）

> **新版 v2 Manifest Reader 合同、33 个自动测试、构建发布新镜像、真实 worker01 上原有两个 v1 READY 的回归验证均 PASS。** 本轮**没有**把 v2 Publisher 或运行中的 Airflow Consumer 升级/启用，也没有向 S3 发布新的 v2 READY Manifest。TASK004 IN PROGRESS，TASK005 ON HOLD。

## 权威源码、实际测试和 digest

- Healthcare [PR #100](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/100) squash 合并 Main SHA `0e3fb4dc6f608766583e30dd17f9814b63365102`（实测源 SHA `63a5c209d91783db9123b8cad1083e7b71ff287a`）。
- Self-Runner [PR #87](https://github.com/JohnZhang-DataForge/Self-Runner/pull/87) squash 合并 Main SHA `25e013728946d05efe0192922ab9ea8a975690a2`。
- **真实 [Self-Runner Run 38491626783](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38491626783) SUCCESS**：GitHub-hosted 33 NEW_ONLY tests PASS / Docker image smoke PASS / GHCR push PASS；worker01 `dw-synthea` 新 image 拉取与两个已有 v1 S3 Batch 的 18/18 SHA256 GET readback 均 PASS。没有 S3 PUT 或 DB DML。
- 本轮实际发布的严格 v2 Reader + 历史 v1 Reader 共存镜像：
```text
ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:d53a706feba8aff30375836f84c9228d22e61aa35578349b01ddcb1b5d532350
```

## 版本化隔离的设计（已进 Main）

- `apps/task004/validate_new_only_v2_manifest.py` 为独立 v2 合同入口；原有 `apps/task004/resolve_verified_landing_file.py` 只新增 `manifest_version == "2.0"` 时显式委托新校验器，**其原有 v1 校验流程保持原样**。现有 `apps/landing_discovery/scan_ready_batches.py` 复用共同 Resolver，因此使用新源码/镜像的扫描器能够按精确版本识别，其他版本拒绝。
- v2 Batch ID 强制 `synthea-new-only-<request_id>`，且 `source_parameters.generation_mode=NEW_ONLY` 与请求 ID 必须一致；`synthea-update-only-`、`synthea-mix-data-`、历史 `task004-airflow-` 无权冒充 v2。
- 18 CSV 路径、filename、dataset 和 **每个 header** 必须与打包的 `contracts/synthea/new-only/csv-contract-v2.json` 完全一致；Manifest `contract.path` 和 SHA256 必须精确吻合。Person 和 Encounter `row_count >= 1`，仅其他 16 个辅助 CSV 允许 `row_count = 0`；即使仅表头，文件大小也必须大于 0；所有文件都必须带合法 SHA256。
- 检查 `manifest_version=2.0`、`INTAKE_VERIFIED`、完整 S3 URI lineage、`source_provenance` 固定 Synthea `v3.3.0` + commit `995cf2fd33e67918d4e33110d9f68ad248002221`、Manifest `payload_fingerprint` 与 18 文件 SHA、`verification.s3_readback=PASS` + 18 文件计数。
- `tests/synthea_new_only/test_v2_consumer.py` 使用 1 Person/1 Encounter、16 header-only 辅助表的**合成测试固定数据**校验 Manifest v2 / Resolver / Discovery，测试拒绝 16 组安全负例和 v1 零行负例；这属于**单元测试**，不是一个真实 Synthea 生成/实际 S3 已发布的 v2 批次。
- `images/synthea-new-only/Dockerfile` 同时携带 v1 解析器和 v2 校验器；更新后的 digest 已经在 worker01 上从真正 SeaweedFS 重新验证：
  - `synthea-new-only-gh-38484300008` 73 Person / 12159 Encounter，完整 SHA256 readback PASS；
  - `synthea-new-only-gh-38489944582` 70 Person / 11487 Encounter，完整 SHA256 readback PASS。
- 该 Runner 没有修改运行中的 Airflow/KPO 镜像，没有 Claim、Writer Plan、PG ledger 或 OMOP 写操作，没有生成新 Synthea 批次。

## 下一个必须完成的安全闭环

1. **NEW_ONLY v2 专用 Publisher**：为合法零辅助表生成独立 `manifest_version=2.0` 的本地 Draft，必须从已冻结且重新核验的 NEW_ONLY 参数/CSV 构建，18 个 CSV 逐文件 SHA256 GET 全量验证后才不可变 PUT `manifest.json`，严格失败处理/重放复用；不得给既有 `publish_synthea_landing.py` 放宽 v1 `row_count > 0` 的硬门槛。
2. **真实 v2 生成测试**：使用新的独立 1..100 Synthea Request（不能伪造真实数据）；只有真实批次出现合法零辅助表才使用 v2 Publisher，否则 v1 继续有效。不能使用人为删除已有真实批次数据冒充 Generator 成功。对新 Request 再做 S3 + PG Source ID 只读碰撞预审，真实 v2 Manifest S3 PUT/readback + Discovery + Replay 全部 PASS 才可称 v2 Landing DONE。
3. **运行环境启用**：将真正运行 Airflow Discovery/Resolver 的 Consumer 镜像升级到通过验证的版本，验证 GitSync DAG/run、V1 & V2 分类/严格拒绝/Claim=NO；当前将仅源码与独立 NEW_ONLY 镜像准备好，不代表 Airflow Consumer 已升级。
4. **Main Manual Workflow**：Self-Runner Main `Synthea NEW_ONLY - Run New Independent Request` 已可见，但 Main `workflow_dispatch` 未单独触发验收；其原有代码对合法空表返回 `HOLD_V2_CONSUMER_REQUIRED`（不能认为是一份 READY）。在 v2 Publisher 与实际 Consumer 未同时验证前不要改成自动批准 v2。
5. Writer 旧 Batch ID / `BLOCKED:EXISTING_TARGET_DRIFT` 完全保留；Claim/Spark/PG ROLLBACK 正例、事务内 fencing、幂等 COMMIT 均属独立下一阶段。UPDATE_ONLY、MIX_DATA 未实现；TASK004 仍 IN PROGRESS，TASK005 ON HOLD。

**状态：V2_READER_CODE_AND_IMAGE=REAL_PASS；V1_REAL_BACKWARD_COMPATIBILITY=REAL_PASS；V2_SYNTHETIC_HEADER_ONLY_TESTS=PASS；V2_REAL_S3_READY=NO；AIRFLOW_CONSUMER_V2_DEPLOYED=NO；POSTGRESQL_MUTATION=NO。**
