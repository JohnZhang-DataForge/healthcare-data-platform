# Tasks — Reuse Native Marquez Public Showcase

> ACTIVE / DOCS AND OFFLINE DEVELOPMENT FIRST. 初始方案批准不等于 Kubernetes/Tunnel/Marquez 公网实际部署授权。PR Body 必须单独声明 `OpenSpec-Change: reuse-marquez-public-showcase` 与本 Change 中唯一一个任务 ID；所有实现 PR 同步修改自己的任务行。跨 Session 合并由 Coordinator 执行。

## 0. Formal Change & Coordination
- [x] 0.1 确认用户选择现有官方 Marquez Web 作为公网只读首版，核对 2026-10-25 内网 Table/Column 真实证据、GitHub 最新 Main、OpenSpec/Agent 规则；创建 Proposal/Design/Specs/Tasks/并行 Agent 分工及手工 Cloudflare 初稿。本项仅文档 CI/Main readback 闭环。
- [x] 0.2 主 Session 在旧 `healthcare-on-demand-live-demo` 标记首版静态 Web/Marquito 路线被本 Change 取代（不勾选旧任务为真实 Done），保留 Blob Relay、Fabric HOLD 和后续按需触发；关闭或暂缓过时的 Agent A PR #518/#519，保留历史研究 PR #526。 **已由 [PR #528](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/528) 将旧 Change 标记首版被替代，Main `06fb3f1135696b4f47f810d994fa9e69be1db7e4`；旧前端 PR #518/#519 均关闭、未合并，#526 研究 PR 历史资料已合并；未操作运行环境。**

## 1. Native Marquez UI / API Audit (Agent M1)
- [ ] 1.1 只读核对现有 Marquez 0.51.1 原生 Web/API 的真实请求矩阵、必要静态资源、Home/Jobs/Run/Dataset/Table/Column 功能及已知展示不完整边界，输出有代码证据的审核报告，不动既有 Helm/K8s。
- [ ] 1.2 确认首版是否 **零 UI 代码更改**即可交付；仅如必要，再独立建议最小 UI 调整和禁用按钮，但不把隐藏按钮当后端保护。

- [ ] 1.3 **Dedicated Public Web image (CODED, NOT DEPLOYED)**: 基于 Marquez Web 0.51.1 的固定官方镜像，在 `platform-portal/portal/web/` 创建只读展示 Overlay，隐藏 Job/Dataset 删除、Tag 编辑/删除、Tag Submit 和目前被 Gateway 拒绝的 raw Events 页面入口；保留 Dashboard、Jobs、Datasets、Run History、Table/Column Lineage 与只读导航/缩放/刷新。独立 GHCR 构建 Workflow + 离线测试。镜像实际构建、发布和公网切换须按对应证据验收；未经授权不改本地 Gateway/Tunnel/K8s。本项不因代码入 PR 即勾选。

- [x] 1.4 **LAN 前置只读核查**：2026-10-28 UTC [Self-Runner #40623915046](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40623915046) 通过；`dw-marquez` 原 Marquez API/Web/Gateway、原 NodePort 30999 存在，独立新组件不存在，NodePort 31080 未占用，节点 Ready、无 ExternalIP，检查时 active K8s Jobs=0，部署 RBAC 可用。只读，不修改集群。
- [ ] 1.5 **Public Web LAN isolation rollout**：从已发布 GHCR digest `sha256:2ae03240ed5297f6bfaab08bc37d7752c43c0175b112ae02a7f19de3b4abeebf`，仅创建 `dw-marquez` 中新 Deployment `marquez-public-web`、Service `marquez-public-web` (ClusterIP)、Service `marquez-public-web-lan` (NodePort 31080)，保持原 30999、Gateway、Cloudflare 上游完全不变。K8s YAML: `platform-portal/portal/web/kubernetes/lan.yaml`。正式 rollout/探针/GET/API/GUI 独立读回后才可勾选。不可凭 YAML/PR 完成标 Done。

- [ ] 1.6 **Public Web Datasets UX (CODED; IMAGE/LAN NOT VERIFIED)**: 首次进入 Datasets 且浏览器没有历史 Namespace 选择时选择 `s3://health-processing`，保留用户手动选择、Jobs 原筛选语义。仅对完整可解析的 Processing Dataset 将重复的 Namespace/Source 可见列替换为 Batch/Ingest Date，Entity + Run 展示在 Dataset 名称区域，保留 Updated At、Quality、Column Lineage、原始完整 URI/链接及 tooltip。原 Marquez Namespace、Source 独立保留在 tooltip，`source=synthea` 标记 Producer 而不是混作 Marquez Source；不认识的路径退回原版。源码/测试 `platform-portal/portal/web/`；Build/CI/运行浏览器真实验收之前保持 OPEN。不能直接修改 30999、31080、Gateway 或 Tunnel。

- [ ] 1.7 **Public Web LAN image refresh**：2026-10-28 PR #545 合并 Main `b3d48bd0ba8010bf2e7d559eee47031597f6a104`，镜像构建发布 [#40686987016](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40686987016) PASS，Digest `sha256:483f115e3be0b69c755b07982d714319646bd124d3804645541e367222a97317`。受本次用户授权，将 `dw-marquez/Deployment/marquez-public-web` 的 `public-web` 镜像从旧固定 Digest `sha256:2ae03240ed5297f6bfaab08bc37d7752c43c0175b112ae02a7f19de3b4abeebf` 更新到新 Digest；只修改镜像，不修改任何 Service/NodePort/Cloudflare Gateway/Tunnel、Marquez API、PG14、Airflow 或数据。Runtime 更新与内网独立 GET/浏览器验收尚未完成，实际 Run/回退和源码版本需读回后才可勾选。

- [ ] 1.8 **Landing Dataset readable filenames (CODED, LIVE NOT VERIFIED)**：根据公开 Marquez API GET-only [#40768910661](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40768910661) 的真实元数据，Landing 12 行为 4 Batch × 3 文件（manifest.json、encounters.csv、patients.csv），没有 `entity`/`run_id`/Column Lineage。扩展 `platform-portal/portal/web/public-datasets.js` 的可读标题至 `s3://health-landing`，以真实文件名 + Batch ID + Ingest Date 区分记录；Processing 保留 Patient/Encounter + Run ID。不能猜造 Landing `run_id` 或 Column Lineage，未知文件/命名回退原样，完整 Dataset href/Name/Namespace/Marquez Source 保留。此项须 PR CI/Main 镜像/受控部署与真实浏览器验收，暂不标完成。

- [x] 1.9 **Landing Public Web image refresh — runtime verified, GUI check pending separately**：2026-10-28 Healthcare Main `d8e768cf98e9823c0dbf70f2f64c4b54e5ee8d86`（PR #551）固定新镜像 `sha256:c506087183e12899d98a4f721b79c416889f606fe10b89a7b373e7c3e23038aa`；用户授权的 [Self-Runner #40771026383](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40771026383) SUCCESS：旧镜像与 Namespace/Service 预检通过，以镜像-only JSON Patch 更新 `dw-marquez/Deployment/marquez-public-web`、Rollout Ready、新/旧 Gateway/Web/NodePort Service 规格不变、`31080` Endpoint Ready；新版 Pod 和 Gateway GET 验证真实 Landing 12 Dataset、三种文件标签，POST 写入拒绝 405、raw Events GET 拒绝 403。独立公网 HTTPS GET-only [#40771212533](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40771212533) SUCCESS，域名 HTML、新 `public-datasets.js` 和 12 个 Landing API Dataset 返回正常。未改 Cloudflare Tunnel/DNS/Gateway 或原版 `30999`。**Chrome GUI 实际文本显示、切换 Namespace 与血缘图点击验收仍需用户截图，本项完成不代表完整公开安全审计已过。**

- [ ] 1.10 **Datasets trailing slash regression (CODED; browser verification pending)**：用户两张公开 Chrome 截图显示 `https://lineage.johnzhang-dataforge.site/datasets/` 下 Processing 8 行、Landing 12 行均退回 NAME/NAMESPACE/SOURCE，根因 `public-datasets.js` 只识别无尾斜杠的 `/datasets`。修复两种路由格式兼容，增加两种路由下 Processing + Landing 的真实 ID 保真、列标题、文件标题、初访选择、手动选择与 /jobs 隔离的 Node DOM regression。修复后仅通过受控镜像升级触及 `dw-marquez/Deployment/marquez-public-web`，Gateway/Tunnel/Service 不变。**必须真实 Chrome/Playwright 验证 DOM 可见标题后才视为对用户缺陷完成。**

## 2. Read-only Showcase Gateway (Agent M2)
- [ ] 2.1 在 `platform-portal/marquez/showcase-gateway/**` 实现独立轻量 HTTP 网关，转发已审核的 HTML/资源/GET(HEAD) 请求，默认拒绝全部修改方法/未许可路径；只访问现有内网 Marquez Web，不连接 PG14，不改业务运行。
- [ ] 2.2 完成标准/负向测试与无真实外网依赖的 Fake Web：POST/PUT/PATCH/DELETE、GraphQL/admin、URL 双重编码/目录穿越、错误时 fail closed、不能通过页面或直连绕过 Gateway；审计敏感 GET 元数据披露，不将“请求只读”当作“输出字段已经审核”。

## 3. Cloudflare Tunnel (Agent M3 docs + user manual)
- [ ] 3.1 准备可按 UI 实际操作的 `documents/systems/platform-portal/marquez/PUBLIC-TUNNEL-RUNBOOK.md`，Tunnel 仅指 Gateway，不映射 NodePort、API、PG14；Token 本地保存，含测试、诊断和一键撤销方案。
- [ ] 3.2 **用户手工执行（PARTIAL LIVE）**：2026-10-28 UTC 用户已在 Cloudflare Dashboard 创建 Tunnel、Published Application/CNAME，手工部署 K8s Secret/cloudflared Deployment，且公网 Marquez 页面实机可达；但 M1/M2 完整安全 Gate、Cloudflare Access 与 Token 轮换/连接器健康尚无独立验证，**不视为批准匿名发布或本任务全验收**。见 [本次用户现场观察](evidence/PUBLIC-MARQUEZ-RUNTIME-OBSERVATION-20261028.md)。

## 4. Acceptance / Release (Coordinator + user)
- [ ] 4.1 **现场部分通过（2026-10-28 UTC）**：用户贴出的 Gateway 本地只读验证有 GET/HEAD 200、POST/DELETE 405、指定 API 403；公网 Chrome 已显示真实 Job `COMPLETED`、Person/Encounter Table Level 和 Patient Column Level 六条映射。**尚缺 Encounter 公网 Column、Run History 精确读回、全部敏感 GET/写方法/编码绕过测试、Access/Token 轮换确认及独立运行版本证据**，因此不勾选。详见 [OpenSpec 观察记录](evidence/PUBLIC-MARQUEZ-RUNTIME-OBSERVATION-20261028.md)。
- [ ] 4.2 **域名已经实测可访问但匿名正式发布尚未获验收**：用户公网截图证实 `https://lineage.johnzhang-dataforge.site` 返回真实 Marquez Web；仅证明当时访问可用，不证明 Access 限制、敏感内容审查、外网负向安全、持续在线或 Always-on SLA。必须先完成 4.1 剩余安全 Gate，再批准稳定匿名展示；**没有自动静态快照回退**。
