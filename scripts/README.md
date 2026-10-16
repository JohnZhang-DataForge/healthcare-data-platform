# Development and operational scripts

[← Repository overview](../README.md) · [Development operations](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md)

**Legacy scripts** are organized by historical task/milestone number. **New maintained scripts must be organized by component/function** (for example `scripts/omop/verify_condition_fk.sh`) under the [mandatory naming standard](../documents/development/CODE-ORGANIZATION-AND-NAMING.md). Many are reference, smoke, source preparation or one-time verification utilities; **not all scripts are part of the current runtime ETL path**, and some can mutate S3/Kubernetes/PostgreSQL.

| Directory | Scope |
| --- | --- |
| [`task001/`](task001/) | Synthea 18-file intake contract, S3 publication and readback verification |
| [`task002/`](task002/) | Canonical Person foundation, mapping, stage load and idempotency validation |
| [`task003/`](task003/) | Visit candidate/Raw/Processed mapping, reconciliation and writer controls |
| [`task004/`](task004/) | Independent Synthea, Airflow and Person/Visit processing milestone helpers |

## Which scripts should an Agent run?

1. **Start with** [`docs/README.md`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/README.md) and [`TASK-STATUS.md`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-STATUS.md); identify the currently approved step and its current canonical source.
2. Check whether a script is **READ ONLY**, a generator, a publication helper, a deployment or a business-commit command.
3. Prefer an existing bounded GitHub/self-hosted Runner workflow where one exists; verify the version, branch and exact inputs.
4. Use fixed batch/manifest identities and read-only durable inspection before any recovery attempt.

Historical scripts under `task004` remain for repeatable evidence and compatibility and should **not** be mass-renamed. The primary accepted new-batch path is now the Airflow DAG [`new_only_omop_consumer`](../airflow/dags/new_only_omop_consumer.py), not a sequence of manual Shell commands.

In lab sessions the convention is one reviewable step at a time, new scripts committed under their component/function folder (Task/Step names remain in Issue/PR/Run evidence, not new source paths), and temporary developer experiments kept outside the canonical repo under `/data/spark/temp_shell` when applicable.
