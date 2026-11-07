# HL7 local Delta/dbt Canonical Candidate

## ADDED Requirements

### Requirement: Immutable verified OIE V2 HL7 Intake
系统 SHALL 仅在输入 Manifest SHA、对象清单、医院/Feed/Request 身份、完整 Raw HL7 bytes SHA/size、MSH-10 和 A01/A03 实际临床字段一致时创建结构化 Local Delta Staging；无真实源事实 MUST HOLD。

#### Scenario: Valid source
- **GIVEN** 冻结来源 Manifest 和已审核 OIE V2 A01/A03 实际格式消息
- **WHEN** Python hl7apy Adapter 执行本地审计和投影
- **THEN** SHALL 保留全部 Source provenance、PID/PV1/EVN 入院与出院时间、Raw 文件指针与 SHA

#### Scenario: Incomplete or corrupt source
- **GIVEN** 任意对象篡改、Hospital Authority 不符、A03 未配对或丢失 Manifest
- **WHEN** 进行 Intake
- **THEN** MUST 在任何 Staging Delta 写入前失败，不造 Clinical Concept/缺少的时间

### Requirement: Local Delta and dbt Candidate only
系统 SHALL 先将可信结构化行写入**本地**持久 Delta，随后本地 dbt-fabricspark Spark SQL SHALL 读取该 Delta Source 生成 Canonical v1 Candidate；不得把 dbt PASS 当作正式 Silver/Gold 提交。

#### Scenario: Source to Candidate
- **GIVEN** 已核验 HL7 Raw 和审核的 Patient/Encounter Source Profile
- **WHEN** local Spark Delta 和 dbt Core session 完成转换
- **THEN** SHALL 产生符合权威 Canonical Patient 18/Encounter 27 字段的 Delta Candidate，且不执行 Fabric Capacity 计算

#### Scenario: Replay and conflict
- **GIVEN** 同一 Staging 已存在
- **WHEN** 同批重试
- **THEN** 完全相同内容 SHALL SKIP，不同内容 MUST HOLD；不能覆盖旧 Delta

### Requirement: One downstream Silver owner
HL7 Candidate SHALL 通过已有统一 Contract/DQ/Approval/Single Writer 门禁才可进入正式 Canonical Silver；MUST NOT 新建第二套 OMOP Identity/Concept Mapper 或绕过 Warehouse Writer。

#### Scenario: Candidate is not an approved Silver writer
- **GIVEN** local Delta staging 与 dbt Candidate SQL 完成并返回 PASS
- **WHEN** 本地 job 返回结果
- **THEN** SHALL 保持 `CANDIDATE_ONLY`，MUST NOT 启动共享 Silver/OMOP Writer 或发布正式 Gold
