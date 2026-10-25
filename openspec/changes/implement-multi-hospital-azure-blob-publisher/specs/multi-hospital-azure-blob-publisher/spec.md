# Multi-Hospital Immutable Azure Blob Landing Publisher

## ADDED Requirements

### Requirement: Publishing requires verified immutable source

共享 Publisher SHALL 接收独立 Generator P4.1 验证后的 `SOURCE_HANDOFF_VERIFIED`，并校验冻结的 request_id、hospital_id、feed_id、source Manifest SHA256、文件字节 SHA256；未通过不得发起 Azure Blob PUT。

#### Scenario: Source Manifest mismatch
- **GIVEN** 一个冻结但 Manifest 或 FHIR Payload 被篡改的请求
- **WHEN** Publisher 验证输入
- **THEN** 它 MUST 拒绝发布，任何成功状态/Manifest 均不能提交

### Requirement: Azure Blob data objects and commit Manifest are immutable

Publisher SHALL 使用稳定、按医院/Feed/Request/Format 隔离的 Blob key，使用条件创建阻止覆盖，读取目标实际字节重新计算 SHA256，并最后创建及读回成功 Manifest。HTTP PUT 成功或源端 SHA 正确本身都不足以声明发布成功。

#### Scenario: Matching retry
- **GIVEN** 已提交的同一 request_id、source Manifest SHA256 和 Blob 内容
- **WHEN** 相同的 Publisher 请求再次到达
- **THEN** Publisher SHALL 从 Azure 读回实际对象并确认相同，不覆盖或产生不同对象，返回可审计的幂等结果

#### Scenario: Content conflict
- **GIVEN** 目标 Blob key 已存在但字节 SHA256 与新请求不同
- **WHEN** Publisher 执行 immutable create
- **THEN** 它 MUST 拒绝覆盖并标记 HOLD，不得更新已提交的 Manifest

#### Scenario: Partial upload
- **GIVEN** 多对象上传过程中出现一个失败
- **WHEN** Publisher 尝试完成提交
- **THEN** 不得创建代表完整成功的 commit Manifest；后续仅允许基于独立读回的安全恢复

### Requirement: Atlanta and Johns Creek use external hospital delivery routes

Atlanta `DIRECT` FHIR SHALL 发布已验证 FHIR R4 原始字节。Johns Creek `OIE` HL7 SHALL 只发布经 OIE 4.7 Channel 真实转换、且独立 HL7 v2.5.1 ADT^A01 解析成功的合法住院事件。对不合格的 Encounter MUST 记录 SKIP，不得伪造 A01；两个医院的前缀和身份不可混用。

#### Scenario: Atlanta FHIR delivery
- **GIVEN** `atlanta-hospital-a` 已验证 FHIR Bundle 与医院 Profile
- **WHEN** Publisher 提交 Azure Landing
- **THEN** 对应 FHIR Blob 和最终 Manifest 必须可从目标 Azure Container 独立 GET/校验，未执行 OIE 变换

#### Scenario: Johns Creek outpatient
- **GIVEN** `johns-creek-hospital-b` 的 AMB Encounter
- **WHEN** OIE 路由准备发布
- **THEN** 不生成任何 ADT^A01 Blob，对跳过事件有可追踪的计数

### Requirement: No legacy OMOP or unapproved live mutations

共享 Publisher SHALL 保持与 `apps/synthea/new_only/`、Airflow、Spark、Writer、OMOP/PostgreSQL 和既有历史 PVC 的隔离。实际 Azure/K8s 操作 MUST 在明确授权、资源协调及读回 Gate 后执行。除已有目标 Landing 不得擅自创建 Azure 收费资源。

#### Scenario: Missing deployment authorization
- **GIVEN** 未获批准的 Azure Blob 权限或正在运行的并行 Shared Job
- **WHEN** 触发发布请求
- **THEN** 仅允许离线验证，所有共享环境和云端写入必须 HOLD
