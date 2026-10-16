# Architecture decisions

This folder explains the **important design choices** that shape the Healthcare Data Platform.

Examples include separating Synthea generation from Airflow consumption, keeping the OMOP writer responsible for database transactions, using Marquez for data lineage, and taking an OneLake-first approach to cloud analytics.

The [decision register](DECISION-REGISTER.md) records what was decided, the rationale, and which parts have actually been implemented. Planned work should not be confused with deployed functionality.

Explore the [overall architecture](../architecture/SYSTEM-OVERVIEW.md), [components](../components/README.md), or [current project status](../status/PROJECT-STATUS.md).
