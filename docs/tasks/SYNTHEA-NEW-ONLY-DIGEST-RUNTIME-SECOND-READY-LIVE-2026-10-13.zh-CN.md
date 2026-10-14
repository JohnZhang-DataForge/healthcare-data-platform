# Synthea NEW_ONLY — 独立 Digest 镜像、第二个真实新批和手工新 Request 工作流（2026-10-13 EDT / 2026-10-14 UTC）

> **NEW_ONLY DEDICATED IMAGE BUILD/PUSH = LIVE PASS；第二个独立 Request → LocalPath 生成 → S3 首次发布 → 18 CSV 校验回读 → Manifest 重放 = REAL PASS。** 本报告是本轮真实证据；不宣称 Airflow 自动 Claim/Spark/OMOP PostgreSQL COMMIT 已完成。版本化 v2 对辅助零行 CSV 的消费支持**仍未启用**。TASK004 IN PROGRESS；TASK005 ON HOLD。

## 权威仓库及验收

- Healthcare 源码 [PR #96](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/96)，受控镜像实际源码 feature SHA `605ac22c5adcc37e78b714784fd92fc340fbf09b`；合并主线 `bef856c474a783ea8a1e5b23d96b512b9a7dd69e`。
- Self-Runner [PR #85](https://github.com/JohnZhang-DataForge/Self-Runner/pull/85)，合并主线 `05df669f6ddf390b296a21af51379bad3cebb833`。
- 镜像真实构建/发布：[Run 38489695549](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38489695549) 27 tests PASS，首个专用 image push PASS；修复动态验收后：[Run 38490227474](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38490227474) **29 tests PASS**、重新 Docker build/smoke/push 完整 SUCCESS。
- 修正版最终实际 GHCR digest：
  ```text
  ghcr.io/johnzhang-dataforge/healthcare-synthea-new-only@sha256:36b69a26f25f9b627da693fc1aa70b8d0a37de0af755bcb7d95d140568efa909
  ```
  不是虚构的 tag：GitHub-hosted Docker 构建完成、`docker push` 成功后由 Docker 真实 `RepoDigests` 返回。基于历史 pinned v3.3.0 Synthea base image，内建代码和 v1/v2 两套完整 CSV Contract；没有重新编译 Synthea Java、没有改旧 Runtime 镜像。
- 本轮集群首次完整 new request: [Run 38489944582](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38489944582)：在 worker01 成功 pull 正式 digest、生成并持久保留真实 NEW_ONLY 第二批；真实 S3/PG source audit PASS、旧 v1 strict Validator PASS、真实 S3 PUBLISHED_NEW 和 18 文件 SHA readback PASS；**此 Run 最后 verify step FAILURE**，原因是 `verify_v1_ready.py` 当时错误地硬编码了上一个 73 Person / 12159 Encounter 的验收数字，第二批实际为 70 / 11487。该失败不能抹去已完成的真正 S3 发布。
- 对上述已发布批次修复后做**恢复验证，不重新生成，也不再次新发布**：[Run 38490367050](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38490367050) SUCCESS，`NEW_ONLY_NEW_70_PERSON_REAL_S3_READBACK=PASS`、`NEW_ONLY_NEW_70_PERSON_IMMUTABLE_REPLAY=PASS`、`NEW_ONLY_FRESH_NEW_REQUEST_LIFECYCLE=PASS`。`PUBLISH_MODE=REUSE_EXISTING`，前/后 Manifest SHA 完全相同，读回 18/18。
- 首轮 Kubernetes 工作流 [Run 38489870801](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38489870801) 在 Pod 创建前被过宽 YAML 注释模板检查拦住；已明确修复。累计两次实际测试问题（注释检查、验收器硬编码）后恢复 PASS；未超过三次未成功测试上限。

## 第二个真实 NEW_ONLY READY

```text
generation_request_id=gh-38489944582
batch_id=synthea-new-only-gh-38489944582
person_rows=70
encounter_rows=11487
csv_file_count=18/18
strict_v1_all_csv_nonempty=YES
historical_s3_source_collision=0
historical_postgres_source_collision=0
manifest_uri=s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38489944582/manifest.json
manifest_sha256=be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256
first_publish=PUBLISHED_NEW
subsequent_replay=REUSE_EXISTING
source_pvc=dw-synthea/synthea-new-only-state (Retain, worker01)
postgres_mutation=NO
airflow_claim_change=NO
```

至此还有此前已验收的第一个 READY Batch `synthea-new-only-gh-38484300008`（Person 73 / Encounter 12159），其 Manifest SHA `66b6e79cee03b1c4acdc6b7dc9ca07288fef658d7cf6b4f978e04dde2102baa9`；这两个均是真实数据，不能合并或覆盖，保留各自不变 Manifest 和生成参数。

## 正式新 Request 触发方式

- Self-Runner Main 已安装 `.github/workflows/synthea-new-only-run-new-request.yml`（名称 `Synthea NEW_ONLY - Run New Independent Request`），可由 GitHub Actions **Run workflow 手工触发**；默认使用唯一 `gh-$GITHUB_RUN_ID` 请求身份，无需编辑 Shell 或手工配置 Seed/人口/州/日期。
- 该 Workflow 使用上述独立代码 SHA + 真实 digest，在 `dw-synthea/worker01` 调用独立 Job：生成（PVC 可写、无 S3 凭据）→ 预发布 S3 身份只读审计 → PostgreSQL `READ ONLY` 历史 Person/Visit Key + Ledger 防撞 → 严格 v1 validate → 不可变 S3 发布 → 原有 v1 Discovery/Resolver readback → replay。各阶段短命 Job 清理，PVC/PV 和已发布原始数据保留。
- 新镜像的 `entrypoint.py` 支持 `generate`、`prepublish`、`validate`、`publish`、`replay`、`verify`，**仅属于 NEW_ONLY 单一业务系统的生命周期分阶段**，不是一个 Generator 通过模式开关实现 NEW_ONLY / UPDATE_ONLY / MIX_DATA。后两种模式 DESIGN ONLY。
- GHCR 新 Package 在集群 Job 使用临时 `imagePullSecrets`（来自该 Actions 权限范围）成功拉取，Job 完成删除该 Secret；未假设 package public，也未永久保留临时 Actions Token。未来从其他调度器自动调用需提供独立持久可用的镜像拉取身份或发布 Package visibility 管理，不能假设短命 token 跨 Run 永久有效。
- **重要区分**：手工 `workflow_dispatch` 文件已入 Main，但没有在本次提交后单独点 Run workflow 再启动第三个新 Request；已真实测试的是它基于的逻辑在 feature Runner 上生产了第二个 Request，并在修正版 digest 做了 recovery + replay。不能虚报 manual dispatch 已验收。
- **安全分叉**：Synthea 合法的 1～100 人随机批次，部分辅助 CSV 可能仅有表头。此时独立 Generator 的 LocalPath 生产仍可完成；必须返回 `HOLD_V2_CONSUMER_REQUIRED` / `S3_NEW_READY_PUBLISHED=NO`。新版 `csv-contract-v2` 是设计/本地校验边界，**尚未有 v2 Landing Consumer 真实部署测试**，绝对不能放松旧 v1 18 文件都非空的规则。

## 下一步与安全待办

1. **需要真实运行日常工作流**：下一 Session 可以从 Self-Runner Main 的 `Synthea NEW_ONLY - Run New Independent Request` 手工触发第一个 Main Workflow 测试，验证 GitHub UI 工作流对每个新 `gh-<run_id>` 的完整效果；若出现合法空表必须 HOLD，不是发布失败逃避合同。
2. **v2 Consumer 支持**：正式版本化处理辅助 CSV 合法零行情况，否则不能承诺每次随机 1～100 人都可发布 READY；旧 v1 Consumer/Writer 不能粗暴改成接受任何 v2。
3. **发布安全加强**：当前 S3/PG source-key check 是在发布时间点的只读预审，绝非事务级锁；写入目标 PostgreSQL 前，必须在受控事务内重新核验 Source ID、活跃 Claim/Owner、幂等重放/变更与 Existing Target Drift Gate；`NEW_ONLY_READONLY_SOURCE_AUDIT=PASS` 标志只是独立 Runner 审查链的阶段标记，不能当作 PostgreSQL COMMIT 授权。规范最小权限 S3 凭据及持久镜像 pull 身份也需要后续配置。
4. Airflow 新批次真实定时读取/Claim/Spark/OMOP Writer ROLLBACK 正例和可控 COMMIT 尚待单独开发/验收；OpenLineage/Marquez 属并行范围，不能误当成此 Generator 已完成的部分。TASK004 IN PROGRESS、TASK005 ON HOLD。

**状态：NEW_ONLY_IMAGE_PUBLISHED=PASS；NEW_ONLY_FRESH_BATCH_REAL_S3_READY=PASS；NEW_ONLY_IMMUTABLE_REPLAY=PASS；MANUAL_DISPATCH_AFTER_MERGE=NOT_YET_LIVE_TESTED；ARBITRARY_LOW_POP_V2_READY=NOT_IMPLEMENTED；POSTGRES_DYNAMIC_COMMIT=OFF。**
