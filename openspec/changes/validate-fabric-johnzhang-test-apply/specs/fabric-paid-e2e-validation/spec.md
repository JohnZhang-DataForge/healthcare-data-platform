# Real Isolated Fabric Terraform Apply Validation

## ADDED Requirements

### Requirement: Independent test Workspace and OneLake Roots

A `johnzhang-test` Fabric Workspace SHALL use standalone Terraform `workspace` and `onelake` roots and a matching non-default CLI Workspace, without touching `healthcare-omop` or historical State.

#### Scenario: test Lakehouse reads Workspace Output
- **WHEN** the `johnzhang-test/onelake` Root Plans
- **THEN** it SHALL read `fabric_workspace_id` from the matching Workspace remote State and MUST fail without that output.

### Requirement: Paid Capacity is separately managed by Terraform and never by Workspace REST

The test paid Azure Fabric F2 Capacity SHALL be provisioned only through the independent `shared-infra/capacity` Terraform Root, returning the real Fabric Capacity GUID for the Workspace Terraform Root to reference. No Workspace REST API SHALL create/modify any Workspace.

#### Scenario: Capacity and Workspace ownership
- **WHEN** the Terraform Capacity Root is applied
- **THEN** it owns only the new Azure Fabric Capacity, and Workspace Root alone owns the Fabric Workspace and its `capacity_id` association.

### Requirement: No unbounded paid compute

A bounded paid test operation SHALL verify it can suspend the new paid F2 Capacity when testing finishes or fails. It MUST NOT treat successful CLI exit or REST POST as confirmed suspension; Azure ARM GET must show the final non-running state.

#### Scenario: unknown paid status
- **WHEN** the Apply outcome or suspension result cannot be established
- **THEN** mark run blocked, inspect Azure resource and disclose potential charges; do not automatically retry or destroy.
