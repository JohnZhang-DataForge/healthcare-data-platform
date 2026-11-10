# Design — single-container Blob Batch Control / Processed receipts (MVP)

## 决策与唯一边界

**已接受**：existing `johnzhang/landing` + one existing authorized Azure credential + two new virtual prefixes. 禁止新 `g5-trust-ledger` Container；禁止因这个 MVP 增加新的 Azure Storage Account、Identity、WORM 或 Fabric Capacity。一个 Credential 暂时贯穿本 MVP 的允许 Blob 操作；这个业务便利不意味着跳过真实性、哈希、身份和单次执行检查。不扩大原只读 Fabric WorkspaceIdentity Connection 的角色来碰运气：先只读确认现有 Blob Publisher/SP data-plane 权限是否足够；不足时保持 HOLD 并最小化单次授权请求。

```text
existing johnzhang / landing  (ONE container)
  clinical/v1/<hospital>/<feed>/<request>/<FHIR_R4|HL7_V2>/...
       data objects + delivery manifest LAST   [EXISTING, IMMUTABLE, NO MOVE]
  _control/v1/<hospital>/<feed>/<request>/<stage>/claim.json
       mutable owner / lease / attempt / observed ETag [NEW; tiny JSON]
  processed/v1/<hospital>/<feed>/<request>/<stage>/<version>/receipt.json
       immutable verified completion receipt           [NEW; tiny JSON]

Runner / one approved Blob credential → HEAD/GET control/processed
  → if verified terminal outcome, SKIP without Fabric CU
  → if new, atomic Claim + verify fixed landing Manifest SHA
  → start Fabric only when required; source adapter → Canonical → Shared
  → verify actual corresponding G4 Silver / Candidate / Gold output
  → receipt LAST only for the stage independently proved
  → release Claim; replay remains safe; unknown ACK → VERIFY_READONLY/HOLD
```

These are Blob **name prefixes**, not Azure filesystem directories or new containers. `<hospital>/<feed>/<request>/<stage>/<version>` MUST use existing canonical, safe identity rules and stable digest pins; never incorporate PHI or arbitrary URL/path segments. Stage is explicit: `SILVER_APPROVED`, `CANDIDATE_APPROVED`, or `GOLD_COMMITTED`; a Silver receipt is **not** Gold. Writer/Mapping/Profile/Manifest/processing-version drift must not reuse prior completion.

## 状态协议与原子性

1. **Discover**: only existing publisher's fully committed immutable delivery manifest (manifest LAST) may yield a Batch. Independently validate request/hospital/feed/format, ETag, full-content SHA and required payload inventory. Do not ingest half-uploaded source files.
2. **Precheck**: HEAD/GET the exact `processed` stage/version key; if receipt exists, validate its canonical bytes, exact source Manifest SHA, processing/Mapping/Wheel version, stage, target publication/approval ID, timestamp and prior independent readback evidence. A valid prior receipt can avoid Fabric start for a matching *already verified and immutable* release. Unknown/unverifiable/drift → HOLD or restore actual Fabric readback, **not blind SKIP**.
3. **Claim**: `_control` conditional `If-None-Match: *` for first registration; ETag `If-Match` and short renewable Azure Blob Lease (where needed) for controlled state transitions, attempt owner fencing and concurrent run exclusion. Claim is scoped to the single stage and release identity. On collision, GET and validate exact identity/status; mismatched Manifest/Owner/Stage → HOLD, not overwrite. A stale worker must not create a completion receipt after losing its Claim; validate current lease/ETag immediately before receipt publication.
4. **Run**: only approved Fabric Notebook/Pipeline path, `run_mode=HALT` until separately authorized. Existing Silver, Candidate, F2 identity and Gold gates remain authoritative. A Blob Claim is **not** clinical/License signoff, production signature or writer token. It cannot authorize Gold or ID allocation.
5. **Finalize**: independently reopen real target Delta/Warehouse and verify release/approval/fingerprint/counts; then write only that stage's `processed` JSON receipt with conditional create and independent GET byte/hash readback. Never modify historical receipt. Mark control terminal only after consistent receipt & target proof. If receipt PUT ACK unknown, GET canonical bytes + verifiable target evidence; until reconciled return `VERIFY_READONLY`/HOLD. Never assert cross-system atomicity.
6. **Replay**: shared pure Replay engine owns `NEW`, `SKIP`, `HOLD_CONFLICT`, `HOLD_VERSION`, `VERIFY_READONLY`. Blob Adapter supplies stable records; does not duplicate Shared business logic. Genuine retry after failed/expired Claim requires explicit reconciliation and fresh bounded owner/attempt; no automatic lease-stealing. Original Landing paths remain immutable, even when processed.

## 单 Credential、权限与成本

- **明确用户决定**：MVP 可先使用一个受信任的现有 Azure Blob Credential 处理全部允许动作，不建立独立权限隔离、第二 Runner identity、第二 Storage Account/Container、Blob WORM。该 Credential 的当前 Azure data-plane READ/CREATE/CONDITIONAL UPDATE/LEASE 权限必须真实验证；若缺少权限，只报告实际缺口，不能通过禁用检查或更改已有 Reader Connection 来绕过。
- **代码最小保护**：Adapter 拒绝输入中非 `_control/v1/` 与 `processed/v1/` 的任何写目标；原生 Publisher 仍是原始 `clinical/v1/` 写入唯一 owner。绝对禁止 Control Adapter 对 `clinical/v1/` 执行 PUT/DELETE/COPY/MOVE/RENAME；所有接口禁止 wildcard prefix 删除、Clear、全容器覆盖。即便单凭据潜在具备更广泛权限，也不主动使用它。
- **费用优先**：Blob tiny JSON objects/requests 不需要 Fabric CU；仅实际有新业务时启用 Fabric。请求成本与每个 Batch 复杂度成正比；不引入后台扫描高频请求或额外 OneLake Delta Ledger 副本。真实费用以后由单独预算/账单观察证明，不能声称绝对零成本。

## Legacy P3.21 与新路线关系

此前 [Self-Runner PR #658](https://github.com/JohnZhang-DataForge/Self-Runner/pull/658) 的源级 `fabric_g5_blob_nonce_claim_contract.py` 提议了 `johnzhang/g5-trust-ledger`，仅通过 offline/mock CI；该专用 Container **没有创建，也不再是当前决策**。它的 signed-token nonce 保护仅是未来可选的授权防重放机制；不得因为这份旧合约而自动部署 `g5-trust-ledger`。此次方案处理的是**业务 Batch Replay/Claim**，不等同于一次性生产签名 nonce 的实际持久验证；G5 P3.19 人工审批、生产 signer/Native trust、交易时 F2 和真实 Gold 均维持原 HOLD。

## E2E 测试边界与协调

- 先在 Self-Runner 只读核查最新 Main、工作流、权限、Azure 既有 `landing` 实物前缀与当前运行的 G5/HL7，防止并行 PR 冲突。
- 离线 mock + Azurite（如可用）覆盖新/重复/并发/失效 Lease、ETag race、Manifest drift、hash mismatch、unknown ACK、跨院前缀、阶段回执乱序、错误 Credential、旧版本重跑。
- 单独授权仅对 **全新测试 Batch** 的一次真实 Azure conditional PUT/GET 和 ETag/Lease 读回；测试路径确定、无患者数据、无复制/移动/清理历史原件；使用唯一 Run ID、保留可审计回执。
- 接入实际 G5 执行之前仍保留原 G4/P3/F1/F2 完整门禁，不重复过往验收，不擅自启用候选写入。
- 每次实验后须记录准确 Git SHA、Azure Request IDs（非凭据）、source/target SHA、实际状态、CI/Job Run、Unknown ACK 结论。失败不得假定已完成。

## 2026-11-09 — Restricted historical G4 Silver completion registration (accepted)

A single **previously physically approved** historical G4 `SILVER_APPROVED` Stage is the sole reviewed exception to the initial “new synthetic test Batch only” completion acceptance approach: `atlanta-hospital-a/atlanta-hospital-a-fhir-r4/atlanta-fhir-gh-41552666929` with the original Shared Batch ID and distinct delivered vs upstream Manifest SHA pins. The stage was already physically complete in OneLake before Blob Batch Control existed.

For this **one pin-exact case only**, an independent real Delta Parquet/commit/approval readback is required **before** a new control Claim is registered. This new Claim represents the current bounded recovery/control registration attempt, **not a fabricated historical execution Claim**. Reuse normal conditional Claim create, renewable short Lease, ETag CAS, exact Landing Source check, fresh trusted PhysicalTargetReader, immutable `VERIFIED` Receipt create, independent GET and terminal Claim transition. Only after those succeed can a separate Blob-only worker with **no Fabric OIDC or Capacity access** return `SKIP` for the same Scope. Unknown ACK requires GET and valid same-owner Lease/physical revalidation, never blind overwrite or auto lease stealing.

This is a stage-specific state reconciliation, **never a retroactive Silver Writer**, and is not generalized to arbitrary old batches or Stage approvals. The existing source files were not touched. Evidence: Self-Runner Runs [#42707893782](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42707893782) and [#42708750893](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42708750893); full Artifact SHA, request budget and negative checks in `tasks.md`. G5 Candidate/Gold, P1/F1/F2/License/Native signature and formal 4.1 automatic orchestration remain separately gated, with default HALT unchanged. Source-modeled Blob requests are **not** actual Azure billed charges.

## Task 4.1 step A — pre-capacity decision (bounded, accepted 2026-11-09)

The Self-Runner orchestration entrypoint is deliberately split from execution. Before any Fabric API, OIDC exchange, Capacity or Writer is available, a **Blob-only** worker can run one `StageScope` through the existing Healthcare Ledger `precheck()` and Shared Replay. A matching `VERIFIED` Receipt, terminal `COMPLETED` Claim and unchanged original Manifest means **`SKIP`** for **that exact Stage/Release only**. The standalone worker terminates without Fabric. Every other status, including `NEW`, returns HALT; a new Batch is NOT granted permission to start compute or write merely by an absent Receipt. The read-only adapter is intentionally incapable of `create`, `cas_control`, `acquire_lease`, `renew_lease`, `release_lease`, `delete` or `move`.

For the first actual bounded one-shot, G4 `SILVER_APPROVED` is pinned to the already accepted original Shared Batch, Publication, delivered Manifest ETag, Release/Stage scope digest and exact immutable Receipt SHA. The runner uses only the existing Publisher SP for GET/HEAD; its job has no Fabric OIDC permission. [Real Self-Runner Run #42715771329](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42715771329) verified `SKIP` while the Capacity and writer paths remained untouched. This is the **read-only front half of Task 4.1**, not a production dispatcher.

The missing **Task 4.1 step B** is a distinct approved **new-Batch** execution controller: authenticate all independent clinical/License/F1/F2/Native proof gates, preserve Notebook/Pipeline default HALT, then use a controlled Claim/Lease and accepted existing writer (not a replacement Mapper) with target-specific physical readback and immutable Receipt finalization. A status of `NEW` is not such a token; unsigned metadata or mocked approvals may never bridge this missing boundary. Until separate authorization and real acceptance of that execution controller, **Task 4.1 remains OPEN** and Candidate/Gold/4.2 remain HOLD.


## Task 4.1 step B1 — source ready is not execution ready

A new Stage is reviewed by `precheck()`: `SKIP` stays a zero-CU terminal decision, conflicted/unknown `BUSY`, `VERIFY_READONLY`, `HOLD_*` all HALT. For `NEW` on an explicitly non-historical StageScope, a separate **read-only** inspector verifies the already-frozen source with the **single Healthcare `verify_source`** (Manifest LAST + exact SHA/ETag and full payload inventory, scope and sizes) and re-reads `precheck()` to detect races. It validates actual pinned Git Pipeline JSON with the same `safe_readonly_pipeline` used by prior Fabric preflights. No source format-specific duplicate Parser/Mapper or second Replay protocol is introduced.

Even on successful source verification the result is `HOLD_SOURCE_VERIFIED_G5_INDEPENDENT_APPROVAL_REQUIRED`, not a runnable job request. Authority must be independently produced by separate trusted signed-review, F1/F2, Native transport and per-stage physical target owners; existing shared provenance-only attestation does **not** grant writer capability. The future approved owner must use the ordinary conditional first-Claim/Lease/CAS on the exact same Stage/Manifest/Version before requesting compute, and independent physical target readback before Receipt-last. No automatic retries or lease stealing, no production auto-dispatch, no new Azure account/container/identity.

Step B1 [Self-Runner Run #42730498091](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42730498091) is SOURCE/OFFLINE only, including a real *Git* Pipeline configuration read (not Fabric cloud deployment readback). Claims, Capacity, signed approvals and writers are still not authorized. Task 4.1 is OPEN.
