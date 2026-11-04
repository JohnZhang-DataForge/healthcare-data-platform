# Tasks — G5

## 1. Scope / contract

- [x] 1.1 只读核对双仓当前 main、原生 Pipeline HALT、G4 物理 Silver Approval/Quarantine 与唯一 Shared Engine 的实际缺口（2026-11-03；本 Change 起始基线记录在 design.md）。
- [x] 1.2 建立独立 G5 Proposal/Design/Tasks；冻结 G4 原始两个 Request、分离 Candidate/Gold/WORM，定义 IdMap 不自动分配原则。
- [ ] 1.3 检查共享资源 Active Runs 与有效 Fabric Native Pipeline 定义，确认云端修改和执行窗口。

## 2. Pure Shared Candidate

- [x] 2.1 从既有 Local Mapper 抽离唯一无 I/O 的 OMOP Person/Visit Candidate DataFrame 逻辑；稳定 ID Map、Concept Profile、原始 v1/v5.4 Contract 由调用者验证/注入；Candidate-only，不改变 Local Writer。
- [ ] 2.2 正负向单测：已验证合成 P1/E2、G4 P99/Q26 Approval-denied、跨医院 FK、重复/缺失 ID、未知 Concept、重放一致性；待增加完整 P100/E5918 fixture/映射 Profile 实测，不生成假临床值。
- [ ] 2.3 更新 Shared CODE-map、边界 CI 与 Wheel 版本；单独构建固定 hash 的新 Wheel，Published Environment 读回后才能进行真正 Fabric import。

## 3. Fabric Candidate and Pipeline

- [ ] 3.1 原生 Notebook 保留 HALT 与 Fabric cell 格式，增加 approved Silver 真正独立读回入口；要求精确批次 SHA/processing/Approval，不触碰已通过 G4 数据。
- [ ] 3.2 Candidate-only 物理 Delta 首次写入、独立完整重读、Approval-last fence、异常/HOLD 与 replay SKIP；不冒充 OMOP Gold。
- [ ] 3.3 原生 pl_fhir_ingest 编排 fail-closed read-only → Candidate；无 schedule、retry=0、默认 HALT；Pipeline SUCCESS 不代替 Candidate 读回。
- [ ] 3.4 Native + Notebook + Pipeline 代码/参数的离线 CI/安全负向测试 PASS，并完成云端真实 definition 独立读回。

## 4. Live E2E / closure

- [ ] 4.1 真正 Fabric Notebook Spark 原始 G4 P100/E5918 的 Silver fence→Candidate 执行，记录完整 Job UUID、精确物理路径/行数、readback。
- [ ] 4.2 真正 Fabric Pipeline Run、独立读回及同 Request Replay SKIP；容量建立 Spark Session 前的失败单独记录，POST uncertain ACK 先 GET。
- [ ] 4.3 检查 PR Required CI / 目标 SHA 后合并 main，准确写入实际 Run/Artifacts，不提前核销未实机验证的 Task。
- [ ] 4.4 Gold Warehouse 单事务与 Azure WORM / Blob 漂移 / 真实网络 ACK 均作为独立后续验收；不把本 Change Candidate PASS 标为 Gold COMMITTED。

## 2026-11-03 G5 Shared Engine candidate offline evidence (NOT Fabric deployment)

- [PR #629](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/629) on feature branch; Python 3.11 + PySpark 3.5.7 synthetic **23/23 PASS**, independent built Wheel 0.1.2 reproducible byte comparison and isolated package import PASS; Python 3.13 + PySpark 4.1.1 added G5 Candidate **8/8 PASS**, installed Wheel 0.1.2 import PASS.
- [GitHub Actions Shared Engine Wheel Offline Validation #41619656145](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41619656145), exact source head `b11be171d787abd73f40e2540a87d65fe87b78b6`, both jobs SUCCESS. Earlier #41619502401 Python3.13 workflow failed due literal shell `\\n` between commands; fixed in `b11be171...`; original failure not a candidate mapper failure and remains historical.
- Verified tests use a synthetic-only profile, not a reviewed live FHIR→OMOP clinical Concept profile. Real Fabric environment is **still Wheel 0.1.1**, Notebook/PL default HALT and Candidate physical Write/Readback NOT_RUN. This OpenSpec change remains ACTIVE and unchecked tasks MUST NOT be inferred PASS by main merge.

## G5 read-only Pipeline candidate (design + code only; NOT deployed)

- 第二批独立 PR 预备：原有 `pl_fhir_ingest` 单 Activity 通过 Fabric Pipeline expression 显式传递读回所需 exact request、Manifest、Local Contract，write_authorized 和 retention_preflight_verified 永久 false，默认 HALT / retry=0 / no schedule。离线测试见 `azure-fabric/notebook-development/tests/test_g5_pipeline_readonly.py`。
- 设计对应 Task 3.3 的**只读预备片段**，不标记完整任务成功；真实 Notebook/ Pipeline E2E + Candidate/Gold 尚未执行。Workflow 对 candidate Wheel 0.1.2 vs Fabric Published 0.1.1 分别检查，严禁把包 hash 混为一谈。

## G5 hospital-scoped identity mapper correction (2026-11-04, source-only)

- `build_omop_candidates` now requires independently verified hospital_id and checks it against the existing canonical v1 namespaced `source_system`; does **not** change G4 canonical schema or existing approved Silver.
- F1 Warehouse map `entity_type/hospital_id/source_system/source_business_key/omop_id` replaces the old hypothetical `source_person_id/person_id` fixture contract. Global Person ID, hospital scoped namespace and casefold collision validation are covered by new offline PySpark positive/negative tests.
- Shared Wheel candidate version is 0.1.3, offline-only until separately published and read back in Fabric. G5 2.3 and native runtime acceptance remain OPEN. No Candidate Delta or Gold data write occurred.

## 2026-11-04 — Hospital-scoped G5 Candidate source CI

- [PR #647](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/647) merged SHA `13da96a9bc82463c8be23e3d5f8be385a9655ad4`; [Wheel Validation Run #41827968535](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41827968535) SUCCESS both Python 3.11/PySpark 3.5.7 and Python 3.13/PySpark 4.1.1 jobs. Built, reproducible, independently installed candidate Wheel 0.1.3 PASS offline.
- The real F1 Identity Map columns and hospital-scoped join are now implemented, synthetic cross-hospital and duplicate/foreign ID tests PASS. No existing G4 Canonical schema mutation, no Fabric Environment update or real Gold insert.
- Wheel publish/import, approved Concept Profile, G4 100/5918 real Silver readback, physical Candidate and Warehouse Gold remain explicitly NOT_DONE.

- CI linkage: this documentation-only PR records the previous real SUCCESS #41827968535 and does not run a new Fabric Environment publish; OpenSpec-Change `fabric-omop-foundation` task `2.1` remains a source-contract milestone, not a clinical Gold closeout.

## G5 Wheel 0.1.3 effective cloud release — 2026-11-04

- [Self-Runner #41833502954](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41833502954) real Staging sync preserved all user Workspace-only resources; [Self-Runner #41834029745](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41834029745) real Environment Published **sole 0.1.3 Custom Library** PASS. Prior historical statement “still 0.1.1 Published” describes the 2026-11-03 baseline, now superseded.
- Isolated Runtime import from separate temporary Notebook [#41835694167](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167) is distinct. Until exact Completed + exitValue PASS and cleanup are recorded, **Wheel runtime not accepted**.
- G5 Candidate 100/5918 physical readback and Gold Writer COMMIT are still **NOT_DONE**.

## G5 0.1.3 real isolated Spark import PASSED — 2026-11-04

- [Self-Runner #41835694167](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41835694167) confirms Published 0.1.3, full temporary Notebook definition readback, real Spark Job **Completed**, exact exit `G5_ENGINE_013_SPARK41_IMPORT_PASS`, and successful temp Notebook cleanup. Runtime package acceptance is **PASS**.
- Source/Environment release is now genuinely complete, but this **does not complete G5 tasks 2.3, 3.1–3.4, or 4.1–4.4**: business `nb_fhir_ingest` remains HALT and still checks 0.1.1; approved Concept Profile, P100/E5918 Silver readback, physical Candidate Delta, Warehouse Gold COMMIT and Replay have not been accepted.

## 2026-11-04 — G5 Stage 3.1a Silver physical preflight (no writes)

- [ ] 3.5 Add a distinct, strictly read-only `G5_CANDIDATE_SOURCE_READONLY` native Notebook mode that reuses actual G4 frozen source/Manifest/Approval/Canonical Delta readback; re-open independent Delta Patient, Encounter and approval paths; validate exact accepted P100/E5918/Q0, source batch SHA, source namespace, historical processing 0.1.1, pinned Canonical contract raw bytes, unique keys and FK. This is **source-only**, not Candidate or Gold.
- [ ] 3.6 Offline negative tests must reject changed Manifest, rejected G4 request, unexpected write authorization, unknown path overrides, partial/duplicate Approval, patient/encounter tampering and silent non-approval; run required CI and merge reviewed PR.
- [ ] 3.7 Actual G5 mode live Spark execution and exact exit / independent physical readback remain a separately scheduled, explicitly authorized stage. No assertion of PASS based on deployment or offline tests.
- [ ] 3.8 Physical Candidate requires real approved Concept Mapping Profile and independently verified persisted Warehouse Identity Map; do not synthesize missing IDs, fake clinically approved Concepts, or publish Candidate using `silver_identity.py`'s preview.
