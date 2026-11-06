## Requirements

### Requirement: Marquez SHALL produce a daily local development backup
The system MUST create a logically consistent `pg_dump -Fc` archive of the existing Marquez PostgreSQL 14 database at 03:00 `America/New_York`. The backup SHALL reside only in the `marquez-backups/` directory on the existing `dw-postgre14-data` PVC, separate from the `pgdata/` cluster directory, and the Job SHALL run on the same node as the database Pod.

#### Scenario: Scheduled invocation
- **WHEN** local time reaches 03:00 and there is no previous backup Job still running
- **THEN** the configured CronJob MUST start one backup, without modifying the running database, its StatefulSet or the Marquez Helm deployment

#### Scenario: Completed backup
- **WHEN** `pg_dump -Fc` succeeds and `pg_restore --list` can parse its archive
- **THEN** a nonempty `.dump` file MUST be atomically published in the backup directory with file mode 0600
- **AND** only matching `marquez-*.dump` files older than 7 days MAY be removed

#### Scenario: Backup failure
- **WHEN** the dump, archive check, or file publication fails
- **THEN** the Job MUST fail, MUST NOT prune existing completed backups, and MUST NOT delete or alter PostgreSQL business files

### Requirement: Local backups SHALL NOT be misrepresented as offsite disaster recovery
This installation MUST preserve the explicitly accepted single-PVC failure domain; it MUST NOT require new storage infrastructure or touch OMOP PostgreSQL 17.

#### Scenario: Local disk or PVC failure
- **WHEN** the PostgreSQL 14 PVC becomes unusable
- **THEN** the runbook MUST identify that both live data and on-volume backup copies may be lost and MUST NOT claim disaster recovery protection
