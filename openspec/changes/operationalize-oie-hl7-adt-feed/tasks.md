# Tasks — Operational OIE HL7 v2.5.1 ADT source

> 目标是 **可真实运行且消息语义正确的医院 HL7 Producer/Feed**，不是声称实现 HL7 所有子协议。当前仅旧 OIE A01 Channel 的实机历史证明；A03 / Raw Blob / MLLP / Fabric HL7 均尚未验收。每项任务以 SHA + CI/Run + 独立读回判定；不因用户说“继续”而绕过 SAFE-OPERATIONS 的实际资源写入审核。

## Phase 0 — 设计与维护既有事实
- [x] 0.1 只读核对 Main OIE 4.7.0 Channel、FHIR→ADT^A01、已有 OIE Derby/PVC 及 Writer=none、Legacy 历史实机证据。
- [x] 0.2 核对 Canonical Patient/Encounter v1 必填信息、Self-Runner dbt POC 和隔离边界，规定 A01/A03 原始 HL7 → dbt → ONE Silver。
- [x] 0.3 docs/spec-only 提案 [PR #733](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/733) 经 Required OpenSpec Change/Static/Links/Index 检查通过并合并 Main `97758b51ca7446669fbe3cbfd19beb82482ed380`；未部署 OIE/Blob/Fabric。

## Phase 1 — OIE ADT Producer 可操作语义（offline first）
- [ ] 1.1 评审源 Patient FHIR Profile；实现 PID-7 DOB、PID-8 gender、PID-10 Race、PID-22 Ethnicity 的真实字段映射及缺失/未知/编码系统 Fail-Closed，保留独立 Stable Identity。
- [x] 1.2 完成**离线纯函数**的 versioned `ADT^A01` + `ADT^A03` 业务生成、明确时序及 `PV1-44/45`，源码单测/hl7apy 读回 PASS；现有已部署旧 A01 Channel ID/字节行为保持不动。OIE 新版本实机运行仍是 2.3/2.4 待办。
- [x] 1.3 新测试 `.github/quality/tests/data-platform/clinical-producers/oie/` 覆盖合成历史完整、in-progress A01-only、编码缺失、标识碰撞、负时间、时区和转义，Node 10/10 + XML 4/4 + 独立 hl7apy 3/3 + legacy 10/10 PASS（新 V2 Channel 实机不在内）。
- [x] 1.4 对应更新系统 CODE owner、人类 OIE 文档与本 Change tasks；正式离线源码 [PR #735](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/735) 已通过 CI 并合并 main `ea9dda11c0b683de993394a01c275e75250d47bc`。

## Phase 2 — Channel、原始传输、Blob（尚未授权实机）
- [ ] 2.1 构建 versioned OIE 多事件单消息控制 Channel/Router（新 Channel ID；禁止覆盖现有），独立导出/import 校验及内存队列/持久化策略。
- [ ] 2.2 设计 OIE 真实 HL7 raw bytes 出口及 Publisher（manifest-last、SHA256、独立远端 GET、source/proc/publication identities、replay/冲突 HOLD）；与现有 Azure Publisher 主线复用，禁止新造平行 Source Authority。
- [ ] 2.3 对 OIE persistent state / Session Coordination / 新 Batch 进行只读审计与显式有副作用操作审批，之后才允许真正 Channel 导入、Blob PUT、K8s 工作负载操作。
- [ ] 2.4 真正 OIE A01/A03→raw HL7 Blob 的完整实机验收及独立读回；禁止旧完成 Batch 重放。

## Phase 3 — 增强的医院接口能力（独立验收）
- [ ] 3.1 评审 A08 Patient/Encounter update 事件类型与生命周期，规划更新版本/Replay/HL7 profile。
- [ ] 3.2 评审并实现内部限定 MLLP/ACK/NAK 接口，用隔离地址检查 AA/AE/AR、重试/未知 ACK 和权限；非公开暴露；未运行不能标记为“支持”。
- [ ] 3.3 复核 HELD/QUARANTINE 统计、存储保留/重启恢复、事务证据与 Lineage；如需授权真实运行单独评估。

## Separate product handoff
- [ ] H.1 HL7 open-source Parser+dbt source-specific Candidate → One Canonical Silver Publisher 与 FHIR 汇合；dbt backend (DuckDB/Local Spark/remote Fabric) 选型保持 **PENDING**，此 Change 不实现 OMOP Mapper 或写正式 Silver。
- [ ] H.2 完整上线验收前必须有正反向、故障注入、来源合成、独立 OIE 消息和远端 Blob readback 证据；不因 Phase 1 完成就宣称 E2E 成功。

## 2026-11-06 ET — Versioned A01/A03 Source Implementation Candidate (STATIC / CI PENDING)

- 在独立 Healthcare feature PR 实现 **新** `local-data-platform/apps/clinical_producers/oie/adt_events_v2.js`，与已部署旧 `adt_a01.js` / `build_channel.py` 完全分离。强制 Synthea/FHIR Patient.birthDate、male/female gender、FHIR US-Core Race/Ethnicity OMB Code extensions；合法 IMP in-progress→A01，finished + sourced end→A01/A03；同源 bytes/同 event type MSH-10 稳定，医院隔离。代码仅构建新 V2 的 HL7 v2.5.1 原始消息，不写 Azure，也不把 A01-only 填为 completed Encounter。
- 新 `build_adt_events_v2_channel.py` 只生成**新 Channel ID** 的 OIE 4.7.0 Channel Reader 静态 XML；one-event-per-message 必须由 `requested_event_type` 请求并在 OIE 重新校验 eligibility。源 Writer 沿用 upstream `none`；因此不是可交付的 Raw HL7 Publisher。旧 OIE Derby/PVC/Channel 保持原样；未通过 live auth。
- 新质量测试及 CI 均归 `.github/quality/tests/data-platform/clinical-producers/oie/` 和 `.github/workflows/oie-adt-events-v2-unit.yml`；源码/组件 CODE 入口见 Synthea CODE Owner，技术说明见 `documents/systems/data-platform/clinical-producers/OIE-OPERATIONAL-ADT-V2.md`。
- **状态：source committed in PR branch; CI + independent HL7 Parser parse-back still need fresh evidence before marking 1.1/1.2/1.3 complete**。任何 OIE live/Blob/MLLP/Fabric 不在本源码 PR 中，Phase 2/3 不得提前打勾。

## 2026-11-06 ET — OIE ADT V2 offline evidence

- [Source PR #735](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/735) 为**新版本** `adt_events_v2.js` + `build_adt_events_v2_channel.py`，与旧 deployed A01 Channel/ID/`adt_a01.js` 完全隔离。实际 Node 输出为两条真正不同的 HL7 v2.5.1 A01/A03 原始消息；PID-7/8/10/22 分别来自 FHIR birthDate/gender/US-Core `ombCategory`，A03 的 PV1-45 来自真实 `Encounter.period.end`；A01-only 不制造出院。
- [GitHub-hosted Run #42220398131](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42220398131)（源 `c88083764832cc77fd232ed2f5a2f9e4fee14be9`）：V2 Node 正反向 10/10、OIE 新 Channel XML 4/4、第三方 hl7apy v1.3.5 对 Node 输出真实字节及 PID/PV1 独立 3/3、原 Legacy OIE A01 10/10，全 PASS。属于静态/离线 SOURCE 验证，不是新版 OIE Channel 的真实 Derby/Blob Producer E2E。
- **仍在 1.1 OPEN：** CI fixture 使用标准 US Core 扩展结构，但尚未独立读取真实冻结 Synthea FHIR Patient 的性别、DOB、Race/Ethnicity 实际字段分布和缺失率；只有源数据 Profile 检查通过、必要时 upstream 真实合法数据补全后才能说满足实际 OIE 医院 Feed。不能以合成 fixture 等同真实源。
- 1.4 尚待 PR 合并。所有 Azure Blob Publisher、OIE 新 Channel 实机导入、MLLP/ACK、A08 和 FHIR/HL7 dbt→Silver 仍为后续受控任务；不复用已完成历史 batch。

## 2026-11-06 ET — Shared Blob A03 immutable payload extension (CODED, CI PENDING)

- 已核实既有共享 `apps/clinical_producers/azure_blob_publisher.py` 具有 Mock/Azurite 的 conditional-create + GET/readback + manifest-last 验证；现存 `blob_publish_contract.py` 与 `oie_hl7_publisher.py` / `oie_persisted_readback.py` **只认可旧 A01 / 单 Encounter 的一条消息**，不能把其静态支持错误称为新版两事件链路完成。
- 在新 feature PR 中为 `oie/hl7_readback.py` 增加独立严格的 `parse_adt_a03`，保留旧 `parse_adt_a01` 原签名与逻辑；`blob_publish_contract.verified_plan` 仍是一套共享合同，允许通过严格 A01/A03 readback 且 Control ID 完全一致的两件 raw HL7 数据对象。源 bytes SHA/size、不可变 Blob key 与 manifest-last 继续由共享 Publisher 实现而非重新复制 Writer。
- 对应新质量测试 `.github/quality/tests/data-platform/clinical-producers/oie/test_a03_blob_contract.py`：直接从已合并 V2 Node mapper 生成两条真实格式合成消息、验证严格 A03、共享计划、Fake Blob 双对象 manifest-last、同 request replay SKIP 和恶意字节/Control ID 冲突拒绝；Hosted CI only、无任何 Azure/OIE/cluster 权限。源码来源/测试定位更新至 Synthea CODE Map。
- **此 PR 尚未声明 2.2 E2E PASS。** Channel Writer 仍为 none；真实 OIE 4.7 持久消息的 `oie_persisted_readback.py` 仍只识别 A01 并限制每 Encounter 单一 message；`oie_hl7_publisher.py` 仍是 A01-only handoff。后续必须新增**与 legacy 兼容的 versioned per-event receipts**，才能合法将 A01/A03 的两条持久消息关联到单个 Encounter。完成后还需 real OIE + Azure Blob 独立 GET 才能标记 2.2/2.4 正式验收。
- dbt Core DuckDB / Local Spark 选型继续 PENDING。此改动不产生在 Fabric Silver 或 OMOP 的第二份正式 Mapper。

## 2026-11-06 ET — A03 shared Blob plan real offline evidence

- [Source PR #736](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/736), [GitHub-hosted Run #42221717395](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42221717395): newly added A03 Blob offline tests **5/5 PASS**, generated by the actual versioned V2 Node mapper; strict legacy A01 readback and new A03 readback both PASS; shared `verified_plan` produces two independent immutable raw objects; existing `publish_immutable` Fake backend verifies manifest-last, independent readback and same request replay; wrong source SHA / MSH-10 / discharge time reject before writing. All original Publisher/legacy OIE independent CI PASS. Exact source SHA before this docs-only update: `a7f7f91c0a0135076d2f7ad19a5175bcaea7819d`.
- Only `oie/hl7_readback.py::parse_adt_a03` and the shared `blob_publish_contract.verified_plan` have been extended. Existing published `azure_blob_publisher.publish_immutable` was **reused unchanged**, preserving conditional create and remote GET mechanics. This is **NOT** a new remote Azure Storage or actual OIE readback success; OIE Channel Writer still none.
- `oie_hl7_publisher.prepare_oie_hl7` and `oie_persisted_readback.fetch_persisted_readbacks` still use legacy **one Encounter → one A01** contract. DO NOT feed A03 into those old APIs; next implementation needs source-scoped new *event receipt* and versioned persistence adapter with dual event correlation, old A01 API unchanged. 2.2 remains OPEN until this and remote publisher contract are verified, 2.3/2.4 HOLD for actual live OIE/Azure operation.
