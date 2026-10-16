# PostgreSQL and OMOP SQL

SQL definitions and queries for **batch tracking, data mapping, transaction-related structures, and database validation**.

## Contents

- [`landing_claim/`](landing_claim/) — batch ledger and claim/fencing SQL
- [`task002/`](task002/) — historical Person loading logic
- [`task003/`](task003/) — historical Visit mapping and identifier logic
- [`task004/`](task004/) — Person/Visit batch staging, checkpoints, and reconciliation queries

This directory includes both **read-only queries and statements that change database state**. The files are versioned source material, not a snapshot of the current database.

For the broader workflow, see [OMOP Writer](../documents/components/omop/README.md) and [Python applications](../apps/README.md).
