# Design — Local OMOP snapshot exporter through shared Blob Publisher

## Existing boundary

```text
dw-postgre / PostgreSQL17  [read-only role]
   |  pg_dump --format=custom --schema=cdm (no app sources)
   v
dw-synthea / Job initContainer  [staged omop-cdm.dump in emptyDir]
   |  same Pod volume, no cross-Namespace PVC
   v
dw-synthea / existing Azure Blob Publisher image
   |  separate OMOP runtime using existing AzureSDKBlobBackend
   |  conditional create -> independent GET/SHA256 -> commit manifest LAST
   v
existing Azure Blob container / omop/snapshots/<snapshot_id>/
   |- omop-cdm.dump
   `- snapshot-manifest.json  (commit marker)
```

## P1 contract

- Stable `snapshot_id`: `omop-YYYYMMDD-<unique-suffix>`, validated path-safe ASCII. It is a **once-created identity**; running a new pg_dump of the same ID may produce different bytes and MUST hold as an immutable conflict.
- `omop-cdm.dump` is a PG custom-format dump of **cdm schema only**. `pg_dump` uses a consistent database snapshot for its dump, and is issued with PostgreSQL role that can SELECT only approved schema tables. It does not include GitHub/source/ETL code, `etl` schema or PV/PVC files.
- Blob prefix is separately approved at runtime; prohibit `landing` FHIR/HL7 branch, `..`, backslashes, URL path escape. Azure container is passed at runtime, not inferred from SeaweedFS bucket names.
- Stage file must be regular, non-symlink, nonempty, bounded (first MVP cap 256 MiB) and readable only within the Job. No data bytes or raw PG / Azure exception details in logs. Reject missing/oversized file before first remote write.
- Upload data first with immutable `overwrite=False` via existing backend and independent actual GET; include SHA256, byte length, ETag and version ID in JSON commit Manifest; commit Manifest last via the same immutable GET/readback. Manifest preflight rejects same ID with changed digest, without writing any more data.
- No Azure container creation, DELETE, overwrite or PostgreSQL writes. A failure before Manifest allows only an identical-byte retry with verified remote data; an existing conflicting Blob MUST remain untouched.
- Default K8s Job in `dw-synthea`; `postgres:17` init image and publisher image are separately digest-pinned during deployment. Password comes from new scoped `dw-synthea` read-only PostgreSQL credentials Secret; Azure identity uses the **existing** `azure-blob-publisher-identity` Secret with RBAC rechecked for OMOP prefix. Existing FHIR volume/PVC not mounted.
- No job is deployed by merging code; separate live authorization + resource coordination + independent Azure readback required.

## P2 table export (separate step)

- Only actual OMOP `cdm` base tables, **not** `etl`, `public`, app scripts or SQL source files; enumerate from `information_schema`, preserve OMOP column/type metadata, row counts and table-level SHA256; Parquet files plus a Schema/Manifest.
- Use a consistent read-only PG snapshot and bounded streaming export. Empty tables may appear in schema inventory but need not produce Parquet data objects. Reuse the **same** independent immutable Blob transport with a new snapshot ID.
- Fabric consumes Parquet as Golden Dataset for Person/Visit and other populated tables and can compare key integrity/record counts against native Spark Delta; not a substitute for FHIR -> Bronze -> Silver -> OMOP.

## Testing and lifecycle

1. OpenSpec strict validation, static namespace/source/template/secret constraints.
2. Pure offline unit/fault tests with Fake Azure backend: success, matching retry, bytes altered, remote metadata changed, existing-commit conflict, GET failure, partial write without manifest.
3. CI test on exact PR SHA; do not conflate Mock PASS with real K8s/Azure.
4. After explicit permission: read-only PG preflight; check single active jobs/PG role, run a unique snapshot, independent Azure GET/manifest/digest and optional `pg_restore --list` of downloaded dump. No destructive restore into live DB.
5. After independent P1 live acceptance, schedule P2 Parquet implementation and regression against Fabric. Do not archive while these tasks are pending.

## Rollback

No current OMOP/Producer/Publisher objects are modified by P1. Failed Job can be removed only after ownership check; partial immutable Blob objects are retained for readback/retry. Never delete an existing snapshot or overwite Blob to “repair” a conflict.
