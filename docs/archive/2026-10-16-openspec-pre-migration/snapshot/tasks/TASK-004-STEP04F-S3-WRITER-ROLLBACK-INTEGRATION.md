# TASK004 STEP04F — Real S3 to CDM Writer ROLLBACK Integration

**Status: S3-to-writer wiring built/published; historical-batch incompatibility correctly rejected; fresh-batch end-to-end successful ROLLBACK still NOT demonstrated.**

Added `--rollback-from-s3 person|visit` to the independent CDM Runtime CLI. It verifies immutable batch plan, uses the already established strict source adapter to read and validate S3 Manifest and Processing Parquet and performs OMOP row transformation in memory, then calls the existing scoped `cdm_writer` rollback-only PostgreSQL executor. No rows.json or COMMIT CLI is used.

Evidence: [Healthcare image build 38430224357](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/38430224357) SUCCESS. Immutable image: `ghcr.io/johnzhang-dataforge/healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e`.

[Self-Runner Kubernetes integration 38430437561](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38430437561) tested the fixed previously COMMITTED historical S3 Person batch using `cdm_writer`. The historical batch ledger carries contract `task004-person-v1`, whereas the new dynamic writer requires `task004-dynamic-v1`. The expected `BLOCKED:LEDGER_DRIFT` rejection verifies the contract guard prevents silently mixing incompatible commitments. This is an **expected failure of the inner Kubernetes Job**, not positive completion of a full writer ROLLBACK transaction; independent readback confirms Person 136 / Visit 9391 unchanged.

**Next:** test a genuinely new immutable S3 batch with no historic ledger conflict and run actual full Person then Visit PostgreSQL ROLLBACK (with no COMMIT). This requires obtaining or generating a new well-scoped immutable source batch and should not rewrite the historical ledger or disable the drift gate. Airflow COMMIT / replay and TASK005 remain ON HOLD.
