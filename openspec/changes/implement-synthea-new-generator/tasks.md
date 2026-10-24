# Tasks — Independent synthea_new_generator

> **状态：ACTIVE / P1、P2 已合并，P3 4.1–4.4 已通过 GHCR 发布与受控 K8s Live 验收；P4 待开发。** K8s 新生成器已经独立运行，**不声明 FHIR→OIE、Azure Blob 或 Fabric 已完成**。原 `apps/synthea/new_only/` 及 OMOP 链路绝不因本 Change 改写。

## 1. P0 — OpenSpec design and baseline

- [x] 1.1 只读核对当前 Healthcare Main、旧 `generate_new_only.py`、Synthea 基础镜像、旧 S3 发布合同与 OpenSpec/命名/CODE Map 治理；明确旧 NEW_ONLY 不动。
- [x] 1.2 建立本独立 Change 的 Proposal、Design、Delta Spec、Tasks；冻结 `synthea_new_generator` 参数化/本地生成接口、Atlanta/Johns Creek 两 Profile 和下游 OIE 边界。
- [x] 1.3 本 OpenSpec PR 在精确 Head 上通过 Strict Validation、Trusted Change Gate、文档链接等适用检查；合并后核对 Main 与 PR/CI 证据。**仅规划成功，不等于业务实现。**

## 2. P1 — Request and frozen-generation core

- [x] 2.1 定义 `contracts/synthea/new-generator/` 的 request-v1 / generation-manifest-v1 JSON Schema；验证 request_id、mode、人口、州/城市、日期/Seed、输出格式、路径、版本与 fingerprint。
- [x] 2.2 新增 `apps/synthea/synthea_new_generator/` 的统一 CLI、参数解析与 Synthea v3.3.0 CLI argument builder；仅 NEW_ONLY，CSV、FHIR 或两者可选。
- [x] 2.3 实现独立持久请求冻结、本地隔离临时输出、完整文件核验、Manifest-last 和失败/重试逻辑，禁止同请求参数漂移及静默覆盖。
- [x] 2.4 单元/合同负向测试：非法值、模式拒绝、重试、SHA 篡改、半成品、不同请求/并发隔离和无外部云/数据库调用。

## 3. P2 — Real Synthea formats and hospital profiles

- [x] 3.1 使用固定 Synthea 版本实际运行 CSV-only、FHIR_R4-only、CSV+FHIR，核验 Bundle/Patient/Encounter/Reference、真实文件清单与计数；记录不支持的 Synthea 参数或输出差异。
- [x] 3.2 为 Atlanta/FHIR 和 Johns Creek/HL7 两个**独立生成请求**建立外部配置 Profile，均从 FHIR R4 起步；运行验证 Georgia Atlanta/Johns Creek 地理参数，不暗中回退州/城市。
- [x] 3.3 验证不同医院 Profile/请求重试互不影响，新医院 Profile 不要求修改 Generator 代码；保持医院/Feed ID 与文件交付元数据由外部组件管理。

## 4. P3 — Package and isolated Kubernetes jobs

- [x] 4.1 建 `images/synthea-new-generator/`，引用固定 Synthea parent digest/commit；只安装最小 Runtime 依赖，无 OIE/Azure/PG 客户端或 Credential。
- [x] 4.2 建 `kubernetes/manifests/synthea/new-generator/` 独立 Job/存储配置、最小权限、资源限制、显式镜像 Digest；不动 `synthea-new-only-state` 和旧 NEW_ONLY 工作负载。
- [x] 4.3 按仓库强制源码地图规则同步 `documents/systems/data-platform/synthea/CODE.md`、相关组件文档和适用 CI；绑定真实 PR Head、镜像构建/测试证据。
- [x] 4.4 经授权和资源协调运行真实 K8s Job；已在 worker01 验证状态、FHIR Bundle/Patient/Encounter 数量、持久 Manifest 文件 SHA256、同请求幂等、独立 Retain PVC 及旧 PVC 身份未变。证据见 Run #40100347980。

## 5. P4 — Handoff and finish

- [ ] 5.1 定义 Producer 本地完成状态与 FHIR 下游读入合同；验证 FHIR Generator 本身不依赖 OIE、Blob Publisher、Fabric。
- [ ] 5.2 与后续 FHIR→OIE PoC Change 约定实际 FHIR Bundle 输入与 ADT 事件映射验收，真实转换未证实前不宣称 HL7 生成成功。
- [ ] 5.3 由独立 Change 更新现有多来源总体设计中已过时的共享 Cohort/三医院叙述、建设 FHIR/HL7 Publisher/Fabric；在本 Change 仅记录其新生成器边界被覆盖，不伪造上下游运行状态。
- [ ] 5.4 全部代码、适用测试、实际运行证据和最终 Main 验证完成后，才考虑同步 Current Spec / Archive。

**执行规范**：后续每个实施 PR 在 PR Body 单独声明 `OpenSpec-Change: implement-synthea-new-generator` 与真实 `OpenSpec-Task: n.n`，且同 PR 更新本 `tasks.md`。静态/本地测试无需写共享 K8s；对共享环境操作必须先读 Safe Operations / Session Coordination 并取得相应明确授权。


### P1 实施记录（本 PR）

- 已实现源文件：`apps/synthea/synthea_new_generator/{request,generator,entrypoint}.py`，v1 JSON Schemas、本地 Manifest/冻结/幂等安全检查及 Stub/负向单测。
- 新增仅 CPU 的 PR 工作流 `.github/workflows/synthea-new-generator-unit.yml`；此处不依赖真实 Java Synthea、Kubernetes、Azure/OIE/Fabric。
- P1 的 `2.1–2.4` 已覆盖源码、Mock/负向/并发单测；本 PR 最终 HEAD 的 CI 结论另以实际 Run 校验，不将 Stub 执行视作真实 Synthea/JAR、FHIR Bundle、州/城市匹配或镜像/K8s 的验证。P2/P3 仍保持未完成。


### P2 实施记录（Profile / 实体 Source Smoke PR）

- Atlanta/FHIR 与 Johns Creek/HL7 由两个独立 Profile 管理：同一个 `synthea_new_generator` 统一执行 `FHIR_R4` 原生生成，下游以 `DIRECT` 或 `OIE` 区分，不在 Generator 中引入医院/OIE 分支。
- 本 PR 新增 Profile Adapter、Schema、单测及 GitHub-hosted 隔离 Synthea Source Smoke；任何临床事件→ADT 转换与 Blob Publisher 均不在此 PR 中。
- GitHub-hosted 真实 Synthea Smoke [Run #40095976490](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40095976490) 已在功能源码 SHA `a347454b16e6c93804e399543b46ce6dfcb4a4ac` PASS：pinned v3.3.0 upstream `995cf2fd33e67918d4e33110d9f68ad248002221`；Atlanta FHIR 1 Patient/43 Encounter/1 Bundle；Johns Creek FHIR 1/31/1 Bundle；Atlanta CSV 1/43/18 CSV；combined 1/43/18 CSV + 1 Bundle；同请求 FHIR readback/replay PASS。外部 Profile 单测和 CI 全部通过。该执行只发生在 GitHub-hosted 临时环境，未触发共享 Kubernetes/OIE/Azure/PG。后续提交后的 PR HEAD CI 需单独核实。

**P0/P1 Merge 证据**：OpenSpec PR [#414](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/414) Main `0f808fca1a7ac80308859cde27cd5838082185bb`；P1 代码 PR [#417](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/417) Main `8e075bca130429c261a0f2cf245daef83ba8eebf`，受信任 OpenSpec / Component Map / Unit 测试通过。本 P2 对应 PR [#418](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/418)，完成合并后核对最新 Main。


### P3 package/CI PR 记录（待证据复核）

- 新增 `images/synthea-new-generator/Dockerfile`：父镜像使用经验证的 Synthea v3.3.0 不可变 `@sha256`，镜像内仅增加 Generator 源码，不引入旧 NEW_ONLY Writer 或 Azure/OIE 客户端。
- 新增 `kubernetes/manifests/synthea/new-generator/{pvc.yaml,generate-job.yaml.tpl}`：独立 PVC、强制 Digest/ConfigMap 占位符、最小运行权限、非 root、readOnlyRootFilesystem、受限 CPU/内存/磁盘、无 ServiceAccount Token。
- 新增 `synthea-new-generator-image-smoke.yml`：静态合同 → GitHub-hosted Docker 无缓存构建 → 新镜像真实 Atlanta 和 Johns Creek FHIR 生成 → 本地文件 SHA 读回与同请求重复执行；不触发共享集群、PG、S3、OIE、Azure 或 GHCR 写入。
- 4.1–4.3 代码/CI 证据见 PR #420；`4.4` 必须另行授权共享 K8s、核对资源占用，并执行真实 Job 与独立持久化读回，目前保持未验证。

**P3 独立镜像真实验证（PR #420）**：首次构建镜像/实际生成均成功，但宿主 Runner 尝试读取 UID 10001、0600 Manifest 被正确拒绝（CI FAIL），修复为独立无网络、只读挂载容器以同一非 root UID 读取后，最终测试 PASS。已观测父镜像 `ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2ef13ae77d476983ea88a5377570190859f253c9f98eb0652ebc793ef685b6b1`，源固定 Synthea `995cf2fd33e67918d4e33110d9f68ad248002221`；新镜像本地 Image ID `sha256:01ffcc673bbccde5c0720ab5bdf11522beebfe8930f4a6d470fdcf351bbbced8`；Atlanta FHIR: 1 Patient/43 Encounter/1 Bundle；Johns Creek FHIR: 1/31/1 Bundle；重复请求 0 漂移；双 Manifest 独立 SHA 校验 PASS。以上镜像 **尚未推送 GHCR**，Kubernetes **尚未部署/读取**，Blob/OIE/Fabric **尚未执行**。本地 Docker Image ID 不可用作集群部署的 Registry Digest。

### P3.4 GHCR 发布（本次已获用户授权）

- 新增 [独立发布 Workflow](../../../.github/workflows/synthea-new-generator-ghcr-release.yml)：仅 Main、固定父镜像 Digest、独立生成 FHIR 并验证 SHA 后发布唯一 `git-<MainSHA>` GHCR 标签，绝不修改 `latest`。
- **不在 Merge 前勾选 4.4**：成功发布还需要记录 GitHub Run、实际 Registry Digest；真正 K8s PVC/Job 及重试/读回必须由 Self-Runner 独立受控验证。

### P3.4 实际 K8s 接入修正（2026-10-24）

- GHCR Main-only Release [#40099221313](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40099221313) PASS：发布独立版本 `git-2209f350fcb3feb67969f2a5e34f1cd4b64b1100`，Registry Digest `sha256:7aeb7dab50611a39953e59eb8032446087208fed8d01fb4795580138bb040f7e`，未覆盖 `latest`。
- 首次 Self-Runner Live Run [#40099579358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40099579358) 集群安全预检 PASS，建立新的 10Gi PVC 后在 Job 模板渲染阶段阻断，未创建 Job；PVC 按 Retain 保留。
- 第二次 Live Run [#40099715955](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40099715955) 固定镜像已被 worker01 成功拉取、运行；但 ConfigMap 目录投影的 `request.json` 是符号链接，与 Generator 强制拒绝符号链接的合同冲突，报 `INVALID_REQUEST_FILE`，K8s Job FAIL。未生成本地 Patient、也未写 Azure/PG/S3。已确认旧 PVC 未动，新 PVC Bound。
- 最小修复：Job 模板将只读 ConfigMap 的单个键使用 `mountPath: /inputs/request.json` + `subPath: request.json` 挂为普通文件；保持原 Generator 严格拒绝符号链接的安全规则不变。经 PR #423 修复和 Main SHA 固定后由 Live Run #40100347980 复验通过；该句所述失败过程保留为历史。

### P3.4 生产前隔离部署验收闭环 — 已通过

- **GHCR 正式发布**：Healthcare [PR #421](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/421)、[Run #40099221313](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40099221313)，源 Main `2209f350fcb3feb67969f2a5e34f1cd4b64b1100`。唯一标签 `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-generator:git-2209f350fcb3feb67969f2a5e34f1cd4b64b1100`，Digest `sha256:7aeb7dab50611a39953e59eb8032446087208fed8d01fb4795580138bb040f7e`，未更新 `latest`。
- **失败修复证据保留**：Self-Runner [Run #40099579358](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40099579358) 的 Job 模板渲染断言阻断；[#40099715955](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40099715955) 的 ConfigMap 目录符号链接输入触发 `INVALID_REQUEST_FILE`。仅清理本轮创建的失败 Job/ConfigMap/临时拉取 Secret，持久 PVC 保留。修复标准模板 [Healthcare PR #423](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/423)，Main `45ae41dd364eb9771c7d22ab29030d40eb65ecb4`，通过 `subPath: request.json` 正常提供只读普通文件，Generator 安全逻辑未放宽。
- **实际验收 PASS**：Self-Runner [Run #40100347980](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40100347980)，Self-Runner Workflow 源 SHA `6d1ce2975838d3a4bebfb3a890781c8050913abc`，固定 Healthcare `45ae41dd364eb9771c7d22ab29030d40eb65ecb4` 和上述 GHCR Digest；`dw-synthea/worker01` 的 Request `p34-atlanta-40100347980` 实测 1 Patient、43 Encounter、1 FHIR Bundle，`SOURCE_GENERATED_VALIDATED`、重复请求无重新生成、SHA256 独立读回全部 PASS。
- **状态与安全边界**：`synthea-new-generator-state` (10Gi, `synthea-local`, Bound) 的新 PV `pvc-00a9270b-cf8d-44aa-8f46-f882c85d637b`，ReclaimPolicy=Retain；旧 `synthea-new-only-state` PVC UID/原 PV 前后不变。临时 Job、ConfigMap、GHCR 拉取 Secret 已清理，持久数据保留。未执行 OIE、Azure Blob、Fabric、S3 或 OMOP PG 写入；P4 和上游医院文件交付尚未实现。此 Live 验收**只覆盖 Atlanta 的 1 人 FHIR NEW_ONLY**，Johns Creek 有先前真实 Docker Smoke 证据但尚无单独 K8s Live 数据批次。
