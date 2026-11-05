# Fabric Deployment and Component Ownership

## ADDED Requirements

### Requirement: Fabric deployable assets and runtime business code have stable, non-overlapping owners
The Healthcare repository SHALL route Git Native Item definitions to `azure-fabric/workspaces/healthcare-omop/`, deployable Warehouse DDL/metadata and Listener configuration to `azure-fabric/deployment/<component>/`, component business Writer/Publisher code to their component source owners, Terraform to `infra-terraform/`, and shared reusable transformations to `shared-data-engine/src/`.

#### Scenario: A new Warehouse schema migration is proposed
- **WHEN** an agent adds an executable versioned Warehouse DDL or schema deployment artifact
- **THEN** it SHALL be created under `azure-fabric/deployment/warehouse/` and reviewed independently of OMOP row-writing business code.

#### Scenario: An OpenLineage integration is proposed
- **WHEN** an agent implements a Listener deployment configuration versus an OpenLineage RunEvent publisher
- **THEN** the deployment config SHALL belong to `azure-fabric/deployment/openlineage/` and the Publisher SHALL remain under `azure-fabric/openlineage/`.

### Requirement: New component paths require a recorded owner and validation
The repository SHALL provide a machine-readable register for notebook, pipeline, environment, lakehouse, warehouse, openlineage and common deployment component owners. New source paths MUST NOT create a second Native Notebook implementation, Fabric I/O Wheel, fabricated `*.Warehouse/` item or undocumented deployment executor.

#### Scenario: An agent introduces a new deployment component
- **WHEN** a new `azure-fabric/deployment/<component>/` file is added
- **THEN** its declared owner, CODE map and associated quality/test path SHALL be reviewed, and an applicable enforceable CI path check SHALL validate the ownership.

### Requirement: Source migrations preserve active consumers and historical evidence
Any physical Warehouse or OpenLineage path migration SHALL preserve original blob contents, all current-main consumers, historical fixed-SHA evidence, and applicable offline test discovery; it MUST NOT automatically execute Fabric/SQL/Marquez, and cannot bypass protected trusted policy.

#### Scenario: A Warehouse SQL path is relocated
- **WHEN** source is moved from `azure-fabric/warehouse/` to `azure-fabric/deployment/warehouse/`
- **THEN** current-main Self-Runner consumers SHALL already support the new path, test sources SHALL be updated, and content identity SHALL be verified before the old path is deleted.

#### Scenario: A legacy fixed-SHA Warehouse workflow is reviewed
- **WHEN** an old workflow checks out a pinned historical Healthcare commit
- **THEN** the migration SHALL preserve that pinned checkout's reproducible old paths without rewriting the historical evidence.
