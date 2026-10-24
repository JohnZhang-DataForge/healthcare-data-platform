# Tasks — OIE FHIR→HL7 ADT PoC

> **ACTIVE / DEBUG OIE 4.7.0 RUNTIME VERIFIED.** Strict mapping offline tests and nonpersistent `dw-oie/worker01` OIE engine installation have passed. **OIE Channel FHIR→HL7, Azure Blob, Fabric, and persistent PVC remain NOT VERIFIED.**

## 1. Planning and boundaries
- [x] 1.1 Check real main/source P4.1 boundary, OIE release/license/container provenance and relevant governance; preserve old Local DP/OMOP.
- [x] 1.2 Specify strict Patient/Encounter → ADT^A01 mapping, skip/reject logic, stable IDs and independent parse-back gates.
- [x] 1.3 Specify `dw-oie`, exclusive `worker01` placement, Derby/PVC and cross-namespace handoff design; no shared runtime operation in design PR.
- [x] 1.4 Confirm design PR OpenSpec/Trusted Gate CI and merge into Main.

## 2. Implementation (new bounded PRs after this change is merged)
- [x] 2.1 Implement isolated OIE ADT Channel source mapping and offline positive/negative deterministic tests.
- [x] 2.2 Build own pinned OIE 4.7.0 container from verified official artifact; CI test image/Java/OIE startup in disposable environment.
- [x] 2.3 Add `dw-oie` namespace, single worker01-pinned OIE workload, isolated PVC, ClusterIP and minimal Secret/permissions templates; only static validation until authorized.
- [ ] 2.4 Run real OIE 4.7.0 conversion on actual Johns Creek Synthea FHIR Bundle, independently HL7 v2.5.1 parse/readback; record skips, rejects, retries and exact SHA/Digest/Run.
- [ ] 2.5 With separate user approval and session coordination, validate live `dw-oie` placement/PVC and isolated OIE Channel; preserve durable state and inspect other live work before write.

## 3. Follow-on boundaries
- [ ] 3.1 Document actual OIE runtime evidence in this Change and link handoff contract; do not mark Azure Blob publication done.
- [ ] 3.2 Hand off shared immutable Azure Publisher and Atlanta/Johns Creek publishing to a separate Change; only archive after all OIE scope evidence is verified.

**Execution rule:** each implementation PR must include `OpenSpec-Change:
implement-oie-fhir-to-hl7-adt-poc` and an actual `OpenSpec-Task: N.N`,
with `tasks.md` updated in the same PR. Shared K8s remains HOLD without
separate coordinated runtime authorization.

### P2.1 Offline mapping implementation (2026-10-24)

- `apps/clinical_producers/oie/adt_a01.js`: OIE-compatible ES5 candidate mapping function, actual HL7 2.5.1 MSH/EVN/PID/PV1 field construction, deterministic MSH-10, explicit non-admission skip / malformed candidate reject.
- `tests/clinical_producers/test_oie_adt_a01.js`: Node offline positive/negative and no-Node-global VM smoke, tested by isolated GitHub-hosted CI. `MAPPING_VERIFIED_ONLY` is not OIE engine conversion; 2.2–2.5 remain OPEN.
- Planning PR #427 merged as Healthcare Main `9d818c3fae27a828b72bdad5392407bdbca04a8d`; for this implementation the exact CI/head and merge evidence must be independently confirmed.

### P2.3 worker01 manifests — static only (2026-10-24)

- `local-data-platform/kubernetes/manifests/oie/`: proposed `dw-oie`, dedicated templated RWO PVC, one-replica StatefulSet **pinned to worker01**, and internal-only Service. OIE 4.7.0 secret config via `/run/secrets/mirth_properties` verified against real upstream source. Image Registry Digest and StorageClass are **required unresolved placeholders**, not unsafe defaults.
- No namespace, PVC, pod, admin password, Service or other cluster resource has been created. Template-only CI tests are static, not OIE startup/runtime acceptance. Task 2.5 and Blob publisher remain OPEN.

### P2.3 pre-runtime file permission hardening (2026-10-24)

- Upstream `USER engine` is a named Linux account, so Kubernetes `runAsNonRoot` requires a numeric `runAsUser` known from the **actual image**. Static template updated with mandatory UID/GID placeholders; Secret `0440` and matching `fsGroup` prevents root-only initial bootstrap file from causing an unreadable configuration at startup. Still **no live K8s operations** and no claim of verified UID/GID.

## 2.6 — Disposable first-install before durable storage (user-directed, 2026-10-24)
- [x] 2.6.1 Add worker01-only OIE debug Deployment + ClusterIP service templates with ephemeral `emptyDir`, separate Secret and no PVC/StatefulSet creation; static CI and component map.
- [x] 2.6.2 After exact image verification/publishing and coordination, install a **disposable** OIE in `dw-oie` for real startup/Channel E2E. Record runtime evidence. Do not create PVC or move local data.
- [x] 2.6.3 User provisioned dedicated worker01 local-path host directory and accepted single PVC appdata binding before OIE clinical Channel validation. Evidence in 2.7; future StatefulSet migration is not required for this bounded stage.

The previously authored durable manifests remain **later-phase source definitions only**; do not apply them during initial debugging. This scope change explicitly supersedes any earlier advice to create `oie-state` PVC before first debug install.

### P2.2 isolated image build gate candidate (2026-10-24)

- 官方 OIE 4.7.0 tag 已核实解析为 immutable upstream `f9ba73e28de151b041b97e7383e0ab9d2c4f1799`；该 release 不提供已打包的 4.7.0 Docker image。新增只在 GitHub-hosted runner 构建官方源 `jre-run` target、只读版本/用户检查以及临时 loopback HTTPS 启动的 CI；不会写入 GHCR、K8s、Blob、OMOP。
- Task 2.2 **保持 OPEN**，直到该工作流在确切 Head 上构建/启动 PASS，记录测试 image ID、依赖 Digest 并由独立流程发布可部署 registry Digest；只有 workflow 定义不等于已经成功构建。2.4 OIE Channel 真实转换仍 OPEN。

### GHCR immutable OIE 4.7.0 publication gate (2026-10-24)

- 添加仅 Main 触发的独立 SHA 标签 GHCR Release Workflow，锁定官方 OIE 4.7.0 源码 Commit，必须通过临时 Docker HTTPS 启动测试才能推送镜像；输出 registry Digest 与实际非 root UID/GID，不覆盖 `latest`。
- **仅此代码 PR 不等于 Publish**：2.2 保持 OPEN，直到 Main 后发布 Run 实际 PASS、Registry Digest 独立核对。任何在 `dw-oie` 创建 K8s 资源仍需额外资源检查与协调。

### P2.2 + P2.6.2 — Verified immutable image + worker01 disposable installation (2026-10-24)

- Healthcare exact upstream OIE `v4.7.0` commit `f9ba73e28de151b041b97e7383e0ab9d2c4f1799`, source image build and isolated HTTPS startup: [Healthcare Run #40118903350](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40118903350) PASS. Fixed Build PR [#430](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/430) merged Main `cfc600846278aee98b1d29c5c585c924e514cc2f`.
- Real GHCR release [Healthcare Run #40119734447](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40119734447) PASS, release Main `bcb18bc93e0372e4e78aa373c83768a143ab4b0d`, immutable `ghcr.io/johnzhang-dataforge/healthcare-oie@sha256:6716fb6210f9dc029c801b13cc152ff3fcb1ad4df05c1dbe5a9d438a482ba84b`, UID 100 / GID 65533. No `latest` promotion.
- Independent real [Self-Runner read-only preflight #40119650504](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40119650504) PASS: `worker01` Ready/unpressured, `dw-oie` absent, active K8s Jobs=0, runner namespace-create RBAC yes. Earlier [#40119576058](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40119576058) failed ONLY because an absent namespace `--ignore-not-found -o json` yielded empty stdout, subsequently fixed.
- **REAL OIE K8s INSTALL PASS**: [Self-Runner Run #40120249619](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120249619), final Self-Runner [PR #248](https://github.com/JohnZhang-DataForge/Self-Runner/pull/248) Main `7f06aed022c91db2dac2535d1b5fc7d0b6db42a5`. New `dw-oie`; Deployment `oie-debug`, Pod `oie-debug-f8f5d9c89-44vd2` on **worker01**, ClusterIP, OIE 4.7.0 and Derby existence/Ready PASS. **`emptyDir` only; 0 PVC in `dw-oie`; PV/PVC/StorageClass mutation NO**. Temporary Secret used for initial admin password, not logged.
- **HISTORIC 2026-10-24 INITIAL DEBUG BOUNDARY (superseded by 2.7 live PVC verification):** at initial installation, user storage was not yet configured and the OIE Deployment was emptyDir; see subsequent 2.7 for actual persisted state. OIE Channel actual clinical conversion remains task 2.4 OPEN; durable 2.5/2.6.3 remain OPEN. Never treat OIE startup as Patient/Encounter→ADT runtime validation.

## 2.7 — worker01 local-path OIE persistent appdata (user authorized, 2026-10-24)
- [x] 2.7.1 Read-only check of user-created `storageClassConfigs.oie` under `local-path-config`, exact `worker01:/data/oie`, no other worker paths, provisioner hot-reload already Applied, currently no SC/PVC; [Self-Runner #40121142405](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121142405) PASS. **No provisioner restart required**.
- [x] 2.7.2 Add `oie` Retain/WaitForFirstConsumer StorageClass and `dw-oie/oie-state` 10Gi RWO PVC manifests, component CODE map, OpenSpec, static CI. Documentation and code definitions are NOT actual storage acceptance.
- [x] 2.7.3 After fresh shared resource/parallel-session gate, create only `oie` SC/PVC, patch existing worker01 `oie-debug` appdata volume to PVC, independently validate PV/PVC Bound on /data/oie, Retain, OIE Derby restart, node/image/service, and absence of other mutation. Do not restart local-path provisioner or create second disk directory.
- [x] 2.7.4 Update actual rollout Run/PR/Main evidence and only then close durable acceptance. OIE Channel HL7 conversion and Blob publication still open.

### 2.7.3–2.7.4 — Real single PVC and restart/readback evidence (2026-10-24)

- **SC/PVC LIVE PASS**: [Self-Runner #40121734522](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121734522), [PR #251](https://github.com/JohnZhang-DataForge/Self-Runner/pull/251), merged Self-Runner SHA `56f7145a8a3ca3df9a10fe1071594b3abbc496e5`. Fresh preflight verified `worker01:/data/oie`, provisioner config hot-reloaded, no other active K8s Jobs, no preexisting OIE PVC. Created only dedicated `oie` StorageClass (`Retain`/`WaitForFirstConsumer`) and `dw-oie/oie-state` PVC (10Gi/RWO), patched existing one-replica `oie-debug` appdata volume, no other Namespace, SC, PVC or local-path mutation. PV `pvc-8ca5e84e-d58a-4448-9059-47473023f036` Bound, host path `/data/oie/pvc-8ca5e84e-d58a-4448-9059-47473023f036_dw-oie_oie-state`, ReclaimPolicy=Retain, worker01 pinned, same OIE 4.7.0 image, Pod Ready and Derby directory writable. Initial run [#40121683706](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121683706) failed **prior to any write**, due to overstrict escaping match in provisioner log; fixed without bypassing ConfigMap/namespace safety check.
- **PERSISTENCE RESTART E2E PASS**: [Self-Runner #40122005828](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40122005828), [PR #252](https://github.com/JohnZhang-DataForge/Self-Runner/pull/252), merged Self-Runner SHA `283f19fd542d280f945a6f0b670ba64d59735202`. Rechecked PV/claim ownership and active jobs, wrote unique proof marker in mounted `/opt/engine/appdata`, restarted ONLY `dw-oie/deployment/oie-debug` once (strategy Recreate), confirmed new Pod `oie-debug-5dbf74d9cf-vgjkd` Ready on worker01, same PVC and pinned image, **marker bytes survived Pod recreation** and embedded Derby directory present; deleted only its own proof marker. No local-path restart; PVC/PV retained.
- **No need to create a second storage path for current MVP**: one PVC owns OIE embedded Derby DB, generated keystore, server ID and runtime appdata; separate Secret/image configuration remains external to PVC. Later independent local HL7 file spool only if architecture changes. **OIE Channel FHIR→ADT^A01 true conversion remains task 2.4 OPEN**, as do downstream Azure Blob publication and Fabric consumption. Do not archive this Change on the basis of storage success alone.


### OIE 2.4 Channel import preparation (2026-10-24)
- [x] 2.4.1 Fetch exact official upstream OIE v4.7.0 Channel Reader test fixture; render versioned Johns Creek OIE Channel XML using existing `adt_a01.js` in preprocessor. `fhir_events.py` splits read-only verified source FHIR by Encounter without clinical mapping. Add channel XML/offline behavior tests and canonical source map.
- [ ] 2.4.2 Import into actual persistent `dw-oie` only under separately coordinated workflow and ensure channel ID does not conflict; verify source/target connector runtime using OIE v4.7.0 API and independent message readback.
- [ ] 2.4.3 Submit **actual** Johns Creek Generator FHIR inputs into live Channel; independently parse ADT^A01 output, ensure non-IMP skipped, malformed candidates fail and retries stable. Never claim Azure Blob success.


### 2.4.2 — OIE import HTTP 500 isolation (2026-10-24)
- Live attempt [Self-Runner #40124412640](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40124412640) passed auth, worker01 PVC and Channel render but **FAILED** at first `POST /api/channels/` (HTTP 500). Do not replay until cause identified and channel existence checked; no Blob processing occurred.
- Read-only [#40124515326](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40124515326) found OIE Ready, Derby Bound, no Pod restart; server error `InaccessibleObjectException` while serializing an internal SQLException, which hides the underlying import cause.
- Add GitHub-hosted **throwaway OIE 4.7.0 Derby container** with diagnostic `--add-opens=java.sql/java.sql=ALL-UNNAMED` solely for this test, reusing same canonical Channel render; no shared cluster/real PVC/Blob mutations. Need distinguish this temporary CI diagnosis from accepting a live Channel.


### Confirmed original OIE Channel 500 root cause (2026-10-24)
- [GitHub-hosted isolated OIE import diagnostic](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40124952205) with temporary `VMOPTIONS=--add-opens=java.sql/java.sql=ALL-UNNAMED` unmasked Derby `SQLDataException`: inserting Channel name `Healthcare Johns Creek FHIR to HL7 ADT PoC` exceeded `CHANNEL.NAME VARCHAR(40)`. **This is not an OIE database/PVC corruption or a broken engine image.** Live Channel was not verified imported.
- Change canonical Channel name to `Johns Creek FHIR to HL7 ADT` (<=40 characters), preserve fixed Channel ID and mappings, rerun isolated import; only if success, update controlled Self-Runner live workflow expectation and recheck channel list before a new POST. No shared Derby/PG migration.


### 2.4.3 — Independent HL7 v2.5.1 server-message readback contract (2026-10-24)
- **Offline implementation complete:** Add `hl7_readback.py` strict MSH/EVN/PID/PV1 decoder + source identity/time/control ID correlation to verified Johns Creek Patient+Encounter envelope and negative tests. Designed to validate **actual OIE returned bytes** independently of JavaScript mapper; this unit gate is NOT live OIE conversion.
- **Live readback remains pending:** Supply actual OIE message processed content after one-channel guarded import, assert 1 IMP A01 / 30 AMB never A01, retry stability, no Blob writes; retain failure records.
