# Fabric Capacity Runtime Lifecycle

## ADDED Requirements

### Requirement: Terraform exclusively owns Fabric Workspace

The system MUST continue to create/configure Fabric Workspace, including its `capacity_id` association, only through the existing Terraform Workspace Root. The Capacity REST controller MUST NOT create, update, delete, assign or transfer any Workspace.

#### Scenario: Trial capacity inspected

- **WHEN** workflow runs Trial Capacity inspection
- **THEN** it calls GET on the Capacity endpoint only, without Workspace REST calls or State modifications.

### Requirement: Trial Capacity REST controller is read-only

The system SHALL offer a read-only GET for a configured existing Trial Capacity GUID. It MUST refuse suspend/resume attempts before authentication or API calls.

#### Scenario: Trial suspend requested

- **WHEN** operator requests trial suspend or resume
- **THEN** controller aborts with a clear validation error and sends no POST.

### Requirement: Paid Capacity runtime actions require gated Azure ARM identity

The system SHALL only suspend/resume an existing paid Fabric F SKU Capacity when the full Azure ARM resource ID belongs to the configured Subscription, an explicit enabled flag and matching user confirmation are present, and Azure authorization succeeds. A REST operation SHALL NOT create, purchase, delete or scale capacity.

#### Scenario: Paid resume without confirmation

- **WHEN** user selects paid resume without separate confirmation and feature enablement
- **THEN** no ARM token is requested and no write operation is attempted.

#### Scenario: Paid pause accepted asynchronously

- **WHEN** Azure accepts suspend asynchronously
- **THEN** controller verifies final resource state via GET; it MUST NOT report success merely from a 202 response.

### Requirement: CI and execution isolate Capacity lifecycle from shared Terraform

The source SHALL remain alongside the relevant Fabric Workspace as `capacity-api/`, not an extra Terraform Root; Self-Runner SHALL expose separate manual Workflow with default `trial/inspect`. Existing Workspace/OneLake Terraform backend keys and old State MUST remain unchanged.

#### Scenario: CI runs without paid resources

- **WHEN** unit and contract tests run
- **THEN** all HTTP/auth calls are mocked, no Capacity or Workspace is mutated, and the Workflow has no automatic scheduled or push lifecycle trigger.
