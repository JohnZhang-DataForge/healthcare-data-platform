# Spark OpenLineage probe

A **standalone PySpark experiment** for exploring what a Spark application sends to the Marquez lineage service. It uses its own tiny CSV input rather than the Person/Visit business pipeline.

## Contents

| File or folder | Purpose |
| --- | --- |
| [`probe.py`](probe.py) | Reads a sample CSV and runs a small aggregation |
| [`input.csv`](input.csv) | Minimal sample input |
| [`render.py`](render.py) | Produces Kubernetes YAML for the independent probe |
| [`sparkapplication.yaml.tpl`](sparkapplication.yaml.tpl) | SparkApplication template |
| [`requirements-static.txt`](requirements-static.txt) | Dependencies for static checking |
| [`tests/`](tests/) | Offline tests for source and rendered definitions |

An isolated Spark run and partial Marquez readback were recorded; application Job/Run association and full input/output dataset lineage remain separate work.

See [technical experiment notes](TECHNICAL-REFERENCE.md), the [Portal overview](../../README.md), and the [Portal component documentation](../../../documents/components/platform-portal/README.md).
