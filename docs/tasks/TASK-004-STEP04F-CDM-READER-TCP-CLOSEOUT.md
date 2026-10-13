# TASK004 STEP04F — Independent CDM Reader TCP Smoke

**Result: PASS.** Self-Runner workflow: https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38420850261.

Verified from an independent ephemeral Kubernetes Job in namespace `dw-spark`, node `worker02`, using `postgres:16-alpine` against PostgreSQL Service `dw-postgre.dw-postgre.svc.cluster.local:5432`. Credentials were injected via the pre-existing `task004-cdm-reader-db` Kubernetes Secret; no credential values were printed or committed.

A real `psql` read-only transaction returned the expected `current_user=cdm_reader`, `transaction_read_only=on`, `cdm.person=136`, `cdm.visit_occurrence=9391`, fixed historical batch Ledger count 1, and `has_table_privilege(current_user,'cdm.person','INSERT')=false`. The workflow checks each marker and printed `CDM_READER_TCP_LOGIN=PASS`, `OMOP_MUTATION=NO`; job was scheduled, completed and had a cleanup trap.

**Scope boundary:** This proves TCP authentication and SELECT using a separate in-cluster PostgreSQL client, not the published CDM runtime image (which still lacks a PostgreSQL connector). The privilege test was metadata-based (`has_table_privilege`); no actual INSERT was attempted. No new roles, secrets, grants, OMOP changes or Airflow tasks were created here. Next checkpoint: package read-only PostgreSQL access inside CDM Runtime and verify with dedicated credentials; writer integration remains separate. TASK005 on hold.
