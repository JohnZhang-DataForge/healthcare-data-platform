# Tasks — Repository / Fabric Layout Governance

## 0 — OpenSpec 方案先行（仅计划，无生产改动）

- [x] 0.1 只读审计 Healthcare main `8d8ba3f9fa4593430550c3e8906c8fc089ef17fa` 与开放 PR：Fabric 15 测试、8 README、2 份其他说明性 MD，确认真实 Fabric Native Items 和 Warehouse Workspace-only 所有权。
- [x] 0.2 依据用户确认缩小范围：先统一规范和 Gate，仅清理 Fabric 存量，不迁移 Local DP、Portal、Shared Engine 的测试或业务源码；不得新建 `azure-fabric/src/` 或为漂亮目录移动 Warehouse。
- [x] 0.3 建立包含确切存量、阶段 PR、正负向门禁测试、兼容性、回滚及验收条件的 OpenSpec Proposal、Design、Delta Specs、Tasks。
- [x] 0.4 本**纯 OpenSpec 计划 PR** 通过 `validate-openspec`、可信/普通 Change Gate、文档链接等适用 CI，按最终 HEAD 审核合并；独立 main 读回；确保 1–5 阶段仍 OPEN。

## 1 — 先防止新违规（独立实现 PR）

- [x] 1.1 将本 Change 的最终文件所有权规则落实至 `AGENTS.md`、`DOCUMENTATION-GOVERNANCE.md`、`AGENT-RULES.md` 和受影响的 Shared Data Engine / Fabric ADR；明确旧路径冻结例外、未来新文件唯一位置与规范优先级。
- [x] 1.2 在 `.github/quality/scripts/` 编写**只读、按确切路径**的布局门禁；检查源区新增 README/说明 MD、测试归属、Native Fabric Item、未批准的新模块及 CODE.md 同步；现存 Local/Portal/Shared 文件严格 allowlist。
- [x] 1.3 在 `.github/quality/tests/` 加完整正向/负向单测，模拟旧存量编辑、新违规新增、路径穿越/绕过、伪 Fabric Warehouse Item、未更新 CODE.md，明示 `path + rule + expected owner`。
- [x] 1.4 修复 `check_component_code_map.py` 对 Fabric Native 项的旧 `notebooks/` / `pipelines/` 子路径假设，覆盖实际根级 `*.Notebook/`、`*.DataPipeline/`、`*.Environment/`、`*.Lakehouse/` 的合规范围，不触碰 Native 内容本身。
- [x] 1.5 将布局检查接到可靠的 PR Gate，与现有 Trusted Change Gate 兼容；真实正向 PR 可合并、真实负向 PR 被 GitHub Ruleset **Required Check** 阻止。如果缺少仓库管理权限，留明确 HOLD，不将 CI green 冒称规则生效。

## 2 — Azure Fabric 文档清理（独立 Docs PR）

- [x] 2.1 对账 `azure-fabric/infra-terraform/` 3 份 README；保留 Capacity、OIDC、Remote State、IAM、已创建/未创建区分和真实 Run 的独有内容到 `documents/systems/azure-fabric/`。
- [x] 2.2 对账 Notebook 1 份与 OpenLineage 1 份 README，以及 `openlineage/PUBLISHER.md`；保留 HOLD、真实运行边界、只读协议、源代码唯一性。
- [x] 2.3 对账 Warehouse 3 份 README（包含 `writer/README.md`）及 `ID-ALLOCATION-STATE-MACHINE.md`；保留 INT allocator、单写入者事务、ROLLBACK、G4/G5 概念映射与 `NOT GOLD_COMMITTED` 约束。
- [ ] 2.4 重建所有反向链接及权威 CODE.md，完成内容一一核对之后删除旧说明性文件；8 份 README 无遗漏、2 份其他 MD 有明确处理结果；文档链接/CI PASS。

## 3 — 仅 Azure Fabric 的 15 个测试迁移（可按 3 个小 PR 串行）

- [ ] 3.1 Notebook 8 个测试迁至 `.github/quality/tests/azure-fabric/notebook/`：修正 `fabric-fhir-notebook-offline.yml`、测试 Import/PYTHONPATH、Fixture/Native Contract、关联 CODE.md，确保旧/新用例集及断言等价。
- [ ] 3.2 OpenLineage 2 个测试迁至 `.github/quality/tests/azure-fabric/openlineage/`：保留 Blob Publisher 的安全负向测试、Mock 和已固定协议，修复所有调用方路径。
- [ ] 3.3 Warehouse 5 个测试迁至 `.github/quality/tests/azure-fabric/warehouse/` 的 CDM/OMOP 子目录；修复 `fabric-omop-cdm54-schema-offline.yml`、`fabric-omop-foundation-identity-schema-offline.yml` 路径与发现规则，保持原 DDL 来源 SHA、Identity/Mapping 防护不变。
- [ ] 3.4 按实际 Git 搜索/Workflow 内容逐一核对 Self-Runner 对旧路径的引用；若依赖不可验证则 HOLD，不删旧入口；每组运行适用测试及构建、OpenSpec/Docs/Code Gate 后才合并。

## 4 — 可选辅助源码归属，不再另起大迁移

- [ ] 4.1 审计 `notebook-development/fhir_ingest_notebook.py`、`native_item_readiness.py` 的真实调用/依赖。如果确为独立测试辅助且搬迁有明确收益，可以迁移到 `.github/quality/scripts/azure-fabric/`；否则保留源文件并仅修正文档 Owner。
- [ ] 4.2 再次确认 `warehouse/`、`openlineage/` 与真实 `workspaces/healthcare-omop/` 的唯一 owner，**不**搬 Warehouse/Lineage 业务代码、不创建 `src/` 镜像树、不变更真实 Workspace Item。

## 5 — 最终独立审计和收口

- [ ] 5.1 独立 QA 读取最终 main 和合并 PR、CI、文件 inventory：核实 Fabric 15/15 测试按规划归位，8/8 源码 README 退役，2 份其他 MD 已治理、历史例外清单准确。
- [ ] 5.2 独立检查正向与负向 PR、真实 Ruleset Required 状态；未做到实际 blocked 则保持任务 OPEN 并报告管理权限阻断。
- [ ] 5.3 对关键 Native Item / Warehouse / Pipeline 的 Git 树 SHA 与整改前固定 SHA 独立对账；确认**没有任何 Fabric/Azure/Local Runtime 操作**或业务数据变更。记录准确 main SHA、PR、Run、保留的 Legacy 例外。
- [ ] 5.4 全部要求和负向测试通过后再审查 Current Spec/Archive；OpenSpec `validate --all --strict` 不是实际实施或运行时验收。

## Stop / HOLD

任何阶段发现需要修改 G4/G5 历史数据、真实 Warehouse Schema/Gold、Fabric Native Item metadata、已通过的 Wheel 版本、Local DP/Portal/Shared 的测试物理路径，立即 HOLD 并另开获批 Change。相同原因 3 次修改验证仍失败停止自动尝试；不用无限重试方式扩大目录迁移。

### P1 implementation audit (2026-11-04)

- Source baseline: `ee435d8720cfed698e239f767f313addf36a924e`; PR #671 merged. P1 branch `governance/p1-repository-layout-gate-20261104`.
- Tasks 1.1–1.4 implemented and merged via PR #672; the original checker bug was corrected in merged PR #674. The layout baseline freezes **185 exact existing paths** only. All Fabric 15 source tests / 8 README remain untouched.
- Task 1.5 is completed based on real post-fix protected green #676 and blocked negative #675; see final acceptance evidence below. No P2–P5 runtime, migration, or other work is in P1.

- **Historical post-merge 1.5 HOLD (resolved by merged PR #674):** [controlled negative PR #673](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/673), required job [41943842231](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41943842231), was correctly BLOCKED by `require-trusted-change`, but revealed a false positive: pre-existing root `.gitignore` was not in `ALLOWED_TOP_LEVEL`. At that time, Task 1.5 remained OPEN. The subsequent one-time approved Ruleset maintenance window was completed because the trusted policy is deliberately frozen and runs from `main` for every PR; do not bypass silently. Verified exact main tree: adding `.gitignore` to allowed root entries yields no other root or legacy baseline violations.

### P1 final post-fix Required Check audit (2026-11-04 ET)

- [#674](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/674) is merged. The independently read back main is `fbd08553b97064ab805c40aa6884bcaa1889a274`; `.gitignore` is admitted by the trusted checker and its regression tests are present.
- Ruleset `25365902` is **active** with `require-trusted-change` and `validate-openspec` required (GitHub Actions integration `15368` for both), without bypass actors.
- Post-fix **negative** [#675](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/675) at `cf03a3dea67b79baeea1c1930af10f40623d4707` was rejected by the actual Required Check: [run 41947587388](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41947587388), job `126983525823`, `PATH=azure-fabric/warehouse/p1-postfix-negative/README.md RULE=new-source-document EXPECTED_OWNER=documents/`, `REPOSITORY_LAYOUT_GATE=FAIL`; GitHub `mergeable_state=blocked`. PR closed **unmerged**.
- Independent Git-tree SHA inventory: all **34** protected pre-P1 paths are byte-identical to `ee435d8720cfed698e239f767f313addf36a924e`: 11 Fabric Native Git Item files, 15 Fabric tests, and 8 source README files. The frozen legacy baseline remains exactly **185 paths**; **P2–P5 not started**.
- Post-fix **positive** [#676](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/676) proved actual trusted enforcement **PASS** on first valid PR body edit: [run 41947856108](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41947856108), job `126984406775`; explicit `REPOSITORY_LAYOUT_GATE=PASS` (`legacy_exact_paths=185`), `CODE_MAP_GATE=PASS` (`mapped_fabric_native_files=11`), and `OPENSPEC_CHANGE_GATE=PASS`. `validate-openspec` also succeeded. The final acceptance-record commit requires its own successful Required checks before merging #676. All normal branch protection stays enabled.


### P2 Terraform documentation migration (2026-11-04 ET)

- Task 2.1: consolidated three exact source README files into `documents/systems/azure-fabric/infra-terraform/{FABRIC-ENVIRONMENT-ADOPTION,CAPACITY-LIFECYCLE,LANDING-CONNECTION}.md`, preserving original command references, OIDC/State/Import/RBAC constraints, Trial-vs-paid capacity behavior and actual 2026-10-22 Reader/Connection Run evidence. The three old README source files are retired in this PR; Terraform files and State are unchanged.
- Explicitly distinguished the original 2026-10-16 seven-Root Plan-only evidence from later Control Plane Apply/GET; neither is Blob data-plane read or Runtime acceptance.

- Task 2.2: migrated Notebook's Git-first/HALT/old Wheel checkpoint to `notebooks/GIT-FIRST-OFFLINE-VALIDATION.md` and preserved complete OpenLineage compatibility+Publisher protocol under `openlineage/{README,CODE,PUBLISHER}.md`. Retired the two source README and source PUBLISHER Markdown; **no Notebook/Pipeline/Environment/Publisher Python/test was moved or executed**. Historical 0.1.0 Wheel and trial runs are labeled historical, not current environment release.

- Task 2.3: retired the three Warehouse source README files plus the source ID allocation state-machine Markdown, moved all four unique technical/evidence contracts into `documents/systems/azure-fabric/warehouse/`, added one owner README and refreshed Warehouse CODE navigation. Pinned upstream OHDSI SHA, Fabric INT/identity caveats, snapshot isolation, global writer fence, six-table rollback #41824079608, and NOT GOLD_COMMITTED are preserved. No SQL/test/Writer runtime files were changed or executed.
