# Tasks — OIE FHIR→HL7 ADT PoC

> **ACTIVE / PLAN ONLY.** Scope is clinical mapping and isolated OIE runtime.
> No K8s deployment, OIE conversion, Blob or Fabric is accepted by this PR.

## 1. Planning and boundaries
- [x] 1.1 Check real main/source P4.1 boundary, OIE release/license/container provenance and relevant governance; preserve old Local DP/OMOP.
- [x] 1.2 Specify strict Patient/Encounter → ADT^A01 mapping, skip/reject logic, stable IDs and independent parse-back gates.
- [x] 1.3 Specify `dw-oie`, exclusive `worker01` placement, Derby/PVC and cross-namespace handoff design; no shared runtime operation in design PR.
- [x] 1.4 Confirm design PR OpenSpec/Trusted Gate CI and merge into Main.

## 2. Implementation (new bounded PRs after this change is merged)
- [x] 2.1 Implement isolated OIE ADT Channel source mapping and offline positive/negative deterministic tests.
- [ ] 2.2 Build own pinned OIE 4.7.0 container from verified official artifact; CI test image/Java/OIE startup in disposable environment.
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

### P2.2 isolated image build gate candidate (2026-10-24)

- 官方 OIE 4.7.0 tag 已核实解析为 immutable upstream `f9ba73e28de151b041b97e7383e0ab9d2c4f1799`；该 release 不提供已打包的 4.7.0 Docker image。新增只在 GitHub-hosted runner 构建官方源 `jre-run` target、只读版本/用户检查以及临时 loopback HTTPS 启动的 CI；不会写入 GHCR、K8s、Blob、OMOP。
- Task 2.2 **保持 OPEN**，直到该工作流在确切 Head 上构建/启动 PASS，记录测试 image ID、依赖 Digest 并由独立流程发布可部署 registry Digest；只有 workflow 定义不等于已经成功构建。2.4 OIE Channel 真实转换仍 OPEN。
