## ADDED Requirements

### Requirement: 真实来源和正式 Vocabulary 必须共同证明临床 Concept Profile

系统 SHALL 只依据已批准的真实 Silver 和已验证的 Vocabulary Release，检查原始代码覆盖、Concept Domain、标准性和有效日期。预检结果 MUST NOT 自动升级为临床审批或 Gold 授权。

#### Scenario: 通过纯离线校验但没有云端审查

- **WHEN** 测试 fixture 的来源代码和全部 Concept 校验成功，但缺少真实 Source/Vocabulary 双重读回
- **THEN** 只允许 `P1_CONCEPT_PREFLIGHT_ONLY_NOT_CLINICALLY_APPROVED`，正式 Candidate 保持 HOLD

#### Scenario: 未映射源值或非法 Concept

- **WHEN** 任何已观察代码不存在于版本化 Profile，或者 Concept 非标准、Domain 不匹配、失效或已过有效日期
- **THEN** 必须拒绝整个输入，不得静默截断、猜测 Concept ID 或丢弃不合法 Encounter

### Requirement: 持久化身份和 Gold 提交必须可重放且原子化

系统 SHALL 使用全 Warehouse 全局 INT 分配器和医院隔离的稳定源键；只有单写入者事务内复核后才可持久化 Identity Map、Person、Visit 和 Ledger。对未被强制的 PK/FK MUST 显式核验。

#### Scenario: 相同请求成功重放

- **WHEN** 已 COMMITTED 批次收到完全相同 Manifest/Profile/身份并经独立 SQL 读回验证
- **THEN** 只能 SKIP，不得再次分配 Person/Visit ID

#### Scenario: 写入冲突或未知 COMMIT ACK

- **WHEN** 快照发生漂移、SQL 回滚或提交 ACK 不确定
- **THEN** 必须 HOLD 并查询真实 Ledger/Gold 状态，不得盲目重试或声称 COMMITTED

### Requirement: Candidate、Gold 和 Pipeline 证据不得互相替代

系统 SHALL 保留真实 Job ID、source SHA、mapping hash、物理 Item GUID 和独立数据读回证据；Native Pipeline 必须默认 HALT、无 schedule、retry=0。

#### Scenario: Source Readonly 成功但没有 Candidate/Gold

- **WHEN** G5 真实 Silver Source Readonly 通过，而 Candidate/Gold 未获明确授权或未写入
- **THEN** 只报告 Source Readonly PASS，Candidate 和 Gold 状态仍为 NOT_DONE
