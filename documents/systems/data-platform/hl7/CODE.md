# HL7 — official consumer Source CODE map

> **当前唯一可执行 Source Owner：** `local-data-platform/spark/apps/hl7/`。这里的部分 dbt 代码是经过真实**本地合成数据**运行验证的功能基线，**不是只可随便删除的 POC**。未来 Fabric dbt 独立工程目标：[`azure-fabric/dbt/hl7-canonical/` 规则](../../azure-fabric/dbt/README.md)；目前尚未创建。旧 Self-Runner `experiments/hl7-dbt-canonical/` 仅历史隔离 POC。OIE Producer、共享 Silver Writer / OMOP 均不归本组件管理。

## 代码去留标记（Agent 必须先读）

- **保留 / 业务依赖**：目前仍负责 HL7 协议解析、Manifest 校验、物理 Delta Staging；dbt 新工程完成 **不构成删除这些 Python 文件的条件**。如需以后改用 Shared Engine / Fabric Adapter，另做已验证的 Owner/消费者切换。
- **参考 → 切换后待退役**：旧 dbt SQL/项目配置供新的 `hl7-canonical` 开发时对照语义、参数、输出合同和回归测试。**允许新工程作为候选与旧文件临时并存，旧版本冻结不再增加新业务模型；只允许一个已指定的正式执行入口。** 新项目验证并完成消费者切换后，清理旧 dbt 文件，不维护两份正式实现。
- **拆分复核 / 暂保留**：混合 Python/dbt 依赖清单及旧 CI/质量测试，等实际执行方、版本和调用路径确认后拆分或更新；不能按目录一键删。
- **历史参考 / 不回滚**：旧 Self-Runner POC 和已合并的历史 PR/Run 作为基线证据，不等于最新工程的通过证明。

## 现存文件、未来用途与退役门槛

| 真实源码 / 入口 | 当前职责 | 对新 dbt 工程的用途与计划 |
| --- | --- | --- |
| [parse_oie_v2.py](../../../../local-data-platform/spark/apps/hl7/parse_oie_v2.py) | 经审核 OIE V2 的 `hl7apy` 协议解析和临床字段投影 | **保留 / 业务依赖**：下游仍需结构化 HL7；不是 dbt SQL，不能因 dbt 完成删除 |
| [landing_intake.py](../../../../local-data-platform/spark/apps/hl7/landing_intake.py) | Manifest、Raw SHA、Hospital/Batch/对象身份校验，限本地读取 | **保留 / 业务依赖**：数据真实性 Gate；另行评审共享 Adapter 或新 Consumer 后才可考虑替代 |
| [write_staging_delta.py](../../../../local-data-platform/spark/apps/hl7/write_staging_delta.py) | Spark 3.5 本地 Delta Staging，create / exact replay skip / conflict HOLD | **保留 / 业务依赖**：dbt 需要其结构化 Delta 输入，后续独立替换时才可考虑退役 |
| [dbt_project.yml](../../../../local-data-platform/spark/apps/hl7/dbt_project.yml) | 现有可运行 dbt 项目，当前名 `hl7_canonical_candidate` | **配置参考 → 切换后待退役**：新项目使用 `hl7_canonical` 和规范目录；新工程验收+CI/消费者切换后删旧 |
| [models/sources.yml](../../../../local-data-platform/spark/apps/hl7/models/sources.yml) | `hl7_staging.hl7_events` Delta source + 现有模型数据测试 | **参考 → 切换后待退役**：新项目重建独立 source/schema tests，保留原断言 |
| [models/canonical_patient.sql](../../../../local-data-platform/spark/apps/hl7/models/canonical_patient.sql) | HL7 Patient v1 Candidate，不是 Approved Silver | **逻辑参考 → 切换后待退役**：对照最新合同和真实字段，按 dbt staging/intermediate/canonical 分层实现 |
| [models/canonical_encounter.sql](../../../../local-data-platform/spark/apps/hl7/models/canonical_encounter.sql) | 同批 A01+A03 关联生成 Encounter v1 Candidate | **逻辑参考 → 切换后待退役**：复用配对/时序/去重语义并测试边界，不直接当最终业务模型 |
| [profiles/local/profiles.yml](../../../../local-data-platform/spark/apps/hl7/profiles/local/profiles.yml) | dbt-fabricspark `method=session` 的 local-only 配置 | **配置参考 → 切换后待退役**：新工程独立配置、无密钥；新项目生效后删旧 |
| [requirements-local.txt](../../../../local-data-platform/spark/apps/hl7/requirements-local.txt) | 混合锁定 HL7 Parser / Spark / Delta / dbt 依赖 | **拆分复核 / 暂保留**：先清点 CI 与真实执行依赖；分别为 Parser/Writer 与 dbt 提供版本来源后才能拆或删 |
| [HL7 CI](../../../../.github/workflows/hl7-local-delta-dbt-offline.yml) | GitHub-hosted synthetic HL7 → local Delta/dbt → Replay/Contract readback | **回归基线 / 待改接**：新模型开发时以旧 CI 为验收参考；实际切换时更新 `paths`、工作目录、profiles/requirements 和测试调用，不得提前删 |
| [Synthetic OIE V2 fixture generator](../../../../.github/quality/fixtures/hl7/generate_oie_v2_sample.py) | 用真实 OIE JS Mapper 生成新合成 HL7/Manifest | **回归基线 / 保留**：可供旧/新候选对照，不因 SQL 工程完成就自动删除 |
| [Offline negative tests](../../../../.github/quality/tests/data-platform/hl7/test_hl7_intake.py) | Manifest/Identity/Raw SHA/A01+A03/路径负向 | **回归基线 / 保留**：针对 Parser/Intake 的测试，业务组件保留时测试也应保留 |
| [Candidate independent readback](../../../../.github/quality/tests/data-platform/hl7/check_local_candidate.py) | 物理 Delta/_delta_log、Patient 18/Encounter 27 字段 | **回归基线 / 待改接**：新项目独立验收复用语义及合同检查；消费者转移后更新而非机械删除 |

**合同归属：** [Patient v1](../../../../local-data-platform/spark/contracts/canonical/patient-v1.json)、[Encounter v1](../../../../local-data-platform/spark/contracts/canonical/encounter-v1.json)。新工程必须复用现有权威合同，不因目录变化复制第二套 Canonical/OMOP/Publisher。

## 允许清理旧 dbt 文件的前置检查（不是日期触发）

1. 新的 `azure-fabric/dbt/hl7-canonical/` 已按标准骨架建立，解决了原生 `tests/` 与受保护 Layout Gate 的冲突，拥有唯一 Fabric dbt CODE Map；旧 SQL 仅作冻结参考，**不再同步新增功能**。
2. 新 dbt SQL/源配置完成 `compile/run/test`、Patient/Encounter 正负向语义、物理 local Delta 独立读回、Replay/幂等与 Canonical Contract 验收；若真实 Raw/Fabric 银层的验收尚未进行，要如实记录，不虚称 E2E。
3. 已逐项审查 `.github/workflows/`、Self-Runner 调用方、`DBT_PROFILES_DIR`、cwd、`dbt_project.yml` 位置、requirements、源码及 Markdown/CODE 链接，所有**当前活跃消费者**已切到新目录并有对应测试证据。
4. 最终**一个受控切换/清理 PR**删除旧 `dbt_project.yml`、旧 `models/*.sql/.yml`、旧 `profiles/local/profiles.yml` 及确已无引用的文件；同时更新 CODE Maps/Workflow/OpenSpec，核对新主线 CI。不能删除整个 `spark/apps/hl7/`、Python Parser/Intake/Writer、其负向测试或冻结历史证据。
5. 若切换失败，旧实现暂留为回退参考且不承担新增开发；记录真实阻断，禁止宣布“旧实现已退役”。是否终止或切换现有运行入口必须按受控 PR 和实际执行权限进行。

**已验证边界：** 现存本地/合成数据 CI [Run #42419252459](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42419252459) 证明过当前 Parser→Delta→dbt Candidate，并**未**真实消费 Azure 已发布的 42 条 HL7、也不等于 Fabric Approved Silver/Gold。上述未来清理计划由 [Fabric dbt OpenSpec](../../../../openspec/changes/govern-fabric-dbt-project-layout/tasks.md) 跟踪；历史来源实施的业务 P2/P3 仍由 [HL7 Consumer OpenSpec](../../../../openspec/changes/implement-hl7-local-delta-dbt-canonical/tasks.md) 独立跟踪。
