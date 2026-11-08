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
- [ ] 3.3 在受控切换 PR 中审查全部活跃 Workflow/Self-Runner/源码/配置/文档引用，改接唯一新 dbt 工程并复验，不因新 SQL 可以运行就删除旧文件。
- [ ] 3.4 切换确认后**另一个清理 PR**删除旧 dbt models/project/profiles，更新旧 HL7 CODE、新 Fabric dbt CODE、CI/依赖及全部导航；Python Parser/Intake/Delta Writer 与必要测试继续保留，混合 requirements 按消费者拆分，不做全目录删除。
- [ ] 3.5 同步 Current Spec 的**真实执行 Owner 和迁移状态**；未来 FHIR/业务项目仍走独立 OpenSpec 准入，不预建。

## 已采用治理规则

- 2026-11-07：P1 规则随 PR #811 在 Main 生效；Current Spec 正式采用至 `openspec/specs/fabric-dbt-project-layout/spec.md`（与本次 P1 关闭记录配套）。**P1 目录/AI 治理和 P2 可信 Gate 例外均已验证生效；P3 新 dbt 工程开发、验收与切换仍 OPEN。**

## P3 Candidate implementation (subject to PR review)

- 3.1: Standard new `hl7_canonical` project, CODE Map, schema tests, isolated local profile and dedicated hosted-only P3 Workflow are authored; legacy Parser/Intake/Writer/SQL/Workflow remain unchanged and sole active entry.
- 3.2: **Local synthetic runtime ACCEPTED** at [PR #820](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/820), validated exact source HEAD `cc58df1ef202b2d833c1421200ffebc7f761b26f` by [GitHub-hosted Run #42444753385](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42444753385) SUCCESS: real physical local Delta staging 2 rows CREATED + identical replay SKIP, dbt debug/compile PASS, 5/5 models, 15/15 tests, independent physical Patient 18 / Encounter 27 fields + clinical values, second run fingerprint replay PASS; four isolated expected-failure negative scenarios each detected (unpaired A03, reversed time, cross-patient identity collision, duplicate message control). This is offline **local-only Candidate** runtime, not Azure 42 real HL7 objects, Fabric remote Spark, Silver or Gold. First Run #42444412477 failed on test-harness dbt diagnostic phrase despite correctly detected negative; repaired only negative assert matching and reran full acceptance. Latest evidence applies to code SHA above; this documentation-only closeout does not change the tested SQL/Workflow.
- 3.3: A separate cutover PR adapts the original HL7 GitHub-hosted regression workflow to the approved `hl7-canonical` project and compatible `hl7_candidate` output schema, retains old Parser/Writer and Contract readback, adds a static anti-fallback test, and documents that Self-Runner historical POC is not a live dbt consumer. Mark 3.3 DONE only after the cutover PR exact HEAD has passed BOTH hosted workflows, four trusted Required Checks and independent physical Candidate readback; no remote runtime touched.
- 3.4: The obsolete old SQL/project/profiles, any now-unused test/CI dependency, and historical documentation refs require a **separate** consumer-dependency-verified cleanup PR. NOT YET DONE.
- 3.5: Source owner and runtime *scope* are updated in Current Spec and CODE Maps in this cutover PR; only finalize DONE after actual PR acceptance. No live Azure/Fabric/Silver/Gold claim.
