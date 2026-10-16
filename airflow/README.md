# Airflow orchestration

This directory contains the **Airflow DAGs and Python helpers** that coordinate data batches and launch downstream processing. Airflow handles orchestration; the substantial data transformations happen in Spark.

## What's here

- [`dags/new_only_omop_consumer.py`](dags/new_only_omop_consumer.py) — controlled NEW_ONLY batch workflow for Person and Visit
- [`dags/new_only_omop_routing.py`](dags/new_only_omop_routing.py) — batch selection and already-completed routing
- [`dags/new_only_omop_writer_handoff.py`](dags/new_only_omop_writer_handoff.py) — prepares information passed to the database writer
- [`dags/landing_batch_discovery.py`](dags/landing_batch_discovery.py) — inspects available landing batches

Other DAG files include historical prototypes and supporting processing routes. Their presence does not imply that every route is actively scheduled or deployed.

See [Airflow component notes](../documents/components/airflow/README.md), [Spark](../spark/README.md), and [the overall data flow](../documents/architecture/DATA-FLOW.md).
