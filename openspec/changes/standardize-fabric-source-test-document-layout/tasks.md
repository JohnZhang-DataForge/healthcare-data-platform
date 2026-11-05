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
- [x] 2.4 重建所有反向链接及权威 CODE.md，完成内容一一核对之后删除旧说明性文件；8 份 README 无遗漏、2 份其他 MD 有明确处理结果；文档链接/CI PASS。

## 3 — 仅 Azure Fabric 的 15 个测试迁移（可按 3 个小 PR 串行）

- [x] 3.1 Notebook 8 个测试迁至 `.github/quality/tests/azure-fabric/notebook/`：修正 `fabric-fhir-notebook-offline.yml`、测试 Import/PYTHONPATH、Fixture/Native Contract、关联 CODE.md，确保旧/新用例集及断言等价。
- [x] 3.2 OpenLineage 2 个测试迁至 `.github/quality/tests/azure-fabric/openlineage/`：保留 Blob Publisher 的安全负向测试、Mock 和已固定协议，修复所有调用方路径。
- [x] 3.3 Warehouse 5 个测试迁至 `.github/quality/tests/azure-fabric/warehouse/` 的 CDM/OMOP 子目录；修复 `fabric-omop-cdm54-schema-offline.yml`、`fabric-omop-foundation-identity-schema-offline.yml` 路径与发现规则，保持原 DDL 来源 SHA、Identity/Mapping 防护不变。
- [x] 3.4 按实际 Git 搜索/Workflow 内容逐一核对 Self-Runner 对旧路径的引用；若依赖不可验证则 HOLD，不删旧入口；每组运行适用测试及构建、OpenSpec/Docs/Code Gate 后才合并。

## 4 — 可选辅助源码归属，不再另起大迁移

- [x] 4.1 审计 `notebook-development/fhir_ingest_notebook.py`、`native_item_readiness.py` 的真实调用/依赖。如果确为独立测试辅助且搬迁有明确收益，可以迁移到 `.github/quality/scripts/azure-fabric/`；否则保留源文件并仅修正文档 Owner。
- [x] 4.2 再次确认 `warehouse/`、`openlineage/` 与真实 `workspaces/healthcare-omop/` 的唯一 owner，**不**搬 Warehouse/Lineage 业务代码、不创建 `src/` 镜像树、不变更真实 Workspace Item。

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


### P2.4 final source-path and CI evidence — 2026-11-04 ET

- Review PR [#677](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/677) at verified pre-closeout HEAD `0b3a293cab7049c2cfc2c359f9ffdc03b88380b7`. **All ten** Azure-Fabric source-area Markdown files (8 README + 2 technical MD) were retired from the branch, with ten relocated detailed documents plus system-specific README/CODE additions. No source-area Markdown remains under `azure-fabric/`.
- **Reverse link gate:** [Documentation Relative Links Run #41951371069](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41951371069), job `126995847564`: `DOCUMENTATION_LINKS_GATE=PASS; files=338; checked=1911; missing=0`.
- **Central quality/ownership CI:** [Run #41951371217](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41951371217), job `126995847886`: `Ran 179 tests` PASS and `CODE_MAP_GATE=PASS; mapped_fabric_native_files=11`. The existing central quality contract `.github/quality/tests/test_fabric_shared_connection_contract.py` was minimally updated to require the authoritative new Landing Connection doc instead of source `README.md`; its Terraform/IAM assertions remain intact. This is **not** one of the 15 source-area Fabric test migrations scheduled for P3.
- **Trusted Required Check:** [Run #41951366537](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41951366537), job `126995834821`: 25 OpenSpec + 19 Layout unit tests PASS, `REPOSITORY_LAYOUT_GATE=PASS` for exact 185-path baseline, `CODE_MAP_GATE=PASS` (11 native mapped), `OPENSPEC_CHANGE_GATE=PASS`. `validate-openspec` separately succeeded at HEAD; all 24 reported GitHub checks completed SUCCESS before this evidence-only commit.
- **Independent tree hash comparison** vs pre-P2 main `5a7bd15977b307c358ff50155888a58f813e06ed`: all 11 Fabric Native item blobs, all 15 source-area Fabric test blobs, and all non-Markdown Fabric blobs unchanged; no SQL, Writer logic, Env/Wheel, runtime data or Terraform definitions altered.
- P2 is a **docs/quality-test migration only**, not cloud Runtime verification, Vocabulary license closeout or clinical Gold COMMIT. P3 test move remains **OPEN**. Merge only after latest closeout HEAD again passes actual protected PR checks, then independently read back main.


### P3 test-value and compatibility audit — 2026-11-04 ET

- P3 inventory baseline from merged P2 main `bd8b5c1cafde090b415fb1d82df1df7734aea8a7`: **15 Fabric Python test files, 118 individual `test_*` methods** (Notebook 8/77, OpenLineage 2/8, Warehouse 5/33). These are active/valuable security and regression contracts, not archival-only copies: FHIR Manifest/Source/Delta guards, immutable Publisher, pinned CDM DDL, stable INT identity, Concept negative, Replay and single-writer safety. None is approved for deletion based on current evidence.
- P3.1 migrates 8 Notebook files without removing tests, moves path-based `__file__` root calculations only, and changes `fabric-fhir-notebook-offline.yml` to enforce exactly 8 test files and **at least 87** discovered tests with real `TextTestRunner` execution (zero/skip-only discovery is not sufficient). The Notebook Native source and two offline helper programs remain in source location.
- Cross-repo Self-Runner main at audit SHA `10ef1321fd7a191c2a418700e331551ba523ce2e`: four workflow references to the former Fabric tests are bound to fixed historical Healthcare SHAs, including `fabric-api-client.yml` and the three OMOP deploy/rollback workflows. **Do not rewrite historic frozen source SHA/test paths.** They continue testing the old version; any new unpinned consumer must use current centralized paths. Workflow safety remains independent from file movement.
- Task 3.1 actual regression execution verified: [GitHub Actions Run #41955947551](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41955947551), job `127010747129` emitted `FABRIC_NOTEBOOK_DISCOVERED=87; required_min=77; files=8` and `Ran 87 tests in 17.359s` → `OK`, Wheel 0.1.3 byte-identical, runtime HALT expected. The original inventory had **77 explicit test-method definitions**; unittest discovers 87 due to inherited/parameterized cases. First draft's single outdated Runbook link was fixed in the next branch commit; final protected CI/link tests must again PASS before #678 merge. P3.2/P3.3/P3.4 independently gated.

- Count guard tightened after first real migration run: **77 explicitly declared test methods yielded 87 discovered unittest test cases**. The final Notebook CI must require >=87 discovered/executed cases and exactly 8 files. Historical Run #41955947551 accurately logged the former `required_min=77`; final CI is reverified under new threshold. No runtime, writer or data mutation.

### P3.2 OpenLineage audit (pending protected CI)

- Retained both useful offline tests (Spark/Scala incompatibility and authenticated immutable Blob Publisher FAIL-CLOSED/partial retry), 8 explicit unittest methods; moved paths only with equivalent Python importlib target path. Added a dedicated read-only GitHub Hosted workflow with strict >=8 test discovery, exactly two source test files, and fail-on-test-error. Runtime publisher/compatibility implementations unchanged. Task 3.2 passed actual dedicated CI discovery/runner evidence at [Run #41956789788](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41956789788), job `127013507494`: `FABRIC_OPENLINEAGE_DISCOVERED=8; required_min=8; files=2`, `Ran 8 tests`, `FABRIC_OPENLINEAGE_OFFLINE_CONTRACT=PASS; CLOUD_WRITES=0`. Check-links, trusted Required Check and validate-openspec succeeded on initial PR head; verify final evidence-only HEAD before merging.

### P3.3 Warehouse audit (pending protected CI)

- Five source-area Warehouse regression test files with **33 explicitly declared test methods** remain valuable and are only relocated: CDM54 1/2 plus Foundation 4/31 (Concept Profile, F1 Schema, INT-ID Replay and Silver-to-Identity preview). Upstream OHDSI fixed SHA, global positive INT, single-writer/snapshot safety, Concept rejection, no Gold writes preserved. Both existing offline workflows are updated with exact file inventory and minimum test-discovery checks. Final P3.3 task status requires real CI proof, no static-only assertion.


### P3.3/P3.4 verified execution and cross-repo source audit (2026-11-04 ET)

- Warehouse actual tests at PR [#680](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/680) source head `48f84f776d956ec5039d6c0bebad9dd2d4b6719a`: [CDM54 offline PR checks](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/680/checks) job `127015303829` reported `FABRIC_CDM54_DISCOVERED=2; required_min=2; files=1`, `Ran 2 tests`, `FABRIC_CDM54_OFFLINE_TESTS=PASS; CLOUD_WRITES=0`; Identity job `127015304074` reported `FABRIC_FOUNDATION_DISCOVERED=31; required_min=31; files=4`, `Ran 31 tests`, `FABRIC_FOUNDATION_OFFLINE_TESTS=PASS; CLOUD_WRITES=0`. Combined **5 source files / 33 executed methods**. Validate final evidence commit's actual Required checks before merging.
- P3.4 independently re-read Self-Runner main at SHA `10ef1321fd7a191c2a418700e331551ba523ce2e` and scanned the content of **all 170 tracked GitHub workflow files**; the only four legacy Fabric test path mentions were in `.github/workflows/fabric-api-client.yml`, `fabric-omop-cdm54-schema-deploy.yml`, `fabric-omop-f2-transaction-rollback.yml`, and `fabric-omop-identity-schema-deploy.yml`. All four explicitly check out **immutable historical Healthcare SHAs** (`dde06bf86f7a5390709b66d95ea07e086595385d`, `860af51ca3c1f7389c2276b68494eab274888f94`, `ede02cdaf3ff8b41fc39455be387233f538fa8f9`, `195b1f9a387e3393c47cbc298b1110fc34ba52d5`). Independent recursive Git-tree fetch for **each exact SHA** confirmed the expected original path+test files actually exist. Do not rewrite these fixed historical references to today's test folders; no unpinned Self-Runner workflow reference to removed test paths was found among those workflow files.
- Also searched all **59** current Healthcare GitHub workflow file bodies at the P3.3 PR head; none contains old `azure-fabric/*/tests` execution entrypoints. Explicit new centralized test start dirs are in their respective Notebook/CDM/Foundation/OpenLineage workflows. Offline code-only tests have zero Azure/Git/SQL/Spark persistent side effects.
- Note: These workflow body scans prove only tracked workflow references, **not uninspected arbitrary Self-Runner Python/scripts or external consumers**. Historical source pins are intentionally untouched. P3/P4/P5 remain distinct; P5 must still independently reconcile the exact legacy baseline and true Ruleset enforcement.


### P4 optional helper ownership audit (2026-11-04 ET)

- Task 4.1: inspected the exact `azure-fabric/notebook-development/fhir_ingest_notebook.py` (17-line `importlib` compatibility shim resolving the one true Native Notebook) and `native_item_readiness.py` (63-line read-only native export/HALT checker). The centralized Notebook 87-case offline suite still imports those names through source `PYTHONPATH=azure-fabric/notebook-development`; [Fabric Notebook Offline Workflow](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/main/.github/workflows/fabric-fhir-notebook-offline.yml) directly invokes `native_item_readiness.py` and demands expected exit 2. Relocating them would break imports/relative paths without any approved runtime or maintenance benefit. **Accepted optional decision: keep both in the existing development helper location.** No business source copied/moved.
- Task 4.2: verified the exclusive owners: Git Native Notebook/Pipeline/Environment/Lakehouse remain directly in `azure-fabric/workspaces/healthcare-omop/`; Workspace-only `dw-omop-5.4` has no fabricated `*.Warehouse/` Git Item; `azure-fabric/warehouse/` owns OMOP CDM/Writer, `azure-fabric/openlineage/` owns immutable Publisher and compatibility adapter. After P3, all 15 Fabric `test_*.py` files reside only in `.github/quality/tests/azure-fabric/`. No mirrored code tree, shared Wheel change, production run or cloud mutation performed.
