# Design — seven-day Marquez local backup

## Runtime
```text
CronJob / dw-postgre14 / 03:00 America/New_York
   → postgres:14 pg_dump -Fc (TCP read from dw-postgre14)
   → format list check (pg_restore --list, no restore)
   → same RWO PVC dw-postgre14-data/marquez-backups/
   → prune own finished *.dump older than 7 days, only after success
```

- The CronJob and PG14 StatefulSet co-locate using required Pod affinity to the PostgreSQL Pod label on `kubernetes.io/hostname`; both mount the existing local RWO PVC without changing its claim or PV.
- `/backup/marquez-backups` in the backup Pod is the PVC root's `marquez-backups/`, separate from PostgreSQL `/var/lib/postgresql/data/pgdata`. No other directory can be purged.
- Use the existing `dw-postgre14/postgres-secret` keys through Pod env; credentials never leave the cluster or appear in backup filenames or CI logs. Pod service-account token disabled; UID/GID 999.
- Output `marquez-YYYYMMDDTHHMMSSZ.dump` with temporary hidden `.partial`; `pg_restore --list` and size check must pass before atomic `mv`. `umask 077` and file mode 0600.
- Keep seven 24-hour periods with `find -mmin +10080`; cleanup never runs on dump failure and applies only to `marquez-*.dump` in that exact directory. Existing metadata rows never expire.
- `concurrencyPolicy: Forbid`, one attempted Job per execution (backoffLimit 0), bounded 15-minute execution and one-hour late-start tolerance; scheduled failures remain visible in Job status/log.
- Minimal verification: offline unittest including bash syntax, Kubernetes GET preflight, exact new CronJob apply, single manual Job, Job success and filesystem readback. Any privileged restore or disaster recovery test is deliberately out of scope.

## Recovery (manual only, separate authorization)
Keep the `.dump` archive; to actually restore, stop Marquez writers, select a separately authorized **isolated** PostgreSQL database, use `pg_restore`, and verify objects/relationships before deciding on further action. Never restore onto the live Marquez database as part of the scheduled backup job.

## Accepted risk
Same PVC = single failure domain; not protection from host or PVC failure. This trade-off is explicitly chosen for a low-cost development environment.
