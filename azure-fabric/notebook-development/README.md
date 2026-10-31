# Fabric FHIR Notebook — P2 offline working source (NOT Native Item)

The files in this directory contain **one future notebook application's implementation** and its offline tests. This is not another package, a Python scheduler, a Fabric I/O framework, or a deployable `.Notebook` folder.

The authoritative Git-connected target remains `azure-fabric/workspaces/healthcare-omop/notebooks/ingestion/nb_fhir_ingest.Notebook/`. Its `.platform` / logicalId MUST be exported from the actual Fabric Workspace before the business code can be integrated into a native definition. The Pipeline and Environment native definitions are similarly **BLOCKED**. Do not copy `johnzhang-test` metadata.

The code follows Pipeline parameters supplied as explicit `BatchContext`, validates exact Manifest bytes and object SHA256/size, uses the native Spark `binaryFile` reader, preserves an independently read-back Bronze receipt, imports the sole installed Shared Wheel, writes immutable version-scoped Silver Delta with `errorifexists`, verifies Patient/Encounter PK/FK and batch fields from fresh Delta reads, and records `SILVER_APPROVED` only after physical readback. It provides Quarantine evidence and explicit `VERIFY_READONLY` for partial/unknown ACK. It never declares Gold COMMITTED.

**No cloud read/write is executed by offline CI.** `execute_native_notebook` defaults to `write_authorized=False`, also requires separate verified source retention preflight and live authorization before execution. CI only exercises manifest verification, synthetic Shared transformations and real local PySpark schemas plus Spark DataFrame readback checks. It does not install or publish the Wheel to Fabric.

The future actual Notebook must contain this logic visibly, bind a real approved Lakehouse, use a genuinely exported Environment with Wheel `healthcare-data-engine==0.1.0` SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7`, verify effective published library version, and use real Pipeline params, failure branch, monitoring and selective retry. Pipeline Notebook activity SUCCESS must never be interpreted as Gold COMMITTED.

Before any live release collect **read-only** evidence for healthcare-omop Workspace ID, Lakehouse ID/schema and capacity status, source Shortcut/Copy byte retention, Git branch/folder association, item permissions, effective Environment library list, Notebook effective version and cost. Current rights do **not** authorize Native Item creation/update/Publish, Pipeline run, OneLake/Blob/PG/K8s writes or TF State changes.

Readiness check (safe; reports `BLOCKED_NATIVE_EXPORT` until actual exports exist):

```sh
python azure-fabric/notebook-development/native_item_readiness.py
```
