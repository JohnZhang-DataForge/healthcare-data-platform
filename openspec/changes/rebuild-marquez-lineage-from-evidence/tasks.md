# Tasks — Rebuild Marquez lineage from evidence

## 1. Recovery inventory and provenance
- [x] 1.1 Reconfirm Marquez retention disabled, original PG14 volume still bound, historical metadata rows zero.
- [x] 1.2 Examine K8s backup/snapshot resource inventory, archived GitHub P5 evidence, SeaweedFS Filer named archive buckets and raw lineage prefixes.
- [x] 1.3 Record strict distinction between exact restored history and newly executed genuine events.

## 2. Bounded actual OpenLineage run
- [x] 2.1 Preflight existing Airflow `platform_portal_openlineage_probe` DAG and no-retention live config.
- [x] 2.2 Execute exactly one opt-in Airflow real two-task run with unique ID; no synthetic `/lineage` HTTP POST.
- [x] 2.3 Independently verify Marquez Job/Event counts and linked task records; report success or failure without rewriting historical proof.

Actual Airflow live evidence: [Self-Runner Run #41858128218](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41858128218), 2026-11-04 15:29 UTC: retention off, source SHA, no active DAG, true DagRun SUCCESS, Marquez PG14 counts Jobs 0→3, Lineage Events 0→6, Datasets 0→0. These are newly executed Airflow events, NOT recovered historical Patient/Encounter events.

## 3. Bounded real Spark fixture lineage (not historical Patient/Encounter)
- [x] 3.1 Preflight no active TASK004 Spark, the pinned local fixture, and permanent no-retention.
- [x] 3.2 Execute one isolated portal-a4 Spark probe with synthetic 3-row CSV, unique ConfigMap/PVC and no S3 or OMOP access.
- [x] 3.3 Verify genuine Spark Job/Event + Input CSV / Output Parquet Datasets are durably stored in Marquez; record exact run and PV.
- [x] 3.4 Do not label synthetic probe datasets as previously deleted Patient/Encounter lineage.

Actual Spark fixture: [Self-Runner #41858844788](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41858844788), 2026-11-04 15:34 UTC: 3-row synthetic input, isolated PVC `portal-a4-r41858844788-output`, SparkApplication `portal-a4-r41858844788` COMPLETED, PG14 Jobs 3→7, Datasets 0→2, Events 6→18. No S3, OMOP or Writer mutation. THIS IS NOT ORIGINAL OCTOBER PATIENT/ENCOUNTER HISTORY.

## 4. Future historical Patient/Encounter recovery
- [ ] 4.1 If original committed raw events / verified PG14 dump found, replay/restore in provenance-controlled fashion with independent readback.
- [x] 4.2 Rebuild Patient/Encounter graph only from actual new Spark execution or byte-exact old OpenLineage, under a separate stage gate; never re-run committed Writer.


## 5. New Patient / Encounter / Reconcile Spark-only regeneration (P3)
- [x] 5.1 Read-only live preflight: current SHAs, DAG GitSync, no-retention, active Airflow/Spark/Actions, READY Manifest identity and Claim/Ledger/Fence; record evidence and select only genuinely unclaimed input.
- [x] 5.2 Independently record protected PG17 OMOP state before running; verify source digest, no Writer COMMIT flag, exact manual DAG route and original pause state.
- [x] 5.3 Run exactly one uniquely identified real Patient + Encounter + Reconcile Spark-only flow under shared concurrency gate, without OMOP Writer or old Batch replay.
- [x] 5.4 Independently GET Marquez action-level Job/Run/Input+Output DatasetVersions, Reconcile's two exact inputs, column facets where real, and public read-only graph. Preserve START-only / missing facets.
- [x] 5.5 Independently read back PG17 and prove protected state unchanged; attach exact source SHA, workflow Run, actual Spark IDs, Airflow tasks, Marquez details and failures to evidence.
- [ ] 5.6 Run required CI, review and merge scope-limited PRs only after required gates pass; mark unexecuted/blocked tasks honestly.

**Status 2026-11-04:** this plan is not proof of business Spark execution or graph restoration. The verified 3-row portal P2 fixture remains separate from real Patient/Encounter.

### P3 live preflight evidence (new run; not historical recovery)

- [Self-Runner #41866921442](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41866921442) **SUCCESS**. Healthcare exact source `3d2c30486814e8a14151eefd7bec724e1c215b47`; Self-Runner source `a34e371acb4bb445820a168e98fc5fd613c923c3`.
- Marquez no `dbRetention`, no active SparkApplications, zero active Airflow TaskInstances and business DagRuns, installed three consumer DAG files match Healthcare Git SHA, original DAG paused=True.
- S3 inventory: READY 38, quarantined 1. Selected S3-validated immutable uncommitted input: `synthea-new-only-gh-40194178133` (2026-10-25, 18 files), manifest SHA256 `4617b030fec9eb6446a7672cf58db9a4b8364262af74e6d570bb421416f1a533`. PostgreSQL `landing_claim_worker` read-only check found zero Claim rows and zero Writer Ledger entries for this candidate.
- The new business Spark-only run [Self-Runner #41868276334](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41868276334) is separate. This preflight alone does **not** prove Patient/Encounter graph regeneration or OMOP unchanged post-run.


### P3 业务血缘重建真实验收（2026-11-04；新运行，不是旧 Run 精确恢复）

- **Source / Scope**：执行时 Healthcare 固定源码 commit `3d2c30486814e8a14151eefd7bec724e1c215b47`；Self-Runner [PR #506](https://github.com/JohnZhang-DataForge/Self-Runner/pull/506) 已合并（squash `a4fddfc91c1f07d0a94c0558e5d5539ce1d27b3b`）；实际 Spark 镜像 digest `sha256:42d6d087de4dfecf35c51bf84461fddea9635506ed73b6a59f7de8c44d8e775d`。批次 `synthea-new-only-gh-40194178133`，18 文件，Manifest SHA256 `4617b030fec9eb6446a7672cf58db9a4b8364262af74e6d570bb421416f1a533`。本次没有复原原始 10 月 Run UUID。
- **Live execution**：[Self-Runner Run #41868276334](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41868276334) 其 **GitHub workflow 原始结论 FAILURE 必须保留**：业务 `new_only_omop_consumer` DagRun `marquez-p3-spark-only-41868276334` 实际 `success`；`spark_patient`、`spark_encounter`、`spark_reconcile`、`prepare_writer_handoff`、`route_writer_authorization` 均 `success`；`execute_new_only_writer`、`writer_committed_verified` 均 `skipped`；DAG 原始 pause=True 已恢复。失败来自当时验证器将 `health-landing` 错查到 Dataset `name` 而非正确的 `namespace`，**非业务 Spark 失败**，无自动重跑。
- **Protected PG17 readback**：Run #41868276334 的事前/事后 `BEGIN READ ONLY` 精确行内容 MD5 均一致：`cdm.person` 1394、`cdm.visit_occurrence` 200556、`etl.landing_batch_ledger` 18、`etl.task004_batch_ledger` 19；该候选批次 Claim/Writer ledger 均 0。标记 `MARQUEZ_P3_PROTECTED_OMOP_FINGERPRINT_UNCHANGED=PASS`；不得将 Spark-only 写 Processing 误报为 OMOP 写入。
- **Independent API readback**：[Run #41869499368](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41869499368) PASS（初版证明图结构）；[Run #41923060868](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41923060868) PASS（修复严格命名空间/路径/版本校验）；[Run #41923297428](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41923297428) PASS（字段映射强断言，GET-only）。14 个同一业务窗口内的 Spark child Runs；Patient、Encounter 各有真正 `COMPLETED` 的 `adaptive_spark_plan.normalized_data` 子 Job，并含 Landing Input 与 Processing Output 的真实 `(namespace, name, version)`。Reconcile 的两条 input DatasetVersion 精确等于上述两个 Output DatasetVersion，**不只是路径模糊匹配**。
- **字段血缘**：直接查询 Marquez `/api/v1/namespaces/{namespace}/datasets/{dataset}` 的 `facets.columnLineage.fields`，而不是 Run Detail 的 `outputDatasetVersions[].facets`。Patient：18 个 Processing 字段，6 条真实映射（`Id→source_record_id`、`BIRTHDATE→birth_date`、`DEATHDATE→death_date`、`GENDER→gender_code`、`RACE→race_code`、`ETHNICITY→ethnicity_code`）；Encounter：27 个 Processing 字段，15 条真实映射（例如 `PATIENT→source_person_id`、`START→start_datetime`、`STOP→end_datetime`）。Run #41923297428 对两者数量及每条真实输入字段关联进行了只读断言。
- **公网 UI**：用户于 2026-11-04 在 `https://lineage.johnzhang-dataforge.site` 实际浏览截图确认 Landing 3 数据集、Processing 2 数据集、Patient 表级图以及 6 条字段级连接。Runner 内部通过 `urllib` 对公网 `/`、`/api/v1/namespaces` 两次探测返回 `HTTPError`；该探测 **不构成公网 HTTP API 自动验收 PASS**。公网浏览器页面正常显示、内网 GET 严格验收 PASS，二者须独立报告。
- **保留缺口**：同一窗口 14 个 child Runs 中有 7 个 parent/RDD action 仍显示 `RUNNING` / START-only，不能写入假的 COMPLETE；旧历史 RunEvent / Run UUID 并未全量找回，Task 4.1 保持未完成。任何未来真实 Writer/已提交批次 Replay 都需新的单独批准。
- **Git status**：Healthcare [PR #660](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/660) 已合并 OpenSpec P3 设计；Self-Runner [PR #506](https://github.com/JohnZhang-DataForge/Self-Runner/pull/506) 已合并执行与独立读回脚本。本次文档更新的适用 PR/CI/合并应在完成后核对，未完成的 5.6 不得提前打勾。
