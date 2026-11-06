# OIE HL7 v2.5.1 ADT 业务事件 V2 — 离线实现与验收边界

> 状态：**SOURCE / STATIC PASS（GitHub-hosted offline CI）**；当前尚无新版本 OIE Channel 实机导入/运行，也未完成 Raw HL7 → Azure Blob 交付。本文件不授权任何真实资源写入。任务与证据见 [Active OpenSpec](../../../../openspec/changes/operationalize-oie-hl7-adt-feed/tasks.md)。

## 业务目标

这条 Hospital B 模拟 HL7 路线要展示**不同医疗数据源格式**，而 FHIR Fabric PySpark 与 HL7 Parser + dbt 展示**不同数据处理引擎**，均在相同 Canonical v1 Patient/Encounter Candidate → 一套 Silver Approval 和共享 OMOP 逻辑汇合。OIE 是医院来源的 HL7 Producer，不执行 dbt、不写 OMOP、更不先将 HL7 解回 FHIR。

首版逐事件：
- `ADT^A01`：来源 Encounter class=IMP，status=`in-progress` 或 `finished`，以 `period.start` 时间为入院。
- `ADT^A03`：仅 `finished` 且拥有**真实** `period.end`，出院时间不早于入院时间；PV1-45 和 MSH/EVN-2 从真实结束时间计算。
- 没有 A03 的源只表示已入院/尚未证实出院，后续 dbt 不得为了满足非空 `end_datetime` 假造 Encounter Completion。
- A08 更新、MLLP Listener/Sender、ACK/NACK、远端 Blob Publisher、Fabric Silver 物理写入在 OpenSpec 其它独立任务，尚未实机验证；“可操作”的目标不等于一次实现整个 HL7 v2.x 标准。

## Versioned V2 源码与现有环境保护

- 旧 `local-data-platform/apps/clinical_producers/oie/adt_a01.js`、`build_channel.py` 与旧历史 Channel ID `69ace705-a675-45f6-b126-a3b22a65212a` **保持原样**。其历史实机验收（31 FHIR → 1 A01, 30 non-IMP SKIP）不由此版本重复运行。
- 新 `local-data-platform/apps/clinical_producers/oie/adt_events_v2.js` 为 OIE Rhino/ES5 纯生成函数 `fhirToHl7AdtEventsV2`；同一已验证 mini-Bundle `finished` 生成两条独立 `A01`/`A03` event 记录、`in-progress` 生成一条。每条有不同稳定 MSH-10，原始 HL7 v2.5.1 bytes 独立保留。
- 新 `build_adt_events_v2_channel.py` 从既有已验证 OIE Upstream XML Fixture 渲染一个**全新确定性 Channel ID** 的 OIE Channel Reader；`requested_event_type` 在输入 envelope 仅请求该事件类别，OIE 函数**独立**决定是否具备临床资格；一条 OIE Channel Message 返回一个原始 HL7 消息或显式 NOT_APPLICABLE。Channel 仍为 upstream none Writer，因此**不表示**已安装完整下游 Publisher。不能将一次 preprocessing 返回的 A01/A03 拼成单个传输“消息”。
- 严禁在没有新来源 SHA、K8s/OIE/Session 审计和精确审批时导入此新 Channel 或重放已有完成批次。

## 临床字段边界和来源验证

HL7 源直接从 **真实 FHIR Patient/Encounter 字段**投影：

| HL7 Field | 来源 | 当前 V2 Pilot Scope |
| --- | --- | --- |
| PID-3 | Patient.id + Assigning Authority | 有效来源限定 ID |
| PID-5 | Patient.name | HL7 正规转义，缺少姓名不伪造 UNKNOWN |
| PID-7 | Patient.birthDate | 必须 YYYY-MM-DD 合法日期，转 YYYYMMDD |
| PID-8 | Patient.gender | Pilot 仅 male→M、female→F；other/unknown 因 profile 未审核而 HOLD |
| PID-10 | US Core Race `extension/ombCategory/valueCoding` | CDCREC OMB 单一代码，来自 FHIR 扩展（非任意文本），无/多值暂 HOLD |
| PID-22 | US Core Ethnicity `extension/ombCategory/valueCoding` | CDCREC 单一 OMB code（Hispanic/Non-Hispanic），缺失/错误 HOLD |
| PV1-19 | Encounter.id + Assigning Authority | 同一真实 Visit |
| PV1-44 | Encounter.period.start | 入院有时区，规范化 UTC |
| PV1-45 | Encounter.period.end | 仅在 A03 真实出院时写入 |
| MSH-10 | hospital/feed/request/encounter/A01 or A03 | Event-scoped 稳定控制 ID |

- 使用的 US Core FHIR 扩展与代码系统须经来源 Profile 验证：[US Core race](https://hl7.org/fhir/us/core/STU6/StructureDefinition-us-core-race.html)、[US Core ethnicity](https://hl7.org/fhir/us/core/STU6/StructureDefinition-us-core-ethnicity.html)。多种 race/repeat/multi-coding 实例需要**另立 Mapping Profile 审核**，不能随意选择第一个代码而损失临床语义。
- 病人出生日期、gender、race、ethnicity、Encounter.period.end 不存在或不合法时阻断，不填固定默认值；已验证旧 A01 不自动满足新 V2 requirements。
- 编码和日期字段归属于医院 Source Adapter；Canonical 之后的 OMOP mapping/Concept/Identity 仍以共享业务框架管理，绝不在 OIE Channel 里自建 OMOP Mapper。

## 独立 CI（无需集群/云权限）

- 新 JS 测试：`.github/quality/tests/data-platform/clinical-producers/oie/test_adt_events_v2.js` 覆盖 A01/A03 时间、PID/PV1、FHIR source facts、缺字段、错误编码、临床状态、稳定 ID、不同 Hospital、HL7 转义和 ES5 VM。
- Python static test：`.github/quality/tests/data-platform/clinical-producers/oie/test_adt_events_v2_channel.py` 验证 XML 与旧 Channel ID 区分、one-event source wrapper、Channel Reader 和确定性。
- 新 GitHub-hosted CI：`.github/workflows/oie-adt-events-v2-unit.yml`，`permissions: contents: read`；不连接 Azure、OneLake、worker01、OIE 8443/Derby、K8s 或 PHI。
- **已验收离线证据：** [PR #735 最新 CI（首次完整代码验证）](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42220398131) — V2 Node 10/10、Channel XML 4/4、第三方 hl7apy 3/3、旧 A01 回归 10/10 PASS。真实冻结 Synthea FHIR Source Profile、实际 OIE 新 Channel 运行仍 **OPEN**。
- **独立实机门禁：** 只有 Node/Static CI 不能宣称 OIE v2 已运行。需在受控授权后用新来源批次部署到 OIE，并由独立读回解析 HL7；Blob Delivery 另需 manifest-last + remote GET/sha 验证。

## 下阶段必需的真实工程工作

下一阶段要完成：实机部署前只读审计、Channel Writer/Transport 方案与单消息持久化、原始 HL7 bytes 的出口、source+processing identity + Blob manifest-last/remote GET、failure/replay/HOLD 以及 Sender 两次事件请求 A01/A03 的执行/回退。MLLP/ACK 属于之后展示真实医院消息传输协议时单独开放的受控接口。**这些任务当前均未完成**。

## 共享 HL7 Blob Publisher 扩展（新 A03 离线阶段）

**复用而非另建：** 当前仓库已经拥有 `local-data-platform/apps/clinical_producers/azure_blob_publisher.py` 的不可变条件创建、每对象独立读回和 `landing-manifest.json` manifest-last；`blob_publish_contract.py` 是共享 FHIR/HL7 传输入口。此前 HL7 plan 校验仅有 A01；新的离线实现加入 `oie/hl7_readback.py::parse_adt_a03`，允许严格验证的 A03 与 A01 原始消息分别以 `hl7/<source-visit>-A01.hl7`、`hl7/<source-visit>-A03.hl7` 作为**两个独立对象**发布，MSH-10 与 Plan `source_event_id` 必须一一对应，不能覆盖已有对象。仍只使用既有的 `publish_immutable`；这次新增的 Mock Blob 测试不是 Azure 实机成功记录。

**下一项阻断：** 既有 `oie_hl7_publisher.py` 的 `prepare_oie_hl7` 和 `oie_persisted_readback.py` 均仍是 A01-only/每 Encounter 一条消息的 legacy 接口。真实 V2 会对完成的一次 Encounter 生成两条 OIE 持久消息（各自 Message ID、MSH-10、事件类型），所以必须先新增 versioned Event Receipt（组合键 `encounter_id + event_type`、Channel ID、Message ID、原始字节 SHA、来源批次身份），并确保原 API 不发生行为改变。必要时需要让 OIE **实际持久化/GET** 能独立分辨 A03 与 `OIE_ADT_V2_EVENT_NOT_APPLICABLE`，完成失败/未知 ACK 审计之后才能启动真实 Blob PUT。

**当前不属于已验收：** 真实 OIE Source Channel v2 的部署、使用真实冻结 FHIR 源、Azure Storage RBAC、工作负载身份、远端 Azure GET/ETag、经批准的 Fabric Silver 发布。严格 A03 mock 验收仅覆盖未来 Publisher 的传输及计划子集。

## 双事件 OIE Message Receipt（新版本：离线阶段）

旧 `oie_persisted_readback.py::fetch_persisted_readbacks` 的接口为**每 Encounter 一条消息**，且旧 transport parser 将所有以 `MSH|` 开始的 Source Connector Payload 临时分类为 `ADT_A01`。这对 V2 一次住院可能产生两条分别可审计的 A01/A03 不成立。**旧接口保持冻结**，不静默更改其语义。

新 `local-data-platform/apps/clinical_producers/oie_event_readback_v2.py` 用 `(source_encounter_id,event_type,message_id)` 绑定单条 OIE 源消息，必须有明确的新 Channel ID、医院/Feed/Request/Assigning Authority；复用现有只读 Scoped GET 及 OIE Source Connector 安全 XML 解析，只允许显式 GET 的 Message IDs，不枚举或发送/重放消息。返回**原始** HL7 bytes、SHA256、Control ID；根据实际 A01/A03 subtype 重新做严格解析和来源关联检查，而不是相信旧的 legacy A01 disposition。A03 若没有已核实的 A01 在同一受控输入中则 HOLD（跨批次晚到出院留待 versioned reconciliation 设计）。

新静态测试：`.github/quality/tests/data-platform/clinical-producers/oie/test_oie_event_readback_v2.py`，使用 V2 Node 生成的消息嵌入 OIE 4.7 仿真持久 XML 响应，并使用 FakeScopedGetter。任何离线通过都不是 **真实 worker01 OIE 新 Channel GET** 或 Azure Blob 发布证明。正式发布前还需要冻结 FHIR Source Handoff / Event Type 与每条 OIE Message ID 的双向验证，以及现实运行的独立 GET、SHA/manifest-last。
