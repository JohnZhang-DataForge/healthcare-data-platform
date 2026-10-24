# Eclipse OIE 4.7.0 — source-pinned image (isolated smoke only)

## Immutable upstream baseline

- Official upstream repository: `OpenIntegrationEngine/engine`
- Release: `v4.7.0` (official announcement 2026-10-21).
- Exact upstream source commit:
  `f9ba73e28de151b041b97e7383e0ab9d2c4f1799`
- Upstream original `Dockerfile`, final build target: `jre-run`
  (Java 21, non-root engine).
- License: [MPL 2.0](https://github.com/OpenIntegrationEngine/engine/blob/v4.7.0/LICENSE).

The official 4.7.0 release does not include a published official Docker
image. Do not use Docker Hub `latest` or quietly fall back to 4.5.x.
The official release `tar.gz` and checksums could alternatively provide
a pinned packaged release, but are **not yet used** by this smoke.

## Source-build gate

The Healthcare GitHub-hosted workflow
[`oie-470-isolated-image-smoke.yml`](../../../.github/workflows/oie-470-isolated-image-smoke.yml)
checks out the exact commit and runs the *upstream*
`docker build --target jre-run`, without modifying upstream source
or pushing any image. It separately verifies the built image's
`version = 4.7.0`, non-root user and no mutation to Healthcare/OMOP.
The smoke attempts an isolated HTTPS endpoint startup with
`/run/secrets/mirth_properties` bootstrap configuration and a
random ephemeral password (never printed).

`/opt/engine/appdata` is writable per disposable container; in live
Kubernetes it must map to the dedicated `dw-oie/oie-state` PVC.
OIE's upstream `configure-from-env` edits `/opt/engine/conf/mirth.properties`
at startup. Avoid `readOnlyRootFilesystem` until a compatible config
mount/entrypoint has been proven. A startup probe here does *not*
exercise an imported Channel nor prove FHIR→HL7 transformation.

**Before any registry push/live use:** record the locally tested
Docker image ID, build provenance/base digests, publish a versioned
GHCR image with an immutable registry digest (not `latest`) only
through a separate approved/checked release step, update the K8s
`__OIE_PINNED_IMAGE_DIGEST__` placeholder, and verify the exact image
actually pulled on worker01. No GHCR publication is performed by the smoke.
