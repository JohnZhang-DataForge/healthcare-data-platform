# Fabric / Local Spark OpenLineage compatibility — offline candidate

**Status: HOLD for Fabric.** Three Fabric Notebook trial attempts did not return independently verifiable PySpark output. This work is source-only, does not start a fourth notebook, touch Azure/K8s/Marquez, modify frozen ETL or choose the default backend.

| | Local K8s | Fabric Workspace Runtime 2.0 |
| --- | --- | --- |
| Spark | 3.5.7 inventory, in-memory PySpark smoke PASS | 4.1 (Microsoft guide also lists 4.1.1) |
| Scala | Existing OpenLineage listener artifact `openlineage-spark_2.12:1.47.1` | 2.13.16, cannot load 2.12 binary |
| Python / Java / Delta | full local inventory not independently read | Python 3.13, Java 21, Delta 4.2 |
| OpenLineage | Existing local event capture; business COMPLETE/lineage gaps remain | **Listener NOT_TESTED**, no Fabric OpenLineage events proven |

Evidence: [Local Spark PASS](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40439394218) and failed Fabric [attempt 1](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40439764059), [2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40440025579), [3](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40440244737). [Detailed prior POC](../../documents/infra/SPARK-PORTABILITY-POC-20261026.md).

Vendor references: [Fabric Runtime 2.0](https://learn.microsoft.com/en-us/fabric/data-engineering/runtime-2-0), [Fabric migration guide](https://learn.microsoft.com/en-us/fabric/data-engineering/runtime-2-0-migration-guide), [OpenLineage Spark installation](https://openlineage.io/docs/integrations/spark/installation/). Microsoft explicitly requires separate Scala 2.13 builds and Java 21 checks. OpenLineage documentation describes `openlineage-spark_2.13` packages, but **candidate 1.54.0 is NOT validated against Fabric Spark 4.1**: resolve availability, signed/pinned checksum and transitive dependency compatibility before approved live trial.

`compatibility.py` creates an inert candidate `spark.extraListeners` / HTTP transport config; the local existing listener is not replaced. Neither `file` nor HTTP transport directly commits Azure Blob. An **additional private authenticated collector**, not implemented in this task, must accept verified standard RunEvents and relay to the immutable Blob Publisher. Do not expose Marquez to Fabric or to the public.

## Future gated sequence (requires Main Session + user approval)
1. Validate Fabric Notebook definition through item LRO terminal success + independent definition SHA readback **before** a separately authorized test; verify Trial-only capacity and cost. No fourth test under this Session.
2. Resolve Fabric-specific Scala 2.13 / Spark 4.1 listener JAR and Java 21 dependencies, inspect real listener log and capture authentic START/COMPLETE event(s), including actual input/output Dataset URI and, when present, ColumnLineage facet.
3. Create an independent **private** Blob event container/prefix `openlineage/v1/` outside Landing/RAW/READY and Terraform State. Grant private Publisher identity scoped `Storage Blob Data Contributor`, Local Consumer scoped `Storage Blob Data Reader` (or narrower equivalent); use workload identity, no public access/account keys in source.
4. Deploy an authenticated private event collector and outbound connectivity separately. Test 401/403, offline buffering, retries, quota, no SQL/credentials/patient content, immutability and event SHA readback.
5. Local Consumer may POST events to **existing internal** Marquez `/api/v1/lineage`, then independently GET exact Run, Job, and input/output Datasets before persistent checkpoint. It must never replay Synthea, Spark, PG17 Writer or any OMOP batch.
6. Full acceptance additionally requires same source Manifest SHA / exact dataset URI evidence before linking any Local/Fabric datasets. Similar names and Fabric CascadeDelete edges are not evidence.

Run **offline only**: `python -m unittest discover -s azure-fabric/openlineage/tests -p 'test_*.py' -v`. Candidate source/Mock PASS is not real Fabric acceptance.
