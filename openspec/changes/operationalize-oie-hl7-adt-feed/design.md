# Design — Operational OIE HL7 ADT Feed

## 1. 已证实的实际状态（勿混淆）
- 现有 Johns Creek OIE 4.7.0 Channel ID `69ace705-a675-45f6-b126-a3b22a65212a` 在 worker01 的 `dw-oie`，以内部 Administrator HTTPS REST `POST /api/channels/{id}/messages` 的 **Channel Reader** 收事件，转换 `FHIR mini-Bundle → ADT^A01`；31 合成 Encounter 的实机验证中 1 IMP→A01、30 AMB→SKIP，同源重跑 HL7 字节一致。Writer 为 `none`，既无 Blob 写入，也不是已验证 MLLP Listener。现有持久 OIE Derby 必须保护。
- 原 `local-data-platform/apps/clinical_producers/oie/adt_a01.js` 严格 A01 子集：MSH/EVN/PID-3/5/PV1-19/44，缺 DOB/Gender/Race/Ethnicity 和 A03 PV1-45；不能由现有输出推导 Canonical v1。
- Self-Runner PR #525（Main `f45131f`）只是离线 synthetic Parser + dbt 完整 Canonical 18/27 字段的 POC，不是运行时 OIE Producer 的业务证据、Blob delivery 或 Silver Approved。

## 2. 首期业务边界
- 医院模拟：OIE 用冻结的已验真合成 FHIR Patient+Encounter 事件产生**真正 HL7 v2.5.1 传输消息**（不是把 FHIR 改成 JSON 再声称 HL7）。
- **A01：** 源 Encounter class=IMP 且 status=in-progress 或 finished；time=Encounter.period.start。仍在院的 Visit 只产生入院事件；下游不得据此填造出院时间。
- **A03：** 同一 inpatient Encounter status=finished 且 `period.end` 有真实有效时间、`end >= start`；time=period.end；PV1-44=admission、PV1-45=discharge。完成的历史住院可以发送 `A01` 与 `A03` 两条不同 MSH-10 控制消息，但不能假装同时真实发生，Event Time 来自源数据。
- **A08：** 患者/住院信息变化属于后续独立 Change task；需明确 snapshot / update feed、变化语义、消息 ID、版本和重放，不允许把 A01 重发充当 A08。
- **字段：** PID-3 Patient.id + assigning authority，PID-5 Name；PID-7 birthDate；PID-8 gender 仅根据源 `male/female/other/unknown` 与审核后的 HL7 mapping profile 映射（无已批准 profile 的无法映射值 HOLD）；PID-10 Race 和 PID-22 Ethnicity 从真正存在的 FHIR US Core 扩展/源 profile 明确映射，无合法来源则 HOLD；PV1-2=I、PV1-19 Encounter.id、PV1-44/45、MSH-9/10/12、EVN；患者生日 date-only 不发明时间。
- **禁止**静默默认种族、族裔、临床 Concept 或 end time。其它 HL7 ADT 类型、ADT^A08、Orders/ORU/OBX、FHIR 之外的真实医院接入扩展必须另行验证。

## 3. 一条可操作的 Producer 到 Silver 业务链
~~~text
Hospital B simulated Synthea FHIR verified source
     ↓ frozen source request + immutable provenance
OIE 4.7.0: event classification/validation
     ├─ A01 admission (single HL7 message, unique deterministic MSH-10)
     ├─ A03 discharge (single HL7 message, unique deterministic MSH-10)
     ├─ non-IMP SKIP and reason count
     └─ invalid/unknown facts HOLD/REJECT with controlled evidence
     ↓ audited OIE destination/retention + controlled HL7 extraction
Immutable Azure Blob raw HL7 v2 bytes + source/processing manifest-last
     ↓ remote GET SHA256 / row, message and semantic readback
Self-Runner / dbt source-specific path (backend PENDING)
     ↓ hl7apy Parser → source-scoped staged PID/PV1 ADT events
     ↓ dbt SQL models → Canonical Patient & Encounter Candidates
ONE shared Contract/DQ/Approval/Publication boundary
     ↓ ONE Fabric Silver Delta canonical_patient/encounter
ONE Shared OMOP Candidate Mapper / Identity / Concept / DQ
     ↓ authorized Fabric Warehouse Gold Writer
~~~

Current OIE preprocessing script returns only ONE raw string per input. Do **not** combine A01/A03 as multiple HL7 messages in a single preprocessing return and call them separately verified. Choose a safe concrete one-message-per-Channel-message arrangement: versioned, event-specific Channel (or approved and tested OIE message routing), source event input preserving immutable mini-Bundle and event intention, independently validated event classification in OIE. Preserve the existing A01 Channel behavior and Channel ID until versioned replacement is accepted. OIE source event planner may only choose a bounded event identity; OIE remains authority for clinical classification/validation, not the sender.

## 4. Producer identity / delivery / runtime
- Each event key includes `hospital_id/feed_id/request_id/encounter_id/event_type` and normalized MSH-10 bounded length. A01 vs A03 different IDs, same input yields exact byte-for-byte repeat; conflicting same request with new source SHA yields HOLD. Namespace includes hospital to avoid MRN/Visit ID collisions.
- Raw HL7 persisted **before** downstream acknowledgement of successful delivery; treat OIE internal queue/Derby persistence and external Blob Publisher state separately. OIE API message response is *not* Blob publication proof.
- Publisher outputs immutable raw bytes, per-object SHA/length, source-handoff/manifest SHA, OIE message ID, MSH-10, Feed/Batch identities, profile/version, counts by ADT type, quarantine/reject codes. Manifest-last only after all object PUT and **independent remote GET** evidence. Same source+processing replay SKIP, same request ID/different SHA HOLD. No premature READY or SILVER_APPROVED.
- OIE outbound retry and transport evidence must distinguish unknown ACK / pending vs delivered; no overwrite of already published Blob or completed Batch. Do not expose port, password or PHI in CI/logs.
- Do not use Shared Wheel / Fabric Notebook / OMOP business code inside OIE Channel. This is source-specific event preparation only.

## 5. MLLP/ACK 与版本策略
- **P1/P2：** functional OIE Producer through existing internal secured REST + durable verified raw HL7 delivery; this alone makes hospital's HL7 source usable by downstream.
- **P3：** To additionally showcase real HL7 interface-engine transport, implement and verify isolated **MLLP listener and/or sender**, framing and acknowledgement AA/AE/AR, message correlation, timeout/retry/reconciliation, minimal service exposure. That is NOT a requirement to publish raw HL7 through Blob and is NOT already enabled. Do not attach an unauthenticated MLLP socket to public network.
- Versioned Channel/source profile and existing state preserved. No direct reload of currently running legacy Channel without backup/validation and explicit user-approved exact live change.

## 6. 负向和真实验收
- Unit Contract: valid IMP in-progress A01; finished IMP A01+A03; AMB/EMER/OBSENC skip; planned/cancelled skip; missing DOB/gender/US-Core code/period.end HOLD; timezone/illegal date, period.end<start reject; duplicate/source collision; escaped delimiters; other/unknown gender profile behavior; missing Patient reference; A03-only/delayed A03 policy.
- Independent HL7 Parser: v2.5.1 `hl7apy` parses MSH-9/10/12, PID-3/7/8/10/22, PV1-19/44/45 and temporal semantics; output stable against replay. Freeze exact test input, manifest/version and SHA.
- Static/OIE XML Channel: package/importable XML with **new Channel ID**, keep old deployed ID untouched; input envelope one event → one message, OIE event choice fail closed.
- Runtime: preflight actual OIE/Pod/Channel IDs, session ownership and clean source request; new accepted event and OIE persistent output independently GET/read back; then create verified HL7 Blob manifest as separate controlled step. Only after cross-source Candidate contract and governed Publisher approval can call Silver `SILVER_APPROVED`.
- All tests for new code under `.github/quality/tests/data-platform/clinical-producers/oie/`; human docs under `documents/systems/data-platform/clinical-producers/`. No new source README, no cloned Mapper, no premature backend choice.

## 7. Implementation and hold points
1. New OpenSpec + accepted design before code (this Change); docs-only phase no live runtime.
2. Implement versioned source OIE mapping (new function/library where feasible, no change to accepted old A01 output) and offline tests; SHA/CI/code owner update.
3. Versioned OIE Channel with guarded import source; parse-back; safe message storage; dedicated output integration and remote Blob publisher.
4. Live OIE/Blob readback **only after separately approved** exact resources and new immutable source Batch.
5. HL7 Parser/dbt Candidate → governed Silver Publisher; independent Fabric capacity and real table runs are a distinct Change.
