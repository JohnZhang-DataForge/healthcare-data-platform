---
status: approved-target-design
scope: fhir-hl7-multisource-mvp
last_reviewed: 2026-10-19
implementation_status: not-started
---

# Healthcare V2 — FHIR R4 / HL7 v2 多来源 MVP 设计

> **设计方案已确认；本文件不代表已实现、部署或完成运行验收。** 本文仅冻结 FHIR/HL7 来源、合成患者交叉关系与最小交付边界；PG→Fabric 的资源部署、账号迁移另议。实施以 [OpenSpec Change](../../../openspec/changes/design-fhir-hl7-multisource-mvp/tasks.md) 之后分别批准的功能 Change 为准，项目 CURRENT/NEXT 仍以 [PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md) 为准。

## 1. 目标与设计原则

- **MVP First**：优先三条来源真实可运行、可验证、可展示；拒绝为“生产级完整性”提前建设额外中间件。
- **共享生成核心、隔离来源**：复用一套上游 Synthea 核心与明确版本化的合成患者基线，投影为 Hospital A/B/C 三个**模拟**来源系统。三者是逻辑独立的源身份/交付合同，**不宣称是三个真正独立的真实 EHR 或三份独立患者样本**。
- **部分患者重叠**：同一个合成患者可出现在多个模拟医院，但各有不同、稳定的院内标识；不根据姓名/生日“猜测”身份，也不简单把同一就诊事件复制三遍。
- **格式和职责分开**：Synthea 原生生成 CSV 和 FHIR R4；OIE 的 Channel Transformer 根据标准化事件输入生成 HL7 v2 ADT，不另造 Python HL7 v2 编码器。Fabric 不运行 OIE，负责解析落地的原始 FHIR/HL7。
- **现有运行链路优先保护**：Local OMOP 已验收的是 NEW_ONLY Person/Visit；当前目录迁移后新路径 Runtime 兼容仍待验收。新数据源不回放旧 Batch、不修改冻结 Writer/Claim，不让 FHIR/HL7 依赖尚未完成的 UPDATE_ONLY/MIX_DATA。
- **全链路可追溯**：源 ID、版本、Batch、文件校验、关联关系及错误场景可以独立复核；只是设计已确认，非运行事实。

## 2. MVP 数据流和系统边界

```text
                    Versioned Synthetic Cohort / Scenario
                       Synthea Core + Patient Crosswalk
                                     |
                  +------------------+------------------+
                  |                  |                  |
              Hospital A         Hospital B         Hospital C
               CSV/OMOP          FHIR R4 JSON       CSV/JSON events
                  |                  |                  |
      Local Kubernetes DP       Blob: fhir/       OIE in Kubernetes
      S3→Airflow→Spark→PG        hospital-b/          Transformer
                  |                  |                CSV/JSON→HL7 v2
           PG exporter (*)           |                  |
                  |                  |             local file spool
                  |                  |                  |
                  +-------+----------+----------+-------+
                          |                     |
                         Azure Blob: OMOP / FHIR / HL7
                                          |
                               Fabric Data Pipeline
                                          |
                               OneLake Bronze (raw)
                                          |
                               Fabric PySpark Notebook
                                          |
                             Silver + cross-source mapping
                                          |
                        Small Gold / patient timeline demo
```

(*) PG Exporter 与 Fabric 的详细资源/账号重建**不在本方案内**，沿用现有 [V2 总路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md) 和 [Azure/Fabric 系统说明](../../systems/azure-fabric/README.md)。上述三源云端 ETL 均未在本轮实现；“Hospital”仅为合成源命名。

### 2.1 Hospital A — 本地 OMOP

- 沿用 Synthea CSV → 本地 S3 → Airflow/Spark → PostgreSQL OMOP 的既有方向；本轮不改任何本地部署或业务 Writer。
- Fabric 只读取将来经一致性导出的 OMOP 分析副本，不直接回写本地 PG。
- OMOP person_id 是目标数据库主键，**不能当作**跨医院统一身份。

### 2.2 Hospital B — FHIR R4

- 复用**同一套 Synthea 程序版本/基础合成群体**，按 Hospital B 的稳定子集与来源规则导出 FHIR R4，首期 **Patient、Encounter**；保留必要关联的 Bundle/Reference 和原始 JSON。
- MVP 使用 Synthea 的原生 FHIR **Bundle JSON**，不先建设 HAPI FHIR Server，也不强制 NDJSON；若未来使用 Bulk NDJSON，必须作为明确的合同变更处理。
- 以不可变 Batch 将文件上传 Azure Blob `fhir/hospital-b/<batch_id>/...`，全部校验成功后才写 READY Manifest；Pipeline 只消费 READY 批次。
- Fabric Bronze 保留原始 JSON；PySpark 在 Silver 提取源 Patient/Encounter、稳定引用、必要的基础 DQ。禁止默认将 FHIR Patient.id 等于 OMOP person_id。

### 2.3 Hospital C — HL7 v2

- Synthea **不原生提供本方案的 HL7 v2 ADT 导出**。先根据 Synthea 的 patients/encounters 和医院场景/身份映射制作一个**轻量标准化事件输入**（例如 JSON，包含 hospital_patient_id、event_id、event_time、encounter、event_type）。这一步只完成关联和医院事件选择，**不自行编码 HL7 v2**。
- 在本地 Kubernetes 部署 **Eclipse Open Integration Engine（OIE）**，用版本受控的 Channel/Transformer 将标准化事件转换成 HL7 v2 ADT；MVP 选择 `ADT^A01`（入院）、`ADT^A08`（患者信息更新），`ADT^A03`（出院）作为较小的下一步扩展。只选择事件语义匹配的源记录，不把任意 Encounter 强行当入院。
- 每条消息保留 `MSH-10` 消息控制 ID、`MSH-7` 事件时间、`MSH-9` 事件类型、`PID-3`（包括 assigning authority）和 `PV1` 等字段。固定 `source_system + event_id + message_type` 到稳定 `MSH-10` 的映射；不能每次重试产生新 ID。
- **首版单 OIE Channel、文件交付**：OIE File Writer 保存 UTF-8 原始 HL7 文件到有持久化保障的本地 spool；轻量 Blob Publisher 读取成功封存的文件，按不可变批次推送到 `hl7/hospital-c/<batch_id>/...`，校验后发布 READY Manifest。允许简单限次重试、失败留档与人工重新发起；上传失败不得发布 READY。
- 不加入 Kafka。**MLLP Sender/Listener、ACK 演示、双 Channel 互发与完整消息确认协议不作为第一版成功的前置条件**。将来需要展示 MLLP 时另开 Change，ACK 成功也不得被解释为 Blob 上传或 Fabric 处理成功。
- Fabric Bronze 保留原文，PySpark 用经过测试的 HL7 v2 解析逻辑提取 `MSH/PID/PV1`、验证消息类型与字段并生成带 source_system 的 Silver；**Fabric 不部署 OIE**。
- OIE 是推荐组件，实施前必须检查可用发行版本、许可证、容器/K8s 部署与 File Reader/Writer、Transformer 的实际行为；不得把旧 Mirth 示例当作 OIE 新发行版的实测证据。若发行版不可用或不稳定，先记录阻塞，不擅自转向商业 Mirth 或大范围自研。

## 3. 同一患者跨三个医院：合成身份与数据选择

**固定版 Synthetic Patient Registry / Crosswalk** 是本 MVP 的轻量、版本化数据合同（可先用小型 CSV/JSON 文件，不建服务和数据库），内容至少包括：

| 字段 | 用途 |
| --- | --- |
| `synthetic_person_key` | 合成患者唯一稳定主键，来源于冻结的基础人群 |
| `source_system` | `hospital-a-omop` / `hospital-b-fhir` / `hospital-c-hl7` |
| `source_patient_id` | 各医院稳定、互不混用的患者标识 |
| `cohort_version` / `scenario_version` | 冻结选择逻辑和来源群体 |
| `source_record_ref` | 可追溯到输入患者/事件的记录引用 |

- 规模示例（**仅演示目标，不是实际数据量**）：Hospital A 200 人、Hospital B 150 人、Hospital C 100 人，选取约 30 人出现在多个系统中；实际总体去重人数由明确的交集分布计算，不能直接将三组人数相加。
- 第一版优先**一次生成并冻结基础患者群体**，按确定的集合与事件投影到 A/B/C；各医院赋予不同源 ID、不同事件子集或新增合成场景，不是复制三份同样就诊记录，也不宣称“三套独立 Synthea 生成相同患者”已自动实现。
- 相同患者在不同医院的出生日期、性别等不可无解释地随机漂移；故意制造质量异常时需单独标记 `scenario_version`，用于明确的数据质量演示。
- **身份重叠 ≠ 数据更新**：已有 Synthea Snapshot/演化（`-u/-i`）能力以后可用于 NEW+UPDATE 情景；本 MVP 不以已有 UPDATE_ONLY/MIX_DATA 功能作为依赖，且不能仅凭同一 seed 保证患者身份不变。
- Crosswalk 只用于可验证的合成数据关联；没有明确 crosswalk 的跨系统记录保持 `unresolved`，不以姓名、生日作自动匹配。

## 4. 文件合同、验证与最小失败处理

每个来源独立 `source_system`、`batch_id`、`manifest.json`，不可变写入原始文件；Manifest 最后发布为 READY，至少包含：`source_system`、`batch_id`、`cohort_version`、`scenario_version`、`schema_format/version`、文件清单、条数、SHA-256、生成时间/来源修订版本。具体 JSON Schema 在实施 Change 中冻结。

- **FHIR**：检查 Bundle 语法、Patient/Encounter Reference、必需字段、重复输入不会形成重复 Silver 记录。
- **HL7**：检查版本/分段、MSH-10、PID-3、PV1、事件类型；用 `source_system + MSH-10` 保证跨批次重复消息不会产生重复事件；同 ID 不同内容视为冲突而不是静默覆盖。
- **文件发布**：本地 spool 文件确认写入完成后才允许读取；Publisher 上传、读回/哈希校验后发布 READY。Blob 故障只留下可重试状态，不报告完成；同一消息重新发布应内容一致。
- **Processing**：Fabric 读取 READY 原始文件；在 Silver 用来源键、患者 crosswalk 与事件键做确定性去重，失败记录可追查到原始文件、batch 和 source，而不是仅依赖 Pipeline Success。
- **状态语义**：`SOURCE_GENERATED` → `OIE_TRANSFORMED`（仅 HL7）→ `BLOB_READY` → `FABRIC_PROCESSED`。这些是建议的可观察状态，不代表现有状态机已经实现。

## 5. 第一版验收范围与非目标

| 检查项 | 最小验收 |
| --- | --- |
| FHIR | 至少一批真实合成 Patient/Encounter R4 Bundle → Blob READY → Bronze/Silver；重复批次无额外重复 |
| HL7 | OIE 实际把标准化合成事件生成 A01/A08、输出原始消息 → Blob READY → Fabric 解析；至少一次无效消息/上传故障验证 |
| 跨源 | 固定跨系统共享患者子集，各医院 ID 不同，通过 Crosswalk 能查出至少一条跨系统 Patient Timeline；未映射患者不会错误合并 |
| 可展示 | 保留可公开的合成数据、源码 SHA、Batch、处理行数与成功/失败结果；外部展示由独立 Showcase Change 决定 |
| 未完成标记 | 单元/静态通过、K8s/OIE 实际运行、Blob 实际读回、Fabric E2E 分别标状态；不得互相替代 |

**暂不做**：Kafka、HAPI FHIR Server、独立 Python HL7 v2 编码器、完整 MLLP/ACK 演示、第二套 OIE、实时 CDC/流处理、复杂主患者索引 MPI、完整 UPDATE_ONLY/MIX_DATA、全部 OMOP Domain、完整 Gold、付费 Mirth 许可采购、账号/Trial 重建自动化。

## 6. 交付与变更边界

1. 本文件是跨系统**长期目标设计**。实施时使用**独立 OpenSpec 功能 Changes**（FHIR、HL7、Crosswalk/分析）管理 Proposal/Tasks/测试，`documents/` 不维护平行进度表。
2. 先完成必要的 Local DP 目录路径兼容与可验证的 OMOP→Fabric 最小链路，再依次引入 FHIR、HL7 与 Crosswalk；如果不影响已验收本地链路，FHIR 的生成合同可以独立开展静态设计。
3. 变更均用最新 Main、功能分支、PR、适用 CI 和明确授权的运行/读回证据；不重放已冻结的 TASK004 数据，不运行未经授权的 Terraform Apply、K8s 部署或 DB Writer。
4. OIE Channel、场景映射、Crosswalk、Publisher 和 Fabric 解析模块应成为正式 Git 源码/配置，环境 ID、Blob 凭据与租户配置外置；具体目录在对应实现 Change 里确定。
5. 此设计**不改变 Fabric 环境/账号可移植性**的单独决策；只要求本方案无硬编码身份/资源 ID。

## 7. 来源与相关文档

- Synthea 官方格式/配置：[Synthea README](https://github.com/synthetichealth/synthea)、[FHIR R4 Export](https://github.com/synthetichealth/synthea/wiki/HL7-FHIR)（原生 FHIR R4/CSV；未声称原生 HL7 v2）。
- OIE [项目源码](https://github.com/OpenIntegrationEngine/engine) 与 [Eclipse 项目说明](https://projects.eclipse.org/proposals/eclipse-open-integration-engine)；实际可用镜像/插件/版本须在部署前核验。
- Mirth 家族 JSON→HL7 的[社区 Channel 示例](https://github.com/marlycormar/mirth-connect-channel-examples)：仅证明技术方案有参考，**不代表已对 OIE 当前发行版做了兼容测试**。
- [Healthcare V2 总路线](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md) · [Local Data Platform](../../systems/data-platform/README.md) · [Azure/Fabric](../../systems/azure-fabric/README.md) · [Project Status](../../engineering/status/PROJECT-STATUS.md)。
