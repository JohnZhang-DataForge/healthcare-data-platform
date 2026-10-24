# Azure Blob Publisher — dw-synthea DIRECT FHIR runtime (static)

## Current accepted deployment boundary

- Publisher Job runs in **`dw-synthea`** on **`worker01`**. This is the **same Namespace** as `synthea-new-generator-state`; do not create another Namespace or another Publisher PVC.
- `publish-direct-fhir-job.yaml.tpl` mounts the **existing Generator PVC read-only** at `/synthea-new-generator-state` in both `volumes[].persistentVolumeClaim.readOnly` and `volumeMounts[].readOnly`. Never rebind, resize, delete, or modify the original PVC, source Manifest, or generated FHIR data. Check the actual PVC accessModes (RWO vs RWOP), current node ownership and active Generator Job before deploying; incompatible concurrent use = HOLD.
- The job invokes `apps.clinical_producers.azure_blob_runtime` with `--source-mode direct-readonly-pvc`. No staged `/handoff`, additional storage, cross-Namespace byte transfer, or artificial ready marker. Real `verify_handoff` and **externally pinned SHA256** of the frozen source Manifest still run before initializing an Azure SDK client.
- `azure-blob-publisher-identity` is a **future, separately scoped Secret in `dw-synthea`** with keys `tenant-id`, `client-id`, `client-secret`. It does **not** exist merely because this template exists. Scope Azure Storage Blob Data Contributor to the explicitly approved landing container; no credentials in Git/Pod logs.
- The Profile ConfigMap and exact digest-pinned Publisher image have not been built or deployed as part of this change. Render all `__PLACEHOLDER__` values through a reviewed Workflow and verify source identity / no active jobs / Job/Secret/Pod name collision; do not run this static YAML without a new explicit authorization and full preflight.

## Other clinical route

`dw-oie` remains independent, with its own Derby/PVC and existing internal OIE Service/Channel. It receives verified FHIR data **via authenticated OIE API requests**, not by mounting the Generator PVC. The future Johns Creek production Publisher must read independently authenticated persisted OIE HL7 bytes/skip receipts and verify their FHIR provenance before Azure write. No old accepted 32 Derby messages may be replayed. The current Job supports only DIRECT FHIR and does not yet wire this OIE source.

## Historical retirement

The formerly isolated `dw-az-blob` namespace was created in [Self-Runner #40133194325](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40133194325), then revoked by user decision and **deleted after UID and emptiness checks** in [Self-Runner #40133855773](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40133855773). Independent API readback reported namespace absent; `dw-synthea`/`dw-oie` identities and PVCs did not change. Its old namespace manifest/default-deny policy/staging Job are not supported deployment targets.

**No Azure Blob PUT/GET, GHCR Publisher release or Pod/Secret deployment has been accepted** at the time of this code. Hosted Mock/Azurite CI does not establish live Azure identity or runtime.
