# Synthea OMOP Demographic Mapping

## ADDED Requirements

### Requirement: Supported Synthea race values map to validated OMOP race concepts

The NEW_ONLY Synthea Person-to-OMOP mapping SHALL support valid source `race_code=native` by mapping it to the semantically correct, verified OMOP race Concept ID from the deployed vocabulary. It MUST preserve normalized `race_source_value` and MUST NOT silently coerce a recognized race to `0` or an unrelated concept.

#### Scenario: Native race mapping

- **GIVEN** 一个源代码为 `race_code=native`、其他关键字段有效的 Synthea Canonical Person
- **WHEN** 使用经核对的标准 OMOP 词表执行 Person Mapping
- **THEN** 正确输出标准 `race_concept_id` 和 `race_source_value=native`，该行不因 `unknown_demographic` 被拒绝

#### Scenario: Existing supported races remain stable

- **GIVEN** 一个以前已被正确映射的合法 Race 源值
- **WHEN** 重新执行修复后的同一 Mapper
- **THEN** 仍保持相同有效 Race Concept、source value 和确定性业务指纹语义

### Requirement: Unknown demographics fail before atomic commit

The mapping pipeline SHALL reject unsupported demographic source values before executing any NEW_ONLY Atomic Writer COMMIT, and SHALL provide diagnostic context identifying the invalid field and source value without exposing sensitive identifiers or credentials.

#### Scenario: Unsupported race rejected

- **GIVEN** 一个确实不在验证后值域内的 `race_code`
- **WHEN** Writer 映射或只读前置校验运行
- **THEN** 明确指出无效字段与值并拒绝映射，不允许继续提交此 Batch

### Requirement: Deterministic replay and writer safety remain unchanged

The race mapping change MUST preserve immutable Batch identity, Person/Visit source relationships, stable fingerprints, the existing atomic Writer fencing contract and idempotent same-Batch skip semantics.

#### Scenario: Historical failed Batch read-only mapping regression

- **GIVEN** 已保存的因 `native` 映射失败的真实 Parquet Batch
- **WHEN** 以只读模式执行修复后的 Person/Visit 映射
- **THEN** 保持源身份与行数一致、正确映射 `native`，不修改 PG Claim、Ledger 或业务表

#### Scenario: New Batch complete acceptance

- **GIVEN** 修复后源码和受影响镜像已正式合并发布且新的 Batch 尚未提交
- **WHEN** 完整执行新的 Synthea → S3 → Airflow → Spark → Atomic Writer，并重跑同 Batch
- **THEN** 首次 COMMIT 可由独立 PG/S3 Readback 核验，第二次安全 SKIP 且 PG 业务数据零变化
