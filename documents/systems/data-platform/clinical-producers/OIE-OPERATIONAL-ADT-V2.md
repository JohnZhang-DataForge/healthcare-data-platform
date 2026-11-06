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

## V2 Source Manifest → Event Receipts → 共享 Blob Bridge（离线实现）

- 新增独立适配层 `local-data-platform/apps/clinical_producers/oie_hl7_publisher_v2.py`：先用现成 `source_handoff.verify_handoff` 核查**冻结 Request/Manifest SHA + 原 FHIR 文件 SHA**，按每一源 Encounter 核对 A01/A03 完整事件集合；随后仅经 `oie_event_readback_v2.fetch_v2_event_readbacks` 对明确的新 Channel/Message ID 做持久 GET。非住院/非适用状态计数跳过；住院进行中只允许 A01，完成住院必须 A01 和 A03，缺/多 Receipt 均 HOLD，不读历史消息。
- 独立核对源 Patient/Encounter 与 OIE 持久 HL7 原字节中的 PID-3/5/7/8/10/22、PV1-19/44/45、事件时刻及 SHA；缺 DOB/Gender/US Core OMB Race/Ethnicity、缺出院或字段冲突，**Blob PUT 前** fail closed。V2 独立对象 `hl7/<encounter>-A01.hl7` / `-A03.hl7` 只复用共享 `azure_blob_publisher.publish_immutable`；对象条件创建、远端 GET、manifest-last、同 Request Replay 与冲突 HOLD 均由共享模块负责。
- 新 CLI 只读扫描已冻结 Synthea FHIR，输出无 Patient/Encounter 标识符的 aggregate mapping 计数与代码级 HOLD 原因。已接入 GitHub-hosted `synthea-new-generator-real-smoke.yml`，结果应以实际 Run/日志为准。仅在源数据被证明兼容当前 V2 strict Pilot Profile 时标记支持；多 Race/category 或未知扩展必须 HOLD 或另行审核映射，不能造值。
- 新离线测试 `.github/quality/tests/data-platform/clinical-producers/oie/test_oie_hl7_publisher_v2.py` 与既有 ADT Hosted CI 集成 Fake OIE 4.7 XML、双消息/独立 Fake Blob 读回；**CI 不能证明 V2 Channel 实机导入、POST/ACK、Derby/PVC 实际写入、Azure Blob 实际远端 GET 或正式 Fabric Canonical/Silver。** 真实操作须重新核查 Session Coordination、目标 SHA、共享资源占用及逐项显式授权；旧 Channel、Derby/PVC、A01 和历史 Batch 不动。

## 冻结真实 Synthea FHIR ↔ V2 Pilot Profile 的首次实证（2026-11-06）

- [GitHub-hosted Real Source Run #42231391800](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42231391800) 使用固定来源 Synthea v3.3.0 在隔离 runner 生成并冻结新的 Johns Creek Hospital B 请求 `ci-johnscreek-fhir-0001`；已读回 Source Manifest SHA `05fe2808331522f2b8dae77c7e844ce0fa2e75081fa41adbedda0e9a49246b81`，并严格核对真正 FHIR 文件。匿名 V2 审计输出 `PROFILE_COMPATIBLE`：31 Encounter、1 inpatient、1 A01 eligible、1 A03 eligible、30 non-IMP skip、0 HOLD。证明**这一次**原始 FHIR Patient DOB/Gender/US-Core OMB Race/Ethnicity 和 finished Encounter period 可以按当前严格规则映射；新样本变化时必须重新审计，不能填造临床事实。
- [Hosted OIE V2 Run #42231391604](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42231391604) 的 V2 Frozen Manifest → Fake OIE persistent A01/A03 → 共享 Fake Blob Adapter 新回归 12/12 PASS；继承已有 OIE V2/legacy 的既有回归全部 PASS。此处 **Real Synthea SOURCE Profile 兼容性** 与 **模拟 OIE/Blob 的离线 E2E** 是两个不同证据；尚未把 real Synthea 原始 Encounter 实际 POST 至 OIE，更未从 Derby 真实 GET 或从 Azure 实际远端 GET。

## V2 Source-bounded one-shot OIE POST / Event Receipt（离线构建）

- 新增 `oie_message_submit_v2.py`（独立于历史 `oie_message_submit.py`）：只有 `johnscreek-hl7-gh-<new-run-id>` 的冻结 NEW Request + 精确 Manifest SHA 才能构建 A01/A03 单事件 JSON envelope，并强制固定 V2 Channel UUID；来源读取严格复用 `oie_hl7_publisher_v2._source_inventory` 与 `_expected_for_envelope`，Clinical 状态由 OIE 新版 JS 重新判断，不在 Sender 制造 HL7 字节。
- `ScopedOIEV2Poster` 继承**既有** `ScopedOIEPoster`（HTTPS/TLS/登录/POST/ACK/安全错误处理），通过少量参数化复用既有只读 Channel GET 预检，以独立 V2 `render_channel_v2()` XML、Channel Name 和 STARTED 状态检查；不接受旧 A01 Channel ID，绝不引入第二套 HTTP 客户端。
- 对合格的 finished IMP 发送 **两条独立请求**（先 A01 后 A03），in-progress IMP 仅发 A01，非住院 SKIP 不发送无效 ADT；本地记录跳过计数。所有消息各有独立 OIE 数字 ID，只有完全 ACK 才组装 `healthcare-oie-adt-v2-new-event-receipts-v1`；未知/超时/重复 ACK 立即 HOLD，无自动重试或猜测 Message ID。接收侧 `verified_v2_post_receipts` 再核对新 Run、Request、Hospital/Feed、Manifest、Channel、事件完整性与 Skip 数，才转换为已有 `OIEV2EventReceipt` 对象交给 V2 只读 GET → 共享 Blob Bridge。
- 不在此 PR 中增加独立自托管 Runtime Workflow。**Self-Runner 旧 `azure-blob-johns-creek-hl7-e2e-manual.yml` 锁定旧 A01 Channel 与旧 SHA，不兼容本 V2。** 新版本实机必须在分离的 Session Coordination 和当前集群/OIE/Secrets/ Azure 前置审计之后编制经审批的 V2 Controller；`submit_v2_new_request` 目前只由 GitHub-hosted Fake Poster 测试，不代表已执行任何真实 OIE POST。

## New V2 source-bound ACK verification (offline)

- `oie_message_submit_v2.verify_v2_receipts_against_frozen_source` independently reopens the original Synthea Source Manifest and recomputes all expected A01/A03 events before accepting the receipt envelope for existing `fetch_v2_event_readbacks`. The receipt alone never authorizes historical OIE GET or recovery from unknown POST outcomes; actual source/controller Run and safe authorization must be separately evidenced.
- Hosted [PR #742 OIE V2 Run #42273806754](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42273806754) verifies 10/10 new fake sender/receipt negative and positive tests. This is **offline SOURCE_PASS**, not actual V2 Channel deployment, real OIE persistence, or Blob publication. Existing Self-Runner live workflow still locks the old A01 Channel and is not a V2 controller.

## 安全的新版 OIE 运行前核对入口（已有源码，尚未手动执行集群）

- Self-Runner 的 [PR #529](https://github.com/JohnZhang-DataForge/Self-Runner/pull/529) 新增 `.github/workflows/oie-adt-v2-readonly-preflight.yml`。它固定 Healthcare Producer PR #742 的 merge SHA `f57cd8a5ab33f41b9aa900aa45f0160c3746abaf`，严格区分旧 A01 Channel `69ace705-a675-45f6-b126-a3b22a65212a` 和新的 V2 Channel `6b91681e-5b3b-59cb-b270-09412054110c`；不使用历史锁定旧 SHA 的 HL7 E2E 工作流进行新版验收。
- 使用 Self-Runner 主分支的 Actions → **OIE ADT V2 worker01 and Channel GET-only preflight** → Run workflow，手工输入 `INSPECT_OIE_V2`。该 Workflow 的实际 worker01 检查**仅在手动触发且 Main + 精确确认值**时运行：K8s 仅 `kubectl get` 固定 Node/PVC/Deployment/Service/active Jobs 与既有 Secret keyset；使用原有 `OIEScopedHTTPSClient` 的叶子证书 pin 及现有内部身份进行 OIE 登录，仅 `GET /api/channels`、新 V2 Channel 配置、状态。不读取患者消息、不使用历史 GET、不打印凭据、没有 Channel 变更/消息 POST/Blob PUT。该流程的自身 Runner Pod 启动会产生集群短暂负载，因此仍应在 Session Coordination、真实资源使用与准许范围核对后再手动触发。
- 解释证据：`OIE_V2_CHANNEL_STATE=ABSENT_IMPORT_REQUIRED` 表示当前尚未安装 V2，仅证明读取成功，不能说 V2 已可用；`PRESENT_EXACT_CONFIG_NOT_STARTED` 意味着仍无法提交；`PRESENT_EXACT_CONFIG_STARTED` 也只能证明配置/运行态，只读结果**不授权**新的 Channel 导入、任何事件 POST 或 Azure 写入。配置/来源身份/其他活动 Job 无法确认时 HOLD。完备 E2E 仍需被批准的新 FHIR Request 经过 OIE Message ID ACK、Derby 独立 GET、共享 Blob Publisher 的 immutable PUT/远端 GET/manifest-last。
- **已完成的是源代码及 Hosted 测试，不是实机：** [PR/Hosted Run #42276226069](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42276226069)、[合并后 Hosted Run #42276333955](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42276333955) 均 PASS；截至本次证据收集，未执行 Main 手动 `INSPECT_OIE_V2`。真实集群环境的唯一可信结论必须以未来获批的 Run ID/独立只读记录为准。

## 新版独立运行入口与 K8s Job 合同（源码候选，实机待审批）

- Sender CLI: `python3 -m apps.clinical_producers.oie_message_submit_v2`，通过固定新 `johnscreek-hl7-gh-<Run ID>` + Manifest SHA + V2 Channel 预检，完成 A01/A03 分别 POST 后仅在每一条 OIE 数字 ACK 全部齐全时打印 `OIE_V2_NEW_REQUEST_RECEIPTS_JSON`；POST 超时或任何未知结果不重试、也不假装真实持久验收。临床状态仍由 OIE Channel 内的 FHIR→HL7 纯 Mapper 再次判定。
- Publisher CLI: `python3 -m apps.clinical_producers.hl7_blob_runtime_v2`，只消费由**同一次已获准的 Controller**冻结的 `new-oie-v2-receipts.json`。独立重读原 FHIR Manifest 和预期事件集合；对指定新 OIE Message ID 独立 GET 严格核对原始 HL7 的 PID/PV1/MSH-10/来源时间/Patient/Encounter，才初始化现有 Azure Blob SDK，复用单一 `publish_immutable` 实现 A01/A03 分对象的 Immutable PUT/远端 GET/manifest-last。它不重新 POST OIE，也不读未知历史消息；独立的 Controller 审批、上游真实 ACK 来源和 Azure Prefix 空检查仍需要另行验收。
- 对应正式静态 Job 模板：`local-data-platform/kubernetes/manifests/synthea/blob-publisher/submit-oie-v2-new-fhir-events-job.yaml.tpl` 和 `publish-oie-v2-hl7-job.yaml.tpl`。旧 A01 的 Job 文件不动。新模板只在源文件和 CI 中，不代表已有适配新版的 GHCR Digest、部署批准、实际运行或 Azure Raw HL7 已经发布。
- 测试：`.github/quality/tests/data-platform/clinical-producers/oie/test_hl7_blob_runtime_v2.py` 并入现有 Hosted OIE V2 Workflow，模拟独立临床事件 ACK→OIE 持久 GET→共享 Blob 两条 HL7 原始消息 → 独立 Fake Blob readback；失败案例必须在任何 Blob 初始化之前拒绝。CI/PR/真实执行状态请以独立 GitHub Run 证据为准，不能提前标记 Live E2E。

## V2 CLI / Sender-Publisher 源码合并的正式验收记录

- [Healthcare PR #746](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/746) 已合并为 Main `872000de1b5bfb839e514d29cd160276ed040733`。新文件 `hl7_blob_runtime_v2.py` 和 `oie_message_submit_v2.main` 是**能调用的应用 CLI**，但不是获批已部署的 K8s Runtime；两个新 Job 模板也只是在 Git 中存在。真实同 Run Controller 仍须单独实现/验收，不能直接重启旧 A01 Sender/Publisher。
- [Hosted V2 Run #42278062653](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42278062653) 在最终源 HEAD 上新 9/9（合成真实 JS ADT 字节/双事件 ACK/持久 OIE Fake GET/共享 Blob Fake PUT+GET/manifest-last/重播/损坏拒绝）和 V2 Sender 10/10、旧 A01 全部 PASS；[Hosted Synthea #42278062650](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42278062650)、[Azure Blob immutable tests #42278062550](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42278062550) 同样 PASS。由于当前 V2 必须保留单一审计过的 OIE 目的端，Sender 的 Channel GET 预检现在还比较预期的 Destination/Writer 和 Source Transport，若有漂移则在发送前 HOLD。
- **未完成的真实条件**：经明确授权后手工执行 Self-Runner 的 V2 GET-only Preflight；确认 V2 Channel 安装/STARTED、现有 Legacy Channel 完好、共享 Pod/Job 不冲突；核对真实 GHCR 内容 Digest 和 Azure Scope，新鲜不可复用 Request/Manifest/同 Run Receipt；最后真实 OIE POST/ACK、独立 Derby GET、Blob PUT + GET/manifest-last 才能标记业务 E2E。尚无这类真实新 V2 Run，不能引用 Hosted FAKE 测试或旧 A01 Run 代替。

## V2 Runner Controller — 源码与 Hosted 验收（尚未真实运行）

- 新 [Self-Runner PR #530](https://github.com/JohnZhang-DataForge/Self-Runner/pull/530) / Main `e56d6e10d08583d1370f13c014988ddc24341d6a`：`scripts/azure_blob_johns_creek_hl7_v2_e2e.py` 与 `.github/workflows/oie-adt-v2-e2e-manual.yml`。在**已审批的未来新批次**中，先完成 worker01/OIE V2 Channel 配置/STARTED/旧 A01 保留的 GET-only 检查，才可能产生新冻结 Synthea Batch；对真实 FHIR 执行 V2 A01/A03 source profile audit、Azure request prefix 无对象检查、OIE 单次事件 POST/ACK、独立 persisted Message ID GET、共用 Publisher Blob PUT/manifest-last/双对象 REST GET/HEAD/HL7 parser 对账。若 OIE POST 超时/ACK 结果不确定，立即 HOLD，禁止重提交/猜测消息/清理未知状态。 
- [PR #530 的最终合并后 Hosted CI #42282257632](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42282257632) 中 Controller 负向/来源/双事件/Remote GET 模拟测试 PASS，真实 Runner Job **skipped**。现有 `PUBLISHER_IMAGE=""` 是专门的 FAIL-CLOSED 运行门禁，若无经正式审查的 V2 GHCR Digest 会在任何共享资源写操作之前阻断。旧 A01 Controller、旧 Channel、Derby/PVC、现有 Azure 已提交 HL7 及 FHIR 保持原状。
- [Healthcare PR #748](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/748) 已使原 Azure Publisher 镜像在 Hosted clean build 中通过 V2 CLI 的 `--network none` Import/Help smoke；[Main Run #42280635889](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42280635889) 的 **GHCR 发布跳过**。发布正式 digest 必须另以 Main 手动 `workflow_dispatch` 执行、保存真实 digest 及镜像 revision/SHA 证据，再审查更新 Controller 的 `PUBLISHER_IMAGE`；不能复用旧 A01 的 SHA/Digest，也不能因用户说“继续”而启动有副作用的 E2E。
- 项目真实 OIE/Blob E2E 的下一步是**仅只读**手工运行已合并的 [V2 preflight (Self-Runner #529)](https://github.com/JohnZhang-DataForge/Self-Runner/pull/529)，固定新 Channel ID `6b91681e-5b3b-59cb-b270-09412054110c`，观测是否已存在/STARTED，以及 worker01/Secret/PVC 共享资源条件。新 Channel 若未安装，仍需单独批准部署；旧 A01 的真实 E2E 历史成绩不能替代新版 A03 验收。

## V2 Source Audit 返回接口修复与验收（2026-11-06）

- 原 V2 Controller 使用 Healthcare 的 `audit_frozen_adt_profile()`，它返回医院/Feed/源 SHA 和 A01/A03 统计，**不返回** `request_id`；Runner 却把 `request_id` 作为严格同次运行验收必需字段。直接进入真实 worker01 的 Source Audit 后就会因为字段缺失而 HOLD，属于离线 Fake 数据掩盖的接口不匹配。
- [Self-Runner #537](https://github.com/JohnZhang-DataForge/Self-Runner/pull/537) 已从已独立验证的 `verify_handoff()` 冻结 Request 补入 `audit["request_id"]`，**不放松**校验也**不修改** Healthcare 公共 Audit Schema；补充实际执行 K8s 嵌入审计 Python 代码的真实合成 FHIR fixture 回归测试。[Main CI #42291756749](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42291756749) 9/9 Hosted PASS，Live Job Skipped。
- 该修复仅消除真实接口必然失败的风险，未执行 OIE 实机只读预检、Channel 导入、FHIR POST、Derby GET 或 Azure PUT；运行前门禁和 `PUBLISHER_IMAGE=""` 仍有效。 
