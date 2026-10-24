# NEW_ONLY 随机 Synthea 批次 Writer 偶发失败——现象冻结记录（2026-10-20）

> **状态：OBSERVED_DEFECT / ROOT_CAUSE_UNDETERMINED / INVESTIGATION_DEFERRED**  
> OpenSpec Change：`relocate-local-data-platform`；归属于 Task 4.7 / 4.9 合并后的真实回归**事实证据**，**不是**本次迁移清理的修复方案或验收失败豁免。  
> 用户决定：保留当前源码、镜像、部署和合同原状；只记录三次运行事实，以后独立授权再调查和决定修复。**不得在本记录 PR 中改应用代码、Mapper、SQL、DAG、Docker、GHCR Digest、K8s 或 PG/S3，不重复生成新 Batch。**

## 1. 已确认现象和边界

相同已合并 Healthcare Main、Airflow GitSync 路径及现行 Writer 镜像，使用每次独立随机生成的 Synthea NEW_ONLY Batch 做完整真实业务 E2E：有两个 Batch 的 S3 READY、Spark Person/Encounter/Reconciliation 均通过，却在 **Atomic OMOP Writer** 阶段失败；第三个 Batch **完整 Writer + 独立 PostgreSQL 对账 + 同 Batch SKIP 成功**。

**可以确认**：当前设计、数据合同或实现至少存在未覆盖的随机数据场景／运行行为缺陷，且“某一批次 PASS”不能推出“所有随机批次 PASS”。**尚不能确认**：具体字段/输入、哪层应负责任、是否为某个映射漏项、两次失败是否为同一原因，以及是否与目录迁移有关。**不因两次失败否认第三次成功，也不因第三次成功抹掉历史失败。**

### 固定复现条件（用于未来区别不同版本）

- Healthcare Main：`ed46876990ec8cb68c8a95d41084831c76add456`，合并了九个一次性历史源码安装器的 [PR #332](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/332)。九个正式安装产物、实际运行 Writer、DAG、测试及合同均保留；此次不反向归因于被退役 Shell。
- Self-Runner 一体化测试 PR [#168](https://github.com/JohnZhang-DataForge/Self-Runner/pull/168)，工作流源码 HEAD `b66e42674dc4982ae96feb2832a22de0941b0f4b`。**第三次通过关闭/重开测试 PR 重触发，工作流与业务源提交未改**；每次 `GITHUB_RUN_ID` 产生新 Request/Batch，并将当次 Manifest SHA 与动态行数传给 Consumer。
- Airflow Scheduler、DAG Processor 活动 GitSync 来源、DAG Parse 14 Tasks 按相同 Healthcare SHA 做了来源门。Writer DAG 声明冻结镜像：`ghcr.io/johnzhang-dataforge/healthcare-data-platform-new-only-omop-writer@sha256:1565a4481669520916a336e7ce5de52f3856333c43632078d03854b22bc28ae4`；第一次失败 Pod 的实际 image 字段与其一致。后续审查仍须按对应 Pod Digest 逐批核实，不能因声明一致就假装所有容器实测一致。
- 执行环境：本地开发 Kubernetes / Airflow / Spark / SeaweedFS S3 / PostgreSQL OMOP，仅合成数据；与 Fabric 工作流无关。

## 2. 三次独立实验（保留 Run 的原始结论）

| 运行链接 | NEW_ONLY Batch | Person | Encounter / Visit | 确认结果 |
| --- | --- | ---: | ---: | --- |
| [Self-Runner #39490048027](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39490048027) | `synthea-new-only-gh-39490048027` | 91 | 15,328 | **FAILURE**。Synthea/S3 READY、Spark Person/Encounter/Reconcile、Writer Handoff/Authorization PASS，`execute_new_only_writer` FAIL；`writer_committed_verified` upstream_failed。 |
| [Self-Runner #39491365702](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39491365702) | `synthea-new-only-gh-39491365702` | 30 | 4,260 | **FAILURE**。Synthea/S3 READY、Spark Person/Encounter PASS，`execute_new_only_writer` FAIL；**该次 Pod 的具体 Python 异常未独立取证**，不能说一定也是 `unknown_demographic`。 |
| [Self-Runner #39494210009](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39494210009) | `synthea-new-only-gh-39494210009` | 51 | 9,413 | **SUCCESS**。Synthea 18/18 CSV/S3 READY、Airflow 14 Task DAG 来源、Spark Person/Encounter/Reconcile、Atomic Writer、独立 PG 读回及同 Batch 幂等 SKIP **全部 PASS**。 |

失败第一次的 **原始只读 Writer Pod 证据**：[Self-Runner 诊断 #39491365767](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39491365767)；Pod `dw-spark/task004-new-only-atomic-writer-357ejmwr`，日志调用链：

```text
new_only_airflow_writer.execute -> joint_s3_rollback.s3_rows
  -> task004_cdm_dynamic_source.read -> task004_cdm_dynamic_adapters.transform
  -> gate(gender in GENDER and race in RACE and eth in ETHNICITY, "unknown_demographic")
ValueError: BLOCKED=unknown_demographic
```

这里仅证明该 Batch 有值不满足当前枚举检查，**未核对是 gender、race 还是 ethnicity，也未读取实际 distinct 值**。例如 `native` 不在已观察到的 Writer `RACE` 枚举，但它只是可能线索，**不是已证实根因**，本轮不得直接填补映射并声称已修复。

第三次 **独立持久化读回与重复运行证据**（来自 [#39494210009](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39494210009) 完成日志）：

| 检查 | 真实值 |
| --- | --- |
| 新 Batch 执行前 | Claim 0 / Ledger 0 / Stage 0 / Checkpoint 0 |
| `cdm.person` | 326 → 377（+51） |
| `cdm.visit_occurrence` | 41,079 → 50,492（+9,413） |
| 本 Batch | `BATCH_CLAIM=1`, `BATCH_COMPLETED=1`, `BATCH_LEDGER=1` |
| Stage 和 ID Map 读回 | Person 51/51、Visit 9,413/9,413 |
| Checkpoint | `BATCH_CHECKPOINT=2` |
| Airflow 首次 + 同 Batch SKIP | `success` / `success` |
| 幂等性 | `NEW_ONLY_SAME_BATCH_REPEAT_SKIP=PASS`、`NEW_ONLY_REPEAT_ZERO_PG_CHANGE=PASS` |
| 环境恢复 | `DAG_PAUSE_RESTORED=PASS` |

**解释限制**：上述成功是一条完整可验收的新路径成功案例；前两条仍然是业务覆盖问题，不能改写为通过，也不因第三次成功而把 Writer 的随机数据兼容性标成 100% 验收。第一次 Writer 在转换阶段报错，尚无完整 DB Commit 证据；发生失败时也不能凭此推断全部中间 S3/PG 状态自动回滚。

## 3. 后续待定、不是本轮修复任务

**DEFERRED / NO FIX APPROVED**。后续若用户单独授权调查，在独立 OpenSpec Bugfix Change 中按以下顺序考虑：

1. **只读**读取失败及成功 Batch 的 Gender/Race/Ethnicity distinct values、分布和对应 Parquet/Canonical 映射字段，不暴露人员标识；同时取得第二次失败的准确 Pod 错误（如日志仍可用）。
2. 对照 Synthea 的有效值域、Canonical Patient Contract、OMOP Writer 允许枚举、实际 Runtime 镜像和版本，区分 `数据源合法但合同覆盖不全`／`映射规则错误`／`运行环境或实现差异`／`其他未确认情况`。不事先选择哪种修复方案。
3. 单独评审修复范围及新回归用例（正例、负例、不同人口值、随机多批），然后明确批准才改业务源码/Contract 或重新打包镜像，并用**新的未完成 Batch**重跑真实 E2E/独立 PG 读回/幂等。
4. 若当前清理 Change 满足它自己的验收边界，可以将该缺陷作为**已知独立遗留问题**链接，而不能因为 Writer 某一批 PASS 就宣称缺陷已消除。是否影响最终 Archive 须在 Closeout 中如实决策。

## 4. 文档记录范围与检索

- 本文是 **2026-10-20 的现象证据**，不是独立的根因报告、修复设计或永久解决方案；冻结以上三次 Run，后续不重写成其他状态。
- 在 `openspec/changes/relocate-local-data-platform/tasks.md` 的 Task 4.7 / 4.9 记录引用；未来根因处理需另建独立 Change，不在此保留第二套并行实施 Tasks。
- `documents/engineering/status/PROJECT-STATUS.md` 可仅提供一条高层链接，具体事实仍以本 Evidence 和原始 GitHub Run 为准。
- 本轮范围 **DOCS ONLY：没有业务源码、配置、CI Workflow、DAG、SQL、镜像、PG/S3/K8s 的写操作**；不新增任何运行。
