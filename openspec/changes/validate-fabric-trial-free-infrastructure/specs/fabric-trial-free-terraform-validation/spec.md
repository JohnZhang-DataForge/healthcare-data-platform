# Fabric Trial Free Infrastructure Validation

## ADDED Requirements

### Requirement: Reuse existing free Fabric Trial Capacity without provisioning billable capacity

The system MUST use only the explicitly configured existing Trial F4 Capacity GUID as the Terraform `fabric_workspace.capacity_id` value. It MUST NOT invoke `azurerm_fabric_capacity`, Capacity REST mutate endpoints, paid Capacity workflows, upgrade, or quota changes in the Trial testing workflow.

#### Scenario: Trial-only deployment

- **WHEN** a reviewed Trial-only execution request is submitted
- **THEN** the workflow validates the exact Trial Capacity GUID and only targets Workspace and OneLake Terraform Roots, without a paid Capacity Root.

### Requirement: Maintain Terraform-exclusive Workspace and separate named States

The system SHALL create `johnzhang-test` Workspace only with Terraform's `fabric_workspace` resource, and then create `lh_johnzhang_test` Lakehouse with the existing OneLake Terraform Root, using matching named Terraform CLI Workspaces and distinct Backend keys.

#### Scenario: Workspace fails due to unsupported Trial service principal

- **WHEN** the Terraform Provider or Fabric API rejects Trial assignment or ownership
- **THEN** no Workspace REST API fallback is invoked and the OneLake Apply is not attempted.

### Requirement: Produce verifiable live acceptance without unsafe State modifications

The workflow SHALL pin Healthcare source SHA, reject Plan changes other than create/read/no-op, verify output IDs and run a second no-drift Plan for each successfully applied Root.

#### Scenario: Fresh Workspace and Lakehouse Apply

- **WHEN** both Roots successfully Apply
- **THEN** the workflow reports actual Workspace and Lakehouse GUIDs and verifies the idempotency of both Roots without changing existing production/paid resources.
