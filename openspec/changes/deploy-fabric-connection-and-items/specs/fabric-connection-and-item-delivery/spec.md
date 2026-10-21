# Fabric Connection and Item Delivery

## ADDED Requirements

### Requirement: Separate ownership of infrastructure, connections, and Fabric business Items

The system SHALL keep Workspace and Lakehouse exclusively in their existing independent Terraform Roots. Account-level Azure Blob Connection SHALL have a separate `shared-infra/connection` Terraform Root and State. Notebook and Data Pipeline Items MUST be created, updated, and published only by `fabric-cicd`, not by a Terraform Root.

#### Scenario: Only the connection Root is selected

- **WHEN** an operator validates or plans `shared-infra/connection`
- **THEN** no Workspace, Lakehouse, Capacity, Notebook or Data Pipeline Terraform resource is managed by that Root.

### Requirement: Connection deployment defaults to no resource creation

The Connection Root MUST default to a disabled/null configuration and SHALL reject inappropriate data-source identity values before creating a connection. Credentials MUST NOT be committed or echoed.

#### Scenario: New account without approved Reader identity

- **GIVEN** no approved Blob Reader identity and no reviewed Connection config
- **WHEN** the Connection Root is validated
- **THEN** the configuration remains non-provisioning, and no implicit Connection or paid Capacity can be created.

### Requirement: Fabric Item publication uses real outputs and stable identity

The `fabric-cicd` publisher MUST target the explicitly selected existing Fabric Workspace, validate actual Workspace/Lakehouse Terraform Outputs, and restrict Item types and identities to reviewed Git-native `.Notebook` and `.DataPipeline` definitions. It MUST NOT create or modify a Workspace or perform orphan deletion.

#### Scenario: Unsupported or unexpected Item is present

- **WHEN** publishing source includes an unapproved Item type, identity, or other Workspace target
- **THEN** the publisher rejects the request without creating or deleting Fabric Items.

### Requirement: Runtime acceptance is separate from deployment

A successfully published Notebook or Pipeline MUST NOT be reported as business E2E success without a real run and independent readback. Business runs SHALL reject incomplete/unsigned READY Manifests and SHALL preserve idempotency under repeat execution.

#### Scenario: A Pipeline is published but has not run

- **WHEN** an Item publication reports success but no Notebook run/readback evidence exists
- **THEN** the stage is recorded as deployed only, not as a passing OMOP data replication E2E.
