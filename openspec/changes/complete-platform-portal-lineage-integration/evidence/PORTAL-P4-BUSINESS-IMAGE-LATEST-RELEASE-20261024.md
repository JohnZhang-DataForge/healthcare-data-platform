# Portal P4 — 实际 NEW_ONLY 三业务 Spark Listener、单镜像 Latest Release（2026-10-24）

> **已验证（代码 / 镜像）：** P4 Person / Visit / Reconcile 三个实际 SparkApplication 模板 OpenLineage 配置通过负向合同 CI，并被成功打入已有 NEW_ONLY `landing-processing-v2` 单一子镜像；GHCR 最新 Digest 与回退版本真实 Push + 独立 Pull 验证。**尚未验证（业务）：** Kubernetes 新控制 Pod 的实际 imageID、真实 Person/Visit/Reconcile SparkApplication、S3A Dataset edges、Airflow↔Spark parent、Writer COMMIT/PG17 数据。镜像验证不等于 E2E。

## 1. Main 合并及源代码定位

- Healthcare [PR #441](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/441)，Squash Main `9199710bf5f43d506628fa31f81cb2b107a55c11`，最终测试 HEAD `7ee1066d1c16792d079c949ea9ee700e7edb22b8`。
- OpenLineage 在真正三个 SparkApplication 模板注入，不修改 PySpark 业务算法、Airflow 14 Task / XCom、Claim / Fencing / Writer、S3 身份与权限；命名空间 `healthcare-platform-spark-business`，`spark.openlineage.appName=__APP_NAME__`，Listener `1.47.1`，Marquez private HTTP。
- 模板路径：`local-data-platform/spark/manifests/task002/person-canonical-adapter.yaml.tpl`、`task003/encounter-canonical-adapter.yaml.tpl`、`task004/person-visit-reconciliation.yaml.tpl`。
- `local-data-platform/images/landing-processing-runtime/Dockerfile` **只覆盖父镜像内三个实际模板**。其余七镜像及原基础 `task004-runtime` `:latest` 未被本轮重新发布。
- P4 GitHub Hosted [Listener CI](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/workflows/portal-p4-business-spark-static.yml) 的实际 PR 检查和源码闭包 PASS；原 TASK004 Offline/Synthea Smoke、OpenSpec/Docs 全部绿灯。

## 2. 真实单镜像构建、Push、Rollback 和 GHCR readback

- [GitHub Actions Run **#40123946926**](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40123946926)，固定源 `9199710bf5f43d506628fa31f81cb2b107a55c11`，只针对 `landing-processing-v2` 发布的**一次性限定分支测试发布流程**；无普通 Main Push 自动构建八镜像。Workflow **SUCCESS**。
- GHCR Package：`ghcr.io/johnzhang-dataforge/healthcare-data-platform-local-dp-landing-processing-v2`。
- 原 Parent：`healthcare-data-platform-task004-runtime` 现有 `:latest` 先 Pull 并用 RepoDigest 固定为 Docker build 的 Base；**没有重建/推送 Parent**。
- 单一新镜像：`git-9199710bf5f43d506628fa31f81cb2b107a55c11-run40123946926-a1`，Digest `sha256:f735f6088efad7f0f0b6f2a4d2540ecfa5195925cda719cfc0c17c5e78a21f37`。
- 旧 `:latest` Digest：`sha256:93adcaeefc5c29f87e3fca212e20faaebbaad99b23c7a8fe0fb5ebe5636331ba`，已以 `pre-latest-run40123946926-a1` 显式 Push，并验证 Digest 一致。
- 新 `:latest`：`sha256:f735f6088efad7f0f0b6f2a4d2540ecfa5195925cda719cfc0c17c5e78a21f37`。仓库 push 后删除本地 latest 标签并重新 `docker pull`，RepoDigest 读回精确相同。
- Logs：`P4_ONE_EXISTING_CHILD_IMAGE_CLEAN_BUILD=PASS`、`P4_ACTUAL_PACKAGED_THREE_SPARK_LISTENERS=PASS`、`P4_IMMUTABLE_NEW_IMAGE_PUBLISHED=PASS`、`P4_PREVIOUS_LATEST_IMMUTABLE_BACKUP=PASS`、`P4_SINGLE_IMAGE_LATEST_REGISTRY_READBACK=PASS`。
- rollback：将本次 old `pre-latest-run40123946926-a1` 指向旧 `latest` 即可恢复**新建 Pod**的旧镜像；不会自动替换已运行 Pod。不得声称源码回退会逆转任何已经写出的 S3/PG 数据。

## 3. 下一个真实业务 Gate（P4 5.3 / P2 3.3）

1. 先确认 Airflow GitSync Main、实际 Scheduler/Task OpenLineage、当前 Live Activity、精确 S3 READY Batch/PG Ledger ABSENT；必要时生成新 Synthetic READY，不盲选历史 COMMITTED 或 FAILED Batch。
2. 受控触发 `new_only_omop_consumer` **manual`consumer_readonly=true,spark_processing=true`，本轮先不设置 `writer_commit`**，从而 Spark Person/Visit/Reconcile 正常运行，Writer 保持原授权 HOLD。
3. 核对实际 KPO Control Pod `imageID` 对应新 Digest，及 Spark Driver/Executor per-job package/Listener 生效。由 Marquez API 读真实 Job/Run：Person/Visit 应各有实际 S3A 输入/输出 Dataset，Reconcile 应有两个输入 Dataset、**无新输出写入**；没有任何伪造的 parent/COMPLETE。
4. P5 才独立授权真实 Writer COMMIT 并用 PG17 Ledger + 表读回，再同批 SKIP/PG 零变化；不能因 P4 Spark 成功声称 COMMIT。

本轮只构建发布了上述一个镜像；至证据记录时，还未通过 P4 5.3，未重置 PG17、未清空 S3，也未凭 Spark 完成提交 Writer。
