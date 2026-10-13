# Synthea NEW_ONLY — worker01 独立生成与 PVC 持久化真实验收（2026-10-13）

> **CURRENT NEW_ONLY LOCAL GENERATOR = PASS；INDEPENDENT S3 READY PUBLISH = NOT DONE；GLOBAL HISTORICAL SOURCE-ID COLLISION GATE = NOT DONE；DYNAMIC POSTGRESQL COMMIT = NOT DONE。** 本文是冻结的真实验收事实，不把某个 K8s Job 成功当成整个 TASK004 完成。

## 1. Git / Self-Runner 权威证据

- Healthcare [PR #87](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/87)：经过 Self-Runner 验收的业务源码精确 SHA：`fb06d225e30c6d8ca0e58e91e0ed23bd02903af6`；Squash merge Main：`46a69f5e4a1f310e73e325ea27e676e9de10d2ab`。
- Self-Runner [PR #80](https://github.com/JohnZhang-DataForge/Self-Runner/pull/80)：合并 Main：`576ee1f19ed19b2c55b2e300e442e8415bad7756`。
- [Storage Config 只读 Run 38483753849](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38483753849)：`storageClassConfigs.synthea-local.nodePathMap.worker01 = /data/synthea`；worker02/03 空；`dw-synthea-s3-secret` 已存在；之前尚无 `synthea-local` StorageClass。
- [真正 NEW_ONLY Live Run 38484300008](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38484300008)：所有 Workflow Steps / Job SUCCESS、8 个 unit tests PASS。首轮 Run 38484228948 仅因新 unit test 的 sample request ID 过短而 FAIL，已修复后重新验收；**两轮，未超过 3 次**。
- 本文档是在业务合并后新增；`38484300008` 绑定的是合并前 PR SHA，未额外声称运行了 post-merge 主线的新批次。

## 2. LocalPath Retain 存储真实状态

- 新 Kubernetes StorageClass `synthea-local`：provisioner `rancher.io/local-path`，`Retain`，`WaitForFirstConsumer`。
- 专用 PVC：`dw-synthea/synthea-new-only-state`，`ReadWriteOnce`，申请 `5Gi`，已 `Bound`。
- PVC 绑定 PV 位于 `/data/synthea/` 下，nodeAffinity 包含 `worker01`；没有复用 SeaweedFS / PostgreSQL 旧 PV。
- worker01 专用短期 Job 写入持久化 sentinel，PV/PVC 真 readback 与下一 Pod 读取同一 PVC 的数据成功；未删除 PVC/PV/StorageClass。
- **存储边界**：LocalPath request size 不一定强制磁盘 quota；虽然路径经 PV 证实位于 `/data/synthea/`，并未审计底层独立物理设备 ID、实际 free bytes 或备份。Retain 不是备份。不得声称已有跨 worker 恢复能力。

## 3. 真正 NEW_ONLY 生成记录

```text
GENERATION_REQUEST_ID=gh-38484300008
BATCH_ID=synthea-new-only-gh-38484300008
NEW_ONLY_GENERATION=PASS
PERSON_ROWS=73
ENCOUNTER_ROWS=12159
CSV_INVENTORY=18/18
CSV_LOCAL_PERSISTENCE=PASS
NEW_ONLY_REAL_LOCAL_GENERATION=PASS
NEW_ONLY_REPLAY=REUSED_FIXED_REQUEST
NEW_ONLY_REPLAY_AND_PERSISTENCE=PASS
LANDING_S3_READY=NO
POSTGRESQL_MUTATION=NO
```

- Kubernetes NEW_ONLY 独立短生命周期 Job/Pod 在 worker01 调用真实 **Synthea v3.3.0** JAR，随机选用有效美国州、目标人数 1..100、独立随机 Seed/Clinician Seed，以请求创建时 UTC 日期冻结 reference/end date，CLI `-o false` 禁止人口 overflow，读回实际 Person 限制 1..100。
- 请求状态在 `/synthea-state/new-only/requests/gh-38484300008/`。`params.json` 采用同目录临时文件 fsync + hardlink 原子首次发布；请求锁防并发，重复 request ID 不重新随机化。
- CSV 本地校验 **18 个现有文件名和精确 header、每行列数、Person source ID 内部唯一、Visit 对 Person 引用、至少一个 Encounter**；低人口允许某些辅助 CSV 零行，是本地 NEW_ONLY 专用 validation boundary，不是历史 `require_nonempty_data_rows=true` 的 V1 Landing Contract。
- PVC 内 NEW_ONLY Local Registry 保存 Person Source ID 摘要以阻止**已在这个 Registry 内登记的其他 NEW_ONLY 请求**重用源 ID；**还没有**对 PostgreSQL 现有 source map 和历史 SeaweedFS S3 所有已入库 Batch 做权威全局碰撞核对；因此本批目前**不能视作可写入 OMOP 的新 Source ID Batch**。
- 第二个新 Pod 重用同一个 request ID，验证固定 params、完整 CSV 和 registry ID hashes，返回 `REUSED_FIXED_REQUEST`。**不是重新生成 73 人**。
- 发布/运行时镜像状态：仓库包含独立 `images/synthea-new-only/Dockerfile`，但本次实际 Job 为同一业务源码通过 ConfigMap 挂载到**已验证的旧 pinned Synthea base image**；尚未构建、发布或验证 NEW_ONLY 专用最终镜像 Digest。不能把模板已写入当成独立镜像已投产。

## 4. 本轮新增文件

```text
apps/synthea/new_only/generate_new_only.py
images/synthea-new-only/Dockerfile
kubernetes/manifests/synthea/new-only/storageclass.yaml
kubernetes/manifests/synthea/new-only/pvc.yaml
kubernetes/manifests/synthea/new-only/job.yaml.tpl
tests/synthea_new_only/test_generator.py
```

旧历史 Airflow generate_publish、Writer Existing Target Drift、Claim 等均未改变。实际本轮无 S3 PUT、未触发 Airflow、未连接或写入 PostgreSQL。Self-Runner 的操作只持久增加专用 StorageClass/PVC/PV 和新生成的本地 Synthea 数据，临时 Job/ConfigMap 在成功验收后清理。

## 5. 真正完整 NEW_ONLY Producer 所需的 NEXT

1. **Versioned NEW_ONLY Landing Contract**：处理小人口造成零行辅助 CSV 的差异，同时保持 18 CSV、header、checksum 和 Consumer 的显式版本兼容；不能修改历史 V1 Contract 来放宽旧数据。
2. **全局 NEW_ONLY 身份核验**：只读查真实 PostgreSQL existing source mapping、历史 READY 批次的 Source IDs；一旦冲突，BLOCKED；保持 Writer `BLOCKED:EXISTING_TARGET_DRIFT` 不变。
3. **专用 Generator 镜像**：构建/推送独立 `synthea-new-only` 镜像并固定 Digest，启动用它，而不是长期依赖历史 pinned image + 临时 ConfigMap。
4. **真正 S3 immutable verified Manifest**：明确 `generation_mode=NEW_ONLY`、`generation_request_id` 与固定 params，先 PUT 各 CSV、按 SHA 独立 GET readback，最后发布 immutable `manifest.json`，重放不能覆盖/换参。用 Self-Runner 实测一批 READY；Airflow 完全不负责触发生成。
5. **Writer 兼容和完整 TASK004**：显式版本化支持 `synthea-new-only-` Batch ID；安全 Person→Visit ROLLBACK 正例、Active Claim Fencing 后独立授权 Dynamic PG COMMIT、DB Reconciliation 和幂等自动消费。此前不开始 TASK005。

**阶段判断：NEW_ONLY Local Generator 已经真实可运行并写入专用 LocalPath；完整独立 Producer（全局防碰撞 + immutable S3 READY）仍 IN PROGRESS；TASK004 IN PROGRESS / TASK005 ON HOLD。**
