# OIE v4.7.0 single-PVC persistent phase (worker01 only)

Live read-only evidence: [Self-Runner #40121142405](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121142405)
confirms `local-path-storage/local-path-config` already includes
`storageClassConfigs.oie.nodePathMap` with **worker01:
`/data/oie`**, worker02/03 empty, and a running provisioner with
`CONFIG_MOUNT_PATH=/etc/config/` and **`Applied config` including oie**.
Do **NOT** restart, redeploy or modify the shared local-path provisioner;
the hot reload is already accepted. Do not change any other StorageClass.

- `storageclass.yaml`: new exclusive StorageClass `oie`, provisioner
  `rancher.io/local-path`, `nodePath=/data/oie`, `Retain`, and
  `WaitForFirstConsumer`. Not default. Do not rename `oie` to
  `oie-local` without updating the actual ConfigMap key first.
- `pvc.yaml`: `dw-oie/oie-state`, `ReadWriteOnce`, 10Gi, uses
  `storageClassName: oie`; requires one Pod specifically scheduled on
  `worker01` before it can bind.
- Existing OIE 4.7.0 instance is `dw-oie/deployment/oie-debug`, one
  replica, `Recreate` strategy, runs on `worker01` and has image
  `ghcr.io/johnzhang-dataforge/healthcare-oie@sha256:6716fb6210f9dc029c801b13cc152ff3fcb1ad4df05c1dbe5a9d438a482ba84b`,
  numeric UID 100 / GID 65533 and `fsGroup=65533`.
  The persistent rollout replaces ONLY the existing
  `debug-appdata` volume definition from `emptyDir` to
  `persistentVolumeClaim: {claimName: oie-state}`. Keep its Pod owner,
  Secret, cluster-only Service, nodeSelector, image and other workloads
  unchanged. Do not create a second simultaneously writable OIE.
- This is **not** a manual PV or hostPath Pod: the local-path provisioner
  creates a new unique PV subdirectory under `/data/oie` at first bind.
  The existing mount at `/data/oie` must be a valid host filesystem as
  configured by the user. A `Retain` policy prevents automatic PV deletion
  when a PVC is removed, but is **not** a tested backup solution.
- OIE appdata stores embedded Derby (channel definitions and message
  history), generated server.id, keystore and runtime appdata; OIE also
  reads its initial administrator configuration from the **existing
  Kubernetes Secret** and its image config outside appdata. One volume
  mounted at `/opt/engine/appdata` covers this first-phase persistence.
  No separate long-lived HL7-file storage is required with the planned
  Azure Blob Publisher route. For a future independent local file spool,
  add a second PVC only through a separate Change.

## Deployment validation and safety

1. Explicitly inspect latest two-repo Main, active GitHub Runs, shared K8s
   jobs/pods and existing StorageClasses, PV, PVC and `oie-debug`
   Deployment. Require the observed `oie` ConfigMap mapping and
   provisioner log evidence before the first write.
2. Create ONLY this new StorageClass/PVC with `kubectl create`, **never
   use apply/delete/recreate** on another owner's storage.
3. `WaitForFirstConsumer` may leave the PVC Pending until the existing
   OIE Deployment's debug volume is patched. Patch only if Deployment
   existing volume is exactly emptyDir, the Pod is worker01 and no
   custom Channel data is known to need preservation. This replacement
   discards the previous debug `emptyDir` Derby; do not pretend it is
   migrated.
4. Perform `rollout status`, then independent verification of the new
   Pod on worker01, the exact pinned image, a `Bound` PVC and PV with
   `Retain`, PVC/PV identity, PV host/nodeAffinity/path under
   `/data/oie`, and an OIE Derby writable directory on the mounted
   volume. Require no other StorageClass, PV/PVC or namespace changes.
5. On failure **do not delete** the new PVC, PV, old OIE Secret or
   provisioner. Preserve evidence and stop for review. If the deployment
   is unavailable after patch, inspect Pod events and storage permissions
   before any second mutation.

OpenSpec Change: `implement-oie-fhir-to-hl7-adt-poc`. Real Channel
FHIR→ADT conversion and Blob publication are **separate, still-open
acceptance gates**.

## Live durable acceptance — 2026-10-24

**Completed, not just planned:** [Self-Runner Live #40121734522](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121734522) installed a single `oie` StorageClass with `Retain`/`WaitForFirstConsumer`, 10Gi RWO PVC `dw-oie/oie-state`, and patched existing `dw-oie/oie-debug` from `emptyDir` to that claim. Exact PV: `pvc-8ca5e84e-d58a-4448-9059-47473023f036`, directory `/data/oie/pvc-8ca5e84e-d58a-4448-9059-47473023f036_dw-oie_oie-state`. OIE 4.7.0 stayed on worker01, Ready, Derby writable. Shared local-path provisioner **was not restarted**.

[Restart durability Run #40122005828](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40122005828) independently verified that a unique test marker written into OIE `/opt/engine/appdata` survived replacement of the Pod; the replacement Pod is `oie-debug-5dbf74d9cf-vgjkd` on worker01, and the marker was safely removed after verification. This establishes **single PVC persistence across Pod recreation**, not a tested off-node backup/disaster recovery solution. Do not delete the Retain PVC/PV; coordinate before changing path, node, image or introducing a second OIE writer. No separate local HL7-file PVC is needed for planned direct Blob publishing. OIE Channel conversion is still not accepted.
