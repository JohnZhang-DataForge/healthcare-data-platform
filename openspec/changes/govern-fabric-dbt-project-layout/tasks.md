# Tasks — Fabric dbt project ownership governance

## P1 — 本轮文档手续
- [x] 1.1 核对 Main、开放 PR、HL7 真实代码位置、Native Items、Shared Engine、现存可信结构检查冲突。
- [x] 1.2 在 OpenSpec 中确定唯一 `azure-fabric/dbt/` 父目录、`hl7-canonical` 命名、标准工程骨架和未来项目准入规则。
- [x] 1.3 更新 Agent 强制入口、开发规则、Fabric 导航和独立 dbt 组件规范文档，明确“目标路径尚未创建”。
- [x] 1.4 文档治理 [PR #811](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/811) 合并到 Main `16bf09baff3ae150a8ba551d9f13aaf6bddde502`；四项受保护 Required Checks 全部 SUCCESS（[Change](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843811)、[Component paths](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843544)、[Fabric deployment](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843615)、[OpenSpec validate](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843584)），文档链接检查亦通过。外部 Cloudflare Workers Build 失败不属于四项 Required Gates，本次 PR 未改 Portal 或部署代码。

- [x] 1.5 将现有 HL7 文件逐项标记“业务保留 / 冻结参考且待退役 / 混合依赖需复核 / 回归测试需改接”，同步新 dbt 项目规则及开发策略；仅文档更新，不删除或搬动源码（已由 [PR #813](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/813) 合并 Main `de7e904ba9efd28cc8484fdc2097f44be1bfb546`；受保护四项 Required Gates 与 OpenSpec/文档链接检查 PASS）。

## P2 — 受保护门禁前置（独立治理 PR）
- [x] 2.1 已通过 [PR #815](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/815) 在 Main `c36ed72ba140d6b2956d71ab97206baa2965bd58` 实施精确 dbt 原生 SQL `tests/` 白名单；Ruleset #25365902 Active、四项 Required 恢复；真实正向 [PR #816](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/816) PASS、负向 [PR #817](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/817) 按预期 blocked，两个临时测试 PR 均已关闭且未合并。详细日志与检查见 [治理任务](../permit-dbt-native-sql-test-layout/tasks.md)。

## P3 — 标准工程真正实施（独立源码 PR）
- [x] 3.1 门禁例外完成后，在 `azure-fabric/dbt/hl7-canonical/` 创建**完整标准骨架**，直接按 dbt 分层开发；旧 SQL/config/profile **冻结供参考而非先迁移**。新工程在验收/切换前仅为 Candidate，不能形成第二个正式生产入口。
- [x] 3.2 新 dbt 工程真实本地 Delta + dbt compile/run/test、Replay、Patient 18/Encounter 27 Contract/负向语义读回 PASS；必要业务扩展按原单独 HL7 Consumer Change 跟踪。
- [x] 3.3 在受控切换 PR 中审查全部活跃 Workflow/Self-Runner/源码/配置/文档引用，改接唯一新 dbt 工程并复验，不因新 SQL 可以运行就删除旧文件。
- [x] 3.4 切换确认后**另一个清理 PR**删除旧 dbt models/project/profiles，更新旧 HL7 CODE、新 Fabric dbt CODE、CI/依赖及全部导航；Python Parser/Intake/Delta Writer 与必要测试继续保留，混合 requirements 按消费者拆分，不做全目录删除。
- [x] 3.5 同步 Current Spec 的**真实执行 Owner 和迁移状态**；未来 FHIR/业务项目仍走独立 OpenSpec 准入，不预建。

## 已采用治理规则

- 2026-11-07：P1 规则随 PR #811 在 Main 生效；Current Spec 正式采用至 `openspec/specs/fabric-dbt-project-layout/spec.md`（与本次 P1 关闭记录配套）。**历史 P1/P2 已生效；P3 3.1/3.2 在 #820 通过真实本地验收、3.3/3.5 由 #821 受控消费者切换和 Owner/Current Spec 同步验收；3.4 旧文件清理仍 OPEN。**

## P3 Candidate implementation (subject to PR review)

- 3.1: Standard new `hl7_canonical` project, CODE Map, schema tests, isolated local profile and dedicated hosted-only P3 Workflow are authored; legacy Parser/Intake/Writer/SQL/Workflow remain unchanged and sole active entry.
- 3.2: **Local synthetic runtime ACCEPTED** at [PR #820](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/820), validated exact source HEAD `cc58df1ef202b2d833c1421200ffebc7f761b26f` by [GitHub-hosted Run #42444753385](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42444753385) SUCCESS: real physical local Delta staging 2 rows CREATED + identical replay SKIP, dbt debug/compile PASS, 5/5 models, 15/15 tests, independent physical Patient 18 / Encounter 27 fields + clinical values, second run fingerprint replay PASS; four isolated expected-failure negative scenarios each detected (unpaired A03, reversed time, cross-patient identity collision, duplicate message control). This is offline **local-only Candidate** runtime, not Azure 42 real HL7 objects, Fabric remote Spark, Silver or Gold. First Run #42444412477 failed on test-harness dbt diagnostic phrase despite correctly detected negative; repaired only negative assert matching and reran full acceptance. Latest evidence applies to code SHA above; this documentation-only closeout does not change the tested SQL/Workflow.
- 3.3: A separate cutover PR adapts the original HL7 GitHub-hosted regression workflow to the approved `hl7-canonical` project and compatible `hl7_candidate` output schema, retains old Parser/Writer and Contract readback, adds a static anti-fallback test, and documents that Self-Runner historical POC is not a live dbt consumer. Mark 3.3 DONE only after the cutover PR exact HEAD has passed BOTH hosted workflows, four trusted Required Checks and independent physical Candidate readback; no remote runtime touched.
- 3.4: The obsolete old SQL/project/profiles, any now-unused test/CI dependency, and historical documentation refs require a **separate** consumer-dependency-verified cleanup PR. NOT YET DONE.
- 3.5: Source owner and runtime *scope* are updated in Current Spec and CODE Maps in this cutover PR; only finalize DONE after actual PR acceptance. No live Azure/Fabric/Silver/Gold claim.

## P3 3.3 / 3.5 hosted consumer cutover acceptance (local-only)

- [PR #821](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/821) tested exact source HEAD `f77eadb7881fc7b2a4bce18b69595e8b610ddf4b`, based on P3 scaffold merged Main `1cde4663162ad3a71163a519ec52bc1e4cedabfa` (#820). Source and workflow changes convert both GitHub-hosted dbt Workflows to the **single** `azure-fabric/dbt/hl7-canonical/` project, local schema `hl7_candidate` preserved. Legacy source remains Parser/Intake/Delta Writer only; old SQL/config/profile frozen, unexecuted.
- [Existing HL7 regression Run #42446038581](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42446038581) **SUCCESS**: physical local HL7 Delta staging CREATED 2 rows + identical Replay SKIP; dbt **5/5** new models, **15/15** tests; original independent **18/27** Canonical Contract readback PASS. Original Python negative unit tests PASS.
- [New P3 full acceptance Run #42446038571](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42446038571) **SUCCESS**: dbt 5/5 and 15/15, physical local Patient/Encounter 18/27, same Candidate logical Replay PASS, four deliberately invalid local Delta fixtures each yielded the intended dbt **FAIL** and were counted as expected-negative PASS.
- All **four** GitHub default-branch trusted Required checks SUCCESS on tested head; OpenSpec, docs links, code naming and active-index checks also PASS. Separate external Cloudflare Workers Build failure is **not** a Required context and unrelated to these HL7 files.
- Consumer inventory: all 70 Healthcare GitHub workflows inspected: only original HL7 regression and new P3 acceptance run dbt, both now use governed project. Self-Runner Main `5ccc39fc42261c5fe10481ec10dd8733e1c8d845` HL7/OIE named Workflows inspected: dbt POC remains pinned to historic Healthcare SHA `ecc99b18...` and its **own** `experiments/hl7-dbt-canonical/`, not the current Healthcare dbt consumer. No Self-Runner production dbt cutover was performed.
- **Scope of DONE 3.3/3.5**: versioned **source and offline CI consumer** migration + Current Spec/CODE owner reconciliation. Does **not** mean Azure 42 real HL7 GET, deployed Fabric Spark, approved Silver or OMOP Gold. 3.4 remains OPEN until separate vetted obsolete-file cleanup PR. Runtime shared resources not touched.
- This documentation-only evidence commit follows the already tested code head. Any additional workflow runs on this new doc-only SHA must be reviewed before merging.

## P3 3.4 old dbt source cleanup candidate (separate PR, pending acceptance)

- Repo verified Main pre-cleanup: `9bb036ca3062b0305f897d9a1235690b4d5773b8` (#821). There are no overlapping open Healthcare PRs at the start of this cleanup. New dbt source is the sole maintained local CI owner; the two independent Hosted Workflow Run IDs on prior cutover are #42446582767 and #42446582771 (both SUCCESS).
- Exactly five frozen SQL/config files are removed from current Main-facing source: old `dbt_project.yml`, `models/sources.yml`, `models/canonical_patient.sql`, `models/canonical_encounter.sql`, `profiles/local/profiles.yml`. Keep `parse_oie_v2.py`, `landing_intake.py`, `write_staging_delta.py`, `.github/quality/tests/data-platform/hl7/check_local_candidate.py`, fixture/negative tests and both Hosted Workflows.
- Split mixed dependencies: old Local DP `requirements-local.txt` retains pinned `hl7apy` / `pyspark` / `delta-spark`, new `azure-fabric/dbt/hl7-canonical/requirements-local.txt` includes the old parser/Delta lock with an explicit relative `-r`, plus pinned `dbt-fabricspark` adapter. Both workflows install from the governed dbt requirement entrypoint.
- Old file navigation links are replaced with fixed historical PR references. Structural regression changes from expecting frozen old project in live tree to asserting complete retirement while preserving Parser/Writer/source contracts. No remote Azure/Fabric/Silver/Gold operations.
- **Acceptance HOLD:** mark 3.4 DONE only after exact cleanup PR HEAD passes both real Hosted local Delta/dbt workflows, static source-structure/format/docs/OpenSpec checks, and four GitHub trusted Required Checks. Existing Self-Runner historical isolated POC and Git history are untouched.

## P3 3.4 actual local cleanup acceptance — exact tested source HEAD

- [PR #822](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/822), physical local cleanup code HEAD `94a9984479f1e6b40a4856b962c335624aceb51d`. Five old dbt files have been deleted from the proposed Git tree; Parser/Intake/Delta Writer and existing 18/27 contract/test assets remain. New governed dbt requirements include the single old Parser/Spark/Delta pinned file and pinned dbt adapter. No Azure/Fabric/OIE or shared cluster action was performed.
- [Old HL7 runner / new dbt consumer regression Run #42447235193](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42447235193) SUCCESS: 12/12 Python tests including anti-rollback/split-requirements, staging CREATED and identical REPLAY SKIP, 5/5 dbt models, 15/15 dbt tests and independent Canonical Patient 18/Encounter 27 physical readback PASS.
- [Independent P3 physical dbt Run #42447235126](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42447235126) SUCCESS: 5/5 models and 15/15 data tests, physical Patient/Encounter 18/27 Contract readback, logical Replay fingerprint PASS, expected-negative failures all detected for unmatched A03, reversed event time, cross-patient identity collision, duplicate control ID.
- Four trusted default-branch Required checks, OpenSpec static validation, documentation relative link checks, Component Code Map/Name, extra Local DP Spark manifest and isolated build/smoke checks all SUCCESS on tested cleanup code HEAD. Initial stale Spark CODE links and missing OpenSpec scenario were fixed before the final green Runs. Non-required third-party Cloudflare Workers Build failure is unrelated to HL7 and is not a required check.
- 3.4 is DONE at **source and GitHub-hosted synthetic local CI level only**. The later documentation-only closeout commit must still pass its own branch Required checks and should not be confused with real Azure 42-HL7 consumption, remote Fabric Spark, approved Silver or OMOP Gold.
