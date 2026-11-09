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
