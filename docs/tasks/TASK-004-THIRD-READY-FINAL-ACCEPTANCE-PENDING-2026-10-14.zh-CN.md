# TASK004 第三个 NEW_ONLY READY — 最终 Airflow Writer 验收待完成（2026-10-14 EDT）

> **CURRENT / 权威进度：第三个全新 READY 已正式发布并独立验证；真实 Airflow Writer KPO COMMIT 尚未执行。TASK004 = IN PROGRESS；TASK005 = ON HOLD。** 不得因发布 READY 而宣布最终验收完成。此文档不是 Final Closeout 或业务 COMMIT 证据。

## 第三个真正独立批次（切勿复用历史 COMMIT）

- **Batch ID:** `synthea-new-only-gh-38588671004`，源数据由 Synthea 在 worker01 独立生成。
- **源生成 GitHub Run:** [38588671004](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588671004)：Person **1** / Encounter **244**；真实 CSV v2 contract PASS。Runner 最后因拷贝的旧固定数量断言期待 812 而 FAILED，**失败发生在 S3 publish 前**；新源请求已保留。避免重新生成相同请求。
- **真实发布 / S3 不变性 Run:** [38588933989](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588933989) **SUCCESS**。复用同一个已生成源，不再生成新的 Synthea；`FRESH_S3_HISTORIC_SOURCE_IDS_ZERO_COLLISION=PASS`、`FRESH_PG_SOURCE_ID_ZERO_COLLISION=PASS`、`NEW_ONLY_V2_S3_PUBLISH=PASS`、`PUBLISH_MODE=PUBLISHED_NEW`、18/18 对象真实 S3 readback、原样 replay `PUBLISH_MODE=REUSE_EXISTING`、Manifest SHA 完全相同。
- **Manifest URI:** `s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38588671004/manifest.json`
- **Manifest SHA256:** `22b6c386b5c165e0c9cff3d3ce5fbae2115aee87b4761fc4c11fb43a2c4720b1`
- **READ-ONLY 集群、GitSync 和 DB 前置验收 Run:** [38589912611](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38589912611) **SUCCESS**；Runner 验收代码 feature branch `feature/task004-third-airflow-final-accept-20261014`。Kubernetes 三节点 Ready、Airflow paused 且 idle、无活跃 SparkApplication；真实 Scheduler GitSync 与 Healthcare Main 上的 14-Task DAG 字节一致，Writer KPO 仍固定镜像 digest `dd0b0483ec01b05f1d072d65c9ab728b563cb063da0705564f3a03e23160fd6c`、retries=0。

## 实际 PostgreSQL 独立 READ ONLY 基准（新批提交之前）

| 对象 | 独立实测 |
| --- | ---: |
| `cdm.person` | 207 |
| `cdm.visit_occurrence` | 21690 |
| `etl.person_id_map` | 207 |
| `etl.visit_occurrence_id_map` | 21690 |
| 所有 Claim | 2 |
| 第一批 `synthea-new-only-gh-38497355290` | COMPLETED、lease cleared |
| 第二批 `synthea-new-only-gh-38489944582` | COMPLETED、lease cleared |
| 第三批 Claim | **0（ABSENT）** |
| 第三批历史 Writer Ledger | **0** |
| 第三批 Stage | **0** |
| 第三批 Checkpoint | **0** |

**没有对前两批或第三批执行 PG 业务写入。** 两个已完成旧批继续永久禁止重复 Writer COMMIT。Source ID collision check 与 S3 READY replay 已通过，独立 PostgreSQL 只读快照证实新批尚未 Claim 或入库。

## 实际阻断及安全边界

- 空间独立部署许可 `dw-spark/task004-new-only-writer-commit` **不存在**。历史两个真实 COMMIT 的管理员凭据不得长期暴露；临时高权限凭据准备/自动下发方案在执行层未获安全许可，因此没有部署 Secret、没有启动带 `writer_commit:true` 的真实 DagRun，更没有业务 COMMIT。
- **Airflow DagRun ID：未生成；第三批 Spark：未运行；第三批 Writer KPO：未运行；第三批实际 COMMIT：NO；第三批端到端幂等性重放：未执行。** 不得以旧批次 completed skip、S3 READY 发布或只读 PASS 替代真正新批的 Writer 验收。
- 为避免不确定提交状态被盲目重试，除非凭据和安全边界明确得到允许，不启动第三批 Spark→Writer。**任何 COMMIT 调用后状态不明，都先独立 READ ONLY 查询 durable Claim/Stage/Checkpoint/映射/目标表，绝不直接重发 Writer。**

## 接手后只需继续的最终主线

1. 基于当时 Main 最新 SHA 重新核对上述 Batch 的 immutable S3 READY SHA、Claim ABSENT、源键 collision-free、DAG 暂停、无竞争 Spark；不要再生成 Synthea。
2. 仅在可获得**合规、临时、最小生命周期**的 KPO Writer Secret 配置时，使用以下**新**批次精确参数手工触发 Airflow `new_only_omop_consumer`：`batch_id=synthea-new-only-gh-38588671004`、上述 URI/SHA、`consumer_readonly=true`、`spark_processing=true`、`writer_commit=true`。DAG 应自动完成 Spark 1/244 → Handoff → Writer KPO → 单事务 COMMIT → 全字段 reconcile；不允许转而使用旧 Runner one-time COMMIT Workflow。
3. 在完全**独立新 PostgreSQL Session** 验证 Person **208**、Visit **21934**、双 Maps **208/21934**、Claim **3**、第三批 Claim COMPLETED + owner/lease cleared，Stage **1/244**、两个 VERIFIED Checkpoint、source-key 和 Person↔Visit FK 正确，两历史批不变。
4. 确定已提交且禁用/撤销临时 Secret 后，重新触发**同一个第三批**完全相同 conf，确认 Airflow completed skip，Spark/Writer 不执行，PG Before/After（含 Stage/Checkpoint/Claim/Map 证据）零变化，DAG 恢复 paused。
5. 只有所有证据和 Run/DagRun ID 均经核验并有 PR 合并 Main，才将 `TASK004=DONE`、`TASK005=READY`，补充正式 Final Closeout；否则保持 `TASK004=IN PROGRESS`、`TASK005=ON HOLD`。

## 运行与代码追踪

- 基础 Healthcare Main SHA（初始及真实只读验收确认）：`2d7e17cb593a7c2993be47174f8581e890ec4c32`。
- SelfRunner 主分支最初 SHA：`cfe2acde3005c868c20adbf8255f0e647c87a882`。本轮安全检测专用 Workflow 存在于 SelfRunner feature branch，**不是一条可当作真实 COMMIT 的正式历史记录**。
- 初次发布尝试 [38586185752](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38586185752) 因 GHCR pull 403 失败、无源/PG 写；第二尝试 [38588671004](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588671004) 源数据成功、固定 812 断言失败；最终 [38588933989](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38588933989) 成功并未重复生成源。
