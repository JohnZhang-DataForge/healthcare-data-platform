# Tasks — Multi-Hospital Azure Blob Landing Publisher

> **2026-10-28 最新真实运行状态 — 两医院 Azure Landing E2E 已验收：** Atlanta Hospital A FHIR Direct 已在 #40238053772 / #40250606505 完成，Johns Creek Hospital B 新 5 人 Synthea FHIR → OIE HL7 ADT^A01 → Azure Blob 独立读回 [Self-Runner #40715594941](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40715594941) **SUCCESS**：136 新 Encounter / 136 新 OIE Message ID / 6 A01 对象 / 130 非住院跳过；6 对象与 Manifest GET/HEAD/SHA/ETag、Publisher-only retry 幂等、临时资源按 Run 清理均 PASS。请求 `johnscreek-hl7-gh-40715594941`、源 SHA `3f997d301a92457985b8aaa7945cf6367935f701cda41265d72de1cc4cedf229`、Azure Manifest SHA `5ee8b78f5307bdeedfcdde76b2d9b15289ce6a2ea5242baddfc34d9f8219f193`。此为 Landing 验收，**不包括 Fabric Notebook/OMOP**。详见 [精确实机收据](evidence/JOHNS-CREEK-HL7-5P-AZURE-LIVE-E2E-20261028.md)。下方旧 dated HOLD 属历史阶段，不覆盖最新验证。

> **2026-10-27 只读源码/验收对账（覆盖原 10-24 规划状态）：** Atlanta FHIR 5/100 Azure Blob 实机 E2E 已由 Run #40238053772 / #40250606505 验收；Johns Creek 实机 OIE 31 Encounter / 32 持久消息于 #40128211780 验收，但属于旧 Channel/旧 Request 历史。新版 Johns Creek OIE→HL7→Azure Blob 的 Task 3.2、双院 4.2 仍 OPEN；不得将旧『尚无任何 Azure 发布』的历史文字套用到 Atlanta，也不得将本分支候选代码视为 Live PASS。

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
- [x] 2.6 Publisher GHCR 镜像 Main-only Clean Build + 无网络非 root Smoke + 唯一 git-SHA 标签发布和 Digest 读回；不修改 `latest`、不触碰 K8s/Azure；[Run #40137992945](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40137992945) 实际成功，镜像 Digest 已记录。

- [x] 2.7 Publisher 已编码并通过离线 CI 支持 GitHub OIDC 换取的短期 Azure Storage Access Token、token 到期边界及同 Namespace 一次性 Session Secret Job 模板；Healthcare PR #469 / Main GHCR Run #40148148246 已成功。真实 Session Secret 生命周期仍由 4.6 另行验收。

## 3. Hospital Routes
- [x] 3.1 Atlanta：源 FHIR R4 → verified handoff → Blob Publisher，验证 Byte-for-byte/FHIR manifest 后可提交。
- [x] 3.2 Johns Creek：新 FHIR Source Request → real OIE Channel → independent HL7 ADT A01 readback → Blob Publisher；非住院事件显式跳过，不制造 A01。
- [x] 3.3 两路线的 request_id、医院和 destination prefix 分离与幂等测试；不得使用已验收 OIE 32 条消息的旧源请求重放。
- [x] 3.4 **受控医院身份命名整改**：Profile、FHIR Publisher、OIE Channel/HL7 Assigning Authority、两仓 Workflow、测试和 Blob Key 使用固定 Hospital A/B 标识；对 `demo-` 临时身份 fail-closed；重新发布匹配源码的 Publisher Digest 并验证运行前匹配。未完成前禁止 Atlanta 真实 PUT。
- [x] 3.5 **Synthea 100 人 FHIR Filename Contract 修复（代码/CI）**：针对真实 100 Bundle 中的撇号及 Unicode 患者名修正 FHIR Blob leaf 安全字符校验，保留 Synthea 原始文件名和字节、HL7 严格 ASCII、URL 保留字符与路径穿越负向门禁；源端和 Publisher 禁止未经验证写入。
- [x] 3.6 **冻结的 100 人 Atlanta Request 发布恢复验收**：失败后只读确认原 Request 文件数、不可变源 Manifest SHA、无 Publisher Job/Blob Manifest，再使用新源码及不可变 Publisher Digest 受控恢复；100 文件逐个 GET/ETag/SHA、Manifest COMMIT、重试及错误 SHA 全 PASS 才完成。禁止直接 rerun 原失败 Workflow。

## 4. Guarded Live and Documentation
- [x] 4.5 用户撤销独立 Publisher Namespace，集群严格核对后删除 `dw-az-blob`，Publisher 改为 `dw-synthea` 只读使用 Generator 现有 PVC，并迁移最近合并的 DIRECT FHIR Runtime Job 模板/回归；OIE 独立不变。
- [x] 4.4 创建独立 `dw-az-blob` Namespace 的静态 Kubernetes YAML/边界文档/离线门禁，显式阻止跨 Namespace 挂载现有 Generator PVC；**仅代码级别完成**，真实 `kubectl` Create/Readback 及 Writer 工作负载不在此勾选范围。
- [ ] 4.1 只读检查 Azure Account/Container/RBAC/网络、两仓 Main/并行任务、worker01/PVC/OIE，并通过 Terraform 授予新 Publisher 的 landing 容器级 RBAC、K8s Secret 后独立验证；真实 Blob 写入需另行 E2E 验收。
- [x] 4.2 新合成源请求 K8s→Azure Landing 全流程 E2E：两医院独立证据、每对象 SHA/ETag/GET、最终 Manifest GET 和相同请求 retry 一致性；保留失败无覆盖。
- [ ] 4.6 将 OIDC Storage Token **恰好在已验证新 Request 的 Job 启动前**以短期 Secret 交付，绑定唯一 Job、期限、只读 PVC 和有界清理；不得把 GITHUB_TOKEN/OIDC JWT 冒充 Azure Access Token，不得提前写入过期 token。
- [ ] 4.7 新隔离 Service Principal 的长期 Client Secret 已在 GitHub 安全配置；受控创建 `dw-synthea/azure-blob-publisher-identity`，验证键名和值的等同性（不输出值）、K8s RBAC 和轮换规则，并用真实 Publisher Source Request 验证存储读写。禁止把 Terraform State 作为密钥容器。
- [x] 4.3 同步真实 PR/Run/Blob object receipt、相关 CODE.md，明确 Fabric/OMOP 不在本 Change；再判断 archive。

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

### P2.6/4.1 — 真实镜像交付与只读集群预检证据（2026-10-24）
- Healthcare [PR #464](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/464) 已合并 Main `56b89b981cfc6088e8404aea5eae6781943d58ef`，GitHub-hosted [GHCR Main Run #40137992945](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40137992945) **SUCCESS**。Publisher 镜像 `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:e53a87105cb489cfd4da4f66734c57c2a1b472d84e6ee8fd91f75510fe88c6a2`，标签 `git-56b89b981cfc6088e8404aea5eae6781943d58ef`，父镜像 `python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70`。镜像 Clean Build、非 root、只读/无网络 Docker Smoke、SDK import、CLI --help 全 PASS，latest 未修改，无共享 K8s/Azure 写入。
- Self-Runner [PR #263](https://github.com/JohnZhang-DataForge/Self-Runner/pull/263) 通过 [Run #40138182990](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40138182990) 实际 worker01/namespace/PVC/OIE **只读预检 SUCCESS**：`dw-synthea/synthea-new-generator-state` 是 `ReadWriteOnce`、`synthea-local`、PV Retain；活跃集群 Job 0，`dw-oie` ClusterIP:8443/OIE PVC Ready、`dw-az-blob` 仍不存在；当前 Runner 拥有在 `dw-synthea` 创建 Job 权限。
- **已证实阻塞**：`dw-synthea/azure-blob-publisher-identity` Secret **不存在**；未发现 Profile ConfigMap；本轮未获取 Azure Account/Container/RBAC 实际状态。Publisher Job 没有创建，Source Generator PVC 未修改，未实际上传或 GET Azure Blob。真实 4.1 Azure 授权与 4.2 双医院 E2E 仍 OPEN。请勿把 Secret/Role 假设为现成或直接使用其它 Fabric 账号。
- OIE 新 [PR #466](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/466) 合并 Main `43733f0f8be6fca71ffdcdac10cf597b8b78d59a`，Scoped Source Connector readback 逻辑与离线测试通过，但真实 OIE scoped user/TLS CA 不存在明确验收，当前 Publisher 镜像 Digest 是 PR #466 **之前** 的 SHA，只能作为相应历史版本的 DIRECT FHIR 镜像，不能虚称新代码已包含在旧镜像内。

### P4.1 — Azure Landing GitHub OIDC 身份/RBAC 真实只读核验（2026-10-24）

- Azure Terraform 的 [shared storage vars](../../../azure-fabric/infra-terraform/shared-infra/storage/terraform.tfvars) 确定现有 Resource Group `OMOP`、Storage Account `johnzhang`、Container `landing`，`blob_role_assignments = {}`：当前 Terraform 并未通过该 map 创建 Publisher 新授权，不代表历史已有授权不存在。
- Self-Runner [PR #265](https://github.com/JohnZhang-DataForge/Self-Runner/pull/265) 第一次只读 [Run #40146328038](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40146328038) 在严格假设 OIDC 默认 `sub` 格式时 `HOLD`，尚未调用 Azure；[PR #266](https://github.com/JohnZhang-DataForge/Self-Runner/pull/266) 保持 issuer/repository/owner/Main ref/push event/audience 强校验，兼容自定义 GitHub OIDC Subject，第二次 [Run #40146476474](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40146476474) **SUCCESS**。
- 成功 Run 使用现有 Self-Runner `vars.AZURE_CLIENT_ID`/`AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID` + GitHub `id-token: write`，无长期 Client Secret。实测 GitHub Main OIDC assertions、Azure ARM 和 Azure Storage OIDC Token Exchange 均 PASS；ARM GET Storage Account 与 Container 均 HTTP 200，订阅/RG/Account/Container roleAssignments REST GET 均 200；对应 service principal 对目标容器存在直接或继承 `Storage Blob Data Contributor` 角色；数据接口 Container HEAD HTTP 200。角色枚举只核对 service principal **直接身份**的可见授权；不对 group-based RBAC 做否定判断。
- **验证只读**：无 Azure Blob PUT、角色变更、Terraform Apply、K8s Secret/Pod/PVC 变更；可以判断 Self-Runner 的 OIDC 身份在 Azure RBAC 上具备所需数据写入角色，但**尚未实际验证 PUT/GET 数据交付**。
- GitHub OIDC 凭据只在 GitHub Workflow 生命周期可用，不会自动传递到 `dw-synthea` Pod。现有 Publisher Job 调用 `ClientSecretCredential` 并引用 `dw-synthea/azure-blob-publisher-identity`（预检 [#40138182990](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40138182990) 确认不存在）。**不能因为 Runner OIDC 通过就宣布 K8s Job 已获得身份。** 后续须明确选择独立 K8s Workload Identity/Scoped Secret 或经过审查改为 Runner 执行 Azure 上传，再做真实数据 E2E。
- 原任务 4.1 保持 OPEN：Azure 身份和目标容器只读预检完成，但 Publisher K8s 认证、完整网络和实际写入授权执行门槛尚未完成；4.2 双医院实际上传/独立读回也 OPEN。

### P2.7 — GitHub OIDC 与 K8s Secret 的现实限制（2026-10-24）
- Self-Runner [Credential Readiness #40147726787](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40147726787) 实际只读检验：`vars.AZURE_CLIENT_ID`、`vars.AZURE_TENANT_ID` 均存在，仓库 `secrets.AZURE_CLIENT_SECRET` **不存在**，`dw-synthea/azure-blob-publisher-identity` **不存在**。不能将 `GITHUB_TOKEN` 或 GitHub OIDC JWT 当成 `ClientSecretCredential` 的 Entra Client Secret，过期的 Azure Storage Access Token 也不能充作长期 K8s Secret。此次只读 Workflow 没有修改 Azure/K8s。
- 选择保持 Publisher 运行在 `dw-synthea`，增加 `temporary-access-token` 认证模式：调用方先用已验证 Self-Runner OIDC 联邦身份向 Entra **换取 Azure Storage audience Access Token**，在真正创建经核验的 Publisher Job 前设一个一次性 Session Secret；运行时拒绝无/近到期 Token、异常 Auth Mode 和同时带有旧 Client Secret 的配置。仍只读挂载 Generator PVC、源 Manifest 的 SHA、远端 immutable Azure GET/Manifest 最后提交规则不变。
- 静态 `publish-direct-fhir-temporary-token-job.yaml.tpl` 使用 `__SESSION_SECRET_NAME__` + `access-token/expires-on`，Job deadline 20 分钟，不代表已将任何真实 Token 写入集群。需具备真实 Source Request/Profile ConfigMap/完整云端读回/生命周期清理和安全门槛后才能做 Live Job，避免生成一个很快过期却无人使用的 Secret。

### P2.7 — GitHub OIDC-only Publisher 代码与镜像真实验收（2026-10-24）
- Healthcare [PR #469](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/469) 所有适用 CI PASS，合并 Main `3b1716b8defd598deedda348a646e4a4280527ac`。独立 GitHub-hosted Main [GHCR Run #40148148246](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40148148246) **SUCCESS**，Non-root/无网络容器 Smoke PASS。实际 Publisher Digest `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:06324ae6571a6f72f3b317a1ba577851952bb421fc33ef1d87b4718acfcea4e6`；旧 `git-56b89b...` 镜像不包含本 Token 功能，不要误用。未修改 `latest`。
- Self-Runner [PR #268](https://github.com/JohnZhang-DataForge/Self-Runner/pull/268) / [Run #40147726787](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40147726787) 只读检查已验证 GitHub AZURE_CLIENT_ID/TENANT_ID vars 可用，但 `secrets.AZURE_CLIENT_SECRET=false`；`dw-synthea/azure-blob-publisher-identity` 未创建。已用 [Self-Runner PR #269](https://github.com/JohnZhang-DataForge/Self-Runner/pull/269) 删除仅一次检查 Workflow，保留 GitHub Run 证据。
- 新临时认证代码明确区分 GitHub OIDC assertion 与 Azure Storage scope Access Token，仅在可信 Runner 上先交换 OAuth Token 后才有可能使用。静态 Job 模板引用 **一次性 Secret** `access-token`/`expires-on` 且对 20 分钟内结束和 SDK 到期保护有约束；当前 **没有** 自动 Secret 创建/绑定/清理 Workflow，也没有任何真实 Secret/Pod/Blob PUT。不要在没有新冻结 FHIR Manifest SHA 和具体 Job 的前提下预先把短期 Token 写入 K8s，避免留下过期 Secret。
- 下一运行前门槛：新 Source Request + hospital profile ConfigMap、当前 worker01/PVC 与全局 Job 无冲突、Main/镜像 Digest 绑定、OIDC 交换为 Storage audience、每次 Job 对应临时 Secret 生命周期及必需清理、实际 Blob GET+ETag+Manifest 读回。仅 2.7 代码/镜像级完成，4.1/4.2/4.6 均 OPEN。

### P4.1 — 新 Publisher 独立 Service Principal 与最小权限 Terraform（2026-10-25）
- 用户已在 Entra 手动创建 `healthcare-blob-publisher` 并将新 Client Secret 安全保存于 Self-Runner GitHub Secret，独立于旧 Terraform/Fabric 身份。
- Self-Runner [PR #284](https://github.com/JohnZhang-DataForge/Self-Runner/pull/284) / [Run #40204467859](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40204467859) 验证 GitHub 配置、`dw-synthea` 可读、Landing 的 Role Assignment 写权限；Graph 应用目录 GET 403 是原 Terraform 身份 Graph 读取不足，并非 Azure Blob 问题。
- [PR #286](https://github.com/JohnZhang-DataForge/Self-Runner/pull/286) / [Run #40204621241](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40204621241) 使用新 Publisher 自身的机密凭据兑换 Storage audience OAuth token：`appId`/Tenant/`aud` 验证通过；从**其自身 OAuth token**解析并确定 `Service Principal Object ID = 01cd737f-6c86-48bb-ae5c-209246d62ed6`，绝非 App Registration Object ID。没有暴露 Client Secret/Token，亦无 Blob/K8s/RBAC 修改。
- 本 Terraform PR 在现有 `shared-infra/storage` 的 **现有** `blob_role_assignments` Map 新增仅一个 `healthcare_blob_publisher`，角色限定为 `Storage Blob Data Contributor`，目标作用域是现有 `OMOP/johnzhang/landing` 容器。其他 Workspace Reader 配置不变；不要重复 Portal 创建同一 Role Assignment。**PR/Plan 不等于已 Apply**，Apply/独立 RBAC 读回和 K8s Secret 状态必须在执行后记录。

- Publisher RBAC `terraform.tfvars` 与离线合同测试采用 Terraform fmt 对齐格式，未改变 `healthcare_blob_publisher` principal、Role、Scope 或旧 Reader；本次仅格式兼容修复，不代表 Azure 已 Apply。

### P4.1 — Isolated Publisher Landing RBAC Terraform Plan PASS, Apply ABAC 403（2026-10-25）

- 新注册 `healthcare-blob-publisher` 自身 Credential 的 Azure Storage OAuth 认证与企业 Service Principal Object ID 已经由 [Self-Runner #40204621241](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40204621241) 实测，GitHub 的三项发布者凭据存在/ID 匹配；旧 Terraform 部署身份 `github-terraform` 不复用给 Publisher。
- Healthcare [PR #480](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/480) 合并 exact Landing Container `Storage Blob Data Contributor` `blob_role_assignments.healthcare_blob_publisher`，角色授予的对象是 Publisher Enterprise Principal `01cd737f-6c86-48bb-ae5c-209246d62ed6`，没有引入 TF secrets；格式和旧 Workspace Reader 合同由 [PR #481](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/481) 校验通过。
- Self-Runner [PR #287](https://github.com/JohnZhang-DataForge/Self-Runner/pull/287) [真实 Run #40205455766](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40205455766)：沿用 shared Storage 远程 State，`terraform init/validate/plan` 成功，严格检查**仅一条 `create`** 且 Scope/Principal/Role 准确，无其它资源改动；随后 `terraform apply` 返回 **403 AuthorizationFailed / ABAC condition not fulfilled**，独立 ARM post-Apply 读回因此没有执行，不得标记授权成功。
- 后续 [ABAC 审计 Run #40205946610](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40205946610) 证实 `github-terraform` 对 `landing` 的 `Role Based Access Control Administrator` 委派带 Condition：仅允许将 `Storage Blob Data Reader`(`2a2b9908-6ea1-4ae2-8e65-a410df84e7d1`) 分配给 Fabric Workspace Identity `1ae64649-a7c3-497e-9fe3-69b37d27c453`。**不允许给新 Publisher 主体创建 Contributor Role Assignment**。权限检查 API 报 possible write 并不证明其 ABAC condition 放行。
- **仍需一次 Azure 管理员操作**：在现有 `johnzhang/landing` 容器 IAM 为 Terraform 身份增加**仅可授予 `Storage Blob Data Contributor` 给 `healthcare-blob-publisher`** 的受限 ABAC 委派，然后对当前失败的 Terraform Workflow 作受控重试；或管理员直接给 Publisher 授权后，先将该现有 Role Assignment Import 到 Terraform State，绝不能直接重复 Apply。不得弱化原 Fabric Reader 委派的约束。
- Kubernetes `dw-synthea/azure-blob-publisher-identity` 的长效 Secret **尚未创建**。GitHub Client Secret 已配置，但没有经过允许的密钥交付 Workflow 与 Kubernetes 内容读回；不能将 RBAC Plan/OAuth 登录视为实际 Blob 上传能力。Source FHIR→Azure Blob/E2E 同样未执行；Task 4.1/4.2 继续 OPEN。

### P4.1 — Publisher Azure Container RBAC 已存在并导入 Terraform State，No Drift（2026-10-25）

- 用户完成 Azure Portal 权限操作后，使用原 [Terraform Apply Run #40205455766 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40205455766) 再次尝试，**精确 Terraform Plan PASS** (1 create, 0 change, 0 destroy)，但 `Apply` 仍遭 ABAC 403；**不得把这次失败视为角色不存在或做第三次 create 重试**。
- 重新运行只读 [ABAC Run #40205946610 attempt 2](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40205946610) 发现 Azure 已有与目标严格匹配的 **唯一** `Storage Blob Data Contributor` 授权：Enterprise Principal Object ID `01cd737f-6c86-48bb-ae5c-209246d62ed6`，Scope `OMOP/johnzhang/landing`。旧 Terraform 身份的 Fabric Reader ABAC 委派条件仍存在，但对 Publisher 角色的读取不受其阻断。
- [Self-Runner PR #290](https://github.com/JohnZhang-DataForge/Self-Runner/pull/290) 使用审查过的 Main-only 一次性 Workflow、现有 Shared Storage Remote State 和精确 Healthcare SHA `3a67e746d8f04003508bb4bb5dce431dfbcfc147`。真实 [Run #40207100424](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40207100424) **SUCCESS**：Azure ARM 精确 Match=1、现存 ID 校验、`terraform import module.storage.azurerm_role_assignment.landing["healthcare_blob_publisher"]` 导入成功、State 资源 ID 独立读回 PASS、`terraform plan -detailed-exitcode` 零漂移 PASS。导入的是 Azure 既存 Role Assignment `556bf8d5-8fd1-4ed5-b7b9-74a2e4b015f8`，并未新增、更新或删除 Azure RBAC / Blob 数据。
- 因此 **Azure Publisher 容器级写角色存在并由 Terraform State 管理**；旧“尚需新建角色委派/再次 Apply”建议已被以上真实证据覆盖，不能再按照历史建议盲目 Apply。仍未验收 `dw-synthea/azure-blob-publisher-identity` 长期 Secret（新任务 4.7），也未执行真实 Publisher Blob PUT/GET（4.2），因此整体任务 4.1/4.2 仍 OPEN。

### P4.7 — 长期 Publisher Kubernetes Secret 手工 Workflow 创建及内容读回 PASS（2026-10-25）

- 用户已将独立 Azure App Registration `healthcare-blob-publisher` 的 Client Secret Value 存入 Self-Runner GitHub Actions `secrets.AZURE_BLOB_PUBLISHER_CLIENT_SECRET`；另有 `vars.AZURE_BLOB_PUBLISHER_TENANT_ID` 和 `vars.AZURE_BLOB_PUBLISHER_CLIENT_ID`。无需在聊天、Workflow 文件、Terraform State 或 Run Log 中再次提供明文；该 Azure Client Secret 有到期时间，未来需要按 Azure Expiration 做有审计的轮换，并更新集群 Secret。
- Self-Runner [PR #293](https://github.com/JohnZhang-DataForge/Self-Runner/pull/293) 已合并 Main `273661160a6cc585709ee54a432e9b9bdcf31afc`，增加 **仅 `workflow_dispatch`** 的 `.github/workflows/azure-blob-publisher-k8s-secret-manual.yml`。在 `main` 手动输入 confirmation=`CREATE` 才允许执行；目标为 `dw-synthea/azure-blob-publisher-identity`，不覆盖已存在 Secret，使用 `kubectl create -f -` 的进程 stdin 交付，严格验证 Tenant/Client ID，验证新 Secret 的 type、三个键名、Value 独立读回（不打印明文），没有在 Git 仓库存放 Secret。
- 用户手动触发的真实 [Self-Runner Run #40208908739](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40208908739) `workflow_dispatch` **SUCCESS**，Job `create-secret` 与全部步骤成功。Run 实测日志：`PUBLISHER_K8S_SECRET_CREATED=PASS`、`SECRET_NAME=dw-synthea/azure-blob-publisher-identity`、`SECRET_TYPE=Opaque`、`SECRET_KEY_COUNT=3`、`SECRET_VALUE_READBACK=PASS`、`SECRET_VALUES_LOGGED=NO`、`AZURE_BLOB_WRITES=NO`。该 Secret 已在集群真实持久创建，不能因为其他旧段落的“尚未创建”结论而重复创建；手动 Workflow 再运行会因不覆盖规则 HOLD。
- Azure 目标 `OMOP/johnzhang/landing` 的 `Storage Blob Data Contributor` 已通过 [Run #40207100424](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40207100424) 证明已由 Terraform Import 追踪且 No Drift。Azure RBAC 和本次 Secret 交付两者均完成，但**尚无针对刚创建的 Secret 的 Publisher Job 真实 Blob PUT/GET/ETag/Manifest 验收**，Atlanta/Johns Creek 独立 E2E (3.1/3.2/4.2) 仍 OPEN；4.7 的轮换流程和真实请求验收也 OPEN，不能将 Secret PASS 宣告整个 4.7 完成。
- 下一新 Session 必须重新读取两仓最新 Main、开放 PR、运行中 Workflows、`AGENTS.md`、Safe Operations、Session Coordination 及本 Change。随后只读检查 worker01/Generator PVC、`dw-synthea` Secret 元信息、新 Source Request + 冻结 Manifest SHA、Hospital Profile ConfigMap、镜像 Digest 与并发；获得本次共享 Runtime 操作许可后运行 **一次** 新合成 FHIR DIRECT 路线的 Publisher Job 与 Azure GET 读回，再处理 OIE HL7。不要重放历史 OIE 32 消息或修改其他 Session Portal P5/PG17 工作。

### P4.1/3.1/4.2 — Atlanta DIRECT FHIR 真实只读预检及受控手工 E2E 入口（2026-10-25）

- Self-Runner [PR #295](https://github.com/JohnZhang-DataForge/Self-Runner/pull/295) 已合并 Main `08df04da30c538cc6141fbb52e1f7297eeaae15e`；更新已有 dw-synthea 只读预检、添加手工 `azure-blob-publisher-atlanta-e2e-manual.yml` 与独立受控 `scripts/azure_blob_atlanta_direct_fhir_e2e.py`。PR Hosted Python 静态编译及 Generator/Publisher 模板渲染 [Run #40219797240](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40219797240) **SUCCESS**，但**无**共享集群或 Azure 数据写入。
- 初次只读 [Run #40218904158](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218904158) 与合并 Main 后 [Run #40219870444](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40219870444) **SUCCESS**：worker01 Ready、Generator PVC Bound/RWO/`synthea-local`，活动 Job=0，OIE 健康，现有 `dw-synthea/azure-blob-publisher-identity` Opaque/三个 Key PASS，Atlanta Profile 源码校验 PASS，真实 Profile ConfigMap **0**。未打印任何 Secret Value；无 K8s/Azure 写入。
- Healthcare Main 已发展至 `36bd4ee903f627bd851ab6a30444d9dd62767788`（对 `b92ccc9b7976e740d9dd77994a0725b115693705` 的增量仅 Portal 文档）；受控脚本按组件路径逐项验证源码和模板零漂移，现有 Publisher Digest `sha256:06324ae6571a6f72f3b317a1ba577851952bb421fc33ef1d87b4718acfcea4e6` 不因无关 Commit 被默认为新镜像。
- 手工执行采用**新** Atlanta Request → Generator PVC → 独立只读 Source Manifest SHA 复核 → 现有长期 Secret 的 Publisher immutable Azure `landing` PUT → Runner 另行 Storage OAuth 独立 Blob/Manifest GET+HEAD、SHA256/ETag → 同 Request retry 不变 → 错 SHA 负向防护；仅管理本 Run 临时 Job/ConfigMap；不接触 Portal/PG17/OIE 消息。
- **STATUS = READONLY PASS / LIVE PUBLISH NOT STARTED**，3.1/4.1/4.2/4.7 仍 OPEN；不得在实际 Blob PUT/GET/Manifest 独立读回前打勾。详细 [ATLANTA-DIRECT-FHIR-PREFLIGHT-20261025.md](evidence/ATLANTA-DIRECT-FHIR-PREFLIGHT-20261025.md)。

### 3.4 — 医院身份命名和历史数据边界（2026-10-25）

- 原先医院配置中的 `demo-atlanta` 与 `demo-johns-creek` 是**已弃用的早期模拟身份**，不得继续作为新 Azure Blob FHIR/HL7 Publisher 的运行标识；这不是重命名历史已发布数据。固定新的 Hospital A/B Profile ID：`atlanta-hospital-a` / `atlanta-hospital-a-fhir-r4` 和 `johns-creek-hospital-b` / `johns-creek-hospital-b-hl7-v2`。
- Johns Creek OIE Channel 新的 HL7 Assigning Authority = `JOHNSCREEKB`；已安装 OIE Channel/历史消息**不会**因为 Git 代码合并自动变更。下一次新 HL7 E2E 前须只读核对部署的 Channel 代码/配置，再单独审查受控更新、只针对新消息验证；不能盲目改已有 32 条历史验收消息。
- 标识的生成/校验、Azure Blob 路径及 immutable Manifest 元数据必须一致；旧 Prefix 可能已有对象时只读保留，不复用旧 Identity、同 Request ID 改名重放或强制覆盖。
- `hospital_profiles.validate_profile` 和 `blob_publish_contract.verified_plan` 在进入 Generator 或 Azure SDK 之前拒绝 `demo-` 占位 Hospital/Feed ID，相关正负测试写入 GitHub CI。
- **发布版本门禁**：旧 Publisher Digest `sha256:06324ae6571a6f72f3b317a1ba577851952bb421fc33ef1d87b4718acfcea4e6` 是本次代码更名前生成，不能用于宣称新策略已打包。先完成 Healthcare GitHub-hosted CI、对应 GHCR 新 Digest，然后再更新 Self-Runner 的手工 E2E 和只读预检，并做静态及 Live 只读验证。未完成真实 Azure PUT/GET/Manifest+幂等前 3.1/4.2 继续 OPEN。

### 3.4 — 稳定身份整改后端到端独立验收（2026-10-25）

- Healthcare [PR #490](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/490) **已合并** Main `b033d7b8fd8cf752de7e64b240ea3dc83ce1fe7d`。两医院正式 Hospital/Feed IDs、Johns Creek Assigning Authority、Profile/Plan Schema、Python/Node 正负测试及新的临时 OIE 完整转换/独立读回 [Run #40225717610](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40225717610) SUCCESS；旧历史 FHIR Artifact 不再作为新身份新 Channel 的业务验收输入。
- Publisher [GHCR Main Run #40225880536](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40225880536) **SUCCESS**：新精确 Digest `sha256:a92d06610813a38d3d9707133038f503f1f49b1d76a4144bc2500bded321e3da`，Nonroot/无网络 Smoke PASS，未修改 latest。旧 Digest 不包含这次修改。
- Self-Runner [PR #297](https://github.com/JohnZhang-DataForge/Self-Runner/pull/297) **已合并** Main `6b1ac1849b5277f647abdedd7f4ee77f526bffbb`，手工 E2E 和只读预检固定新医院 ID / Healthcare SHA / GHCR Digest；Hosted [Run #40226017942](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226017942) PASS；合并 Main 后实际 [Readonly Run #40226055238](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238) **SUCCESS**：worker01 Ready、Generator PVC Bound、全集群 Active Job 0、Scoped Secret Keyset PASS、新 Atlanta Profile PASS、Profile ConfigMap 0，无 K8s/Azure 写入。
- 3.4 仅代表**业务身份整改、镜像发布、离线 CI 与真实只读门禁**已完成。**未**触发新 Atlanta FHIR Azure PUT/GET/Manifest/Retry；Johns Creek 共享 OIE Channel 尚未部署本次新版本，历史 32 条仍原样保留。Task 3.1/3.2/4.2/4.7 继续 OPEN，不能因本勾选视为双医院 E2E 成功。
- 详见 [HOSPITAL-AB-IDENTITY-RENAME-20261025.md](evidence/HOSPITAL-AB-IDENTITY-RENAME-20261025.md)。

### 3.1 — Atlanta Hospital A 真实 Azure Blob DIRECT FHIR E2E（2026-10-25）

- **E2E ACCEPTED**：[Self-Runner Main Run #40238053772](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40238053772) `workflow_dispatch`、Attempt 1 **SUCCESS**，精确 Self-Runner Main `6b1ac1849b5277f647abdedd7f4ee77f526bffbb`，执行时 Healthcare Main `89a14d1949be91c9c5f934fb45962b4e2124630a`，Publisher 受保护输入版本 `b033d7b8fd8cf752de7e64b240ea3dc83ce1fe7d` 无漂移、精确 GHCR Digest `sha256:a92d06610813a38d3d9707133038f503f1f49b1d76a4144bc2500bded321e3da`。
- `dw-synthea/worker01` 生成全新 `atlanta-fhir-gh-40238053772`；Source Manifest SHA `468eb083d7db21dff2fa9336b587250c30f2cdfb853e8e1ee62c4f6537f15327`，FHIR Blob 5 个真实写入现有 `johnzhang/landing`。Commit Manifest key `clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/atlanta-fhir-gh-40238053772/landing-manifest.json`、GET SHA `772bcc6bcce0ffc137df3af0602238f69db18f8418f62acbc865780957af6af7`、ETag `"0x8DF32E36D2AA68B"`。对全部 5 个实际 Blob 的独立 GET/HEAD、SHA/ETag 验证 PASS；安全重试 `ALREADY_MATCHING` 与 ETag 零变化 PASS、错误 SHA fail-closed 并独立验证远端未改写 PASS，Run-scoped Jobs/ConfigMaps 清理 PASS。
- 后置 [K8s 只读复核 Attempt 3](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238/attempts/3) **SUCCESS**：全局 Active Jobs=0，`dw-synthea` 中包含 `profile.json` 的 ConfigMap=0，Publisher Secret/OIE/PVC 正常；不是新数据写入 Run。
- **准确边界**：本次仅完成 Atlanta DIRECT FHIR 的 Task 3.1；双医院共同门槛 Task 4.2、Johns Creek Task 3.2、跨院分离 Task 3.3、Secret 轮换 Task 4.7、整体文档归档 Task 4.3 均继续 OPEN。原先 3.4 文本“尚未触发 E2E”是改名验收当时的历史记录，不覆盖本节最新事实。
- [完整 Source / Blob / Manifest / Run 及后置复查证据](evidence/ATLANTA-DIRECT-FHIR-AZURE-LIVE-E2E-20261025.md)。

### P3.5/P3.6 — Atlanta 100 人真实运行中的 FHIR 文件名兼容缺陷（2026-10-25）

- 用户明确授权新的 `population=100` Batch，Self-Runner [PR #298](https://github.com/JohnZhang-DataForge/Self-Runner/pull/298) 增加 5/100 参数与精确数量验证，后续 [PR #299](https://github.com/JohnZhang-DataForge/Self-Runner/pull/299) 清理未使用的触发入口。[Main Push 单次 Dispatch #40245578811](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40245578811) 通过 [PR #300](https://github.com/JohnZhang-DataForge/Self-Runner/pull/300) **SUCCESS** 并触发真实 100 人 [Run #40245591533](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40245591533)，单次触发器已经由 [PR #301](https://github.com/JohnZhang-DataForge/Self-Runner/pull/301) 从 Main 撤销。
- **原始业务 Run FAILURE，保留不覆写**：`ATLANTA_NEW_GENERATOR_REQUEST_COMPLETED=PASS`，`population=100`，但 `fhir-source-audit` Job FAILED，报通用 `HOLD_RUNTIME_FAILURE_INSPECT_RESOURCES_BEFORE_RETRY`。不是 Azure 成功：旧 Run **没有创建任何 Publisher Job**、不存在已提交的 Azure Manifest 证据，旧 5 人 Batch 未触碰；不得对失败 Run 直接 rerun。
- 单独只读取证 [Self-Runner PR #302 / Run #40246631764](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40246631764) 通过失败 Job 的原始日志确认 `BlobPlanRejected: UNSAFE_OR_DUPLICATE_OBJECT_NAME`；[只读 PVC 定界分类 #40246918815](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40246918815) 在不读取/输出任何 Patient JSON 内容、原始姓名或凭据的情况下证实冻结请求 **100 个 FHIR 文件、重名 0、旧 ASCII Blob key 规则误拒 2 个文件**（含撇号 1、非 ASCII 1），无空格/路径穿越/URL 保留字符；只读分类 Job 已清理。
- 修复采用 **原始 Source 路径保持不变**，仅对 FHIR leaf 增加安全 Unicode 字母/数字与 ASCII/排版撇号；仍拒绝空格、控制符、路径分隔符、URL 保留字符、点路径；HL7 leaf 仍沿用原有严格 ASCII 条件。独立 100 Object 正向与旧负向回归、FHIR 源字节/Blob Name 原样保留测试纳入 CI，Main GHCR 发布必须重新 Clean Build 固定新 digest；旧 Publisher `sha256:a92d0661…` **不包含修复**。
- 本次代码修复的 CI/GHCR 成功不等于恢复发布成功。后续先独立确认冻结 `atlanta-fhir-gh-40245591533` Source Manifest 精确 SHA、无同 Request Azure durable writes，再采用受控只读源 Publisher continuation；仅 Task 3.6 E2E 真通过才可勾选，双院 Task 4.2 仍 OPEN。

### P3.6 — 冻结 100 名患者 FHIR Request 的受控恢复失败历史（2026-10-25，已被下文后续真实验收更新）

- 100 人 Generator 的冻结 Request `atlanta-fhir-gh-40245591533` 已完成，真实 Manifest SHA `6d12659acff1fc59e7d0739410eeed9593323f36a6e5330b9608b1591e73b529`，文件数 **100**。原 E2E [#40245591533](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40245591533) 因 FHIR leaf 不兼容撇号/Unicode 而 FAILED；当时 Publisher Job 未创建，不能视作 Azure 已交付。
- 修复 [Healthcare PR #500](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/500) 已合并 `60d0ee58a050f62045881d169290d2d10a1325eb`，所有相关 PR CI PASS。[GHCR Release #40247661319](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40247661319) SUCCESS：新 Publisher 镜像 digest `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:cfc94ce6ef7814925bfe46efa9e44730cd676d7210550ea0e21292648a342e25`，没有覆盖 latest。新代码接受真实患者文件名，保留 FHIR 原始 Source Bytes 与 Source Manifest。
- Self-Runner [PR #304](https://github.com/JohnZhang-DataForge/Self-Runner/pull/304) 已合并，包含新的 [单次冻结恢复脚本](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/scripts/azure_blob_atlanta_frozen_fhir_recovery.py)，新老 Runner 的 Publisher Digest/SHA 已同步。恢复脚本先核对源 Manifest、全局 Job/PVC/Secret 与 Azure 目标 Request prefix 为空，再创建独立新 Job，只读来源 PVC→Azure Blob，逐对象独立 GET/SHA/ETag/Manifest、幂等重试及错误 SHA 负向；不得重放旧失败 Runner Attempt，也不改历史失败 Job。
- **新恢复 Run [#40248357801](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40248357801) FAILED，未产生 Azure 写入**：严格 Main/版本/PVC/Secret/无 Active Job Gate PASS，执行在 `storage_token()` 前由于本次一次性 Workflow 中 `vars/secrets` 表达式带字面反斜杠，日志为 `HOLD_AZURE_PUBLISHER_IDENTITY_MISMATCH`；`assert_no_prior_azure_objects()` 尚未执行，新的 Source Audit/Publisher/Replay Job **均未创建**。本次失败不是 Azure Service Principal 权限变更，凭据内容未披露。**Azure Manifest 和 100 Object 的独立读回仍未完成，不得打勾 3.6**。
- 尝试修正绑定时，本轮 GitHub 工具写入被安全检查阻止，**没有强行绕过执行权限**。为防误触发，Self-Runner [PR #305](https://github.com/JohnZhang-DataForge/Self-Runner/pull/305) 已合并，**退役**上述单次 Main push 运行 Workflow；[诊断 PR #302](https://github.com/JohnZhang-DataForge/Self-Runner/pull/302) 已关闭，诊断代码未合并 Main。保留永久性手工 5/100 主 Workflow 和经验证源码，不清空成功生成的 PVC 数据，不删除旧失败 Job/ConfigMap。
- **当时的下一安全动作（历史记录，现已完成）**：先在审查可执行的授权渠道修复 Azure 变量引用、核对 Main/保护源码、共享 K8s 空闲与目标 Azure prefix **空且没有部分 Blob**，使用受控的新恢复 Run 仅发布上述冻结的 100 人 Source，核对 100 文件 + Manifest 的实际 Azure GET/SHA/ETag、同源 Retry 不变，才能将 3.6 标记完成。若任何 Cloud 写入结果未知，先只读审计，不直接重跑。Johns Creek 3.2 和双院 4.2 仍 OPEN。

### P3.6 — 同一冻结 100 人 Source → Azure Blob 最终真实验收（2026-10-25）

**状态：E2E ACCEPTED，仅完成 Atlanta Hospital A 的本次 100 人冻结来源发布。**

- [Self-Runner PR #307](https://github.com/JohnZhang-DataForge/Self-Runner/pull/307) 重新实现单次 Main Push 审核恢复入口，并直接复用原 5 人成功 Manual E2E 的三个 Azure Identity GitHub vars/secrets 绑定；PR [Hosted 静态 #40250470993](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40250470993) SUCCESS，精确源码/镜像 Pin 和“无转义反斜杠”门禁 PASS；合并后的 Self-Runner Main `d9f195eabdc34a2075379677c47afaeacf0be2ea`。
- [真实发布 Run #40250606505](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40250606505) Attempt 1 **SUCCESS**：使用 Healthcare runtime Main `18153b887a9dce033c4475c632878db1aa7c0324`，Source Base `60d0ee58a050f62045881d169290d2d10a1325eb` 不漂移，GHCR Publisher Digest `sha256:cfc94ce6ef7814925bfe46efa9e44730cd676d7210550ea0e21292648a342e25`。`NO_GENERATOR`：直接消费旧失败 Run 已冻结的 `atlanta-fhir-gh-40245591533`，Source Manifest SHA `6d12659acff1fc59e7d0739410eeed9593323f36a6e5330b9608b1591e73b529`，100 文件严格审计通过。
- Azure `johnzhang/landing` 精确 Request Prefix **PUT 前只读 LIST 证实 0 Blob**，随后发布 100 个 FHIR JSON Blob 和最终 `landing-manifest.json`；全部 100 个 Blob 独立 GET/HEAD/SHA/ETag **三轮 PASS**，Manifest SHA `7f869bd9e9b9aefa4d6ddfebaf66ce011f53afa143d33b3731bc44dc53fa8c00`，ETag `"0x8DF32FA20C8FA9A"`。同 Request `ALREADY_MATCHING` 幂等、错误源 SHA fail-closed + 100 Blob/Manifest 远端零变化、只清理本次临时 Job/ConfigMap 均 PASS，OIE/PG17/Airflow/Spark 无变更。
- 实机运行前 [K8s readonly Attempt 8](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238/attempts/8) / 运行后 [Attempt 10](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238/attempts/10) **SUCCESS**，Active Jobs=0，原失败 Run 的 Profile ConfigMap 仍剩 1 个但属于历史冻结对象，不在本次清理范围；未删除原 PVC/Blob。
- [Self-Runner PR #308](https://github.com/JohnZhang-DataForge/Self-Runner/pull/308) 合并 Main 并**移除**用过的单次自动恢复 Workflow，避免再次因 Main Push 重复调用。原两次失败 #40245591533 / #40248357801 历史结论仍为失败，最终成功的唯一证据是新的 Run #40250606505。
- [完整 100 Object + Manifest Source/Digest/ETag/GET 验收证据](evidence/ATLANTA-FHIR-100-AZURE-FROZEN-SOURCE-LIVE-E2E-20261025.md)。**3.6 CHECKED**，**3.2、3.3、4.2 仍 OPEN**，不能替代 Johns Creek HL7 或 Fabric 后续装载。


### 2026-10-27 — Task 3.2 新批次 OIE HL7 → Blob 代码/文档一致性审计及候选桥接

- **已核实现行 Main 的事实**：`azure_blob_runtime.py` 只支持 DIRECT FHIR；`oie_hl7_publisher.py` 的完整来源关联和不可变 Blob adapter、`oie_persisted_readback.py` 的指定 Message GET/TLS/scoped cookie client 已在 Main，属于离线通过、**非** Johns Creek Azure Live E2E。
- **文档纠偏**：本文件旧总标题中『只有规划/无任何 Azure Blob Publishing』是早期快照；Atlanta 已真实通过 5/100 FHIR Blob + Manifest GET/SHA/ETag；旧 OIE 32 条历史消息只能作为测试证据，不能复用。后续必须以新 Request + 新的已部署 Channel 签名/Assigning Authority 实机检查为准。
- **本候选实现（仅分支，未声称 CI/Live PASS）**：新增 `hl7_blob_runtime.py` 把独立 Runner 当次新消息收据 → `OIEScopedHTTPSClient` 精确 ID GET → `prepare_oie_hl7` → `publish_immutable` 串接，要求 `johnscreek-hl7-gh-<runner_run_id>`、外部 Source Manifest SHA、医院/Feed/Channel 严格绑定；只接收 Channel/Message 数字 ID，不扫描 OIE 记录，不提交/重放 FHIR，任何源/ID/HL7 检验失败都在 Azure 初始化前阻断。加入同 Namespace 现有 Generator PVC 只读的**静态** HL7 Job 模板、Mock 端到端与现有 Hosted CI。
- **硬性未完成**：需要独立受控 Self-Runner 本次真实 FHIR Generator→新版 OIE Channel POST，记录并独立核验真实 messageId/receipt 来源；生产 scoped OIE 非 admin 账户、匹配 Service DNS 的可信 CA/TLS、真实已部署 Channel 版本检查；新的不可变 Publisher 镜像 Digest 和精确 Main/Runner SHA；真实 Azure Blob GET/Manifest、无重放的幂等验证。ConfigMap 中的收据 JSON **单凭自身无法证明**来自真实新 POST，Runner 必须同次产生并保护；任何 POST ACK 不明需 HOLD，不盲目重试。
- **本阶段验收标识**：`CODE_CANDIDATE / CI_PENDING / OIE_SCOPED_IDENTITY_UNVERIFIED / AZURE_HL7_NOT_RUN`。不得勾选 3.2、3.3、4.2、2.5 或把旧 OIE 32 条消息拿来填充新 Run 收据。


### Johns Creek HL7 Publisher immutable image release (2026-10-27)

- Healthcare PR #534 已于 Main 合并 `37c3cc0d100e5f9e996a76f7d30f42f62d3e9b65`，现有 `hl7_blob_runtime.py` 通过 Host-only Mock/Azurite 验收。此前 GHCR `sha256:cfc94...` 属旧 DIRECT FHIR 源码，**不包含 HL7 新入口**。
- 本候选 PR 更新唯一 SHA-only Publisher release workflow 的 Host CI：增加新的 OIE scoped readback 与 HL7 runtime 完整离线测试；Docker 非 root/无网络、只读 Smoke 强制 import HL7 runtime 并运行其 `--help`。此工作流已有 Main-only SHA 标签、Digest 发布验证，**仅 workflow 路径推送到 Main 后触发一次真实 GHCR 镜像发布**；仍不创建任何 K8s Job/Secret，也不发布 Azure Blob。
- 发布流程必须实际完成 Main Push Run、Digest 单独核对后，才把新镜像标为 `GHCR_RELEASE_PASS` 并给后续受控 Self-Runner 使用；PR CI 和 Host Docker 成功不是 Registry Digest。Johns Creek 3.2/4.2 保持 OPEN。


### 2026-10-28 — Johns Creek新冻结FHIR→OIE提交端代码候选（尚未实机）

- 新增`oie_message_submit.py`：沿用已验收 `source_handoff.verify_handoff`，绑定`johnscreek-hl7-gh-<run_id>`与外部 Source Manifest SHA、Hospital/Feed；读取并校验全部冻结 FHIR Bundle、完整 Encounter 数量与唯一 ID，在**任何** OIE POST 前严格拒绝缺失/篡改。使用 OIE scoped 非管理员账号 + 可信 CA HTTPS，逐条传递 Patient+Encounter Envelope 到**已经实机证实正确的**指定 Channel，仅将真实 OIE 数字 Message ID/源 Encounter 输出给同一 Runner。单次 POST timeout/ACK不明或部分成功均`HOLD_NO_RETRY`，不自动重复上游消息、不触碰历史 32 条 Derby。
- 新增同 Namespace worker01 / Generator 只读 PVC 静态 Sender Job `submit-oie-new-fhir-job.yaml.tpl` 及离线负向测试；现有 Azure Publisher SHA-only Workflow 扩充真实镜像 OIE POST 模块 Import/无网络 CLI Smoke，**该PR合并才触发新 SHA/Digest 构建**，尚未验收Registry。
- 此新增源码不等于完整受控 Self-Runner Controller 或授权：仍待用户执行的真实只读 OIE Channel/TLS/权限实机核对、新 batch生成/审核、新消息一次提交/完整收据捕获、Blob远端独立 GET/ETag/SHA/Manifest、幂等。OpenSpec 3.2/3.3/4.2和OIE 2.5均保持 OPEN。


### 2026-10-28 — Independent GHCR publisher image digest audit (no live effects)

- Exact main source SHA for Johns Creek sender+publisher: `17ead446d8b1364ea2be89937599fc7764f0aa45` (merged PR #538). SHA-only publisher release uses an image label; PR static builds are **not** proof of the actual GHCR digest.
- New `.github/workflows/hl7-ghcr-immutable-digest-readonly.yml` runs GitHub-hosted on PR and authenticates to GHCR with read-only token, pulls only `git-<exact_main_sha>`, checks actual registry Digest + `org.opencontainers.image.revision`, non-root 10001, and imports both `oie_message_submit` and `hl7_blob_runtime` from the same immutable digest (no network inside test container).
- Publish `PUBLISHER_IMAGE_DIGEST_REF` in Run logs and summary only **after** real GHCR pull/verification succeeds; do not synthesize digest from Docker build or code SHA. This is `GHCR_READ_ONLY_AUDIT`; separate worker01/OIE Scoped User/TLS/channel real checks still mandatory. OpenSpec 3.2/3.3/4.2 remain OPEN until Azure live READBACK.

- **Verified real GHCR pull**: [Healthcare Actions #40669656471](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40669656471) SUCCESS; exact immutable Registry digest `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:fbdf32130ea5cc1d8fcec0258022100b5ae06a1ef95d573314b3af7eb242f590`, OCI revision `17ead446d8b1364ea2be89937599fc7764f0aa45`; both sender/publisher imported from pulled Digest on a no-network, non-root container. This verifies image packaging, not Johns Creek live Blob publishing.


### 2026-10-28 — Johns Creek actual infrastructure/TLS/RBAC evidence (live delivery remains HOLD)

- **Immutable GHCR proof (completed):** separate registry audit [Healthcare #40669656471](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40669656471) actually pulled `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:fbdf32130ea5cc1d8fcec0258022100b5ae06a1ef95d573314b3af7eb242f590`, verified revision `17ead446d8b1364ea2be89937599fc7764f0aa45`, nonroot 10001, no-network OIE sender + HL7 Publisher imports; code PR #538 Main `17ead446...`; GHCR status is `REGISTRY_DIGEST_VERIFIED`, **not** live HL7 acceptance.
- **Actual worker01 read-only gate (completed):** User-triggered Self-Runner [#40668247431](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40668247431) first failed at missing `kubectl` before any cluster GET; fixed via Self-Runner PR #322 Main `f43a79906744e391a27576b816da6f2204bc0e66`; next Main-push [#40670186919](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40670186919) PASS: worker01 Ready, Generator/OIE PVC Bound, OIE Service 8443 and Deployment Ready, Azure Publisher Secret keyset correct, zero active Jobs.
- **Actual OIE certificate probe (completed, decisive fail-closed):** read-only TLS/SAN [Self-Runner #40670663820](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40670663820) verified TLS handshake `PASS` but existing OIE server cert lacks DNS SAN for `oie-debug.dw-oie.svc.cluster.local` (`False`). GitHub variables `OIE_SCOPED_SECRET_NAME`, `OIE_CA_SECRET_NAME` unset; there is **no evidence** of a trusted OIE client identity, server hostname verification or Channel deployment signature. These are real HOLD blockers, not an Azure Blob defect.
- **Identity clarification:** Official OIE Administrator docs: https://docs.openintegrationengine.org/engine/accessing_the_administrator.html say by default all users are administrators without the RBAC extension, even when not named `admin`. Never claim a separate named OIE account is channel-scoped without verified RBAC. Official RBAC release notes: https://www.openintegrationengine.org/news/rbac-plugin/ ; version compatibility and first-run Derby schema changes need separate review before install.
- **Protect persistent storage:** OIE `keystore.jks` and embedded Derby live on the preserved `dw-oie/oie-state` PVC. Replacing keystore in-place can risk loss of secrets used to encrypt old persisted messages; do not rotate it without verified backup and explicitly authorized maintenance. A separate restricted TLS gateway may avoid modifying existing keystore, but backend OIE admin privilege persists unless enforced by RBAC; must not misrepresent that as native role scoping.
- **Manual controller is code-ready but not live-deployed:** [Self-Runner Draft #321](https://github.com/JohnZhang-DataForge/Self-Runner/pull/321) binds exact verified Healthcare SHA + GHCR digest; hosted static [#40669974480](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40669974480) PASS, live Job intentionally skipped. It has not been merged or triggered for data writes. Do not run 5-person new Request before user explicitly approves an OIE TLS/identity architecture and coordinated shared K8s OIE change window.
- **NEXT mandatory decision/gates:** (1) choose native OIE 4.7-compatible RBAC plus verified TLS rotation/backup, or an isolated documented API gateway enforcing method/path/channel controls with trusted TLS (but **not** native RBAC); (2) separately authorize exact K8s/Secret/Channel operations and check concurrently active jobs immediately before execution; (3) verify actual scoped API GET/POST and deployed Johns Creek mapper, then run brand-new batch once, commit new signed receipts, remote Azure independent GET/SHA/ETag and immutable Publisher-only retry. Never replay historic OIE 32 messages, never bypass TLS trust silently.
- Status `CORE_INFRA_READONLY_PASS / GHCR_DIGEST_VERIFIED / OIE_TLS_SAN_MISMATCH / OIE_SCOPED_RBAC_UNVERIFIED / JOHNS_CREEK_AZURE_LIVE_HOLD`. Keep Tasks 3.2, 3.3 and 4.2 unchecked.


### 2026-10-28 — Faster internal-only OIE admin/TLS compatibility path

- User authorized using existing OIE admin identity in internal Kubernetes (no native RBAC requirement), prioritizing Emory demo E2E speed. **No independent Gateway** because direct existing internal ClusterIP is fewer deployment components and less code.
- `OIE_INTERNAL_ADMIN_MODE=1` is opt-in only from Johns Creek Sender/Publisher Jobs. Client loads a **single observed OIE server leaf certificate as trusted CA**, keeps TLS certificate validation, but disables hostname matching because existing OIE cert has no Kubernetes Service DNS SAN. It does **not** use `CERT_NONE` for authenticated API calls, edit OIE PVC/Derby/keystore or publish admin endpoint externally.
- Existing `OIEScopedHTTPSClient` strict mode remains unchanged if env flag absent. Only `dw-synthea` scoped new admin credential/cert Secrets are introduced by the separate Self-Runner bootstrap after live admin/Channel preflight, with no encoded values in CI logs. This is an internal MVP tradeoff, **not OIE native RBAC**.
- Rebuild exact GHCR SHA-only Publisher image after Main via reviewed existing release workflow; the previously verified `fbdf3213...` image does **not** have this opt-in. Pin new digest before live. Johns Creek real Task 3.2/4.2 still OPEN until actual OIE ACK and independent Azure GET/Manifest.


#### 2026-10-28 — OIE existing leaf not a valid CA; exact certificate pin compatibility
- Self-Runner live bootstrap #40675672176 reached `TLS_PUBLIC_LEAF`, then `SSLCertVerificationError` when treating OIE existing leaf as normal CA trust. No OIE/Azure messages or persistent OIE modifications occurred. For the user-approved internal-only admin MVP, change `OIE_INTERNAL_ADMIN_MODE=1` to enforce **per-connection SHA256 pinned peer DER certificate** before any HTTP request (including admin login); do not use OS trust chains or DNS SAN, and do not modify the old OIE keystore. The explicit pin is carried by a new immutable `dw-synthea` Secret. TLS is encrypted but does not use CA validation in this mode; identity is validated by the exact pinned leaf. Strict default mode still validates CA/hostname. Separate Runner bootstrap and GHCR release must be rebuilt before E2E. Task 3.2 remains OPEN.

- 2026-10-28 Final pinned OIE leaf fingerprint fix Main `55e8023c3521cb80a2c0ec3574fce7a3f05d6b91` needs independently inspected GHCR SHA tag/Digest. Read-only audit below records actual registry pull, not speculative digest, before Self-Runner E2E controller updates.


### 2026-10-28 — Two-hospital Azure Landing live acceptance (supersedes historical HOLDs above)

- **Hospital A / FHIR Direct:** independent Atlanta 5/100 real Blob object/Manifest GET/SHA/ETag/immutable recovery runs #40238053772 and #40250606505 (not rerun here).
- **Hospital B / OIE HL7:** new 5-patient Johns Creek [Self-Runner #40715594941](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40715594941), SUCCESS; source 136 Encounter, 136 new OIE Message ID receipts, 6 IMP→ADT^A01, 130 non-inpatient explicit SKIP, 6 immutable Azure HL7 objects independently GET/HEAD/SHA/ETag and final Manifest GET/ETag, **Publisher-only repeat returns same committed objects**, no OIE replay. Unique Request `johnscreek-hl7-gh-40715594941`, actual source SHA `3f997d301a92457985b8aaa7945cf6367935f701cda41265d72de1cc4cedf229`, Azure Manifest SHA `5ee8b78f5307bdeedfcdde76b2d9b15289ce6a2ea5242baddfc34d9f8219f193`, ETag `"0x8DF3507BA545A58"`. Existing OIE Channel/Derby/PVC unchanged; own ephemeral ConfigMaps/Jobs cleaned. [Full bounded evidence](evidence/JOHNS-CREEK-HL7-5P-AZURE-LIVE-E2E-20261028.md).
- **Inputs are NOT hardcoded:** Self-Runner PR #332 parameterized the reusable Workflow with `hospital_profile`, `population=5|10`, optional `seed` and `reference_date`; new source request ID generated from exact GitHub Run ID. One-time historical 100-person dispatch removed in PR #335, and failed 100-person Run #40684333118 left unchanged. Current validated OIE integration remains **Johns Creek Channel only**; other profiles require independent integration proofs.
- **Tasks 3.2, 3.3, 4.2, 4.3 accepted within landing scope.** Older 3.2/4.2 unchecked entries and "No live HL7" statements above were historical and are superseded by this exact new Run. 4.1 Terraform RBAC/IaC, 4.6 OIDC short-lived Secret handoff and 4.7 Service Principal rotation/complete governance remain **OPEN**, as do downstream Fabric/OMOP, public Portal and any expanded hospital source deployments. Do not archive the Change while those independent tasks remain unresolved.


### 2026-10-28 — New user-requested 50-person HL7 incremental batch (separate acceptance)

- The validated 5-person Johns Creek Run #40715594941 generated **136 Encounter** resources. A fresh 50-person cohort can exceed the original 1,000-event sender/audit cap; this is a *limit issue*, not a reason to change hospital or generate fixed data within the workflow.
- Raise bounded `oie_message_submit.MAX_EVENTS` to 5,000 while retaining **frozen source SHA, full Encounter count, unique ID, zero POST before complete audit, no retry of ambiguous OIE POST**, and independent immutable Azure readbacks. Self-Runner controller's matching source-audit cap must be aligned. The 50 people are supplied as the reusable workflow **population input**; default 5 and optional 10 remain. Build a new immutable Main-only Publisher image and prove its real Registry Digest before triggering new source.
- This prospective 50-person batch remains **NOT EXECUTED / NOT ACCEPTED** until its own fresh Run ID, full OIE Message IDs and Blob SHA/ETag/Manifest receipts are checked. Existing 5-person accepted Run #40715594941 and failed 100-person Run #40684333118 are separate and must never be replayed.


### 2026-10-28 — NEW Johns Creek 50-person HL7 Azure incremental batch: LIVE PASS

- [Self-Runner main Run #40731892374](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40731892374) SUCCESS after a new parameterized `hospital_profile=johns-creek-hl7` / `population=50` invocation from [#40731847060](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40731847060). Unique new Request `johnscreek-hl7-gh-40731892374`. Original 5-person Run #40715594941 unchanged; failed 100-person Run #40684333118 never replayed.
- Real frozen source audit **1,941 Encounters**, including **21 inpatient**; new OIE Message ID ACK receipts **1,941**; Azure published **21 actual HL7 ADT^A01 objects** and skipped **1,920 non-admission Encounters**. Thus 1,941 source events ≠ 21 Azure artifacts, as intended.
- Independent remote `AZURE_HL7_INDEPENDENT_OBJECT_GET_SHA_ETAG=21`, `AZURE_HL7_INDEPENDENT_MANIFEST_GET_SHA_ETAG=PASS`, `SAME_HL7_REQUEST_BLOB_IMMUTABLE_IDEMPOTENT=PASS` (Publisher-only retry), `JOHNS_CREEK_RUN_SCOPED_EPHEMERAL_CLEANUP=PASS`, `JOHNS_CREEK_HL7_AZURE_LANDING_E2E=PASS`. Source SHA `a0d81382b2075bfe4164d867bf7dd823dd32d4384181782f4d0b8b5e0e312317`, Azure Manifest SHA `d7d234181e6af05f871c07c5eb04931d5baef85b317a87e6e8df7da98a64de23`, ETag `"0x8DF3515A1EE1C78"`.
- Bounded code: Healthcare PR #548 increased `MAX_EVENTS` to **5,000**, exact Main source `875d5e93ee49df66bd26eee097c9c96a609f7ce3`; actual SHA-only GHCR release #40731253810 `sha256:ba8dbf51347f05f58db9af0e5777a125df571ab67644bad7d7fb7f0b15857ead`. Self-Runner PR #340 extended reusable Workflow parameter choice to `5/10/50` with default **5**, not fixed data. [Detailed real live evidence](evidence/JOHNS-CREEK-HL7-50P-AZURE-LIVE-E2E-20261028.md).
- This is **additional scale acceptance** supporting already checked landing tasks 3.2/3.3/4.2; does **not** close still-open Fabric/OMOP, OIDC/Secret governance, Azure Terraform or public Portal tasks.
