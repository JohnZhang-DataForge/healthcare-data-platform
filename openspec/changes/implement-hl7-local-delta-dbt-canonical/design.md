# Design — Local HL7 Delta staging + dbt Candidate

## 已决定的方案（不再重复后端实验）
```text
Azure Blob immutable Raw HL7 + manifest (P3 actual PASS)
  → [单独获批的 GET-only 才能取得真实原始字节]
  → hl7apy Python HL7 Source parser / Manifest SHA + identity Gate
  → structured typed rows in LOCAL physical Delta: hl7_staging.hl7_events
  → dbt Core + dbt-fabricspark method=session (local Spark)
  → LOCAL Delta Candidate: hl7_candidate.canonical_patient, canonical_encounter
  → [待实现] shared Contract / DQ / Approval / single Silver Publisher
  → ONE Approved Canonical Silver Delta → ONE OMOP Identity/Mapping/Gold pipeline
```

HL7 **不**转换为 FHIR。Parser 输出结构化记录；历史 `dbt seed` CSV 是临时测试数据导入方式，本地 Spark 可以直接写 Delta 供 dbt 使用。上述计算可在 GitHub-hosted/self-runner 本地完成而不用 Fabric Spark CU；远端 Silver 发布则依然有正式共享 Writer/CU 和单写入者约束。

## 接口及数据边界
- Input: Caller 已合法取得的本地 Raw HL7 和原始 Manifest、独立来源 Manifest SHA、实际 Manifest SHA、Request/Feed/Hospital。
- Parser: `hl7apy==1.3.5`；目前只支持已审核 Johns Creek Hospital B `JOHNSCREEKB` 源 Profile，接受 OMB CDCREC 5 种 Race/2 种 Ethnicity、真实 DOB/Gender、MSH-9/10/12、PID/PV1/EVN 时间；绝不造缺失临床事实。
- Manifest 验证全部 Raw 字节 SHA、大小、Message Control ID、跨消息 Person/Visit 身份和 A01/A03 配对；所有对象预检成功**之后**才创建本地 Delta。
- Stage: Spark 3.5.5 / Delta 3.3.2 的 `hl7_staging.hl7_events`，每个字段保留 raw pointer/provenance，类型化 date/timestamp/bigint；同内容重跑 SKIP，不同内容 HOLD，不覆盖/append。
- Transform: dbt-fabricspark 1.13.2 `method=session`，两个 Source-specific SQL Model 输出 Patient 18 / Encounter 27 字段候选；dbt test 通过不等于 Silver APPROVED。
- Owner: 真实业务源 `local-data-platform/spark/apps/hl7/`，唯一地图 `documents/systems/data-platform/hl7/CODE.md`；Self-Runner POC 仅历史基线；避免复制后续 OMOP Mapper 和单 Writer。

## 测试、成本、回滚
GitHub-hosted workflow 使用冻结源源码 `adt_events_v2.js` 生成新的 synthetic FHIR→HL7，经过严格本地 Manifest/Parser→Delta/_delta_log→dbt run/test→独立 Spark 合同读回，并检验 A01/A03/篡改/重跑冲突。没有云凭据或共享服务访问，不消耗 Fabric Capacity；本地 Spark JVM 开销较 DuckDB 大但其真实物理 Delta 路径已有 POC 实证。CI 通过后记录精确 PR/Run/SHA；任何错误不绕过 Gate，需修复后再合并。清理临时数据仅限 Github-hosted 临时作业；原 Azure P3 不触碰。
