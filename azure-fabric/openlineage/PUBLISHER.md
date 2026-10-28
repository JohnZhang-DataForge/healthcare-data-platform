# Immutable OpenLineage Blob Publisher

Offline source entrypoint: [publisher.py](publisher.py). Test: `python -m unittest discover -s azure-fabric/openlineage/tests -p 'test_publisher.py' -v`. **No production execution and no Azure credentials are configured.**

A caller supplies actual OpenLineage RunEvent JSON objects, one batch ID, backend (`local` or `fabric`) and a *verified* SHA256 of its upstream Source Manifest. The protocol is `openlineage.blob-manifest.v1`. Events are encoded as canonical UTF-8 JSON + final newline; stable Event IDs bind exact Run UUID/Job namespace/name/Event Type/Time, and each event is placed at `openlineage/v1/batches/<batch>/events/<event-id>.json`. The distinct payload SHA256 is recorded in the committed `manifest.json`.

**Safety semantics:** validate every event first; reject raw SQL/token/password/patient-id keys; create each BlockBlob with `overwrite=False`; independently read back byte-for-byte; publish the immutable COMMITTED Manifest **last**. A partially failed batch leaves no committed marker and is safe to restart. Identical retries are no-op, conflicts fail closed. Never infer Dataset edges or fabricate COMPLETE from START. Do not claim full PHI/secret scanning: deeper facet allowlisting and authorization are required prior to any live event release or public snapshot.

`AzureBlobStore` is injected with an SDK `ContainerClient`, not auto-connected. Its `create` maps actual Azure ResourceExistsError to `BlobExists` and preserves all other failures. The Fake SDK tests assert `BlockBlob` and `overwrite=False`. Real Azure container IAM, app identity, provisioning, monitoring, retry/backoff and private collector ingestion are **HOLD** until independently authorized. Use private `openlineage/v1/` prefix separate from business RAW/READY & Terraform State.

Downstream contract: Local Blob Consumer (separate OpenSpec 7.7 / PR #522, path `platform-portal/openlineage/blob-relay/`) after its separate PR. Same physical Dataset namespace/name or exact Manifest lineage evidence, **never similarity**, is needed for cross-cloud joins.
