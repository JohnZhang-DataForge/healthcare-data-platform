# OIE 4.7.0 disposable install — FIRST, before PV/PVC

**Runtime mode: nonpersistent by explicit user request (2026-10-24).**
Use this isolated OIE Debug Deployment in `dw-oie`, exclusively on
`worker01`, to prove engine startup and Channel conversion before
configuring any on-premises storage. This is the canonical **first
installation phase**; sibling `oie-state` PVC / StatefulSet files in the
parent directory belong only to the later durable phase and MUST NOT
be applied in this phase.

The debug Deployment mounts **only a size-bounded `emptyDir`**
to `/opt/engine/appdata`, where embedded Derby and OIE state are kept.
Restart/replacement destroys the previous Pod's data; never call it
backup or durable acceptance. It uses the existing upstream
`configure-from-env` with `/run/secrets/mirth_properties` sourced
from a distinct in-namespace `oie-debug-bootstrap` Secret.
No user password, kubeconfig, token, or generated patient data
is stored in this repository. Use a unique random password >=15 characters.
The admin listener `8443` is **ClusterIP-only**, not NodePort/Ingress.

Required substitutions before any apply:

- `__OIE_PINNED_IMAGE_DIGEST__`: immutable `ghcr.io/...@sha256:...`
  built from official OIE 4.7.0 commit
  `f9ba73e28de151b041b97e7383e0ab9d2c4f1799`.
- `__OIE_ENGINE_UID__`, `__OIE_ENGINE_GID__`: numeric identity
  measured from that exact image by `id -u` and `id -g`, never guessed.
- `dw-oie` must not already contain another active OIE instance,
  namespace owner or unknown Secret/Deployment/Service. If it does: HOLD,
  never overwrite or take over.
- The exact worker01 Node must be Ready and schedulable, with headroom
  for 250m CPU / 1Gi request and 4Gi ephemeral disk ceiling.
- Prior to runtime execution, verify GitHub Actions, concurrent sessions,
  pods/jobs and safe ownership. No legacy `dw-synthea`, local DP, PG,
  Azure or other namespaces are modified.

The manifest files in this folder are **static candidate templates**,
not a completed installation and not permitted to be blindly applied.
Installation is a controlled, separately evidenced operation. After
OIE startup, import real Channel via audited API/client, process actual
Johns Creek FHIR Bundle, verify actual v2.5.1 HL7 output and exact source
identity, then plan PVC with the user at the on-premises site.
Do not automatically promote temporary Derby data to persistent storage.

No StatefulSet, PVC, StorageClass or persistent local host path
belongs to this debug phase.

## 2026-10-24 actual ephemeral installation evidence

- **RUN PASS**: [Self-Runner #40120249619](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120249619).
- Healthcare deployed source SHA: `bcb18bc93e0372e4e78aa373c83768a143ab4b0d`.
- Pinned OIE image: `ghcr.io/johnzhang-dataforge/healthcare-oie@sha256:6716fb6210f9dc029c801b13cc152ff3fcb1ad4df05c1dbe5a9d438a482ba84b`.
- K8s Namespace `dw-oie`; Deployment `oie-debug`; Pod `oie-debug-f8f5d9c89-44vd2` pinned and actually scheduled on `worker01`.
- Observed READY, correct image Digest, OIE 4.7.0 config, internal Derby path, ClusterIP and `emptyDir`-only Pod volumes: PASS. `dw-oie` had **zero PVCs** after installation. User deliberately deferred persistent storage; Pod recreation erases Derby/Channel state.
- This is **engine-install validation**, NOT OIE clinical Channel conversion, HL7 message readback or Blob publication.
- **Future on-premises handoff**: coordinate before replacing debug Deployment; provision appropriately owned worker01 storage and test new installation before deleting existing debug objects. Never assume `emptyDir` data is a backup or automatically migrate it into a PVC.
