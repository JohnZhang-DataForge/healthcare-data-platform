# Local OMOP CDM 5.4 → Azure Blob — P1 real snapshot acceptance (2026-11-02)

Status: **P1 completed for one actual immutable database archive**, with verification performed across separate execution and independent readback runs. PostgreSQL restore-to-database was deliberately **not performed**. The optional live **identical-byte retry** remains unverified and is not part of this one-shot snapshot acceptance.

## Version / target identity

- Healthcare Publisher business source: `7a597b2f0c946eef80f9e81a0dc2ba6544ad5b0b`.
- Reviewed Publisher GHCR digest: `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:dadc994c589db30cc527236f36a2e3cc1c5da82c792531c1b0f75e80f30985d0`. Built/published by [Healthcare Run #41504516774](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41504516774).
- Producer/execution Self-Runner main: `c9211c732943822ed00aab17b712cd57f2dd7aa7`, [Self-Runner Run #41507610557](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41507610557).
- Independent archive acceptance Self-Runner main: `069136d500491f5212ac2c9dda3b9d12345e0817`, [Self-Runner Run #41509750892](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41509750892), source [Self-Runner PR #441](https://github.com/JohnZhang-DataForge/Self-Runner/pull/441).
- PostgreSQL: local `dw-postgre` namespace, `dw-postgre-database-0`, PostgreSQL 17, database `omop`, exported **`cdm` schema only**.
- Publisher: `dw-synthea`, reused `azure-blob-publisher-identity`; unique short-lived `omop_export_41507610557` PostgreSQL read-only role and `dw-synthea/omop-snapshot-reader` K8s Secret.
- Azure account/container: `johnzhang` / `landing`, immutable snapshot ID `omop-20261102-live-41507610557`.

## Immutable objects (no credential/data bytes recorded)

| Object | Azure Blob key |
| --- | --- |
| PostgreSQL custom dump | `omop/snapshots/omop-20261102-live-41507610557/omop-cdm.dump` |
| Commit manifest | `omop/snapshots/omop-20261102-live-41507610557/snapshot-manifest.json` |

- Archive bytes: **195,370,142** (approx. 186.3 MiB).
- Archive SHA256: `54c02455f9ae305532209ffed9b90354ca5a652df1220ce418be0f084c9dc2cf`.
- Archive format: `PGDMP` PostgreSQL custom archive, using `pg_dump -Fc --schema=cdm`.
- Actual archive TOC read using PostgreSQL 17 `pg_restore --list` against a temporary **file**, not an input pipe: **355 entries**, including **39 CDM TABLE DATA objects**, including Person and Visit.
- Azure independent Manifest GET + SHA256 + Blob metadata: **PASS**.
- Azure independent archive GET + SHA256 + byte count + metadata + ETag: **PASS**.
- Previous K8s Publisher Job: `dw-synthea/omop-snap-41507610557` **COMPLETED**.
- Previous run-scoped K8s `omop-snapshot-reader` Secret: **ABSENT** at independent check; previous PG role revoke/drop reported PASS.

### Real-run chronology (do not overwrite historical failures)

1. [#41505288117](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41505288117) failed before Job/Blob PUT: original `cdm_reader` was not entitled to dump all 39 tables, and the sequence privilege SQL checked a non-Sequence relation.
2. [Forensic #41505709057](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41505709057) confirmed 0 Job, no scoped Secret, and PostgreSQL read-only SELECT connectivity. [Catalog #41506003341](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41506003341) counted 37 missing table SELECT grants and identified the sequence SQL issue.
3. [#41507109783](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41507109783) failed before Job/Blob PUT due to PostgreSQL boolean`::text` producing `true/false` where the test assumed `t/f`; the scoped role was removed.
4. [#41507610557](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41507610557) created and verified a unique all-`cdm` READ-only role, created a short-lived Secret, performed the actual `pg_dump`, completed the `dw-synthea` Job, and committed the immutable Dump + Manifest via Azure SDK readback. Independent Azure GET/hash/ETag checks were reached successfully, but the **final stdin-based `kubectl exec ... pg_restore --list` command exited nonzero**. The job's GitHub conclusion remains **FAILURE**; the role and Secret were cleaned. This is NOT relabeled as a passing run.
5. [#41509750892](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41509750892), **SUCCESS**, explicitly verified **the same already-committed** Azure snapshot through independent REST GET (Manifest, full Dump), checksum/ETag/size checks, and `pg_restore --list <file>` using a restrictive `/tmp` archive inside the existing PostgreSQL 17 container. The local temporary archive was removed via shell trap. **No new pg_dump, Blob PUT/DELETE/overwrite, Kubernetes Job or database restore was performed**.

## What PASS means / what remains outside scope

- PASS proves that one actual, immutable `cdm` PostgreSQL custom archive was uploaded and independently retrievable byte-for-byte, and PostgreSQL 17 can parse its TOC using `pg_restore --list`.
- This does **not** prove a full restore into an independent database, successful OMOP referential constraints after restoration, or correctness of each clinical row. A separate restore drill would require another planned, authorized task.
- Real identical-byte same-ID retry was **not** executed; the Publisher's idempotence and conflict tests had previously passed offline. Any retry must reuse byte-for-byte staged payload; a fresh `pg_dump` under the same ID is not safe. No additional upload is needed for P1 acceptance.
- P2 Parquet/table-level Golden Dataset and Fabric reconciliation are **not implemented** and remain on the active OpenSpec task list.
- Live data in these tests is synthetic, but treat the dump and its access credentials as restricted. No dump bytes or secrets were included in GitHub artifacts or this evidence.
