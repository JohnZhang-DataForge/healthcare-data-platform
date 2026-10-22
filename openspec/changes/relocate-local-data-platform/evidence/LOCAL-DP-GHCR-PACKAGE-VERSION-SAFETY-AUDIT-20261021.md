# Local DP GHCR packages / versions: real inventory and safe-retirement gate — 2026-10-21

> OpenSpec `relocate-local-data-platform`, Task **4.11.6**. **READ-ONLY AUDIT COMPLETED, GHCR PACKAGE/VERSION DELETION = 0, TASK 4.11.6 remains OPEN/HOLD**. This is a safe no-delete decision based on live references, not an assertion that package cleanup succeeded.

## Source, mechanism, and access boundary

- Healthcare Main at audit: `4379bfba19fc64ef0f069464ad6be560d0308073`; Self-Runner Main at audit: `d92f0fac1ded980ab7e68c017fe334a082b2eefa`. No Local DP application source changes were made.
- Temporary Self-Runner [PR #224](https://github.com/JohnZhang-DataForge/Self-Runner/pull/224), final [read-only Run #39710406810](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39710406810), completed `success`; PR **closed unmerged**. Machine-readable retained artifact `local-dp-ghcr-version-audit` contains `ghcr-packages-and-versions.json`, `ghcr-api-status.json`, `static-consumers.json` and `active-k8s-consumers.json`.
- Scoped current two-repo tracked-source audit discovered **609 candidate image/name reference lines**; cluster snapshot **86** Healthcare Pod references (all phases, **not** all actively running), plus **two retained Kubernetes Synthea Jobs** with an explicit historical image Digest.
- GitHub `GITHUB_TOKEN` with `packages: read` can **read individual organization package and version records**. Whole-organization `GET /orgs/JohnZhang-DataForge/packages?package_type=container` returned HTTP **400 Invalid argument**, while direct `GET /orgs/.../packages/container/<name>` and `.../versions` returned success. We therefore enumerate from **the eight canonical current image names plus current checked-in cross-repo references**, not from a verified complete org registry list. All **12** expected current/legacy Healthcare package names found; **do not claim no other packages exist**.
- No `DELETE` HTTP calls, no changes to GHCR tags, S3/PG, Airflow, Kubernetes, Docker node caches, Azure/Fabric, or any live pipeline.

## Exact GHCR inventory — 12 packages / 207 version records

| Package | Version count | Classification | Evidence / decision |
| --- | ---: | --- | --- |
| `healthcare-data-platform-synthea` | 12 | ACTIVE — KEEP | Current 8-image publisher, Synthea parent; two old Kubernetes Jobs explicitly pin `sha256:2dc1e4283eb194e548b245842987ff403bf8e092a70f473fdf6fa5a1c547816d` (tag `git-9a0c3ad195ee657e485f5391e2a417870f441797`) |
| `healthcare-data-platform-task004-runtime` | 51 | ACTIVE — KEEP | Current Landing Processing parent; includes older tagged and untagged OCI manifest versions |
| `healthcare-data-platform-task004-cdm-runtime` | 21 | ACTIVE — KEEP | Current OMOP Writer parent; legacy CDM publishing Workflows / feature branches remain E/HOLD |
| `healthcare-landing-discovery` | 51 | ACTIVE — KEEP | Production Discovery DAG latest/Always; new Pod exact digest already verified |
| `healthcare-landing-claim` | 18 | ACTIVE — KEEP | Production Claim DAG latest/Always; 25→100 preview bugfix image published |
| `healthcare-data-platform-local-dp-synthea-new-only` | 8 | ACTIVE — KEEP | Generator runtime with merged-Main E2E |
| `healthcare-data-platform-local-dp-landing-processing-v2` | 8 | ACTIVE — KEEP | Current Spark Processing child |
| `healthcare-data-platform-local-dp-omop-writer` | 8 | ACTIVE — KEEP | Current atomic OMOP Writer child |
| `healthcare-data-platform-new-only-omop-writer` | 18 | LEGACY — **HOLD** | Main `.github/workflows/build-new-only-omop-writer.yml` still has an explicit `git-${{ github.sha }}` GHCR publish target; Self-Runner `task004-new-only-airflow-writer-gate.yml` pins legacy `sha256:dd0b0483ec01b05f1d072d65c9ab728b563cb063da0705564f3a03e23160fd6c` |
| `healthcare-landing-discovery-v2` | 3 | LEGACY — **HOLD** | Self-Runner `landing-airflow-v2-reader-build.yml` pins tag `1d1bc862e211d9ce39c26996415ff0fcf6ee5e17` and verifies Digest |
| `healthcare-landing-processing-v2` | 4 | LEGACY — **HOLD** | Self-Runner `landing-processing-v2-source-acceptance.yml` pins tag `72be44be9304c7549030951f5d25864075fed5cc`; `task004-newonly-airflow-spark-handoff.yml` pins its Digest `sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937` |
| `healthcare-synthea-new-only` | 5 | LEGACY — **HOLD** | Several still-tracked Self-Runner workflows pin its five historical tags and/or Digests, including `new-only-v2-real-image-generate.yml`, `new-only-v2-real-publish.yml`, `synthea-new-only-digest-runtime.yml`, `synthea-new-only-digest-ready-recovery.yml` |

**Totals:** 8 current packages **177** version records; 4 legacy candidates **30** version records; **207** scoped version records. These are GitHub Package Version objects, **not** a measurement of unique underlying Docker image layers or disk bytes.

## Explicit no-delete decision

- **Whole-package DELETE allowlist: empty (0).** All four historical package names have tracked Workflow consumers; the eight current packages are actively built and have runtime/parent dependencies. A workflow referenced in Main cannot be treated as decommissioned only because its name says `v2`, `task004` or `legacy`.
- **Version DELETE allowlist: empty (0).** Many existing tagged Digests support verified historic E2E, rollbacks or frozen acceptance workflows. Numerous untagged package version entries may be OCI child manifests/layers of retained tagged multiarch manifests; an untagged entry is *not* proof of orphan status. The audit has not closed every parent manifest dependency or old feature-branch/manual rollback consumer. No deletion should be authorized from age or tag absence alone.
- The pinned Job `task004-syn-pub-task004-airflow-task004-step03e-1ebef5e264` and Job `task004-syn-pub-task004-airflow-task004-step03e-f9c5cceee8` in `dw-synthea` still reference the historical Synthea Digest above. They are historical Job resources, not proof of an active producer, but they **are real retained image references**.
- Historical classification [three CDM GHCR Workflows](LOCAL-DP-LEGACY-CDM-GHCR-WORKFLOW-CLASSIFICATION-20261020.md) is still **E/HOLD** because corresponding feature branches and recovery consumers were not exhaustively retired; do not change this classification without a separate validated cleanup decision.

## Next bounded gates (not part of this completed read-only check)

1. Before future GHCR cleanup, first retire or migrate the exact remaining *historical* Self-Runner / Healthcare publisher, reader and recovery Workflow references under reviewed changes, or explicitly designate required recovery snapshots to retain. Recheck old feature branches, Job refs, DAG/K8s runtime and Writer fencing/rollback requirements.
2. For each proposed **version ID**, validate exact Git SHA tag, immutable Digest, OCI parent/child index, all refs in both repos and live cluster including runtime and stable recovery, then build a strict `DELETE` allowlist and keep at least a proven functional current+rollback image lineage.
3. Requery package/version IDs immediately before any actual delete; require authenticated package admin access plus separate pre/post version readback. The current read-only job does not use admin/write credentials and cannot be evidence of delete authorization.
4. Keep Task **4.11.6 [ ] HOLD** and Task 5 Archive [ ] OPEN until these conditions are satisfied. The **source-file cleanup 4.9/4.10 and Discovery restoration are fully DONE and unaffected by this registry retention decision**.
