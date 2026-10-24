# Johns Creek OIE — Kubernetes *static templates only*

This directory is for the **Eclipse Open Integration Engine 4.7.0**
clinical transformer. The first PoC uses a distinct `dw-oie` Namespace,
a single-replica OIE StatefulSet pinned to `worker01`, and a distinct
`dw-oie/oie-state` PVC for bundled Derby + OIE appdata. **No file
in this directory is evidence of a deployed OIE instance.**

- `namespace.yaml`: proposed `dw-oie`.
- `pvc.yaml.tpl`: requires substitution of a **previously inspected**
  `worker01`-compatible StorageClass with an actual Retain reclaim
  policy; do not change the existing `synthea-local` StorageClass.
- `statefulset.yaml.tpl`: requires a pinned image URI with
  `@sha256:<64 lower hex>`, and a manually provisioned Kubernetes
  Secret `dw-oie/oie-bootstrap-properties` with key
  `mirth_properties`. Secret value is the trusted OIE 4.7.0
  `server.initialadminpassword = ...` configuration line, never
  committed or printed. Never use the default admin password or log it.
- `service.yaml`: internal ClusterIP only for 8443 OIE administrative
  endpoint. No NodePort, LoadBalancer, Ingress or publicly accessible
  endpoint; separate future authenticated OIE Channel input needed.

All OIE Pods use `nodeSelector:
kubernetes.io/hostname: worker01`. Namespace boundary means an OIE
Pod **cannot directly mount** `dw-synthea/synthea-new-generator-state`:
the FHIR payload must use a deliberate separately authorized handoff.
Do not conflate OIE's admin port with a Channel's ingest listener.

## Official engine behavior checked against v4.7.0 source

Upstream tag `v4.7.0` resolves to
`f9ba73e28de151b041b97e7383e0ab9d2c4f1799`.
Source [Dockerfile](https://github.com/OpenIntegrationEngine/engine/blob/v4.7.0/Dockerfile)
includes `jre-run` using Java 21 and non-root `engine`.
Source [configure-from-env](https://github.com/OpenIntegrationEngine/engine/blob/v4.7.0/server/basedir-includes/configure-from-env)
merges `/run/secrets/mirth_properties` into config.
The upstream startup script **writes** `/opt/engine/conf/mirth.properties`
and potentially JVM options. Therefore `readOnlyRootFilesystem`
is intentionally not enabled until a controlled image smoke confirms
a writable config mount. The StatefulSet is **not** a verified runtime
manifest until an actual image and startup test exist.

The Docker image itself must be built from upstream **exact commit**,
with recorded digest/startup/readback. Do not substitute Docker Hub
`latest`, a mutable tag, or a previous 4.5.x image for version 4.7.0.
The deployment template MUST reject unresolved placeholders before any
apply. K8s objects should be created only when owner approves the
specific shared-runtime action after active job/node/storage preflight.

## Live acceptance not yet done

Inspect live `worker01` Ready, active Jobs/Pods, existing `dw-oie`
resources/UIDs, StorageClasses, node-local storage, Secret scope, PVC
ownership, pending GitHub Runs, and expected image digest. Do not
automatically reset/clean up a Retain PVC on failure. Start with one
approved OIE Pod, inspect true image/startup/version/admin protection,
then import a tested OIE Channel and run a real Johns Creek source.
Assert HL7 v2.5.1 readback, repeat-control-ID stability, skips and rejects.
No Azure Blob, old Local DP/OMOP or Synthea state mutation is authorized
by this template or these instructions.

## Numeric UID/GID must be measured before runtime

The official OIE upstream image declares `USER engine` (a **name**),
not a numeric UID. Kubernetes `runAsNonRoot: true` can reject a named
image user if `runAsUser` is absent. The StatefulSet therefore requires
`__OIE_ENGINE_UID__` and `__OIE_ENGINE_GID__` to be filled from
`docker run --rm --entrypoint id <exact-image> -u` / `-g` before
any deployment, and sets `runAsUser`, `runAsGroup`, and `fsGroup`.
The Secret uses `0440` mode, only accessible by its owner or matching
group. The PVC's existing on-disk ownership must also be checked before
first start; never chmod or chown unrelated retained volumes.
