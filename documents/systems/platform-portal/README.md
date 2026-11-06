---
status: active
scope: platform-portal-system
last_verified: 2026-11-05
---

# Platform Portal — Marquez / OpenLineage / Public Read-only UI

An observability and lineage subsystem, **not** the OMOP business database writer. Marquez metadata PostgreSQL14 and Local OMOP PostgreSQL17 are distinct. Locate actual source via [Platform Portal CODE](CODE.md).

## Browse by function

| Component | Authoritative reading |
| --- | --- |
| Marquez API, Helm, Web | [README](marquez/README.md) · [CODE](marquez/CODE.md) |
| PG14 metadata/backup | [README](postgres/README.md) · [CODE](postgres/CODE.md) |
| Airflow lineage provider | [README](airflow/README.md) · [CODE](airflow/CODE.md) |
| Spark lineage listener | [README](spark/README.md) · [CODE](spark/CODE.md) |
| OpenLineage Blob relay | [Relay guide](BLOB-RELAY.md) · [consumer source](../../../platform-portal/openlineage/blob-relay/consumer.py) |
| Public read-only Web and Exporter | [Portal README](portal/README.md) · [CODE](portal/CODE.md) · [Public Web](portal/PUBLIC-MARQUEZ-WEB.md) |

## Verified scope, separate holds

Local Airflow/Spark/Marquez observed real Job/Run/Dataset and Patient/Encounter lineage, while PG17's transactional COMMIT/SKIP has independent durable evidence. Historical Spark RDD action terminal-state gaps and the old A4 unknown-job diagnosis are **not** declared fixed; see [Local MVP Closeout](../../architecture/design/LOCAL-PORTAL-MVP-CLOSEOUT-AND-DEFERRED-FOLLOWUPS.md).

An isolated real [Chromium/WebKit browser acceptance](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41965389280) verified public Dashboard, populated Landing Datasets and Airflow Jobs without manual Refresh. Public frontend features do **not** authorize Marquez API mutation; gateway allowlists and sensitive GET rules remain mandatory. Cross-platform Fabric lineage is a separate Active OpenSpec/runtime gate.

Read [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md) before any Kubernetes, PG, scheduler or Marquez write. The [complete previous Portal history](PORTAL-HISTORY-20261105.md) is retained byte-for-byte; dated P1–P6 notes are evidence, not current runtime probes.
