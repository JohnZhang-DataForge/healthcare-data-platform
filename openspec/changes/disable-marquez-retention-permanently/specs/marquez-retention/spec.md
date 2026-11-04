## ADDED Requirements

### Requirement: Marquez metadata SHALL be preserved indefinitely by default
The Healthcare Data Platform MUST deploy Marquez without automatic time-based deletion of Jobs, Runs, Datasets, Dataset Versions or OpenLineage Events. Retention MUST NOT be enabled without a separate explicit change.

#### Scenario: Helm render from the approved pinned chart
- **WHEN** the approved Marquez Helm chart is rendered with Healthcare's values
- **THEN** the rendered Marquez application `config.yml` MUST NOT contain a `dbRetention` block

#### Scenario: Apply no-retention configuration to existing deployment
- **WHEN** the Helm release is upgraded to disable automatic retention
- **THEN** the Marquez API process MUST NOT start a scheduled database retention job
- **AND** the deployment MUST preserve the existing PostgreSQL database PVC and metadata rows

#### Scenario: Regression introduced by chart or value change
- **WHEN** an updated Helm chart or values file introduces a `dbRetention` block
- **THEN** the deployment preflight MUST fail before any Helm mutation
