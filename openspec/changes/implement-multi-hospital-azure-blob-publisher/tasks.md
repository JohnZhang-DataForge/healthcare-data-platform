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
- [x] 2.4 实现 `dw-az-blob` 独立 DIRECT FHIR runtime CLI、不可变 Base Image 的 Dockerfile 和受控 `emptyDir` Stage Job 模板，Host-only 离线失败/重试/身份脱敏测试（**不包含真正部署、镜像发布或跨 Namespace Stage**）。
- [ ] 2.5 原跨 Namespace ephemeral Stage 需求已由 `dw-synthea` 共 Namespace 只读 PVC 设计取消；仍待 OIE authenticated persisted readback Fetcher，运行前独立审查与授权。
- [ ] 2.6 Publisher GHCR 镜像 Main-only Clean Build + 无网络非 root Smoke + 唯一 git-SHA 标签发布和 Digest 读回；不修改 `latest`、不触碰 K8s/Azure（需真实 Main release Run PASS 才完成）。

## 3. Hospital Routes
- [ ] 3.1 Atlanta：源 FHIR R4 → verified handoff → Blob Publisher，验证 Byte-for-byte/FHIR manifest 后可提交。
- [ ] 3.2 Johns Creek：新 FHIR Source Request → real OIE Channel → independent HL7 ADT A01 readback → Blob Publisher；非住院事件显式跳过，不制造 A01。
- [ ] 3.3 两路线的 request_id、医院和 destination prefix 分离与幂等测试；不得使用已验收 OIE 32 条消息的旧源请求重放。

## 4. Guarded Live and Documentation
- [x] 4.5 用户撤销独立 Publisher Namespace，集群严格核对后删除 `dw-az-blob`，Publisher 改为 `dw-synthea` 只读使用 Generator 现有 PVC，并迁移最近合并的 DIRECT FHIR Runtime Job 模板/回归；OIE 独立不变。
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

### P4.4 — dw-az-blob Namespace 真实集群创建与独立读回（2026-10-24）
- Healthcare [PR #456](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/456) 已合并，静态模板/Main SHA `f52138cbffcfe6b4049d0bbe0ccbf1022938829f`；Self-Runner [PR #259](https://github.com/JohnZhang-DataForge/Self-Runner/pull/259)，执行 Main SHA `78bb420f8f30b22025050895ecb4db72679ced56`。
- [Self-Runner Run #40133194325](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40133194325) **SUCCESS**，预检 active Kubernetes Jobs=0、worker01 Ready、dw-synthea/Generator PVC Bound、dw-oie Deployment Ready。原 Namespace 不存在，`kubectl create` 只创建 `dw-az-blob`，独立读回 `PASS`；UID `879dc420-a9c0-4560-bdd7-4dbb72146fbd`，Restricted Pod Security 标签匹配。
- 本次新 Namespace 内 Pods/Jobs/PVC/Secrets=0；NetworkPolicy **未应用**、Publisher Image/Pod/Secret/实际 Azure RBAC 均未配置，OIE Derby 和 Generator PVC 未修改、Azure Storage 写入=0。
- 4.4 的 **Namespace 创建** 可以判为 `LIVE_VERIFIED`，但 4.1（Azure Account/身份/安全联检）、4.2（双医院真实发布）及跨 Namespace 受控 handoff **仍 OPEN**。不能以 Namespace SUCCESS 推断数据能发布。

### P2.4 — DIRECT FHIR runtime 代码候选（原 dw-az-blob staging 方案已退役）（2026-10-24）
- 源码 `azure_blob_runtime.py` 仅接受已 Stage 的 `DIRECT FHIR` 请求。使用外部给定的 Manifest SHA256 与 ready marker 双重门控；复用既有 `prepare_direct_fhir` 和 `publish_immutable`，先验证所有源 bytes/Blob Key，后初始化 SDK SP 身份。访问凭证仅从运行时注入的 Secret 环境变量读取，异常统一脱敏。
- 单独 Dockerfile 必须由未来 Builder 注入 digest-pinned Python Base Image；原 `dw-az-blob` 临时 Stage Job 已随用户决定撤销。**当前** `publish-direct-fhir-job.yaml.tpl` 已迁移到 `local-data-platform/kubernetes/manifests/synthea/blob-publisher/`，固定 `dw-synthea`、worker01，同 Namespace **只读挂载现有 Generator PVC**，引用 Profile ConfigMap/同 Namespace scoped SP Secret，不需要新 PVC；runtime 新增 `--source-mode direct-readonly-pvc`，继续校验源 Manifest 的 out-of-band pinned SHA 和原始 FHIR bytes，旧 staged marker 模式保持兼容。
- 此阶段只纳入 GitHub-hosted offline tests；不再需要跨 Namespace Stage producer/transport，**尚无** 实际 Publisher GHCR 镜像、`azure-blob-publisher-identity` Secret、Azure Container RBAC，亦没有授权/运行任何新的 Publisher Job。2.5/3.1/3.2/4.1/4.2 保持 OPEN。

### P4.5 — 用户决定恢复 Publisher 于 dw-synthea，真实回退证据（2026-10-24）

- 用户撤销 `dw-az-blob` 独立隔离方案，选择 Publisher 与 Generator 共用 `dw-synthea`，避免跨 Namespace 的 PVC 文件复制与临时阶段握手。`dw-oie` 无需迁移：FHIR 通过现有 OIE API 提交、HL7 经未来 scoped fetcher 独立读回；保留原 OIE Derby/PVC 和历史验收。
- `dw-az-blob` 曾由 [Self-Runner #40133194325](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40133194325) 创建（UID `879dc420-a9c0-4560-bdd7-4dbb72146fbd`）。受控删除 [Self-Runner PR #261](https://github.com/JohnZhang-DataForge/Self-Runner/pull/261)、[Run #40133855773](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40133855773) **SUCCESS**：严格核对原 UID、所属标签、无额外 Namespaced 资源、全局活动 Job=0，DELETE 后独立 API 读回 **ABSENT PASS**；`dw-synthea`/`dw-oie` 原 Namespace 与 PVC UID 未变，原 PVC 仍 Bound，无 Azure/OIE 消息写入。
- 此源码 PR 将 [新 DIRECT FHIR Runtime PR #460](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/460) 的 Job 模板迁移至 `local-data-platform/kubernetes/manifests/synthea/blob-publisher/`，使用既有 Generator PVC readOnly（volumeMount + PVC volume）、`--source-mode direct-readonly-pvc`；保留 Runtime、Dockerfile 与原 Blob 模拟/Azurite 安全契约。删除旧独立 Namespace YAML、NetworkPolicy、README、staging Job 和静态测试，更新 CODE.md/CI/Design。
- 只读挂载必须在真正部署前核实 PVC accessModes、worker01、已有 Generator 并发作业、证书/网络/Secret Scope 与远端 Azure Account/Container/RBAC。Publisher 镜像未发布 GHCR、Secret 和运行 Job 未创建、Azure Blob PUT/GET 未执行，两医院 E2E 仍 OPEN；OpenSpec 4.1/4.2 **不打勾**。

### P2.6 — 主线 SHA-only Publisher 镜像发布候选（2026-10-24）
- `.github/workflows/azure-blob-publisher-ghcr-release.yml` 仅因自身路径的 Main Push 自动执行 Release，PR 在 GitHub-hosted Ubuntu Runner 进行 host contract + Docker clean build / non-root read-only/no-network smoke；真实推 GHCR 仅发生在 Main push 或人工 main dispatch，令镜像可复现且不会因其它业务代码更新发布或覆盖 `latest`。
- 基础镜像 `python:3.12-slim-bookworm` 在 CI 中下载后按实际 RepoDigest 转为 `python:3.12-slim-bookworm@sha256:<real>`，构建过程仅使用不可变 digest；最终镜像只发布 `git-<exact Main SHA>` 标签，保存真实仓库 Digest。Dockerfile 仍然要求 `BASE_IMAGE` 参数，不允许静默使用 latest。
- Release 不授权 Publisher Job 或 Azure SP Secret 安装，真实 K8s/PVC/Azure Storage E2E 仍需独立预检与受控执行。PR Test 与 Main Release 的 Run 结论要分别记录；未成功 Push 前 2.6 保持 OPEN。

### P2.5 — OIE scoped persisted message readback 的离线实现（2026-10-24）
- 新增 `oie_persisted_readback.py`：认证 HTTP Cookie Client 只允许集群内 `https://oie-debug.dw-oie.svc.cluster.local:8443`，严格校验 CA 链，不接受 PoC 的 admin 身份或不验证证书的 TLS。API 路径限明确的 `/api/channels/<channelId>/messages/<messageId>` GET，不列举、重放、发送或删除 OIE 消息。
- 对每个新请求 POST 所返回的精确 messageId，XML 中验证 processed、Source Connector `metaDataId=0`、`TRANSFORMED`、消息/Channel ID（响应提供时）和原始 HL7/Skip 字节；再交给既有 `prepare_oie_hl7` 验证所有 Encounter、FHIR A01、MSH-10 和门诊跳过。离线 Mock 覆盖消息重复/缺失、篡改、错误 HTTP/TLS/认证、API 范围越界和凭据脱敏。
- 本 PR **不代表**已经配置 scoped OIE 用户或可信 CA，也没有向已验收 32 条 Derby 消息发起 GET/POST，更没有 Azure Blob PUT。真实新 Source Request 的事件提交收据来源、OIE API 权限、Endpoint 证书与 Live E2E 仍 OPEN；因此 2.5/3.2/4.2 保持 OPEN。
