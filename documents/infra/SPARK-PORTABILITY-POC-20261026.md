---
status: reviewed
scope: healthcare-on-demand-live-demo-spark-portability-live-evidence
last_verified: 2026-10-26
implementation_status: partial-live-verification; fabric-result-hold-after-three-attempts
healthcare_source_sha: 6bf27997a7962b02e97d201f9fc3933ce903203b
---

# Fabric Spark 与本地 Kubernetes Spark 兼容性实测（2026-10-26）

> **证据等级：Local PySpark RUNTIME PASS；Fabric Trial Notebook 创建/调度 PASS_WITH_SCOPE；两端业务结果一致性 UNVERIFIED / HOLD。** 这是用户授权的兼容性调查，不能将 Notebook Job `Completed` 等同于被测 PySpark 转换成功。Fabric 连续三次未拿到可独立校验的结果，遵守三轮失败停止规则：未经新决策不得自动启动第四次重试。

## 1. 测试标的与安全边界

唯一 PySpark 测试源码：[portable_patient_smoke.py](../../local-data-platform/spark/apps/compatibility/portable_patient_smoke.py)，Healthcare 精确源 SHA `6bf27997a7962b02e97d201f9fc3933ce903203b`。内存创建 6 条完全虚构 Patient（含 1 条重复），执行标准 Spark DataFrame `trim`、`lower`、`to_date`/`year`、`filter`、`dropDuplicates`、`orderBy` 后，预期 5 行。结果基于排序后 JSON 的 SHA256：

`5c4add3c4976f2d894fd24da8477ea43c48a9069ef66eb2763d7d47f404eac1b`

不访问真实数据，不写业务 Delta/Blob/S3/PG/OMOP，不回放历史 Batch，不采购 F2，不改变 Terraform/Workspace 配置。Fabric 仅限真实核实绑定 Active FTL4 免费试用容量的 `johnzhang-test`，每轮临时 Notebook 名带专属 GitHub Run ID；每次 DELETE 自有 Notebook 返回 HTTP 200。Local Spark 仅新增独立 SparkApplication/ConfigMap，always cleanup 命令已执行，但未进行事后独立 Pod 回收核实。

## 2. 双运行时实际清单 — GET-only PASS

[Self-Runner Run #40438541415](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40438541415) SUCCESS：

| 项目 | 本轮真实读回 |
| --- | --- |
| `healthcare-omop` Fabric Workspace | Spark Runtime **2.0**、Starter Pool，Spark Settings HTTP 200 |
| `johnzhang-test` Fabric Workspace | Spark Runtime **2.0**、Starter Pool，Spark Settings HTTP 200 |
| 已存在的 Fabric Items | 两个 Workspace 均为 1 Lakehouse + 1 SQL Endpoint；GET 时没有 Notebook |
| Fabric Capacity | 可见 Active FTL4 Trial，以及 PP3；具体测试前独立校验 workspace 与 FTL4 绑定 |
| K8s `dw-spark` | 27 个历史 SparkApplication，全是 Spark **3.5.7** / `spark:3.5.7-python3` |
| 当前并发 | GET 时没有 Active SparkApplication |

Fabric Runtime 2.0 的微软运行时规格为 Spark 4.1 / Scala 2.13 / Python 3.13 / Delta 4.2；**这是官方规格，不是本轮 Notebook 内部输出**。现有 Local OpenLineage 模板使用 Scala 2.12 的 `openlineage-spark_2.12:1.47.1`；不能未经验证直接复制到 Scala 2.13。Local 实际 Python、Delta 的完整版本和两端 OL Listener、Delta Protocol 兼容性尚未实测。

## 3. 本地 Spark 真实执行 — PASS

[Self-Runner PR #314](https://github.com/JohnZhang-DataForge/Self-Runner/pull/314) → [Run #40439394218](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40439394218) **SUCCESS**：

- 在既有 Spark Operator 执行隔离内存 DataFrame 测试。预检查无人占用 Spark；1 core / 1 GiB Driver 与单 Executor。
- SparkApplication 真正完成 `COMPLETED`；Driver 实际输出：`LOCAL_REAL_SPARK=3.5.7 ROWS=5 SHA256=5c4add3c4976f2d894fd24da8477ea43c48a9069ef66eb2763d7d47f404eac1b`。
- `LOCAL_SPARK_COMPATIBILITY_SMOKE=PASS`；自身资源的清理命令在 always step 执行，未宣称 Pod 已独立复核删除。

**严格结论**：本地 Spark 3.5.7 对这一有限纯 PySpark 数据转换是真实 PASS，不能由此直接推出跨云兼容。

## 4. Fabric 免费 Trial 三次实际尝试 — 调度成功，结果验证失败

| 尝试 | Run | 已经真实成功的层面 | 未通过环节 |
| --- | --- | --- | --- |
| 1 | [#40439764059](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40439764059) | FTL4 容量匹配；Notebook Create 202；Run POST 202；Job Completed；own Notebook DELETE 200 | GA Job Status 响应没有可用的转换结果 `exitValue` |
| 2 | [#40440025579](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40440025579) | 同样成功创建/调度/终止/清理；Notebook 专用 Beta GET HTTP 200 | 无非空 `exitValue`，结果哈希不可确认 |
| 3 | [#40440244737](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40440244737) | 更改 Notebook wrapper 为 `mssparkutils.notebook.exit`；Beta GET 200，响应中包含 `properties.exitValue` 字段；DELETE 200 | `exitValue` 仍为空；Notebook `getDefinition` 返回 HTTP 202 异步处理中，未独立确认 Notebook 内容已就绪 |

三次测试的 GitHub Workflow 原始最终结论均为 **FAILURE**，不能改写成 SUCCESS。第三次还确认 Beta 响应的 `properties` 内存在 `exitValue` 这个**字段名**，但缺少有效字段值。可能的解释是 Notebook Create/Definition 的 LRO 尚未完成，就过早启动 Job，导致实际被调度的内容未达到预期；**这只是未验证假设，不是确定根因**。也可能是退出 API/Notebook 内容/运行时执行路径问题。

整个测试没有启用 paid F2，也没有 Blob/PG/业务 Delta 写入。每轮临时 Notebook 的 DELETE API HTTP 200；不声称后台所有资源回收已独立验证。

## 5. 下一安全调查方向 — HOLD，需新的决策

1. **先核实 Notebook Create 的异步 LRO**：读取 Operation Location/ID，确认 Terminal Success，而非只要 Notebook Item 列表可见就启动。
2. **先核实实际已发布 Notebook 定义**：等待 GetDefinition 的 LRO 终态成功，并比较实际返回的 `notebook-content.py` Base64 解码 SHA 与提交源码的一致性；未通过就**不运行** Spark。
3. 若定义读回 PASS，再安排一次有明确新测试假设的免费 Trial Notebook（非自动盲重试），同时获取真实运行日志或输出、`properties.exitValue` 里的 JSON 和 SHA；不能只凭 Job Status Completed 判为通过。
4. 只有纯 PySpark 算子比较一致，才按独立 Gate 再测试 Fabric Spark 4.1 / Scala 2.13 的 OpenLineage Listener、真实 Dataset/Column Facets、Azure Blob JSONL 可靠性、Delta 和 FHIR/HL7 ETL。
5. 后续运行需要重新核对双仓 Main/开放 PR/运行 Workflows、Safe Operations、Session Coordination，并请求用户对第四轮的明示决定。本报告本身只记录证据，不授权任何新 Cloud、K8s 或付费操作。

## 6. 状态结论

| Gate | 判定 |
| --- | --- |
| 双端实际 Runtime Inventory | **PASS**，Fabric Runtime 2.0 vs Local Spark 3.5.7 |
| 本地 5 人 DataFrame 真正执行/哈希 | **PASS** |
| Fabric 免费 FTL4 匹配、Notebook 创建/调度终态 | **PASS_WITH_SCOPE** |
| Fabric 执行完全相同 PySpark 转换的结果哈希 | **HOLD / UNVERIFIED**（三次未读到） |
| 同一代码双 Runtime 真实相同输出 | **HOLD / UNVERIFIED** |
| Fabric OpenLineage/Delta/Blob 的端到端兼容 | **NOT_TESTED** |
| paid F2 / Blob / PG / 业务数据副作用 | **NONE** |

**OpenSpec 继续 Active，Spark 执行后端继续 UNDECIDED。** 本报告是实际验证总结，不意味着后续 2.1/2.2/2.3 任务已全部完成。
