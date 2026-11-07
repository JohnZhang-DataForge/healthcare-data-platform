# HL7 — official consumer Source CODE map

> **唯一组件 Owner：** `local-data-platform/spark/apps/hl7/`。旧 Self-Runner `experiments/hl7-dbt-canonical/` 为已通过的**历史隔离 POC**，不是未来要维护的第二个正式业务模块。本 CODE 不管理生产者 OIE Channel（见 clinical-producers），不管理统一 Silver Writer / OMOP。

| Source path | 唯一职责 |
|---|---|
| [parse_oie_v2.py](../../../../local-data-platform/spark/apps/hl7/parse_oie_v2.py) | 经审核的有限 OIE V2 hl7apy 语法解析与临床字段投影；原始消息 SHA 仍保留 |
| [landing_intake.py](../../../../local-data-platform/spark/apps/hl7/landing_intake.py) | 不可变 Manifest/本地 Blob 相对路径/完整 Raw SHA/医院与 Batch 身份验证；无网络 |
| [write_staging_delta.py](../../../../local-data-platform/spark/apps/hl7/write_staging_delta.py) | 本地 Spark 3.5 Delta Staging，仅 create/exact replay skip，冲突 HOLD；无 Fabric |
| [dbt_project.yml](../../../../local-data-platform/spark/apps/hl7/dbt_project.yml) | local dbt Core 的唯一正式 HL7 Candidate project |
| [models/sources.yml](../../../../local-data-platform/spark/apps/hl7/models/sources.yml) | 显式源 `hl7_staging.hl7_events`，防止误读旧 CSV Seed |
| [models/canonical_patient.sql](../../../../local-data-platform/spark/apps/hl7/models/canonical_patient.sql) | HL7 Source-specific Patient v1 Candidate（非 Silver） |
| [models/canonical_encounter.sql](../../../../local-data-platform/spark/apps/hl7/models/canonical_encounter.sql) | A01+A03 成对的 Encounter v1 Candidate（非 Silver） |
| [profiles/local/profiles.yml](../../../../local-data-platform/spark/apps/hl7/profiles/local/profiles.yml) | **local-only** dbt-fabricspark `method=session`；Warehouse URI 来自显式环境变量 |
| [requirements-local.txt](../../../../local-data-platform/spark/apps/hl7/requirements-local.txt) | 固定已验收的 Parser/dbt/Spark/Delta 兼容组合 |
| [HL7 CI](../../../../.github/workflows/hl7-local-delta-dbt-offline.yml) | Hosted-only 新合成源→物理 Delta→dbt Candidate + replay 合同 |
| [Synthetic OIE V2 fixture generator](../../../../.github/quality/fixtures/hl7/generate_oie_v2_sample.py) | CI 从正式 OIE v2 JS 生成临时合成来源 HL7/Manifest |
| [Offline negative tests](../../../../.github/quality/tests/data-platform/hl7/test_hl7_intake.py) | Manifest/Identity/Raw SHA/事件配对、路径负向 |
| [Candidate independent readback](../../../../.github/quality/tests/data-platform/hl7/check_local_candidate.py) | 物理 Delta/_delta_log 和权威 Canonical Patient 18 / Encounter 27 字段 |

**合同归属：** [Patient v1](../../../../local-data-platform/spark/contracts/canonical/patient-v1.json)、[Encounter v1](../../../../local-data-platform/spark/contracts/canonical/encounter-v1.json)。新实体独立增加 Source-specific dbt 模型，但 Canonical/OMOP/Publisher 的共用合同和事实审查不允许复制。以上源码均为本地/合成开发边界，非 Azure 实机或 Approved Silver 证明。
