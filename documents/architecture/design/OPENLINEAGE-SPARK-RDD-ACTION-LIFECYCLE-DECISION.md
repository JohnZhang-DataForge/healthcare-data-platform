---
status: active
scope: platform-portal-openlineage-spark-observability-design-decision
last_verified: 2026-10-25
source_sha: e06f288f278cbadf72c51ce468c16e19ae769696
evidence:
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197583583
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197739051
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40198536340
  - https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40198710705
---

# 设计决策：OpenLineage Spark 无输出 RDD Action 的 START-only Run 与业务级血缘验收

> **决策：方案 A（用户于 2026-10-25 明确选择）。** 对 Airflow → Spark Application → 实际 DatasetVersion 的身份、父子关系和业务读写版本继续严格验证；将部分底层 RDD Action 的 START-only／`RUNNING` 终态作为独立的待修观测缺口，不以其阻止经过独立安全门槛的 P5 Writer E2E。**这不是宣布 OpenLineage 根因完全闭环、不是放弃血缘正确性、不是将现有 P4 严格验收改成 PASS。**

## 1. 背景、用途和权限边界

- 业务路线：Synthea 合成数据 → SeaweedFS S3 Landing READY → Airflow `new_only_omop_consumer` → Spark Person / Visit / Reconcile → Processing Parquet → Writer 原子 COMMIT → PostgreSQL17 OMOP；OpenLineage 旁路向 Marquez 0.51.1（PostgreSQL14 Metadata）发送 Job / Run / Dataset 事件。
- 真实展示面是 Marquez 官方 Web，而非自建 Portal 前端；`platform-portal/marquez/tests/verify_business_lineage.py` 是**只读审计器**，并非 Marquez UI 的替身。
- 此 ADR 记录**长期设计取舍和故障经验**，当前实施/验收仍由 [Portal OpenSpec](../../../openspec/changes/complete-platform-portal-lineage-integration/tasks.md) 及原始 GitHub Run 裁决；部署/源码变更另行 PR，不借文档批准 Spark、Airflow、PG17、S3 或 Azure 写操作。
- 以下实际证据来自 2026-10-25 当时的现场/独立读回；`last_verified` 不是承诺今天及未来的在线健康。
- **术语**：RDD = Resilient Distributed Dataset（Spark 弹性分布式数据集），属于 **Apache Spark**，不是 OpenLineage 的类型；DataFrame / Spark SQL 操作（如 `count()`、`collect()`）可在引擎底层触发 RDD/Spark Job。`map_partitions_parallel_collection` 是 OpenLineage 根据底层执行过程生成的物理 Job 名称，**不证明**业务源码直接调用 `mapPartitions()`。

## 2. 故障经过：从身份查询误判到真实的 RDD 终态缺口

### 2.1 早期混淆：查询了错误的 Spark Application Job 身份

2026-10-25 的新 READY Batch：`synthea-new-only-gh-40194178133`；Landing 真实 22 Patient / 2,412 Encounter、18/18 Manifest SHA 检查通过，Airflow 三业务任务成功。实际控制容器使用同一个被验证的 V2 镜像 Digest `sha256:42d6d087de4dfecf35c51bf84461fddea9635506ed73b6a59f7de8c44d8e775d`。此批 Spark-only 路径中 Writer **未提交**，PG17 无对应新写入；不可把此批说成 P5 完整 E2E。

最初审计把裸 Spark 名 `task004_person_...` 当作 Application Job 查询，得出 App `RUNNING` / Airflow Parent 缺失；真实 Marquez **Application Job 是包含 Airflow Task 的限定名**，例如：

| 业务 | 真实 Spark Application Job 名 | 真实 Application Run UUID | 读回 |
| --- | --- | --- | --- |
| Person | `new_only_omop_consumer.spark_patient.task004_person_20261025t124314z_9` | `01a17317-7125-7f35-9a59-86d072d556f2` | `COMPLETED`、精确 Airflow Parent |
| Visit | `new_only_omop_consumer.spark_encounter.task004_encounter_20261025t124314z_10` | `01a17317-51fa-7270-9417-3beaf0f7d4a9` | `COMPLETED`、精确 Airflow Parent |
| Reconcile | `new_only_omop_consumer.spark_reconcile.task004_reconcile_20261025t124612z_8` | `01a17319-9703-7f5f-a0d7-4519c0f3fefd` | `COMPLETED`、精确 Airflow Parent |

独立的 Marquez API/PG14 元数据查询证明 3/3 Application 持久化 START/COMPLETE，且 Application `parent` 指向真实 Airflow Task Run UUID，**不是**人工生成的伪 UUID。修复了审计查询的身份映射和对应负向单测：[Healthcare PR #477](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/477)，证据 [#40196841482](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40196841482) / [#40197138492](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197138492) / [#40197583583](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197583583)。

**教训 1：同名裸 Job 与限定 Application Job 可在 Marquez 同时存在，却有不同 Job/Run UUID。按 Namespace + 完整 Job Name + 精确 Run UUID 验证；不能因为裸 Job 没有 Parent 就判断 Spark Application 没发事件。**

### 2.2 修正身份后仍真实存在的异常

在相同批次中，**四条真正的**物理 `map_partitions_parallel_collection` Action Run，分别恰有一条 START、没有持久化 COMPLETE/FAIL/ABORT，Marquez 保持 `RUNNING`；其 Application 已 `COMPLETED`：

| 角色 | Action Run UUID | 观测 |
| --- | --- | --- |
| Person | `01a17318-8dd0-7e88-8522-2ec9a654c8a4` | START-only |
| Visit | `01a17318-5ab1-708e-8855-0c3a3f33408c` | START-only |
| Reconcile 输入 1 | `01a17319-c153-73b3-951d-04f43b9d9654` | START-only |
| Reconcile 输入 2 | `01a17319-dfcc-78fe-ae04-3c9700b0acd2` | START-only |

独立 PG14 原始事件/Run 审计：[Self-Runner #40197739051](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197739051)。同时验证 3/3 Action → 已完成 Application 的真实 ParentRun 关系；Person/Visit 的 Landing CSV → Processing Parquet 各有真实读写 DatasetVersion；Reconcile 两条输入 Action 精确指向上述两个已产出的 Processing DatasetVersion：[Self-Runner #40197583583](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197583583)。

**教训 2：Application 完成、业务数据已经落盘，不意味着它所有物理 Action 子 Run 都有终态；也不能用 Application 自身零 DatasetVersion 推断没有真实输入/输出，数据边常位于子 Job。**

### 2.3 排除业务算法和“升级即修复”的假设

- 已验收的旧隔离 P3 Spark 3.5.7 / OpenLineage 1.47.1 三行 CSV → 真 Parquet 样例：Application `COMPLETED`，`adaptive_spark_plan.*_summary_parquet` 写入 Action `COMPLETED`（Input/Output DatasetVersion 存在），`columnar_to_row` 也 `COMPLETED`；但 `map_partitions_parallel_collection` 为 `RUNNING`。[只读 A/B 基线 #40198536340](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40198536340)。
- 独立 A/B 将**仅测试用 SparkApplication 渲染 YAML 的 Maven 依赖**从 OpenLineage 1.47.1 改为 1.54.0（Spark 仍为 3.5.7）。真实 Spark 完成、Parquet 写入读回、Input/Output DatasetVersion 通过；对应 Action Run `01a1734c-45e8-70f1-a81d-3440345328ff` **仍 RUNNING**。严格终态断言 `P4_OL154_MAP_PARTITIONS_STILL_RUNNING` 如实失败，未把 A/B Workflow 误报 PASS。[Self-Runner #40198710705](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40198710705)，[实验 PR #283（未合并）](https://github.com/JohnZhang-DataForge/Self-Runner/pull/283)。
- 隔离测试不执行 OMOP Writer、PG17 或业务 S3 修改，也不升级生产业务镜像。实验失败后按原法证策略**保留测试拥有的** `dw-spark/portal-a4-a440198710705-output` PVC；这只是清理记录，PVC 当前状态未经再次独立查询。Driver 停止期间曾出现 Kubernetes PVC DELETE 异常，**未证明其与 RDD 终态相关**。

**教训 3：在最小、无业务逻辑的 CSV→Parquet fixture 同样复现，说明不应优先重写 Person/Visit/Reconcile；1.54.0 的真实 A/B 失败说明不能把“升级 OpenLineage”当现成 workaround。**

## 3. 上游实现调查、根因假设与证据等级

已直接对照 OpenLineage 标签 **1.47.1** 与 **1.54.0** 源码：

- [`RddExecutionContext.java` 1.47.1](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/RddExecutionContext.java#L255-L305)：RDD Job 的 `start(SparkListenerJobStart)` 可以发送 START；`end(SparkListenerJobEnd)` 在 `outputs.isEmpty() && !(jobEnd.jobResult() instanceof JobFailed)` 时返回，不发送 COMPLETE。
- [`RddExecutionContext.java` 1.54.0](https://github.com/OpenLineage/OpenLineage/blob/1.54.0/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/RddExecutionContext.java#L256-L306)：相同“成功且无 Output Dataset → 省略结束事件”的过滤分支仍在；新版增加 `finally` 资源清理，但不补发该终态。
- [`OpenLineageSparkListener.java` 1.54.0](https://github.com/OpenLineage/OpenLineage/blob/1.54.0/integration/spark/app/src/main/java/io/openlineage/spark/agent/OpenLineageSparkListener.java#L220-L346)：`onJobStart` 取得上下文并调用 `context.start(jobStart)`；`onJobEnd` 从 RDD Registry 取出上下文并调用 `context.end(jobEnd)`；应用级 `onApplicationEnd` 另行处理。

关键逻辑原样摘录（两版的过滤谓词相同）：

```java
if (outputs.isEmpty() && !(jobEnd.jobResult() instanceof JobFailed)) {
    log.info("Output RDDs are empty: skipping sending OpenLineage event");
    return;
}
```

**当前最强解释（源码支持、与现象高度吻合，尚未完全实机闭环）**：像 `count()/collect()` 引出的正常无 Output Dataset 的底层 RDD Job，可能先发 START，后在上述 RDD `JobEnd` 分支主动抑制 COMPLETE，于是接收端 Marquez 无法得知完成、长期显示 RUNNING。这应视为**OpenLineage Spark 集成中的事件生命周期设计缺陷候选**，不属于“RDD 是 OpenLineage 类”或“Spark 不支持 DataFrame”的问题。

**尚未证实的关键环节**：尚无针对这四个精确 Spark Job ID/Run UUID 的实机 Driver DEBUG 记录，直接证明执行到了 `Output RDDs are empty...` 分支；因此不能排除 listener 回调、序列化/Transport、关停竞态等另一种导致终态缺失的原因。源码解释是高可信**假设**，不是已复现到代码行的最终根因。

上游相邻问题，不应冒充“相同 Bug 官方已确认”：

- [OpenLineage #2810](https://github.com/OpenLineage/OpenLineage/issues/2810)：RDD Job 无实际写出却出现错误输出 Dataset，说明相邻的 RDD 输出判断问题；**并非**相同的 START-only Run 根因证明。
- [OpenLineage #4636](https://github.com/OpenLineage/OpenLineage/issues/4636)：Databricks Spark Terminal Event 丢失，症状相似；其触发路径**不等于**我们完成的 Spark Application / 未闭合物理 Action。
- 可重现后再提出上游 Issue/PR，附独立 fixture、Spark 版本、1.47.1/1.54.0、精确 START-only Run 和源码定位。

## 4. 评估替代方案（决策记录）

| 方案 | 收益 | 损失/风险 | 选择 |
| --- | --- | --- | --- |
| **A. 保留真实 RDD 事件，分层验收** | 保持 Reconcile 已观测的两个输入 DatasetVersion；不中断 P5 | 原生 Marquez 明细可能出现 RUNNING，必须明确标识观测限制；严格物理终态门保持 OPEN | **采纳** |
| B. `spark.openlineage.filter.rddEventsDisabled=true` | 阻止后续 RDD 级 START/END 事件，减少悬挂的物理 Run | 不会修复已存历史 Run；可能连同 Reconcile 的真实输入版本一起删除，破坏必要证据 | **当前拒绝；须隔离验证才可重议** |
| C. 修改上游 `RddExecutionContext.end()` | 对已发送 START 且成功结束的无输出 Action 发真实 COMPLETE，可能根治 | 自建/维护 Spark Listener JAR、兼容与回归成本；必须以真实 JobEnd 身份配对、防重复 | **备选 PoC** |
| D. 只升级 OpenLineage | 可能获得上游改进 | 1.54.0 单变量 A/B 仍失败；不能盲目影响真实业务镜像 | **本次拒绝** |
| E. 重写业务程序“不要 RDD” | 理论上少一类 Action | 当前 Person/Visit/Reconcile 主要是 Spark DataFrame API；底层 Job 仍可能使用 RDD，重写不能可靠消除问题 | **不采用** |
| F. 事后手工 POST COMPLETE / 修改 PG14 | 页面看似干净 | 伪造运行证据、破坏信任和诊断能力 | **明确禁止** |

可选配置 B 的真实意义是**关闭 OpenLineage 的 RDD 事件采集**，不是禁止 Spark 使用 RDD 计算。上游源码的 `isDisabled()` 对 `rddEventsDisabled` 做判断：[1.47.1](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/RddExecutionContext.java#L595-L603)。

### 4.1 方案 A 的验收规则（不得通过降级判定制造“全绿”）

1. **业务级严格正确**：逐 Batch 绑定 Manifest SHA256、Git SHA、镜像 Digest、Namespace、Airflow Task Job+Run UUID；对每个 Spark Application 的完整限定 Job Name、真实 START/COMPLETE、Airflow ParentRunFacet 的真实 Run UUID 作精确匹配。
2. **DatasetVersion 严格正确**：检查实际 Person 和 Visit 的 Landing → Processing 写入 Action、真实 Input/Output DatasetVersion；Reconcile 的 Patient/Encounter 输入 DatasetVersion 与上述两个 Processing 输出**逐一完全匹配**。版本缺失、错配或 Parent 不符即业务级 FAIL，不以 App 成功掩盖。
3. **物理层独立记账**：START-only RDD Action 如实显示 `OBSERVABILITY_GAP` / 原始 `RUNNING`，记录实际 Run UUID、Event 原件、Application Parent 和终态缺口；不凭 Application COMPLETE 推导/伪造物理 COMPLETE。
4. **验收输出拆层**：当前 `verify_business_lineage.py` 因 `reconcile_input_runs_terminal=false` 输出 `business_dataset_gate=INCOMPLETE`，**保持事实不变**。将来若要单独报告 `business_edges_gate=PASS`，必须新增不同字段与测试明确区分，不可把现有严格 Gate 的结果直接改写为 PASS；也不可静默排除无终态的输入 Action。
5. **P5 独立事务门**：Writer COMMIT、PG17 durable readback、同一 Batch 再运行 SKIP/零业务变化各自独立验证，Spark Application COMPLETE 或 Marquez 关系图不能替代 PG17 真实提交；P4 5.3/5.4、P5 6.1–6.4 仍须按 OpenSpec 维持 OPEN 直至真实证据/明确的受审验收变更。
6. **展示与告警**：演示首先展示 Business DAG/Task、真正的 Spark Application、完整 DatasetVersion 及 PG 读回；高级明细保留物理 RDD RUNNING。对完成率/活跃作业数只按精确业务层级统计，不能将全部物理 Run 混算、误告警为计算仍在进行。**现有原生 Marquez UI 不会自动实现这种分类**；可通过独立只读报告，未来经批准的新 UI 实现。

### 4.2 对 Spark Listener 的下一步最小诊断

在**另行授权的隔离 Spark fixture** 下，绑定同一真实 Spark Job ID 的 `SparkListenerJobStart` / `SparkListenerJobEnd`、事件 Run UUID 和 Marquez PG14 保存的 START/COMPLETE；重点寻找 Driver DEBUG 的 `Output RDDs are empty: skipping sending OpenLineage event`。

- 若 Spark JobEnd 已到达且命中上述条件，可复现为上游无 Output 过滤造成的 START-only 生命周期问题，再设计“已发送 START → 对应真实结束事件仍闭合”的最小 Listener patch；保证输入版本不丢、JobFailed 仍 FAIL。
- 若没有 JobEnd 或存在 HTTP/编码失败，转而排查 Spark Listener 注册、关闭时序、Transport、Marquez 接收/持久化；不得仅凭源码假设写结论。
- 与旧 1.47.1 基线对照，不因为 1.54.0 曾成功写出 Parquet 就声称 RDD 终态已修复；严禁直接修改共享运行中的 JAR/八个镜像。

## 5. 对未来 FHIR/HL7 多来源的可迁移经验

**适用范围必须分清**：上述 `RddExecutionContext` 问题只针对**使用 OpenLineage Spark Listener 的 Spark Job**。FHIR R4 Bundle JSON、HL7 v2 原始消息、OIE Channel、Azure Blob Publisher 本身**不是 RDD**，不能因此认定它们会遭遇同一个 Bug；将来在 Fabric Notebook / PySpark Silver 处理 FHIR/HL7 时，如果选用同一类 Spark OpenLineage Agent/运行方式，才需要进行同类 A/B 和验收。

对后续来源的**技术原则**：

1. **分别定义事件身份、数据集身份与处理终态**。FHIR 记录 `hospital/source_system`、`batch_id`、Bundle / Patient / Encounter Reference、不可变 Blob URI 与内容 SHA；HL7 记录 `source_system`、`MSH-10`、`ADT 类型`、事件键、OIE Channel/版本和原始消息 Blob URI/hash；Fabric Silver 版本需能追溯到精确 Bronze 内容，而不以 Job Name 字符串猜测身份。
2. **血缘观测与真实业务状态分离**。Producer 生成成功 ≠ Blob READY；OIE 转换完成 ≠ Blob 验证成功；Fabric Notebook/Pipeline SUCCESS ≠ 最终 Silver 版本正确；Lineage Run COMPLETE ≠ PG17 OMOP COMMIT。各状态以对应真实文件、Manifest、版本和独立读回为准。
3. **按组件选择观测边界**。本地 Synthea / OIE / Blob Publisher 可采用真实 Batch Manifest、来源键、文件 SHA/ETag、原生执行记录 + 经审核的 OpenLineage 集成；只有采用 Spark Listener 的步骤才适用 RDD 事件开关。不能把 `rddEventsDisabled` 错配给 OIE/Blob Publisher。
4. **优先选择可演示的业务层级**：医院/来源 → 原始 FHIR/HL7 Blob Dataset → Fabric Bronze → Silver Patient/Encounter → 跨医院 Crosswalk；保留原始物理 Run 明细，不让不可解释的物理 RUNNING 污染跨医院处理成功率。
5. **每条新来源链路先做最小隔离 Smoke**：正向：1 输入、1 输出、精确 DatasetVersion + Parent；负向：无 Output 的只读校验、写入失败、重复事件、Manifest/hash 冲突、输入版本错配；若通过 Spark 处理，应另覆盖 `count()/collect()` 产生的无输出 Action，检查是否有 START-only。
6. **拒绝“为了图绿”而牺牲血缘**：任何过滤 RDD/SQL 事件、替换 Collector、升级 Listener 之前，先比较是否仍然完整保留 FHIR/HL7 原始→Bronze→Silver 的精确版本边、Run 身份与重复写入保护。
7. **同样使用独立事务/幂等 Readback**：FHIR 引用完整性与患者 Crosswalk；HL7 按 `source_system + MSH-10` 的幂等与冲突规则；不可用单一 Marquez UI 绿色状态替代实际业务校验。

相关目标方案：[FHIR/HL7 多来源 MVP](FHIR-HL7-MULTISOURCE-MVP-DESIGN.md) · [V2 多来源路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md)。此 ADR **不声称 FHIR/HL7 生产链路已部署/已接入 OL**，不自动为其选择或实施观测 SDK。

## 6. 复用时的判定清单

| 检查 | 需要的证据 | 未通过时 |
| --- | --- | --- |
| 业务执行身份 | 源码 SHA、Batch/Manifest、真实任务 ID、镜像 Digest | `UNVERIFIED` |
| Application/DAG 终态 | 原始真实 OpenLineage Event + Marquez Run UUID + 实际 Task 状态 | 不按子 Run 推导 App 成功 |
| 版本边 | 每个 Dataset 真实 URI、内容/版本标识、父子 Run 精确关联 | 业务级血缘 FAIL |
| 物理 Action 生命周期 | START/COMPLETE/FAIL/ABORT 同一个 Run UUID；JobEnd/Driver 日志 | `OBSERVABILITY_GAP`；不得伪补 |
| 数据持久化 | S3/Blob/Parquet/PG17 独立读回及幂等复测 | 业务 E2E 继续 OPEN |
| UI/告警 | 区分 Airflow Task、Spark App、物理 Action，显示警告 | 禁止混合总 RUNNING 统计 |
| FHIR/HL7 适用性 | 是否实际运行 Spark Listener（而非 OIE/Publisher） | 不套用 RDD 特定 workaround |
| 安全性 | 运行窗口授权、Idle Gate、只读与会写动作区分 | HOLD |

## 7. 原始证据与决策来源

**本项目：**
- [Healthcare PR #477：修复限定名 Application 的审计身份与测试](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/477)
- [Healthcare PR #478：真实父链与 DatasetVersion 复核](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/478)
- [Healthcare PR #479：1.47.1 / 1.54.0 A/B 与失败证据](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/479)
- [Self-Runner #40197583583：真实 App COMPLETE/Parent、Action→App Parent、版本边](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197583583)
- [Self-Runner #40197739051：四条真实 Action START-only 的独立 PG14 事件读回](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40197739051)
- [Self-Runner #40198536340：旧 P3 合成隔离样例只读回归](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40198536340)
- [Self-Runner #40198710705：仅测试 YAML 升级至 OL 1.54.0 仍 FAIL](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40198710705)
- [对应 OpenSpec P4/P5 进度、历史 Run 及未完成门槛](../../../openspec/changes/complete-platform-portal-lineage-integration/tasks.md)

**上游：**
- [OpenLineage 1.47.1 RDD END 过滤源码](https://github.com/OpenLineage/OpenLineage/blob/1.47.1/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/RddExecutionContext.java#L255-L305)
- [OpenLineage 1.54.0 RDD END 过滤源码](https://github.com/OpenLineage/OpenLineage/blob/1.54.0/integration/spark/app/src/main/java/io/openlineage/spark/agent/lifecycle/RddExecutionContext.java#L256-L306)
- [OpenLineage 1.54.0 Spark Listener 事件映射](https://github.com/OpenLineage/OpenLineage/blob/1.54.0/integration/spark/app/src/main/java/io/openlineage/spark/agent/OpenLineageSparkListener.java#L220-L346)
- [OpenLineage Issue #2810：无真实写出时的 RDD Output Dataset 识别](https://github.com/OpenLineage/OpenLineage/issues/2810)
- [OpenLineage Issue #4636：不同环境的终态缺失](https://github.com/OpenLineage/OpenLineage/issues/4636)

**最终决策**：优先保证真实业务结果和 DatasetVersion 的严格一致性；接受并公开标注待修的**物理观测局限**，继续在独立授权/安全门槛下推进 P5；待真实 Driver 分支证据闭环后再决定是否提交上游修复。**这是有限范围的架构取舍，不是对数据正确性或历史失败事实的豁免。**
