# Tasks — Fabric Blob Batch Control MVP

> 2026-11-09 用户决定：一个现有 Credential、同一个 `johnzhang/landing` Container，`_control/v1/` 与 `processed/v1/` 虚拟前缀；原始 `clinical/v1/` 完全不动。设计来源 PR #856；Blob Adapter 源码已由 PR #857 合并。只读云审计已受控执行；真实 Blob 状态写入、Fabric E2E 与生产门禁仍保持待验收。

## 1. Design freeze / session handoff (docs-only)

- [x] 1.1 核查最新 Healthcare/Self-Runner Main、既有 Azure Landing 路径和只读 WorkspaceIdentity、LocalDP PostgreSQL Claim/Lease、Shared Replay/G5/P3.21 的边界。
- [x] 1.2 建立独立 Proposal/Design/Tasks/Spec，冻结“单 Container + 单 Credential + 业务 Batch 处理状态 + 处理完成回执”轻量架构，保留现有 FHIR/HL7 不可变 Manifest。
- [x] 1.3 明确非目标：不创建 `g5-trust-ledger`、新账户、新身份、独立 IAM 层、WORM，不移动或删除 Landing 原始文件，不使用 Delta 存储控制 Ledger，不因检查状态而启动 Fabric；历史 P3.21 只作 offline 证据。
- [x] 1.4 G5 OpenSpec 交叉引用此决策且不关闭 3.19，也不勾选任何 Candidate/Gold、临床 License/F1/F2 真实写入验收。

## 2. Next session — Blob Adapter source & offline CI

- [x] 2.1 从两仓最新 Main、OpenSpec、现有 Blob publisher、现实 landing prefix 与 data-plane 实际权限只读审计入手；选定**一个**已有可用 Azure Blob Credential；不能假设 Fabric Reader Connection 能写。
- [x] 2.2 实现小而单一的 Blob state storage adapter：`_control/v1/...` atomic create, ETag CAS, bounded Lease / owner fencing；`processed/v1/.../receipt.json` conditional create + GET readback；严格写路径 allowlist、禁止 DELETE/COPY/MOVE 原始 `clinical/v1`。
- [x] 2.3 定义版本化、stage-scoped Batch/Receipt JSON 合同：hospital/feed/request/batch/Manifest SHA、processing/Mapper/Wheel version、stage、publication/target proof、claim owner/attempt/ETag、reconciliation；复用 Shared `reconciliation/replay.py`，不重复 Mapper/Replay 决策。
- [x] 2.4 Mock/Azurite CI 覆盖并发一胜、重复 SKIP、错误源 SHA、跨院碰撞、stale lease、lost ACK、stage-approval-only、部分 Fabric 写入、Cursor/ETag race、path traversal 和无 Delete；Python 3.11/3.13。绝不把 mock 视为真实云验收。
- [x] 2.5 审查是否需扩展 Shared Engine 小版本并维护 CODE map；只在真正复用共享逻辑时更新 Shared。不要为了存储适配复制临床 Mapper 或 Pipeline。

## 3. Next session — Controlled Azure acceptance

- [ ] 3.1 单独核实一个 Credential 的 `landing` 实际访问与写权限、当前 Blob metadata/Policy、前缀碰撞与活动 HL7/FHIR Job；权限不满足则 HOLD，报告精确原因，不自行创建 IAM 身份。
- [ ] 3.2 新合成测试批次下执行 Azure conditional create / 412 / ETag / Lease / parallel readback / unknown-ACK（仅受控的已批准执行入口）；保留真实 HTTP/ETag/Request IDs，不写历史已交付对象。
- [ ] 3.3 测试 `processed` 回执与既有 Fabric 物理目标校验对齐；任何目标未知/源 drift/暂时关闭 Capacity 必须安全返回 VERIFY_READONLY/HOLD，绝不虚构 Gold。先验证 Blob-only SKIP 可以避免不必要的 CU。
- [ ] 3.4 文档记录真实 Run、成本计数/请求量、重试与异常恢复结果；依测试结论决定是否发布 Adapter。没有必要重新做 G4 P100/E5918 或 F2 六表此前已验收的实机流程。

## 4. Follow-on integration / hold gates

- [ ] 4.1 经新的独立批准后，在 Self-Runner 受控编排中接入 Blob 控制层，保留 Fabric 原生 Pipeline `HALT` 默认值、审批、G5 Native signed-token 及 F1/F2/License 真门禁。
- [ ] 4.2 真实 Fabric Candidate Delta / Gold Writer E2E 仍属于 `fabric-g5-approved-silver-omop-candidate` 的独立待办，不因本 Change 标 [x]；本 change 完成不构成生产授权。


## 2026-11-09 — Batch Adapter source PR (not cloud acceptance)

- Healthcare branch `feature/fabric-blob-batch-control-adapter-20261109` at exact HEAD to be recorded by PR/CI; source entrypoints `azure-fabric/blob-control/blob_batch_ledger.py`, `azure-fabric/blob-control/azure_blob_backend.py`; tests `.github/quality/tests/azure-fabric/blob-control/`; workflow `fabric-blob-batch-control-offline.yml`; system CODE map `documents/systems/azure-fabric/blob-control/CODE.md`.
- Source implements one-credential client factory, allowlisted conditional create, ETag/Lease fencing, stage/version receipt, independently validated Manifest/Payload hashes and Shared pure `BatchContext/decide_replay`. All operations require a caller: nothing automatically invokes Azure, Fabric, HL7/OIE or existing frozen batches.
- Tasks 2.2–2.5 are **SOURCE/OFFLINE CI PASS only** under Healthcare PR #857, exact pre-documentation source SHA `f196b61d958555f82dd111f73c14ccc3ad8d34ca`. [CI Run #42626249495](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42626249495) passed Python 3.11/3.13 synthetic tests and isolated Azurite Azure SDK create/ETag/Lease/readback. Exact-key API uses no cursor/list pagination; bounded listing is separately assessed in the read-only SR audit. This is not real Azure/clinical acceptance. Source QA and CODE map complete; versioned Shared package unchanged. Task 2.1 read-only scope was subsequently verified by the existing Publisher SP on live Azure via Self-Runner PR #668 / Run #42627618366; actual conditional create/CAS/Lease **write** permissions remain Task 3.1 OPEN, not implicitly granted by read access.
- Tasks 3.x and 4.x remain OPEN. No production signer, P3.19 nonce, Clinical License, Candidate/Gold approval or physical Fabric write is authorized by this PR.

## 2026-11-09 — Task 2.1 genuine Azure READ-only audit evidence

- Healthcare source PR [#857](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/857) merged to Main `b7549034530d2cd7dfefe67a6dded356f8e8a580`; source-only offline CI [Run #42626249495](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42626249495) SUCCESS (Python 3.11/3.13 + isolated Azure SDK Azurite).
- Self-Runner read-only audit PR [#668](https://github.com/JohnZhang-DataForge/Self-Runner/pull/668) merged to Main `4448ad872bd6dbdcaf8fb83272da04a0a2975cff`; real Main-push [Run #42627618366](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/42627618366) **SUCCESS**, artifact `fabric-blob-control-readonly-42627618366` ID `13678843018` (digest `55430552e4a96f026698cdb06b46e4e534162cc828a7f6b743d59ac852c1d35e`).
- Trusted Publisher SP client used the existing `johnzhang/landing` endpoint with no new account, Container, credential or IAM. Source manifest `clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/atlanta-fhir-gh-41539769718/landing-manifest.json` independently read with SHA256 `2f9ef5a555f164464a79a5dc457a6d7f9ef79156edca11b2f1fb49789c785c35`, stable ETag and matching source identity.
- Log: `BLOB_BATCH_CONTROL_READONLY_STATUS=PASS_READONLY_PREFIXES_EMPTY_IN_BOUNDED_SCAN`; neither `_control/v1/` nor `processed/v1/` had objects in the bounded first-page listing at audit time. Azure Blob source/data read and container listing permission **PASS**. No Azure Blob PUT/COPY/DELETE; no Fabric Capacity use.
- **Scope boundary:** read/list success is **not** proof of conditional create, ETag/CAS write privilege, Lease permissions, per-object policy or P3.19 production nonce. Tasks 3.1–3.4 and 4.x remain [ ]. Real synthetic new batch must prove writes and independent Fabric target before creating `processed` completion Receipt; do not replay historical G4/F2 or touch ongoing HL7/OIE writes.
