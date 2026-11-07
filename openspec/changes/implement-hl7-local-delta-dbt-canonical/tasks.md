# Tasks — Implement OIE V2 HL7 local Delta staging and dbt Candidate

## P1 — 正式代码与本地物理 Delta/dbt（不用重做旧 POC）
- [x] 1.1 核查双仓 Main/PR/Workflow、OIE P2/P3 真实证据、Self-Runner PR #584 Parser/dbt POC、Canonical v1、源码 Owner。
- [x] 1.2 迁入唯一 Healthcare HL7 Reader/Manifest Parser/本地物理 Delta Writer，采用已测试 Spark 3.5.5/Delta 3.3.2 和 fail-closed Source Profile。
- [x] 1.3 正式 dbt-fabricspark local session 从 Delta `source()` 读取，生成 Source-specific Patient/Encounter Candidate；不写正式 Silver/Gold。
- [x] 1.4 实施 OpenSpec/系统 README/CODE、真实 OIE V2 JS Mapper 新合成 fixture、集中负向测试和 Hosted-only CI。
- [ ] 1.5 CI 实际 local Delta/_delta_log、Replay、dbt compile/run/test、独立 18+27 字段 readback 通过后，登记最终 PR/Run/SHA 并合并 Main。

## P2 — 真实来源和共享业务链路（单独资源授权）
- [ ] 2.1 对 Azure 已发布 42 条 Raw HL7 做 GET-only 最小权限计划与 Batch/资源冲突核查；不重跑历史 P2/P3、不产生 OIE POST。
- [ ] 2.2 使用原 42 条真实 HL7 文件和权威 Manifest 进入本 Consumer 的真实 Source/Delta Candidate 验收。
- [ ] 2.3 接入现有统一 Silver DQ/quarantine/Approval/Single Writer，后续与 FHIR 在已批准 Canonical 汇合；真实 Silver/OMOP 写入需要明确审批与独占窗口。
