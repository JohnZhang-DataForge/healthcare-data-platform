# Tasks — Multi-Hospital Azure Blob Landing Publisher

> ACTIVE PLANNING. 本 Change 只有设计与运行边界获得审查，并不表示 Azure Blob Publishing 已执行；初始权限、Azure 容器名称/Endpoint、OIE scoped account 及 Shared Runtime 授权仍需按实际检查。

## 1. Planning / Contract
- [x] 1.1 从 P4.1 Source Handoff 与 OIE worker01 Live E2E 的证据定义两条医院路线、公共 Publisher、immutable commit/读回、安全身份与 K8s namespace 边界。
- [ ] 1.2 运行 OpenSpec/Trusted Gate，通过规划 PR 合并 Main；确认实际 Azure Account URL、Landing Container、Provider Scope 和 Secret 来源（不得将其写到 Git）。
- [x] 1.3 细化标准 Publisher input JSON Schema、Blob path 安全与源字节校验、严格负向条件，离线 Contract Tests；`receipt` / 远端 idempotency 细节在 2.1–2.2 实现。

## 2. Shared Publisher
- [x] 2.1 在 Healthcare `local-data-platform/apps/clinical_producers/` 实现医院无关 Azure Blob immutable Publisher（SDK 锁定版本、条件创建、已存在读回对比、拒绝覆盖、最终 Manifest commit）。
- [x] 2.2 增加 Mock/Azurite 单元/集成与 Fault Injection：SHA tamper、已存在不同内容、权限失败、部分写入重入、Manifest-only success 禁止、secret redaction。
- [x] 2.3 建立 Generator verified handoff 到 Publisher 交付输入适配，任何医院/格式由 Profile 选择，禁止耦合 Generator 核心源码。

## 3. Hospital Routes
- [ ] 3.1 Atlanta：源 FHIR R4 → verified handoff → Blob Publisher，验证 Byte-for-byte/FHIR manifest 后可提交。
- [ ] 3.2 Johns Creek：新 FHIR Source Request → real OIE Channel → independent HL7 ADT A01 readback → Blob Publisher；非住院事件显式跳过，不制造 A01。
- [ ] 3.3 两路线的 request_id、医院和 destination prefix 分离与幂等测试；不得使用已验收 OIE 32 条消息的旧源请求重放。

## 4. Guarded Live and Documentation
- [x] 4.4 创建独立 `dw-az-blob` Namespace 的静态 Kubernetes YAML/边界文档/离线门禁，显式阻止跨 Namespace 挂载现有 Generator PVC；**仅代码级别完成**，真实 `kubectl` Create/Readback 及 Writer 工作负载不在此勾选范围。
- [ ] 4.1 只读检查 Azure Account/Container/RBAC/网络、两仓 Main/并行任务、worker01/PVC/OIE，批准范围后才允许 Self-Runner 的真实外部写入。
- [ ] 4.2 新合成源请求 K8s→Azure Landing 全流程 E2E：两医院独立证据、每对象 SHA/ETag/GET、最终 Manifest GET 和相同请求 retry 一致性；保留失败无覆盖。
- [ ] 4.3 同步真实 PR/Run/Blob object receipt、相关 CODE.md，明确 Fabric/OMOP 不在本 Change；再判断 archive。

### P1.3 — 实际初始 Blob 发布计划输入合同
- `blob_publish_contract.py` 仅接受冻结 Hospital/Feed/Request 与 `SOURCE_HANDOFF_VERIFIED` FHIR、`OIE_HL7_READBACK_VERIFIED` HL7；不可变对象逻辑以实际源 bytes / SHA256、严格相对路径与事件 Control ID 为起点；禁止含未声明源 bytes、跨医院前缀及模板路径穿越。
- 本轮新增标准 input Schema 和离线单测；**尚无 Azure SDK、PUT、GET、最终 Manifest 或 Blob 发布**，不因此将任务 2.1/3.1/3.2 标为完成。


### P2.1/P2.2 — 隔离开发验收（2026-10-24）
- Healthcare feature branch `feat/clinical-immutable-blob-publisher-20261024`：新增 SDK 隔离后端 `azure_blob_publisher.py`，复用 P1.3 `verified_plan`；`overwrite=False` 实现不可变创建，实际 GET/HEAD 校验 SHA256、metadata、Content-Type 与 ETag，Manifest 最后创建并 GET，失败不返回提交收据。
- Fake 后端覆盖正常、同请求重试、已有不同内容、源清单 SHA 改变、部分故障、未知写入 ACK、GET 失败、metadata 变化和脱敏；隔离 Azurite 测试真实 Azure SDK wire path。当前状态 **UNIT / AZURITE CI PASS，NOT LIVE AZURE VERIFIED**。PR [#451](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/451) 分支源码 SHA `a934a3895e276031a38c593ebaf74a550569a843`：Hosted [Azure Blob workflow](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40131051459) 中 Fake/Fault + 独立 Azurite SDK 两项 PASS；两项 Job 的最终结论均为 `success`；仅证实离线模拟环境。
- 真实 Azure / K8s 验证、两院医院适配器以及对已有 OIE 验收 Request 的任何重放均未授权、未实施。


### P2.3 — FHIR DIRECT adapter 离线验收（2026-10-24）
- [PR #452](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/452) 新增 `direct_fhir_publisher.py`（不含硬编码医院身份），调用已验收 P4.1 `verify_handoff` → 校验外部 Profile 为 `FHIR_R4/DIRECT` → 从只读冻结请求路径读取实际 FHIR bytes → `publish_immutable`。只使用共享 Publisher，不改 Generator、OIE、Local DP；不运行真实 Azure。
- 离线 Fake Blob 测试覆盖 Atlanta Profile、Manifest SHA、逐字节读回、同请求重试、篡改和错路线拒绝。Healthcare [Run #40131636131](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40131636131) 的 Pure Offline/Fault + 本地 Azurite SDK 两 Job PASS；测试源 HEAD `202215fc2b700b700385c89dbf3118b8f3bdf2b7`。因此 2.3 标记离线实现完成；3.1 仍 OPEN 直到真实 Atlanta Azure Landing GET/Manifest E2E，4.2 也继续 OPEN。


### P3.2 — OIE HL7 发布适配器离线候选（2026-10-24）
- `oie_hl7_publisher.py` 从真实 Generator P4.1 源 Manifest 重新核验 FHIR/Encounter，严格要求每个 Encounter 有对应的 **新** OIE persisted message readback：Channel ID、Message ID、实际转换 bytes / SKIP marker，并执行 `verify_adt_against_fhir` 复核 A01 住院和 MSH-10 / 来源关联。
- IMP 不得 SKIP；AMB 不可伪造 ADT A01；仅上传通过验证的 HL7 原始 Bytes，skip-only 禁止伪造成功 Manifest；复用已验收 `publish_immutable`。
- 此处仅离线 Mock 结果，**未授权使用真实 OIE 的 Derby 消息或 Azure PUT**，3.2 / 4.2 保持 OPEN，后续经授权才实现受控 OIE 逐条 Fetcher 与 Live 新 Request E2E。
 
### P4.4 — 独立 Publisher Namespace（仅静态设计）
- 用户将 Publisher 目标 Namespace 指定为 `dw-az-blob`，而 Generator/OIE 分别保持 `dw-synthea`、`dw-oie`。Namespace/Default-Deny NetworkPolicy 作为独立文件，默认不执行；NetworkPolicy 可能阻断 DNS、OIE 和 Azure，必须先制定并验证允许规则。
- 提供 Hosted-only `test_blob_namespace_contract.py` 和新 Namespace README；严格禁止把 `dw-synthea` 的 PVC 直接挂载到 `dw-az-blob`。未来跨 Namespace 的源文件交接和真实 OIE 凭证 Fetcher 仍未开发/验收。
- 此项不代表 Namespace 已在 Kubernetes 创建；4.1/4.2 等真实环境 Gate 保持 OPEN。
