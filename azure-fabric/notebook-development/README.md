# Fabric P2 FHIR Notebook — Git-first source and offline validation

The **single authoritative Notebook business source** is now
[`nb_fhir_ingest.Notebook/notebook-content.py`](../workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py).
It is a real FabricGitSource item with Fabric-generated nonzero `.platform` logicalId
and the actual existing healthcare-omop Lakehouse metadata. The previous
[`fhir_ingest_notebook.py`](fhir_ingest_notebook.py) is now an offline-only
compatibility loader that imports the Native Notebook; it MUST NOT be separately
published or modified as a business implementation.

The Notebook contains the P2 Manifest/SHA verification, Shared Engine FHIR
Patient/Encounter canonical transformation, Bronze receipt, immutable Delta
Silver staging, quarantine, idempotency, independent physical readback, and
explicit approval guards. It intentionally starts with `run_mode=HALT`,
`write_authorized=False`, `retention_preflight_verified=False`, and its
Fabric startup cell **always stops with HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED**.
Authoring the source is not cloud authorization.

The actual Pipeline source is
[`pl_fhir_ingest.DataPipeline/pipeline-content.json`](../workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/pipeline-content.json).
It has one `TridentNotebook` activity referencing verified real Workspace and
Notebook GUIDs, no automatic retries/schedules, and passes only disabled
write parameters. A manual Run now would fail closed and could still incur a
Spark startup cost; **do not run it**. Run status is not business acceptance.

The Shared Engine is one Python Wheel, `healthcare-data-engine==0.1.0`
(SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7`).
The GitHub-hosted [offline CI](../../.github/workflows/fabric-fhir-notebook-offline.yml)
builds, verifies and uploads this Wheel as an artifact; a CI artifact is **not**
a published Fabric Environment. Environment binding/publish, effective library
readback and Lakehouse retention checks remain HOLD.

Run the static Gate (expected exit 2 even after valid Git native export):

```sh
python azure-fabric/notebook-development/native_item_readiness.py
```

Expected `HOLD_NATIVE_RUNTIME_DEPLOYMENT`, not the old
`BLOCKED_NATIVE_EXPORT`. The user will manually switch the Fabric Workspace
from `fabric/native-bootstrap-20261031` to `main` **only after** GitHub
PR/CI and a no-delete/no-recreate Update-from-Git review. That Workspace
change is NOT made by this repo PR.

Further release gates: attached/published Environment with effective Wheel,
valid retained FHIR source/Manifest/Contracts, approved runtime bindings,
capacity/cost, job identity, and Bronze/Silver physical readback. Do not mark
Gold COMMITTED from Notebook or Pipeline success.
