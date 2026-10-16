# Synthea NEW_ONLY — 真实源 ID 防撞及版本化发布前验收（2026-10-13）

> **NEW_ONLY V2 CONTRACT/PREPUBLISH READONLY = PASS；NEW_ONLY S3 READY = NOT YET；DYNAMIC PG ROLLBACK/COMMIT = NOT YET。** 真实生成输入为持久化 `synthea-new-only-gh-38484300008`，没有重新生成患者，也没有改变历史 V1 Consumer、PG Writer 或 Drift Gate。本验收只证明对**审计当时已存在**的 S3/PG Source ID 无冲突，不代表占有未来的全局唯一锁，也绝不是 COMMIT 许可。

## 证据与主线

- Healthcare 业务 [PR #89](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/89)，精确验收源码 SHA `70a5e6f19db0b5dad8046b6586863b43d8ceb9a2`，合并 Main `c791f2608b5e0a5cd27388a07ed6e16dda6e78c4`。
- Self-Runner [PR #81](https://github.com/JohnZhang-DataForge/Self-Runner/pull/81) 合并 SHA `d7a33d09aeb004538cdd2160916ff94083455a31`。
- 真 Kubernetes/S3/PG READ-ONLY acceptance：[Run 38486092750](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38486092750) 全部 Steps SUCCESS；10+ 现有/新增测试随完整 `tests/synthea_new_only` 测试套件 PASS，精确 Repo SHA Gate PASS。
- 首轮 [Run 38485618932](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38485618932) 没有进入 Source ID 查询：本地辅助 `claims_transactions.csv` 超过错误的 64MiB 人工安全限制，真实 Job `BLOCKED:LOCAL_CSV_SIZE_claims_transactions.csv`，S3/PG 都未改；只读诊断 Run `38486000559` 揭示原因。随后改为**流式 CSV 读取 + 分块 SHA256**，第二轮真实验收 PASS；同一问题失败数 1，未超过三次。

## 真实核验对象

```text
SOURCE_BATCH=synthea-new-only-gh-38484300008
REAL_PERSON_ROWS=73
REAL_ENCOUNTER_ROWS=12159
CSV_FILE_INVENTORY=18/18
V2_OPTIONAL_ZERO_ROW_FILES=0
HISTORICAL_S3_SOURCE_CSV_FILES_SCANNED=14
HISTORICAL_S3_PERSON_COLLISIONS=0
HISTORICAL_S3_VISIT_COLLISIONS=0
POSTGRES_EXISTING_PERSON_MAP_KEYS=136
POSTGRES_EXISTING_VISIT_MAP_KEYS=9391
NEW_ONLY_PERSON_EXISTING_TARGET_OVERLAP=0
NEW_ONLY_VISIT_EXISTING_TARGET_OVERLAP=0
NEW_ONLY_PG_SOURCE_ID_READONLY_GATE=PASS
NEW_ONLY_REAL_S3_HISTORIC_READONLY_GATE=PASS
S3_MUTATION=NO
POSTGRESQL_MUTATION=NO
MANIFEST_READY=NO
```

- **Kubernetes/LocalPath**：直接在 worker01 上临时 read-only Pod 挂载现存 `dw-synthea/synthea-new-only-state` PVC，读取该 request 保存的 18 CSV，没有启动独立 Generator 或重新抽取随机 Seed。
- **SeaweedFS**：只读分页扫描 `source=synthea/source_version=v3.3.0/` 下历史 Person/Encounter CSV（包括无 READY Manifest 的已存在数据，只要有匹配文件），对既有 verified Manifest 指定文件做 SHA256 比对；总共读取 14 个历史 Source CSV，当前 73 Person、12159 Encounter 未碰撞。
- **PostgreSQL**：真实 `BEGIN TRANSACTION READ ONLY`，查询 `etl.person_id_map` / `etl.visit_occurrence_id_map` 已存在 Synthea source keys，以 `md5()` 等值摘要在临时 Runner 环境和本次 source ID 哈希比对；同时核查该 Batch 历史 Ledger 和 Claim 为 0。汇总历史 Person keys 136、Visit keys 9391，Person/Visit overlap=0。哈希比对仅是审计预警，不是事务内 exact-source-key fencing；**Writer Existing Target Drift 仍保持完整，后续真实 COMMIT 必须重新精确核验源键和 Claim 状态。**
- 日志只输出计数与 PASS/FAIL；Kubernetes 临时 Job/ConfigMap 清理，无源身份明文随 Artifact 上传。

## 新业务 Contract 及安全边界

- 新增 **`contracts/synthea/new-only/csv-contract-v2.json`**：保留 V1 的全部 18 个 filename 和精确 header；对未来小人口仅要求 `patients` / `encounters` 必须有数据、其他辅助 CSV 可以仅有 Header。该 Contract 显式标 `consumer_compatibility=NOT_YET_DEPLOYED_DO_NOT_PUBLISH_READY`；**没有**动旧 v1 `require_nonempty_data_rows=true`。
- 新增 `apps/synthea/new_only/prepublish_gate.py`：本地 CSV 严格校验/Source Key 唯一性/FK/流式 SHA256，历史 S3 源键防撞、不可覆盖既有 Batch 前缀的只读检查；没有 S3 PUT、Writer COMMIT 或 Airflow 调用。
- 新增 `tests/synthea_new_only/test_prepublish_gate.py`：允许辅助零行、拒绝 Person 重复、Encounter orphan、历史 S3 撞车、校验和漂移等负例。旧历史文件/测试/Worker 任务均不修改。
- **重要发现**：这次固定 73 Person 批次所有 18 CSV 都存在非空数据行，因此**有希望直接沿用已经验收的 V1 Landing Manifest/Publisher/Resolver**，避免此刻升级已运行的 v1 Consumer；后续实际调用 v1 validator 仍需现场验收。未来新批次出现零行辅助表时必须用正式 v2 Consumer 升级并独立验收，不能以当前批次的幸运结果替代。

## 下一有界闭环（尚未执行）

1. 以同一冻结参数、同一 PVC CSV 在 `dw-synthea/worker01` 调用现有已验证 **V1** 18-CSV 严格 Validator（所有表非空、实际 73 人、SHA 不变）；保留额外 NEW_ONLY Request 追溯信息，避免手工重写参数。
2. 独立于 Airflow 使用 NEW_ONLY 功能命名的 publisher runtime，基于已验证 S3 协议 **先 PUT payload，完整 SHA readback，最后 immutable manifest.json**，选择和已冻结 request 一致的 ingest date；重放只能复用相同 Manifest，冲突必须拒绝。真正 PUT 前再次确认历史源键/Batch identity 无漂移。
3. 真实 S3 GET Manifest SHA/18 个文件 readback，并运行现有 v1 resolver/discovery 验收；证明 Airflow 可只读发现但 **Claim ENABLE=NO / 不自动 COMMIT**。若 v1 validator 对本批次阻断，则安全停止，转而实施严格版本化 Consumer，不强行修改旧 v1。
4. 专用 NEW_ONLY 最终镜像 Digest 构建/固定仍待完成；当前新 Generator 仍是独立 Job 和业务 Python，使用旧 pinned Synthea base image + 新代码 ConfigMap，后续再转移到独立发行镜像。

**TASK004 IN PROGRESS；TASK005 ON HOLD。**
