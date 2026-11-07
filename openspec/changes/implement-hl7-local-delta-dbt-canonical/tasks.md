# Tasks — Implement OIE V2 HL7 local Delta staging and dbt Candidate

## P1 — 正式代码与本地物理 Delta/dbt（不用重做旧 POC）
- [x] 1.1 核查双仓 Main/PR/Workflow、OIE P2/P3 真实证据、Self-Runner PR #584 Parser/dbt POC、Canonical v1、源码 Owner。
- [x] 1.2 迁入唯一 Healthcare HL7 Reader/Manifest Parser/本地物理 Delta Writer，采用已测试 Spark 3.5.5/Delta 3.3.2 和 fail-closed Source Profile。
- [x] 1.3 正式 dbt-fabricspark local session 从 Delta `source()` 读取，生成 Source-specific Patient/Encounter Candidate；不写正式 Silver/Gold。
- [x] 1.4 实施 OpenSpec/系统 README/CODE、真实 OIE V2 JS Mapper 新合成 fixture、集中负向测试和 Hosted-only CI。
- [ ] 1.5 CI 实际 local Delta/_delta_log、Replay、dbt compile/run/test、独立 18+27 字段 readback 通过后，登记最终 PR/Run/SHA 并合并 Main。

## P2 — 真实来源和共享业务链路（单独资源授权）
- [ ] 2.1 对 Azure 已发布 42 条 Raw HL7 做 GET-only 最小权限计划与 Batch/资源冲突核查；不重跑历史 P2/P3、不产生 OIE POST。
- [ ] 2.2 使用原 42 条真实 HL7 文件和权威 Manifest 进入本 Consumer 的真实 Source/Delta Candidate 验收。
- [ ] 2.3 接入现有统一 Silver DQ/quarantine/Approval/Single Writer，后续与 FHIR 在已批准 Canonical 汇合；真实 Silver/OMOP 写入需要明确审批与独占窗口。

## 2026-11-07 ET — Actual offline physical Local Delta/dbt acceptance (PR #809)

- Official Healthcare source (pre-merge code head `403437e27dd11eaef62637c0255585c081db7cb5`) + isolated GitHub-hosted synthetic [Run #42419252459](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42419252459), job `128543927482` **COMPLETED SUCCESS**. This test **executes real physical Local PySpark/Delta and dbt**, not static inspection, yet **does not read Azure P3 bytes or execute Fabric**.
- Actual OIE V2 JS Mapper created **new in-memory synthetic** FHIR → A01/A03 HL7 Raw + matching local Manifest and byte SHA; Python `hl7apy` Parser + Source Manifest/Profile/Gate tests PASS. Physical Local Delta `hl7_staging.hl7_events` **CREATED rows=2**, independently verified Delta `_delta_log`; same original source reprocessed in separate Spark process returned **`ALREADY_MATCHING_REPLAY_SKIP`** without overwrite/duplication.
- dbt Core with `dbt-fabricspark(method=session)` local Spark: `dbt compile` + 2 Candidate Delta models **PASS 2/2** and dbt data tests **PASS 6/6**. Separate Spark process read back `hl7_candidate.canonical_patient` **1 row**, `canonical_encounter` **1 row**, independently verified real Delta format + immutable Contract Patient **18/18** / Encounter **27/27** field order/data types/required non-null and the actual Source/clinical facts. Marker: `HL7_LOCAL_DELTA_DBT_CANDIDATE_18_27_CONTRACT=PASS`.
- CI recovered one real regression during development: Spark Delta persisted storage nullability metadata did not match Python in-memory StructType, incorrectly rejecting identical Replay; fixed to compare exact column names/types and symmetric row multisets without bypassing source hash or conflict HOLD, then same Main-bound PR CI succeeded.
- **Remaining hold:** This Run did **NOT** fetch the already published Azure 42 real OIE HL7 objects, no actual Fabric Spark 4.1, no Approved Silver, shared OMS/OMOP or Gold. The local code is source-complete/physical-offline accepted, but final PR merge verification remains task 1.5 until GitHub merges #809. P2/P3 still OPEN.
