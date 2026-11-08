# HL7 — official consumer Source CODE map

 > **职责已分离：** `local-data-platform/spark/apps/hl7/` 仍是 Parser、Manifest Intake、物理 Delta Staging Writer 的业务 Source Owner；**唯一维护中的本地 dbt 执行工程是** [`azure-fabric/dbt/hl7-canonical/`](../../azure-fabric/dbt/README.md)（[Fabric dbt CODE](../../azure-fabric/dbt/CODE.md)）。旧 dbt SQL/project/profile 仅在历史 PR #809 / 固定 Git SHA 保留，不在当前源码树；业务 Python Parser/Intake/Writer 和回归测试仍在此目录。旧 Self-Runner `experiments/hl7-dbt-canonical/` 仅历史隔离 POC。OIE Producer、共享 Silver Writer / OMOP 均不归本组件管理。

## 代码去留标记（Agent 必须先读）

- **保留 / 业务依赖**：目前仍负责 HL7 协议解析、Manifest 校验、物理 Delta Staging；dbt 新工程完成 **不构成删除这些 Python 文件的条件**。如需以后改用 Shared Engine / Fabric Adapter，另做已验证的 Owner/消费者切换。
- **历史参考 / dbt 已退役**：旧 SQL/project/profiles 已按 P3 3.4 从 Main 删除，仅在 [原验收 PR #809](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/809) 和历史 Git SHA 中回溯；正式 HL7 dbt Project 只在 `azure-fabric/dbt/hl7-canonical/`。不再维护两份 SQL。
- **依赖已拆分 / 回归保留**：本目录的 `requirements-local.txt` 只保留 Parser+Spark/Delta Pin，dbt Adapter Pin 归新工程 `requirements-local.txt` 并以相对路径引用本目录锁定依赖；两条 CI 均使用新工程 Requirements。旧质量回归测试仍在集中测试目录。
- **历史参考 / 不回滚**：旧 Self-Runner POC 和已合并的历史 PR/Run 作为基线证据，不等于最新工程的通过证明。

## 现存文件、未来用途与退役门槛

| 真实源码 / 入口 | 当前职责 | 对新 dbt 工程的用途与计划 |
| --- | --- | --- |
| [parse_oie_v2.py](../../../../local-data-platform/spark/apps/hl7/parse_oie_v2.py) | 经审核 OIE V2 的 `hl7apy` 协议解析和临床字段投影 | **保留 / 业务依赖**：下游仍需结构化 HL7；不是 dbt SQL，不能因 dbt 完成删除 |
| [landing_intake.py](../../../../local-data-platform/spark/apps/hl7/landing_intake.py) | Manifest、Raw SHA、Hospital/Batch/对象身份校验，限本地读取 | **保留 / 业务依赖**：数据真实性 Gate；另行评审共享 Adapter 或新 Consumer 后才可考虑替代 |
| [azure_blob_readback.py](../../../../local-data-platform/spark/apps/hl7/azure_blob_readback.py) | Approved exact-key Azure GET-only manifest/raw readback into private local input | **Source-only / fake-GET CI 28/28 Python tests PASS at Run #42449129041; actual original 42 remote GET + local physical Candidate in Self-Runner Run #42488836550 PASS**. This is one-shot source/Candidate acceptance, not deployed Silver/OMOP. |
| [requirements-azure-readback.txt](../../../../local-data-platform/spark/apps/hl7/requirements-azure-readback.txt) | Optional runtime-only Azure SDK pins reuse the existing source/Publisher requirements | No cloud SDK dependency in hosted CI |
| [write_staging_delta.py](../../../../local-data-platform/spark/apps/hl7/write_staging_delta.py) | Spark 3.5 本地 Delta Staging，create / exact replay skip / conflict HOLD | **保留 / 业务依赖**：dbt 需要其结构化 Delta 输入，后续独立替换时才可考虑退役 |
| [silver_handoff.py](../../../../local-data-platform/spark/apps/hl7/silver_handoff.py) | HL7 原始 Request/Source → Shared namespaced/hash Batch Identity 的受限纯内存交接；复用 Shared pinned Canonical v1、PK/FK、DQ/Quarantine；只有 Candidate DQ PASS/HOLD，不负责 Silver Approval / Writer | **P2.3 source-only**；合并需 Hosted 单测/物理 Candidate 验证，既有 Source/SQL 路径不变 |
| [requirements-local.txt](../../../../local-data-platform/spark/apps/hl7/requirements-local.txt) | 保留 HL7 Parser / Spark / Delta 的单一 pinned 依赖源 | **维护**：新工程 [requirements-local.txt](../../../../azure-fabric/dbt/hl7-canonical/requirements-local.txt) 引用本锁定依赖，旧 dbt adapter pin 已从此移除 |
| [Historical dbt PR #809](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/809) | 已退役的旧 SQL/Project/Profiles 与首次本地 18/27 验收来源 | **历史证据**：不得从旧 Git SHA 自动恢复为生产入口；当前树不再保留旧 dbt 文件 |
| [HL7 CI](../../../../.github/workflows/hl7-local-delta-dbt-offline.yml) | GitHub-hosted synthetic HL7 → local Delta/dbt → Replay/Contract readback | **已改接新 dbt 工程**：保留原入口名称、Parser/Writer 和旧 18/27 物理回归断言；`cwd`/profiles 指向 `azure-fabric/dbt/hl7-canonical/`，当前合成 CI 不执行旧 SQL |
| [Synthetic OIE V2 fixture generator](../../../../.github/quality/fixtures/hl7/generate_oie_v2_sample.py) | 用真实 OIE JS Mapper 生成新合成 HL7/Manifest | **回归基线 / 保留**：可供旧/新候选对照，不因 SQL 工程完成就自动删除 |
| [GET-only readback test](../../../../.github/quality/tests/data-platform/hl7/test_azure_blob_readback.py) | Synthetic exact-key fake Azure snapshot/manifest, replay, ETag/version/hash and unsafe-key negative tests | No Azure or real patient access |
| [HL7 shared DQ unit](../../../../.github/quality/tests/data-platform/hl7/test_silver_handoff.py) · [physical readback](../../../../.github/quality/tests/data-platform/hl7/check_silver_handoff.py) | 使用合成 HL7 Canonical Candidate 进行合同、源批次/版本、PK/FK、时间、隔离和负向测试，以及 dbt 物理 Delta 的再次读回；**不执行真实 Silver 写入** | P2.3.1/2.3.2 验收入口 |
| [Offline negative tests](../../../../.github/quality/tests/data-platform/hl7/test_hl7_intake.py) | Manifest/Identity/Raw SHA/A01+A03/路径负向 | **回归基线 / 保留**：针对 Parser/Intake 的测试，业务组件保留时测试也应保留 |
| [Candidate independent readback](../../../../.github/quality/tests/data-platform/hl7/check_local_candidate.py) | 物理 Delta/_delta_log、Patient 18/Encounter 27 字段 | **保留并复用**：新 dbt 工程输出兼容的 `hl7_candidate` schema，旧 readback 可直接验证新工程，不需删除测试 |

**合同归属：** [Patient v1](../../../../local-data-platform/spark/contracts/canonical/patient-v1.json)、[Encounter v1](../../../../local-data-platform/spark/contracts/canonical/encounter-v1.json)。新工程必须复用现有权威合同，不因目录变化复制第二套 Canonical/OMOP/Publisher。

## 旧 dbt 文件退役的验收门槛（已在独立 P3 3.4 PR 执行）

1. 新的 `azure-fabric/dbt/hl7-canonical/` 已按标准骨架建立，解决了原生 `tests/` 与受保护 Layout Gate 的冲突，拥有唯一 Fabric dbt CODE Map；旧 SQL 仅作冻结参考，**不再同步新增功能**。
2. 新 dbt SQL/源配置完成 `compile/run/test`、Patient/Encounter 正负向语义、物理 local Delta 独立读回、Replay/幂等与 Canonical Contract 验收；若真实 Raw/Fabric 银层的验收尚未进行，要如实记录，不虚称 E2E。
3. 已逐项审查 `.github/workflows/`、Self-Runner 调用方、`DBT_PROFILES_DIR`、cwd、`dbt_project.yml` 位置、requirements、源码及 Markdown/CODE 链接，所有**当前活跃消费者**已切到新目录并有对应测试证据。
4. **独立受控清理 PR**删除旧 `dbt_project.yml`、旧 `models/*.sql/.yml`、旧 `profiles/local/profiles.yml` 及确已无引用的文件；同时更新 CODE Maps/Workflow/OpenSpec，核对新主线 CI。不能删除整个 `spark/apps/hl7/`、Python Parser/Intake/Writer、其负向测试或冻结历史证据。
5. 若切换失败，旧实现暂留为回退参考且不承担新增开发；记录真实阻断，禁止宣布“旧实现已退役”。是否终止或切换现有运行入口必须按受控 PR 和实际执行权限进行。

**切换审计：** Healthcare 所有 70 个 `.github/workflows/` 已逐文件扫描旧工程名/路径、`DBT_PROFILES_DIR` 和 `dbt run/test`：仅正式本地 HL7 回归 Workflow 与新 P3 验收 Workflow 执行 dbt，两条均指向同一个新 Project；原 Self-Runner `hl7-dbt-core-local-poc.yml` 固定 Healthcare 历史 `ecc99b18...` 且只在独立 `experiments/` 执行，不是 Healthcare 现行 Consumer。受控切换验收以新 PR/CI 为准；未在共享 Runner/Fabric 部署消费者。

**已验证边界：** 现存本地/合成数据 CI [Run #42419252459](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42419252459) 证明过当前 Parser→Delta→dbt Candidate，并**未**真实消费 Azure 已发布的 42 条 HL7、也不等于 Fabric Approved Silver/Gold。上述未来清理计划由 [Fabric dbt OpenSpec](../../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md) 跟踪；历史来源实施的业务 P2/P3 仍由 [HL7 Consumer OpenSpec](../../../../openspec/changes/implement-hl7-local-delta-dbt-canonical/tasks.md) 独立跟踪。

## Azure Raw readback source gate

The new [Azure GET-only operating contract](AZURE-GET-READBACK.md) owns the mandatory independent manifest SHA/source SHA/request and count pins, least-privilege identity, no-LIST policy, private local staging and runtime approval boundary. This source adapter reuses existing Manifest/Parser checks; **actual published 42 HL7 object GET, remote Fabric Silver and OMOP remain OPEN**.

**Actual real Azure Pilot (2026-11-08):** [Self-Runner Run #42488836550](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42488836550) passed exact 42 real Raw/Manifest GET, original Publisher OAuth, local Delta/dbt Candidate and independent Patient 18/Encounter 27 physical readback. No production Silver Writer, durable Processing layer, OIE POST, Azure mutations or OMOP Gold. Source ownership and dbt project paths unchanged; P2.3 in HL7 OpenSpec remains OPEN.
