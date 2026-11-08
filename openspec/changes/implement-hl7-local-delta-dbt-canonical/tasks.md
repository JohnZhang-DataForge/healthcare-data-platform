# Tasks — Implement OIE V2 HL7 local Delta staging and dbt Candidate

## P1 — 正式代码与本地物理 Delta/dbt（不用重做旧 POC）
- [x] 1.1 核查双仓 Main/PR/Workflow、OIE P2/P3 真实证据、Self-Runner PR #584 Parser/dbt POC、Canonical v1、源码 Owner。
- [x] 1.2 迁入唯一 Healthcare HL7 Reader/Manifest Parser/本地物理 Delta Writer，采用已测试 Spark 3.5.5/Delta 3.3.2 和 fail-closed Source Profile。
- [x] 1.3 正式 dbt-fabricspark local session 从 Delta `source()` 读取，生成 Source-specific Patient/Encounter Candidate；不写正式 Silver/Gold。
- [x] 1.4 实施 OpenSpec/系统 README/CODE、真实 OIE V2 JS Mapper 新合成 fixture、集中负向测试和 Hosted-only CI。
- [x] 1.5 CI 实际 Local Delta/_delta_log、Replay、dbt compile/run/test、独立 Patient 18/Encounter 27 Contract readback 均通过，正式 Healthcare [PR #809](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/809) 已合并 Main `1b0ee1df4baeec986c419e2ee5f36abaf7613782`，四项 Ruleset Required Checks 均 SUCCESS；源码仅为 local Delta + dbt Candidate，不等于真实 Azure HL7 消费或 Silver/Gold。

## P2 — 真实来源和共享业务链路（单独资源授权）
- [ ] 2.1 对 Azure 已发布 42 条 Raw HL7 做 GET-only 最小权限计划与 Batch/资源冲突核查；不重跑历史 P2/P3、不产生 OIE POST。**真实 42 个对象 GET 和资源/授权预检仍 OPEN。**
- [ ] 2.4 实施 bounded exact-key Azure GET-only Reader，复用现有 Intake/Parser，负向测试验证后提交 PR/CI；本项仅 Source/Hosted synthetic Test，不执行远端。
- [ ] 2.2 使用原 42 条真实 HL7 文件和权威 Manifest 进入本 Consumer 的真实 Source/Delta Candidate 验收。
- [ ] 2.3 接入现有统一 Silver DQ/quarantine/Approval/Single Writer，后续与 FHIR 在已批准 Canonical 汇合；真实 Silver/OMOP 写入需要明确审批与独占窗口。

## 2026-11-07 ET — Actual offline physical Local Delta/dbt acceptance (PR #809)

- Official Healthcare source (pre-merge code head `403437e27dd11eaef62637c0255585c081db7cb5`) + isolated GitHub-hosted synthetic [Run #42419252459](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42419252459), job `128543927482` **COMPLETED SUCCESS**. This test **executes real physical Local PySpark/Delta and dbt**, not static inspection, yet **does not read Azure P3 bytes or execute Fabric**.
- Actual OIE V2 JS Mapper created **new in-memory synthetic** FHIR → A01/A03 HL7 Raw + matching local Manifest and byte SHA; Python `hl7apy` Parser + Source Manifest/Profile/Gate tests PASS. Physical Local Delta `hl7_staging.hl7_events` **CREATED rows=2**, independently verified Delta `_delta_log`; same original source reprocessed in separate Spark process returned **`ALREADY_MATCHING_REPLAY_SKIP`** without overwrite/duplication.
- dbt Core with `dbt-fabricspark(method=session)` local Spark: `dbt compile` + 2 Candidate Delta models **PASS 2/2** and dbt data tests **PASS 6/6**. Separate Spark process read back `hl7_candidate.canonical_patient` **1 row**, `canonical_encounter` **1 row**, independently verified real Delta format + immutable Contract Patient **18/18** / Encounter **27/27** field order/data types/required non-null and the actual Source/clinical facts. Marker: `HL7_LOCAL_DELTA_DBT_CANDIDATE_18_27_CONTRACT=PASS`.
- CI recovered one real regression during development: Spark Delta persisted storage nullability metadata did not match Python in-memory StructType, incorrectly rejecting identical Replay; fixed to compare exact column names/types and symmetric row multisets without bypassing source hash or conflict HOLD, then same Main-bound PR CI succeeded.
- **Remaining hold:** This Run did **NOT** fetch the already published Azure 42 real OIE HL7 objects, no actual Fabric Spark 4.1, no Approved Silver, shared OMS/OMOP or Gold. Local Component P1 代码与 Hosted Local Delta/dbt 物理验收均已通过，最终 PR #809 合并 SHA `1b0ee1df4baeec986c419e2ee5f36abaf7613782` 已独立确认；**P2 Azure GET-only 和 P3 正式共享 Silver Publisher/OMOP 仍 OPEN**。

## P2 GET-only Reader — offline implementation / runtime HOLD

- Baseline Main: `86ac0c5c96ff8d5e86fad559da5df97c9ec09433` (#822). New source `local-data-platform/spark/apps/hl7/azure_blob_readback.py` requires independently pinned request_id, exact Manifest key/SHA, frozen source Manifest SHA and object count. The only allowed cloud operations, if separately approved, are exact-key HEAD and conditional GET. No List, Blob write, OIE POST, Spark, Fabric or Silver publisher calls.
- [Operating contract](../../../documents/systems/data-platform/hl7/AZURE-GET-READBACK.md) defines scoped Storage Blob Data Reader identity, exact 42-object resource evidence, shared Runner conflict and private source retention gate. Readback uses original `landing_intake.verified_seed_rows` before the directory becomes visible; matching local replay skips, conflicting output HOLD.
- Keep P2 2.2 real Azure 42 GET and P2 2.3 shared Silver/OMOP open. No secrets, actual PHI or Azure network calls in hosted tests. 2.4 may only be ticked on actual PR HEAD CI PASS.
