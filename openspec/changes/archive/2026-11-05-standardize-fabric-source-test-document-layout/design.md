# Design — Gate-first, Fabric-only legacy cleanup

## 1. 已验证基线与约束

2026-11-04 只读审计 Healthcare `main=8d8ba3f9fa4593430550c3e8906c8fc089ef17fa`（树未截断、1184 个 Git blob、暂无打开的 PR）：

- `azure-fabric/notebook-development/tests/` 有 **8** 个 Python 测试，`azure-fabric/openlineage/tests/` 有 **2** 个，`azure-fabric/warehouse/**/tests/` 有 **5** 个，共 **15** 个 Fabric 测试。
- Fabric 源码区有 **8** 份 `README.md`；另有 `openlineage/PUBLISHER.md` 和 `warehouse/omop-foundation/ID-ALLOCATION-STATE-MACHINE.md` 两份说明性 Markdown。
- Local DP、Portal、Shared Engine 现有约 **148** 个测试相关文件（131+12+5，含个别非 `test_*.py` 工具与 fixture），**本 Change 禁止物理迁移**。其旧测试位置只能作为精确存量例外，不是今后 Agent 创建新文件的许可。
- 已有 `.github/quality/tests/` **17** 个质量检测测试（本次不搬）；现有 Fabric 原生 Workspace 中 **4** 个 Native Item 文件夹、**0** 个测试。
- `DOCUMENTATION-GOVERNANCE.md` 要求 Azure/Fabric 人类文档归 `documents/systems/azure-fabric/`，但 Shared Engine Ownership/早期 ADR 的测试布局和部分 Native Item 示例仍采用旧分类；要保留已验证运行边界并更新这些**过时的规则文字**。
- `.github/quality/scripts/check_component_code_map.py` 的 Fabric Native 规则仍指向旧的 `workspaces/healthcare-omop/notebooks/`、`pipelines/`；真实 Item 在该根下的 `nb_fhir_ingest.Notebook/`、`pl_fhir_ingest.DataPipeline/` 等目录。旧规则的 CI 绿灯**不能充当新布局合规证明**。

本 Change 的设计以**尽量少搬**为原则；不为了形式上实现 `src/` 树再一次全局改变路径。

## 2. 目标文件所有权（不得混同物理 Fabric 资源）

| 类型 | 目标归属 | 禁止事项 |
| --- | --- | --- |
| 正式业务实现、SQL、Terraform、Platform OpenLineage | 各自原有 `azure-fabric/` 功能目录 | 不为了整齐迁移业务源码或复制实现 |
| Git 原生 Fabric Item | `azure-fabric/workspaces/healthcare-omop/<actual-name>.<item-type>/` | 不加虚构 `.Warehouse/`、README、Tests、独立源包 |
| 新的自动化测试 | `.github/quality/tests/<system>/<component>/` | 不在各源码 `tests/` 下新建测试 |
| 测试所用静态样本 | `.github/quality/fixtures/<system>/<component>/`（必要时） | 不将生产数据、许可证文本或 PHI 加入 Git |
| 测试框架/检查脚本 | `.github/quality/scripts/`，按现有组件或系统命名 | 不把正式业务 Runtime Python 当作检查工具迁移 |
| 人类说明文档 | `documents/systems/<component>/`、`documents/architecture/`、`documents/engineering/` | 不在代码区新增说明性 README/CODE/ARCHITECTURE/PUBLISHER 等 Markdown |
| 当前 Change/决策/验收任务 | `openspec/changes/standardize-fabric-source-test-document-layout/` | 不宣称尚未实施的规范已在 main 生效 |

**保留**仓库根 `README.md` 作为公共入口，保留源码区 `AGENTS.md` 作为 Agent 指令、机器可读的 Fabric `.platform`、JSON、SQL 与运行需要的格式。Local/Portal/Shared 的当前 README 和测试是**冻结存量**，不能因本次治理擅自删除或改动。只有经审查证明某 `.md` 为自动化必需的非说明性素材时，才可在目标规则中列出经过审批的精确路径例外。

**Warehouse 物理归属**：真实 Fabric `dw-omop-5.4` ID `7a6d08da-278d-4603-8a3b-28640110984c` 属于现有 Workspace `healthcare-omop`；它目前是受 Git 更新保护的 Workspace-only 项目，保留 SQL/Writer 版本源码于 `azure-fabric/warehouse/`。不新增 `dw-omop-5.4.Warehouse/` Native Item，不碰数据或实际部署。

## 3. 精确存量与迁移目标

### 3.1 Fabric 8 个说明性 README

| 现有文件 | 应迁移的权威文档目的地（须对账并去重） |
| --- | --- |
| `azure-fabric/infra-terraform/components/fabric-environment/README.md` | `documents/systems/azure-fabric/infra-terraform/README.md`、`ARCHITECTURE.md`；注意已废弃的 Root/State 说法仅作历史事实 |
| `azure-fabric/infra-terraform/fabric-workspace/healthcare-omop/capacity-api/README.md` | `documents/systems/azure-fabric/infra-terraform/` 及 `documents/engineering/operations/`，保留 Trial/Paid 授权、安全与成本界限 |
| `azure-fabric/infra-terraform/shared-infra/connection/README.md` | `documents/systems/azure-fabric/infra-terraform/`，保留角色/连接、OIDC/验证边界和真实 Run |
| `azure-fabric/notebook-development/README.md` | `documents/systems/azure-fabric/notebooks/README.md`、`CODE.md`，不维护第二套 Notebook |
| `azure-fabric/openlineage/README.md` | `documents/systems/azure-fabric/` 中唯一的 OpenLineage 组件说明或总索引；历史 HOLD 不能被改写为 PASS |
| `azure-fabric/warehouse/omop-cdm-5.4/README.md` | `documents/systems/azure-fabric/warehouse/`，保留 OHDSI 上游固定 blob SHA、DDL 类型适配和 F0/F1 证据 |
| `azure-fabric/warehouse/omop-foundation/README.md` | `documents/systems/azure-fabric/warehouse/`，保留 Identity Map/Allocator/Ledger、单写入者事务约束 |
| `azure-fabric/warehouse/omop-foundation/writer/README.md` | `documents/systems/azure-fabric/warehouse/` 的 Writer/Identity/Replay 说明，保留 `SOURCE_ONLY / NOT GOLD_COMMITTED` 和 Rollback 证据 |

此外必须审查并仅在完整对账后迁移
`azure-fabric/openlineage/PUBLISHER.md` 和
`azure-fabric/warehouse/omop-foundation/ID-ALLOCATION-STATE-MACHINE.md`。
搬运前核对重复知识、链接、当前真实状态、已批准合同和执行安全约束；**不得把纯代码清理写成业务功能验收**。历史技术详情保留固定 Git commit/PR/Run 引用。

### 3.2 仅迁移 15 个 Fabric 测试

旧路径 → 新目录（保留文件语义命名，不做业务重构）：

- `azure-fabric/notebook-development/tests/` 下 **8 个**：
  `test_fabric_git_native_contract.py`、
  `test_g3_bronze_receipt.py`、
  `test_g3_physical_negative_readonly.py`、
  `test_g4_dq_quarantine.py`、
  `test_g4_silver_delta.py`、
  `test_g5_candidate_source_readonly.py`、
  `test_g5_pipeline_readonly.py`、
  `test_notebook_offline.py`
  → `.github/quality/tests/azure-fabric/notebook/`。
- `azure-fabric/openlineage/tests/` 下 **2 个**：
  `test_compatibility.py`、`test_publisher.py`
  → `.github/quality/tests/azure-fabric/openlineage/`。
- `azure-fabric/warehouse/omop-cdm-5.4/tests/test_cdm54_schema.py`
  → `.github/quality/tests/azure-fabric/warehouse/omop-cdm-5.4/`。
- `azure-fabric/warehouse/omop-foundation/tests/` 下 **4 个**：
  `test_concept_profile.py`、`test_identity_plan.py`、
  `test_identity_schema.py`、`test_silver_identity.py`
  → `.github/quality/tests/azure-fabric/warehouse/omop-foundation/`。

`native_item_readiness.py` 与 `fhir_ingest_notebook.py` 是 `notebook-development/` 下**两份非测试命名的 Python 文件**。先检查 import/runtime/部署入口：若确为离线工具，按明确依赖迁至 Quality scripts；若仍是正式入口，则留在业务源码，不能仅根据目录名推断或删除。

## 4. 按有限 PR 执行（先 Gate，后存量）

| 阶段 | 计划 PR 范围 | 检查及退出条件 |
| --- | --- | --- |
| **P0 Plan** | **本 PR 仅新增 OpenSpec `.openspec.yaml`、proposal、design、specs、tasks** | OpenSpec strict、trusted Change Gate、链接检查 PASS；main 上仍无目录移动；合并后本 Change 保持 Active |
| **P1 Rule + Guard** | 更新 `AGENTS.md`、`DOCUMENTATION-GOVERNANCE.md`、Shared Engine/早期 Fabric ADR 中**实际冲突**的规则；新增 `.github/quality/scripts/check_repository_layout.py` 与 `.github/quality/tests/test_repository_layout.py`、可信 PR Gate；修正根级 Fabric Native CODE-map | exact-path 旧文件基线、增量 FAIL、新路径 PASS；正反向试验，验证 GitHub Required Check，不能仅凭 job SUCCESS 宣称保护已生效 |
| **P2 Fabric docs** | 迁移 8 README 和 2 份说明性 Markdown 到权威文档，按知识领域去重；原代码文件在文档读回和链接 CI 通过后删除 | 8/8 README 内容对账、所有反向链接修正、OpenSpec/文档测试 PASS，历史临床/事务/许可边界不变 |
| **P3 Fabric tests** | 15 个测试按 Notebook 8、OpenLineage 2、Warehouse 5 三组顺序迁移；一个组只在当前 PR CI PASS 并合并后处理下一组 | 旧/新 unittest 相同用例收集量、正负向断言、Fixture、build/import、CODE.md、被影响 workflow paths、Self-Runner path 引用核对；失败即回滚该组，不影响别组 |
| **P4 Optional** | 只在证据确认 `notebook-development/` 2 个工具可以安全退役时移动；否则留存并在任务说明理由 | 不改变正式 Notebook 实现、Wheel、Gateway、Delta 或任何资源路径 |
| **P5 Audit** | 保留精确例外基线的 185 条不可变历史记录，以 `baseline ∩ PR base tree` 作为真正有效例外；独立 QA 检查门禁真实阻止违规 PR | 已退役的 25 条 Fabric 路径不得复活，实存例外为 160 条（按验收快照），负向 #689 必须被 Required Check 阻止；完成 Current Spec 及 Archive 后才关闭 P5.4 |

P1 结束后可以同时准备不同模块的*只读审计或文档草稿*，但是涉及共享文档/规则/Workflow 的真实改动串行集成。默认不进行大规模并行 Git 文件搬迁。

### 4.1 既有 CI/外部依赖至少要检查

- `.github/workflows/fabric-fhir-notebook-offline.yml`：`unittest discover -s azure-fabric/notebook-development/tests`，且 `PYTHONPATH` 指向旧模块。
- `.github/workflows/fabric-omop-cdm54-schema-offline.yml`：直接指向旧 `omop-cdm-5.4/tests`。
- `.github/workflows/fabric-omop-foundation-identity-schema-offline.yml`：测试发现与路径触发器都指向旧 `omop-foundation/**`。
- `.github/workflows/shared-engine-wheel-validation.yml`：现有 `shared-data-engine/tests` **仅记录为冻结存量，不随 P3 移动**。
- `.github/quality/scripts/check_component_code_map.py`：旧 Fabric Native 子路径判断必须修正为真实根级 Item，覆盖 Root Notebook/Pipeline/Environment/Lakehouse，同时审查执行 Gate 的 workflow 的 `paths`。
- 搜索全仓实际 Python import、`pytest`/`unittest`、YAML `paths`、相对 fixture、Docker/打包引用；检查**私有 Self-Runner** 对上述文件是否有固定 SHA/路径引用。未经验证不可移除旧目录。
- 不要在此 PR 开始创建第二只 Shared Wheel、更新 Data Fabric Gate，或为了让 CI 过关而关闭生产测试。

## 5. Guard 实施细节

- 基线取 P1 PR 的**确切被批准的 main SHA**，`git ls-tree` 建 exact-path allowlist，只冻结合法历史存量；不能使用整个目录通配豁免。
- PR 差分拒绝新增源码 README / 说明文档和不在 `.github/quality/tests/` 下的新测试；拒绝新顶层模块而没有显式架构变更。允许更新历史测试源文件以维护现行 CI，不允许从旁复制第二套测试。
- 候选是否违规只处理 GitHub PR 的 Git *路径列表/静态内容*；可信 Gate 在 base 默认分支运行 Checker，**不执行不可信 PR 的 Python/Shell**。复用现有 Trusted Change Gate 思路，不与其 check 名称冲突。
- 不允许通过删除/修改被保护的 Gate、修改 Path filter、缩小 baseline 或假冒 metadata 来绕过。Gate 必须具备可解释的 `path + rule + expected owner` 输出。
- 正向试验包括：现有变更照常 PASS、正确目录新增测试 PASS、Fabric Native 原生 metadata 仍可同步；负向试验包括：新 `source/**/README.md`、新 `source/**/tests/test_x.py`、伪 `*.Warehouse`、未知顶层模块、缺少 CODE.md 同步均 FAIL。
- 仓库 Ruleset 最终要真正**Required** 此检查；如果 GitHub App 不能变更 Ruleset，应登记 HOLD/需要管理员操作，不得把“脚本存在”称为“强制生效”。

## 6. 回归、边界和回滚

- 所有 PR 以最新 main 为基线，避免与 FHIR→OMOP、Marquez 并行 Session 冲突；涉及相同文件的 PR 串行。
- 每个测试迁移 PR 比对被影响测试的发现数量、名称及结果，记录失败用例和 CI Run；原路径执行需在旧 HEAD 上记录，然后在迁移 HEAD 上记录，以免只比较单侧。
- CI 失败优先恢复原路径并修正引用；超出已批准迁移范围、3 轮失败或运行依赖不明时 HOLD。
- 仅变更 Git、静态检查与离线测试；**不运行**任何 Fabric Spark/Delta/Warehouse/DW、Azure Capacity、Terraform Apply/Destroy、Self-Runner 的云端流程，不修改任何过去已批准的数据分区/批次/事务。
- 回滚单组 PR 用对应 Git revert，并恢复旧 CI 路径与文档链接；保持从一开始的 P1 Guard 防止产生新违规。
- 最终独立验收必须核实并报告原始目标：Fabric 15/15 测试迁移、8/8 README 退休和 2/2 MD 去重/有据保留、源代码/Native Item SHA 未变、旧数据未触碰、Rule required 真正阻止新违规。任何未满足项目标记 OPEN，不宣称整体 DONE。

## 7. P5.4 经批准的收口设计变更（2026-11-05 ET）

用户批准将第 4 节 P5 阶段原定的「物理删除 25 条旧 Fabric 例外」调整为**保留 P1 精确历史库存的 185 条不可变路径**，但**这不是 185 条可用豁免**。本段覆盖原方案中的物理删除动作，不改变 P1/P2/P3/P4 的验收结果或任何运行时边界。

- 历史来源：`.github/quality/repository-layout-legacy-baseline.txt` 固定 185 个 P1 原始路径，保持字节内容不变；此文件及 trusted checker 都在 `GUARD_FILES` 保护内，普通 PR 无法改写。以后追查旧版本时仍能查看当时允许的具体路径。
- 有效例外的唯一判定：只有在 `path in baseline` **且** `path in base_paths`（当前 PR 的 Git base tree）时，已存在的历史源码区测试或文档才可继续修改。基线条目本身不会给已删除文件授予重新创建的权限。按 P5 审计快照，25 条 Fabric 文件均已退役，其余 160 条仍然存在；这个 160 是随仓库未来合法删除而单调减少的**快照值**，不能硬编码为永远固定。
- 删除/重建语义：对历史文件的删除允许；以后即使原路径仍列在 185 条库存里，重新新增也属于违规。若要在旧源码目录重新引入，必须另走审查并修改正式治理规则，不能利用历史基线。
- 已有真实证明：负向 PR [#689](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/689) 恢复两个已经退役且仍在历史清单中的 Notebook 路径，`require-trusted-change` 对其分别给出 `new-source-document` 和 `new-test-outside-quality`，GitHub 阻止合并；PR 已关闭、未合并。相关测试/文件库存及 Git blob 不变性的完整证据见 [P5 验收](P5-ACCEPTANCE-EVIDENCE.md)。
- 批准范围：本次仅更新 OpenSpec 决策、验收报告、Current Spec 并 Archive Change，不触碰历史基线、任何 Ruleset、GitHub Actions、测试/生产代码、Fabric Native Item、Local DP/Portal/Marquez、实际云资源或数据。
- 关闭条件：独立验收 P5.1–5.3 已通过；本变更被记录、Current Spec 已采用、原 Active Change 被归档，且最终 PR 的 `require-trusted-change`、`validate-openspec` 必须在未绕过分支保护的前提下成功并合并。OpenSpec static PASS 不代表业务 Runtime 验收。
