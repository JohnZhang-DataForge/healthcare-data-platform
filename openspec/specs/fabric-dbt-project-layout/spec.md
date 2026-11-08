# Fabric dbt Project Directory Governance

## Purpose

本规范定义 Healthcare Fabric-oriented dbt Core 工程的长期目标父目录、标准空目录结构、可扩展命名及 AI/Agent 新建目录的强制审批。目录规则由 [PR #811](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/811) 合并，**精确 dbt SQL `tests/` 例外已由受保护 [PR #815](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/815) 实现并由真实正向 [#816](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/816)/负向 [#817](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/817) 验证**，四项 GitHub Required Checks 已恢复。**HL7 dbt 工程源码尚未从 Local DP 切换，也未因治理验收自动成为 Fabric Runtime PASS。**

## Requirements

### Requirement: Fabric dbt projects SHALL use a governed parent and a single owner
After an approved migration, Fabric-oriented dbt Core project source SHALL belong to `azure-fabric/dbt/<project>/`. The first planned project SHALL be `hl7-canonical` with `name: hl7_canonical`. Additional projects MUST be justified in a separate Active OpenSpec; Native Workspace items, Self-Runner experiments and `shared-data-engine/` MUST NOT become duplicate permanent dbt project owners.

#### Scenario: A future Agent adds FHIR with dbt
- **WHEN** an Agent proposes FHIR dbt SQL
- **THEN** it SHALL examine current PySpark and shared business code, obtain a separate project owner decision, and only then propose `fhir-canonical/`.

#### Scenario: Another hospital requires HL7 SQL
- **WHEN** a new hospital or clinical entity uses HL7 SQL
- **THEN** the Agent SHALL extend the existing approved HL7 project instead of automatically creating a per-hospital or per-table project.

### Requirement: Standard dbt projects SHALL preserve their full directory scaffold
Each new approved dbt project SHALL contain `dbt_project.yml`, `models/staging/`, `models/intermediate/`, `models/canonical/`, `macros/`, `tests/`, `seeds/`, `snapshots/`, `analyses/` and `profiles/`. Empty directories SHALL use `.gitkeep`; unnecessary packages and dummy SQL MUST NOT be added.

#### Scenario: Macros and snapshots are not yet implemented
- **WHEN** the new project does not need a macro or snapshot
- **THEN** its standard empty directories SHALL remain visible in Git via placeholders.

#### Scenario: dbt native SQL tests conflict with protected layout policy
- **WHEN** adding `azure-fabric/dbt/<project>/tests/`, even just `tests/.gitkeep`
- **THEN** only the approved `hl7-canonical` singular `*.sql` or root `.gitkeep` SHALL pass the now-verified trusted repository layout checker (PR #815, positive #816, negative #817); other source-area tests remain prohibited.

### Requirement: dbt Canonical candidates SHALL not duplicate shared business ownership
dbt SQL SHALL produce source-specific Contract-aligned Canonical Candidates and MUST NOT create a second authoritative Canonical approval, identity, OMOP concept mapper or Gold publisher without an explicit approved ownership transfer.

#### Scenario: An Agent proposes shared Canonical business logic in dbt
- **WHEN** a project such as `canonical-transform/` is proposed
- **THEN** the Agent SHALL first obtain a Shared Engine responsibilities decision and an Active OpenSpec Change, avoiding overlapping implementations.

### Requirement: Planned paths SHALL not be treated as implemented
The existing HL7 dbt implementation under `local-data-platform/spark/apps/hl7/` SHALL remain the authoritative running source until a separate tested physical migration updates CODE owners, consumers and verification evidence.

#### Scenario: An Agent reads the new Fabric dbt documentation
- **WHEN** `azure-fabric/dbt/hl7-canonical/` is described but the physical migration is still open
- **THEN** the Agent SHALL use the existing real CODE Map and MUST NOT report the Fabric path as already deployed or tested.

#### Scenario: An Agent develops the replacement dbt project
- **WHEN** a later PR introduces a new `azure-fabric/dbt/hl7-canonical/` project while legacy HL7 dbt code remains
- **THEN** it SHALL freeze old dbt SQL/project/profiles as a reference-only baseline, keep the new project unpromoted, and require a tested consumer cutover and separate old-dbt cleanup before claiming it is the only official source.

### Requirement: Legacy HL7 dbt source disposition SHALL be documented before replacement

The authoritative HL7 CODE Map SHALL classify legacy files for retention, reference or retirement. A new dbt candidate MAY coexist with frozen legacy files in Git, but only one official execution owner is allowed. Cleanup MUST preserve still-required Parser, Intake, Delta Writer and tests.

#### Scenario: An Agent creates the new standard dbt project while old files still exist
- **WHEN** the agent starts the approved new project after the repository layout gate is ready
- **THEN** the old SQL/project/profile SHALL remain frozen reference-only, the new project SHALL remain candidate until approved cutover, and the current CODE Map SHALL stay accurate about the actual execution path.

#### Scenario: A new dbt project passes its local tests
- **WHEN** the new candidate passes compile, run, dbt tests, physical Delta readback and Canonical Contract checks
- **THEN** the Agent MUST still inventory and migrate active Workflow, Self-Runner, profile, requirements, test and documentation consumers before deleting old dbt files; such a PASS alone SHALL NOT authorize blanket deletion.

#### Scenario: A clean-up PR removes the old HL7 project
- **WHEN** the new project has been promoted and all consumers and CODE owners are updated with evidence
- **THEN** only identified obsolete old dbt SQL, project configuration and profiles MAY be removed in a bounded PR; legacy Python Parser/Intake/Delta Writer, necessary regression tests, and historical acceptance evidence MUST remain unless separately replaced and accepted.

