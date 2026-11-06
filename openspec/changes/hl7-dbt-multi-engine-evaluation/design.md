# Design — HL7 v2 Parser + dbt Core → 统一 Canonical Silver（方案待实验）

## 1. 设计目标与事实界限
**两条独立维度：** 数据源差异（FHIR / HL7 / CSV），处理方式差异（FHIR PySpark 与 HL7 Parser + dbt SQL）。两条路线在 Canonical Silver 汇合，**Canonical 后处理逻辑、实体扩展机制、Contract 及 OMOP Mapper 只有一套**；不得为了展示 dbt 制造 FHIR→HL7→FHIR 的循环。

**现有已验证事实（2026-11-05 主分支文档核对）：**
- OIE 4.7.0 在本地 dw-oie/worker01，已验证 Johns Creek 合成 FHIR → ADT^A01 (HL7 v2.5.1)：31 Encounter / 1 IMP A01 / 30 AMB skip / 相同请求重试输出相同；这只是模拟医院的 Producer，当前是 REST Channel Reader，不是已验收 MLLP Listener。
- OIE Channel Writer 的 destination 仍为 none；OIE → Azure Blob HL7 Publisher 和 Fabric HL7 下游 **尚未验收**。不重放固定历史批次。
- Fabric FHIR G4 的 canonical_patient 100、canonical_encounter 5918 在 Delta Silver Approval / 独立读回 / Replay SKIP 有实证；Gold Candidate / 正式 Concept Profile / Warehouse COMMIT 仍 OPEN。
- Canonical patient-v1 **birth_date、gender_code、race_code、ethnicity_code 非空**；encounter-v1 **end_datetime、start_datetime、source_code 非空**。现有 OIE adt_a01.js 只填 MSH、EVN、PID-3/5、PV1-19/44，不满足 v1；HL7 A01 本身通常不足以得出 discharge/end 时间。不能用虚构日期、race 或默认医学概念绕过。
- Local PG Legacy Mapper 尚未与 Shared Wheel 完全统一；这是目标归属，不是已完成事实。

## 2. 推荐逻辑边界
~~~text
Hospital A: FHIR R4 -> raw Blob/Manifest -> Fabric Native PySpark -> FHIR Candidate -.
                                                                                |
Hospital B: OIE FHIR->HL7 producer -> raw HL7 Blob/Manifest                      |
            -> approved open-source HL7 parser (not hand-split)                 |
            -> structured local/Delta staging -> dbt Core SQL -> HL7 Candidate -+
                                                                                |
                                          shared Canonical Contract / PK-FK / DQ / quarantine
                                          + Approval ledger / idempotent Publisher
                                                             |
                                                ONE canonical_patient
                                                ONE canonical_encounter
                                                   (Fabric Silver Delta)
                                                             |
                                          ONE shared OMOP Mapper / Identity / DQ
                                                             |
                                              controlled Warehouse Gold Writer
~~~

**Parser 分工：** 先验证消息 framing、MSH-9/12、PID、PV1、HL7 escape/repeat/optional segments、timezone、event keys；使用固定版本开源库（如 hl7apy，许可证/兼容性/安全性/测试输入需实证）；输出可测试的结构化 Staging（schema + raw pointer + message control ID + batch/provenance），并保留原始 HL7 bytes。不开第二套业务 Mapper。

**dbt 分工：** 负责 HL7 Staging → 按实体独立且可扩充的 Canonical Candidate SQL Models，source-specific code/type/date normalization、tests、增量和重跑。SQL 不直接分配 OMOP INT Person/Visit ID，不直接写 Gold，不擅自写正式 Silver 的 Approved 表。扩展 Observation/Condition 等时增加 Entity 模型，不改变已验证的共享路径。

**Publisher 分工：** 共用既有冻结 Contract，分来源隔离并做 Schema、日期、PK/FK、唯一性、quarantine、count/hash、readback、状态管理、跨批次 replay；共用单一授权的 Silver publish path。DBT test success 仅是 Candidate 层证据。

**OIE Producer 分工：** 产生独立 HL7 数据源并真实保留 HL7 bytes；可扩展 PID-7/8、审定的临床编码及 A03 出院事件，但没有源事实不得造值。A01 与 A03 同一 visit 关联、字段更新和出院时序必须单独规范化；没 A03 时持续未结案 Visit 应 HOLD/Quarantine 或正式评审 Canonical v2 nullable end，而不是填假时间。

## 3. dbt 执行后端（明确 PENDING）
| 路径 | dbt CLI 位置 | SQL engine | Fabric CU / 注意事项 |
| --- | --- | --- | --- |
| A dbt-duckdb | Self-Runner isolated process | DuckDB local | 纯本地转换不耗 Fabric Spark CU；DuckDB Delta extension 写入能力/merge/兼容须真实验证，不认定能直写 Fabric Silver |
| B dbt-fabricspark method: session | Self-Runner isolated process | Local PySpark SparkSession | 纯本地计算不耗 Fabric Spark CU；本地 Spark/Delta/Hive/JDK 和 Fabric SQL 兼容、source reader、版本依赖须验证 |
| C dbt-fabricspark method: livy / Native Fabric dbt Job | Local CLI / Fabric service | Fabric Spark | 远端 Fabric Session 消耗 CU；作为将来可能的基线/对照，不在本次零云 POC 中运行 |

**成本边界：** 即使 A/B 转换在本地，远端 OneLake 读写/管理或最终 Fabric Silver publish 和 Warehouse Gold 仍受 Fabric Capacity/可用性/事务约束。A/B 的本地 Candidate 先写隔离输出（Parquet/CSV/或本地 Delta），以 SHA/manifest 交给受控 Fabric Publisher，先不直接触碰 OneLake 或生产 Delta。

## 4. 受控测试矩阵（只在 Self-Runner）
1. 零凭据离线 synthetic fixtures：HL7 A01 入院、A03 出院、重复 A01、冲突 MSH-10/SHA、无 PID-7/8、缺失 race/ethnicity、缺 A03、时区/转义/重复 segments、非法字段、跨医院相同 MRN；同一组输入适配 A/B。
2. Parser：真实 HL7 v2.5.1 OIE 风格样例、严格字段提取/结构化 JSON 或 Parquet；不以程序自造输出当真实 OIE live 验收。
3. dbt：实际运行 dbt compile + run + test（而非仅 SQL parse）；相同 HL7 fixtures 得到相同 Canonical Candidate 值、行数和异常分类，版本/replay 稳定。
4. Delta/SQL：区分 DuckDB 本地 SQL/Delta extension 的读写能力与 local Spark Delta 表建立/merge。验证 schema types、日期/时区、merge & replay、增量 delete/update、并发冲突模拟、独立读回；失败项不包装为 PASS。
5. 安全与可重复性：单独 Python env、version pin、零网络云 API、禁用实际 Azure/K8s/OIE/PG/Cloudflare 访问；不写 Healthcare repo；固定 Runner commit 和输出证据。
6. 策略选择 Gate：正确性/稳定性（最高）、Canonical Contract 语义、Delta 兼容、迁移成本、部署复杂度、性能、成本。通过前**不选 A/B/C**。

## 5. 代码归属与实验隔离
- 本 Change 仅保存讨论、备选路线与验收标准。Experiment implementation（依赖、Python Parser、dbt profiles/models、fixture、test scripts、CI artifact）放 **JohnZhang-DataForge/Self-Runner** 独立 `experiments/hl7-dbt-canonical/`（先查其最新文件规范，不改现有带资源访问权限的 Workflow）。
- 不在 Healthcare repo 创建实验性 `dbt_project.yml`、notebook、wheel、test 或临时运行脚本；正式产品源码归属等实验定案并审批后再进行单独 Implementation Change。
- 实验最好在 GitHub-hosted ubuntu-latest 或容器隔离执行；不得用长期持有权限的 Self-hosted Runner 接触 K8s/Azure Secrets。原生 Fabric dbt 的 root dbt_project.yml 限制不应迫使现有 Healthcare 源码目录返工。

## 6. 安全/回滚
- 本轮仅文档/本地 POC，无任何 Azure Blob/OneLake、F4 Capacity、K8s/OIE PVC、Warehouse/PG、真实 canonical_patient/encounter 表操作。
- 负向测试任何缺失字段必须严格 HOLD/QUARANTINE，不做静默默认值；现有不可变来源 manifest 仍是 batch authority。
- 失败回滚仅删除 Self-Runner POC branch / 临时本地输出，不触及已验收 FHIR G4 或 OIE 生产者；正式实施需另外申请真实运行授权与最终 OpenSpec。
- 证据：Self-Runner 具体 PR/Head、测试日志及运行环境版本。尚无实际执行的项目一律标记 PENDING。

## 7. 参考
- `documents/architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md`
- `documents/architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md`
- `documents/architecture/DATA-FLOW.md`
- `local-data-platform/spark/contracts/canonical/patient-v1.json` 与 `encounter-v1.json`
- `documents/systems/data-platform/clinical-producers/OIE-CHANNEL-POC.md`
- Microsoft dbt-fabricspark README: https://github.com/microsoft/dbt-fabricspark
- DuckDB Delta extension: https://duckdb.org/docs/current/core_extensions/delta
