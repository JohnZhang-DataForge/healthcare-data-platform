# 开发交接：TASK-003 STEP04 完成，准备 STEP05

交接日期：2026-10-09。本文件描述验收时点，不自动证明未来环境状态。

## 1. 工作方式与边界

- 项目根目录：`/data/spark/healthcare-data-platform`；操作主机：runner01。
- 提供可直接粘贴的 Bash 命令；通过 Shell 生成和修改 Python、YAML、SQL、文档。
- 调试、安装和修复脚本放 `/data/spark/temp_shell`；正式可重建脚本放项目 `scripts/`。
- 已修复内容必须同步正式生成器，不能要求新环境按历史聊天顺序重复打补丁。
- 每一步输出使用 `#### ... OUTPUT BEGIN ####` 与 `#### ... OUTPUT END ####`，退出码由 EXIT trap 输出。
- 每次给出一个可验收步骤，根据真实结果继续；PASS 冻结后不无故重跑或修改。
- `/data/spark/phase3c` 是旧版基准，保持不动。
- 未获凭据时不猜值；不输出 Secret 内容；运行配置不提交 Git。
- 当前协作方式是用户在 runner01 执行命令并回传结果；不要把助手的临时工作区当成 runner01。

运行定位：Spark namespace=`dw-spark`，ServiceAccount=`spark-job`，S3 Secret=`dw-spark-s3-secret`。
S3 endpoint 为 `http://dw-seaweedfs-s3.dw-seaweedfs.svc.cluster.local:8333`。
Spark 镜像、JAR、PVC 和数据库连接方式以正式模板及发现脚本为准；沿用已验收配置，不重新猜测。

## 2. 已完成与未完成

- TASK-001：whole-batch Landing 已验收。
- TASK-002：Person V2 已端到端验收，cdm.person=113。
- TASK-003：STEP03 和 STEP04 已验收；5799 条 Encounter 已进入 APPROVED Raw。
- STEP04 同 run 恢复及重复执行通过，reset 已安装。
- Git main 已同步至 e96ec2a；本地当前分支仍为 feature/task-001-synthea-batch-intake。
- STEP05 尚未实施验收，不能把 Encounter Raw 完成说成 visit_occurrence 入库完成。

## 3. 固定验收定位信息

| 字段 | 值 |
|---|---|
| source / source_version | synthea / v3.3.0 |
| batch_id | synthea-20261005-pop100-atlanta |
| ingest_date | 2026-10-08 |
| Processing run | encounter-20261008T234726Z-1658454 |
| Raw run | encounter-raw-20261009T005128Z-1681690 |
| source_file | payload/csv/encounters.csv |
| source_file_size_bytes | 1883564 |
| source_file_sha256 | 71c7d3fc8dc72c16b33c61c2534c274dcd9f2d96cad102af1554482d69ef7df5 |
| intake_manifest_sha256 | 790409cb0f5f5073d6a94599fcf0e68080216429a9d75b0c89d1a79dc12821e0 |

Raw base URI：

```text
s3://health-raw/canonical_version=v1/entity=encounter/source=synthea/source_version=v3.3.0/ingest_date=2026-10-08/batch_id=synthea-20261005-pop100-atlanta/run_id=encounter-raw-20261009T005128Z-1681690
```

其下正式产物为 `data/`、`dq/result.json`、`manifest.json`。
以上是本次验收定位值；未来 runner 应从已验证状态解析，不能把这些 ID 固定成通用业务参数。

## 4. 必须保留的本地证据

以下路径均相对于项目根目录：

- `runtime/reports/task003/step03/encounter-20261008T234726Z-1658454/run-state.json`
- `runtime/reports/task003/step04/encounter-raw-20261009T005128Z-1681690/run-state.json`
- 同一 Raw run 目录下的 driver.log、SparkApplication、DQ 和 manifest 本地文件。
- `diag-20261009T005543Z-1683198/whole-run.listing.json`：原 Raw 对象清单。
- `resume-20261009T010757Z-1687630/`：第一次恢复成功证据。
- `resume-20261009T011330Z-1689689/`：重复恢复成功证据。
- `replay-check-20261009T011330Z-9iIM2t/`：重放对比和 validation.json。
- `runtime/work/task003-reset-check.SQZpRO/evidence.sha256`：reset 前报告文件哈希清单。

diag/resume/replay 子目录均位于上述 Raw run 报告目录下。
恢复还依赖原 SparkApplication/driver 日志和 TASK-001/STEP03 血缘，不能清理后再假定 resume 可用。
源码仓库不包含这些证据；仅 git clone 不能恢复正在进行中的 run。

## 5. STEP05 开始前需要阅读

1. `spark/contracts/canonical/encounter-v1.json` 与 `spark/contracts/omop/visit-class-v1.json`。
2. `spark/common/omop.py`、Person mapper、Person OMOP SparkApplication 模板和运行脚本。
3. `scripts/task003/01-discover-visit-occurrence.sh`、`02-discover-visit-mapping-foundation.sh` 及可用发现结果。
4. STEP04 正式 manifest、run-state 与现有状态解析代码。
5. 数据库实际 Visit 表、稳定 ID map、约束和词表情况；通过现有访问方式只读核对。

截至本次交接，当前对话尚未收到 e96ec2a 的完整源码包。
已给出 `05a-export-source-context.sh` 导出方式，但没有源码包上传或读取成功证据。
后续可直接读取固定提交，或读取导出的源码包；不要仅凭目录树猜函数接口与数据库 DDL。

## 6. 下一步实施目标

- 从已批准 Raw run 精确读取 Encounter，校验 manifest/DQ/血缘，禁止扫描所有历史 run。
- 复用已验收 Person 稳定 ID；核对 Encounter 的患者关联。
- 依据实际 schema 设计 Visit 稳定 ID 分配，避免重跑时 ID 漂移或碰撞。
- 按版本化合同完成 Visit 类型、日期时间、来源字段等 OMOP 映射；核对词表有效性。
- 通过目标字段、唯一键、Person FK、计数等检查后，发布 OMOP-ready Processed。
- 后续再做 Stage、事务 UPSERT、CDM 对账和幂等验收，不跳过中间验收直接入库。

STEP05 的确切子步骤和 ID map 写入边界，读完现有实现后再确定；当前交接不假定相关 DDL 已创建。
后续本地 MVP 还包括 Condition、Procedure、Drug，以及 Observation 派生 Measurement/Observation，最后加入 Airflow 整批编排和批次汇总。
18 个文件均须有处理结论；不要求本轮把全部 18 个文件映射到 OMOP，非核心文件应明确 DEFERRED。
Azure/Fabric/ML、CI/CD 增强和 FHIR/HL7 接入仍按总设计分阶段推进。
