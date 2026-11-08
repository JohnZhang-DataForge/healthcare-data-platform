# Tasks — G5

## 1. Scope / contract

- [x] 1.1 只读核对双仓当前 main、原生 Pipeline HALT、G4 物理 Silver Approval/Quarantine 与唯一 Shared Engine 的实际缺口（2026-11-03；本 Change 起始基线记录在 design.md）。
- [x] 1.2 建立独立 G5 Proposal/Design/Tasks；冻结 G4 原始两个 Request、分离 Candidate/Gold/WORM，定义 IdMap 不自动分配原则。
- [ ] 1.3 检查共享资源 Active Runs 与有效 Fabric Native Pipeline 定义，确认云端修改和执行窗口。

## 2. Pure Shared Candidate

- [x] 2.1 从既有 Local Mapper 抽离唯一无 I/O 的 OMOP Person/Visit Candidate DataFrame 逻辑；稳定 ID Map、Concept Profile、原始 v1/v5.4 Contract 由调用者验证/注入；Candidate-only，不改变 Local Writer。
- [ ] 2.2 正负向单测：已验证合成 P1/E2、G4 P99/Q26 Approval-denied、跨医院 FK、重复/缺失 ID、未知 Concept、重放一致性；待增加完整 P100/E5918 fixture/映射 Profile 实测，不生成假临床值。
- [ ] 2.3 更新 Shared CODE-map、边界 CI 与 Wheel 版本；单独构建固定 hash 的新 Wheel，Published Environment 读回后才能进行真正 Fabric import。
- [x] 2.4 **业务映射 Profile 源值覆盖审查 SOURCE_ONLY（不授权 Candidate）**：Self-Runner [PR #621](https://github.com/JohnZhang-DataForge/Self-Runner/pull/621) / [CI #42495576735](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42495576735) 27/27 PASS、[原 F0/G4/F2 离线 CI #42495576736](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42495576736) PASS；Provider 复用原真实已采集 G4 P1 code inventory、同一个 Shared G5 八字段 Profile 结构验证，不复制第二 Mapper，PR 离线阶段无 Azure 查询；Main 合并后原有 F0 REST/SQL 只读 [Run #42495667078](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42495667078) 成功，未执行新 P3 业务查询或 Spark/Delta 写入。实际 P100/E5918 源值审查范围：gender **2**、race **6**、ethnicity **2**、visit class **5**；Encounter `source_code` **44** 种独立提示、不假造 Person/Visit Target Concept。`UNK` 种族（2）及 `home`/`virtual` 就诊（4/11）需真正临床审阅；哪怕 SOURCE COVERED，审查状态依然 NOT CLINICALLY APPROVED。生产 Reviewer 公钥/签审包为空，F1 9/9 Source Audit、Release/License 与真实 Candidate Approval-last / Replay 均 OPEN；**不关闭原 2.2/2.3 或 3.1–4.4**。

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

- [x] 3.5 Add a distinct, strictly read-only `G5_CANDIDATE_SOURCE_READONLY` native Notebook mode that reuses actual G4 frozen source/Manifest/Approval/Canonical Delta readback; re-open independent Delta Patient, Encounter and approval paths; validate exact accepted P100/E5918/Q0, source batch SHA, source namespace, historical processing 0.1.1, pinned Canonical contract raw bytes, unique keys and FK. This is **source-only**, not Candidate or Gold.
- [x] 3.6 Offline negative tests must reject changed Manifest, rejected G4 request, unexpected write authorization, unknown path overrides, partial/duplicate Approval, patient/encounter tampering and silent non-approval; run required CI and merge reviewed PR.
- [x] 3.7 Actual G5 mode live Spark execution and exact exit / independent physical readback remain a separately scheduled, explicitly authorized stage. No assertion of PASS based on deployment or offline tests.
- [ ] 3.8 Physical Candidate requires reviewed real Concept Profile, independently verified **complete persisted Warehouse Map/Gold/Allocator/Ledger snapshot** and revalidated F2 `PROVISIONAL` ID proposal where Map is initially empty. Preview is NOT a durable ID reservation. The controlled Warehouse Writer must re-read under single-writer fence and atomically COMMIT Map/Allocator/clinical targets/Ledger; never mark preview or Candidate as Gold.

- [x] 3.9 New Shared Wheel 0.1.6 **source-only** F2 Preview → G5 Person/Visit Candidate ID Handoff: exact G4 source/Approval equality, PERSISTED vs PROVISIONAL lookup state, first batch empty Map, multi-hospital, 100/5918, replay, FK, length, snapshot and collision rejection. CI/PR and merged SHA evidence are required before closing this source-only task. Real Candidate/G5 3.2/Gold remain OPEN.
- [x] 3.10 **P3 实机来源身份 Handoff：G4 P100/E5918/Q0 → F2 全六表独立双连接 → Shared 0.1.7 Candidate ID（非候选发布）**：Self-Runner [PR #620](https://github.com/JohnZhang-DataForge/Self-Runner/pull/620) Main `25d7ad04adcfa9bb73b0fef7109d254e671d60df` / [Run #42493018918](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42493018918) **SUCCESS**，安全 Artifact `fabric-f2-g4-silver-readonly-42493018918` ID `13622585846`。使用实际固定 Silver Delta 的 100 Patient、5918 Encounter、独立 Approval/Q0 及新增实物 `encounter_class`，与两条独立 SQL 连接（F2 六表零行）的真实 IdentitySnapshot/Preview 一起调用现有 `plan_candidate_identity_handoff`；完成 FK、source scope、ID 状态/快照指纹校验，100 Person + 5918 Visit 均 `PROVISIONAL`，未持久化且没有生成 Mapper 的临床 OMOP Candidate 数据行。真实结果 `P3_G5_REAL_DELTA_TO_SHARED_CANDIDATE_ID_HANDOFF_PASS_NOT_RELEASED`。离线 CI 与空 Encounter class 拒绝测试 PASS；临床 Profile/License/F1 原始治理及生产 Reviewer 公钥、真实 Candidate Write/Readback/Approval-last/Replay、Pipeline/Gold 均**未放行**，2.3/3.1-3.4/3.8/4.x 主业务任务仍 OPEN（不得因本项核销）。
- [x] 3.11 **P3 Trusted Provider 六表完整 SQL 行集 → Shared 身份快照指纹（SOURCE-ONLY，非 Candidate 发布）**：Self-Runner [PR #622](https://github.com/JohnZhang-DataForge/Self-Runner/pull/622) 已合并 Main `8112b537549e883437d0b7a997ca862b119e4d7f`；[P3 离线 CI #42501025819](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42501025819) 与 [F0 离线 CI #42501025495](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42501025495) 均 **SUCCESS**。复用现有 `capture_full` 的两条独立 F2 SQL 连接，比较六表完整内存行集与物理 SHA，并通过现有固定版本的 `silver_identity.bridge_f2_sql_readback_rows` 将真实 SQL 行集转换为唯一 Shared `IdentitySnapshot`，要求其逻辑 `fingerprint` 严格匹配固定签审包；物理 SHA 不冒充逻辑 fingerprint。覆盖行集漂移（即使报告 SHA 一致）、指纹替换、固定源码缺失、非法 SHA、F1 九条来源审计未齐等负向 HOLD。此项只完成 Provider 只读源码/离线 CI；**未执行新的 P3 一次性实机业务查询**，Reviewer 生产信任锚、真实 Clinical/License/F1 签审、可信 Notebook 证明传输、短期有效期/防重放、单 Writer 事务栅栏仍未具备；Candidate Delta/Approval-last/Replay/Gold 及原 2.3、3.1–3.4、3.8、4.x 全部保持 **OPEN**，所有 PROVISIONAL ID 未持久化。
- [x] 3.12 **G5 临床映射审核材料准备（SOURCE-ONLY，不是临床审批）**：Self-Runner [PR #623](https://github.com/JohnZhang-DataForge/Self-Runner/pull/623) 已合并 Main `2630566e7aa7ea169523ef8967dac4183176c975`；[P3 临床审核材料离线 CI #42514764050](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42514764050) 与 [F0 契约离线 CI #42514763787](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42514763787) 均 **SUCCESS**。严格复用已存在的八字段 Shared G5 Mapping Profile 原始字节/SHA、冻结 G4 P100/E5918 真实汇总来源代码及现有 Provider Mapping Coverage，不复制 Mapper。针对四类 Person/Visit 源码 15 个实际出现的 Code 逐条列出行数、调用方 Profile 的拟议 Concept ID 或 NULL、临床审核重点与 `PENDING_AUTHORIZED_HUMAN_REVIEW`，审核材料另有确定性 `dossier_sha256`（非签名）。特设 `1002-5`（1）、`UNK`（2）、`2076-8`（1）、`home`（4）、`virtual`（11）审查警示；Encounter `source_code` 44 种 / 5918 行明确在当前 Person/Visit 四字段 Mapper 范围外。完整覆盖、Profile 字节重排、混入未审来源、来源篡改、缺失审核等负向案例要求 HOLD。此项仅完成可测试**源数据映射临床审核报告生成算法**：尚没有提交真实候选 Profile 审核包/临床人员签名/证书，F1 原始 9/9 来源审计与 28 项空版本/License 结论仍待完成；不创建发布授权、不持久化 PROVISIONAL ID、不启动 Candidate Delta / Gold；G5 Task 2.2、2.3、3.1–3.4、3.8、4.x 全部保持 OPEN。

## 2026-11-04 — G5 3.5–3.7 independent physical evidence (source only)

- Healthcare main source `4267d6b4ddb48173b6c020c815a4ed4e0a525edc`; Self-Runner main `ece535b956f6fa0d6f1fbc17470658d60fd167ad` at acceptance. The historical G4 processing partition `fhir-silver-canonical-v1:engine-0.1.1` remains immutable; executing Wheel 0.1.3 is separately verified.
- [Self-Runner real run #41874126635](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41874126635), exact Fabric Spark Job `e5038133-8120-4afe-b132-9abf6fb652ab`: source-only result `G5_CANDIDATE_SOURCE_PHYSICAL_READONLY_PASS`, `ERROR=NONE`. The controlled one-shot runner job completed SUCCESS and archived the independently reopened G4 Patient/Encounter/Approval Delta evidence for approved request `atlanta-fhir-gh-41552666929`, expected P100/E5918/Q0, delivered SHA `425a25a6337e86a2df39c1f7993d46fd0555cfed9107dde415521fde755ff2f1`.
- Task 3.5 (read-only source gate), 3.6 (guarded offline negative tests and merged CI), and 3.7 (actual Spark physical readback) close based on the separately recorded PR/CI and **this exact cloud run**. This is **not** candidate or Gold publication. Task 3.1 remains open in full (includes native Candidate integration); 3.2–3.4, 3.8, 4.1–4.4 remain OPEN pending concept profile, durable identity and actual writes.

## 2026-11-06 — G5 first-batch F2 Preview Candidate handoff, SOURCE-ONLY PASS

- [Healthcare PR #727](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/727), validated exact source HEAD `02084e4b1b59a922c9888182d82e985cfec95c6d`; offline [Wheel Run #42207621020](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42207621020), **SUCCESS both Python 3.11/PySpark 3.5.7 and Python 3.13/PySpark 4.1.1 jobs**: existing 35/35 + new mapping 66/66 (Py3.11), pure FHIR 13/13 + mapping 66/66 + DataFrame 2/2 + OMOP 11/11 (Py3.13); byte-identical candidate Wheel `REPRODUCIBLE_WHEEL_PASS`, independent install `WHEEL_IMPORT_PASS 0.1.6` / `FABRIC_P3_PY313_WHEEL_INSTALL_IMPORT=PASS 0.1.6`.
- In this source-only PR, `IdentitySnapshot` and existing F2 ID Proposal are *caller supplied* and strictly reconciled with G4 Silver Patient/Encounter keys, Approval counts, hashes, same-hospital FKs and target `varchar(50)` lengths; every row retains `PERSISTED/PROVISIONAL` status. It is not the physical Warehouse Identity Map and no Gold DB, Delta, Fabric Notebook, Pipeline or Published Environment was modified.
- This evidence closes only **3.9 (pure interface)**. F1 Vocabulary release/license/audit provenance and true clinical Profile review remain OPEN, so G5 physical Candidate tasks 3.2/3.8 and F2 Gold COMMIT remain OPEN. Last tasks-only evidence edit triggers final SHA GitHub checks, which must pass before merge.
