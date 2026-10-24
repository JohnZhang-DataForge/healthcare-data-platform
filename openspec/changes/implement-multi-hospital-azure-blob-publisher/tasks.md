# Tasks — Multi-Hospital Azure Blob Landing Publisher

> ACTIVE PLANNING. 本 Change 只有设计与运行边界获得审查，并不表示 Azure Blob Publishing 已执行；初始权限、Azure 容器名称/Endpoint、OIE scoped account 及 Shared Runtime 授权仍需按实际检查。

## 1. Planning / Contract
- [x] 1.1 从 P4.1 Source Handoff 与 OIE worker01 Live E2E 的证据定义两条医院路线、公共 Publisher、immutable commit/读回、安全身份与 K8s namespace 边界。
- [ ] 1.2 运行 OpenSpec/Trusted Gate，通过规划 PR 合并 Main；确认实际 Azure Account URL、Landing Container、Provider Scope 和 Secret 来源（不得将其写到 Git）。
- [x] 1.3 细化标准 Publisher input JSON Schema、Blob path 安全与源字节校验、严格负向条件，离线 Contract Tests；`receipt` / 远端 idempotency 细节在 2.1–2.2 实现。

## 2. Shared Publisher
- [ ] 2.1 在 Healthcare `local-data-platform/apps/clinical_producers/` 实现医院无关 Azure Blob immutable Publisher（SDK 锁定版本、条件创建、已存在读回对比、拒绝覆盖、最终 Manifest commit）。
- [ ] 2.2 增加 Mock/Azurite 单元/集成与 Fault Injection：SHA tamper、已存在不同内容、权限失败、部分写入重入、Manifest-only success 禁止、secret redaction。
- [ ] 2.3 建立 Generator verified handoff 到 Publisher 交付输入适配，任何医院/格式由 Profile 选择，禁止耦合 Generator 核心源码。

## 3. Hospital Routes
- [ ] 3.1 Atlanta：源 FHIR R4 → verified handoff → Blob Publisher，验证 Byte-for-byte/FHIR manifest 后可提交。
- [ ] 3.2 Johns Creek：新 FHIR Source Request → real OIE Channel → independent HL7 ADT A01 readback → Blob Publisher；非住院事件显式跳过，不制造 A01。
- [ ] 3.3 两路线的 request_id、医院和 destination prefix 分离与幂等测试；不得使用已验收 OIE 32 条消息的旧源请求重放。

## 4. Guarded Live and Documentation
- [ ] 4.1 只读检查 Azure Account/Container/RBAC/网络、两仓 Main/并行任务、worker01/PVC/OIE，批准范围后才允许 Self-Runner 的真实外部写入。
- [ ] 4.2 新合成源请求 K8s→Azure Landing 全流程 E2E：两医院独立证据、每对象 SHA/ETag/GET、最终 Manifest GET 和相同请求 retry 一致性；保留失败无覆盖。
- [ ] 4.3 同步真实 PR/Run/Blob object receipt、相关 CODE.md，明确 Fabric/OMOP 不在本 Change；再判断 archive。

### P1.3 — 实际初始 Blob 发布计划输入合同
- `blob_publish_contract.py` 仅接受冻结 Hospital/Feed/Request 与 `SOURCE_HANDOFF_VERIFIED` FHIR、`OIE_HL7_READBACK_VERIFIED` HL7；不可变对象逻辑以实际源 bytes / SHA256、严格相对路径与事件 Control ID 为起点；禁止含未声明源 bytes、跨医院前缀及模板路径穿越。
- 本轮新增标准 input Schema 和离线单测；**尚无 Azure SDK、PUT、GET、最终 Manifest 或 Blob 发布**，不因此将任务 2.1/3.1/3.2 标为完成。
