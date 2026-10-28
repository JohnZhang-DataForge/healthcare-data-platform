# Parallel Workstreams — Native Marquez First

> **CURRENT MVP AFTER USER DECISION 2026-10-27**. This file is the code ownership and Session kickoff authority for `reuse-marquez-public-showcase`. Existing `healthcare-on-demand-live-demo` P0 Static/Web/Exporter/Azure tasks are historical or long-term, not MVP prerequisites. No Agent may autonomously start public Cloudflare or shared runtime.

| Session | Scope in plain words | Exclusive files | Task numbers |
| --- | --- | --- | --- |
| M1 — Native UI audit | 现成 Marquez 浏览器到底调用哪些 API，哪些页面真能展示，需不需要隐藏按钮 | `documents/systems/platform-portal/marquez/PUBLIC-UI-AUDIT.md` | 1.1, 1.2 |
| M2 — Gateway | 只转发网页、JS/CSS、经过审核的读取 API，所有写操作与敏感路径直接拒绝 | `platform-portal/marquez/showcase-gateway/**`（及最小 owning `documents/systems/platform-portal/marquez/CODE.md`） | 2.1, 2.2 |
| M3 — Cloudflare user runbook | 把 Cloudflare Tunnel 的手工点选、cloudflared 安装、测试与撤销写清楚 | `documents/systems/platform-portal/marquez/PUBLIC-TUNNEL-RUNBOOK.md` | 3.1 |
| Main Coordinator | 基线、冲突合并、旧 Change Supersession、测试与用户实际发布 Gate | 本 Change Proposal/Design/Specs/Tasks/Plan、原 Change 历史对齐、最后验收记录 | 0.1, 0.2, 4.1, 4.2 |

### Common rules
1. 所有 Agent 先读根 `AGENTS.md`、`documents/README.md`、`documents/engineering/development/SESSION-COORDINATION.md`、`documents/engineering/operations/SAFE-OPERATIONS.md`、`documents/systems/platform-portal/marquez/{README.md,CODE.md,SHOWCASE-RUNBOOK.md}`、本 Change 五文件、最新 Main/开放 PR、现行代码；从最新 Main 建各自 Branch。
2. 只进行公开资料、Git 源码、离线 Mock 测试。**不要**执行 K8s Deploy/Helm Apply、Marquez POST、PG14/PG17 修改、cloudflared 上线、Cloudflare Dashboard 操作、真实 Fabric Notebook 或 Azure 资源改变。实机只读操作也先遵守共享资源协调与授权。
3. 三个 Agent 各自只修改独占业务路径，`tasks.md` 只能最小编辑自己的行，M2 新代码另同步 owning `CODE.md`；冲突 rebase 由主 Session 依 PR 顺序协调。
4. PR Body 独立两行：`OpenSpec-Change: reuse-marquez-public-showcase` 和每份 PR **一个** `OpenSpec-Task: n.n`（按编号引用自己的 task，单 PR 只挂一个任务）；同 PR 必须修改对应 Task 行。所有代码须包含静态/离线正常和负向测试及准确 HEAD/Run 证据；不要自行 merge Main。
5. M2 的安全行为不能依赖 UI 隐藏操作按钮，默认拒绝方法和路径，只能在 M1 提供精确版本/请求证据后放行必要 endpoint；要在内网 Web 自身 API proxy *之前* 拦截。
6. M3 Cloudflare Tunnel 的 Service URL 必须指向 Gateway 服务地址/端口（真正安装位置由用户确认），不可指向原始 NodePort 30999；DNS 由 Cloudflare 托管不等于 Marquez 已部署或公网可达。
7. 最后一段 DONE/NOT DONE/NEXT 包括 exact Main/PR HEAD 40位、CI、源码/文档范围、HOLD、真实环境副作用，用户转发报告给主 Session，主 Session GitHub 重新独立读回。

## Agent M1 kickoff — native UI

你是 **Agent M1 — Marquez Native UI/API Audit**，仓库 `JohnZhang-DataForge/healthcare-data-platform`，OpenSpec `reuse-marquez-public-showcase` 任务 1.1/1.2。只读检查已有 Marquez 0.51.1 Helm/Web 配置、Web 自带 API Proxy、2026-10-25 P6 浏览器证据；结合官方对应版本源码，列出 Home/Jobs/Run/Dataset/Table/Column 可视化所有关键请求的 Method、路径、参数、用途、是否可能 POST 搜索及是否泄露 SQL/内部 URI。区分 UI HTML 200、GET readback、真实 Table/Column 可用性的不同证据等级。默认不修改前端源码：判断是否零修改可发布，操作按钮可暂不隐藏，由 Gateway 拒写；如果必须隐藏，写建议不去改 Marquez 源码。只创建 `documents/systems/platform-portal/marquez/PUBLIC-UI-AUDIT.md` 和最小更新本 Change `tasks.md` 的 1.1/1.2；禁止访问真实共享 K8s/Marquez，除非用户另行批准；独立 PR、CI、OpenSpec linkage、不能自行合并。最后报告精确 API allowlist 草案与 blocked features，发主 Session。

## Agent M2 kickoff — read-only Gateway

你是 **Agent M2 — Marquez Showcase GET-only Gateway**，仓库和 Change 同上，负责 2.1/2.2。仅新增 `platform-portal/marquez/showcase-gateway/**` 并按 CODE 规则最小添加 `documents/systems/platform-portal/marquez/CODE.md` 导航与自己的 OpenSpec task 行；其他业务文件不碰。优先用最轻量的受控反向代理实现：仅将必要 GET/HEAD HTML、JS/CSS/图片/API 转到单个固定上游内网 Marquez Web URL（不能用户控制 upstream/Host），默认拒绝 POST/PUT/PATCH/DELETE/OPTIONS 以外未经审计方法、GraphQL/admin/metrics/未知 API、路径编码绕过、开放代理/任意 Host 转发；响应不缓存危险信息。Gateway 必须位于 Cloudflare Tunnel origin 与 Marquez Web（含其自身 API Proxy）之间。实现 Fake Upstream 的离线正向与攻击负向测试，不连实际 Marquez、不部署；M1 精确 API allowlist 尚未完成时宁可页面部分功能失败也不猜测全放行。用户以后手工 Tunnel 指向 Gateway（不是 NodePort）。独立 PR 更新对应 Task、CI、DONE/NOT DONE/NEXT、主 Session 合并。

## Agent M3 kickoff — manual Cloudflare Tunnel guide

你是 **Agent M3 — Cloudflare Tunnel Manual Runbook**，同一仓库/Change，负责 3.1。只创建 `documents/systems/platform-portal/marquez/PUBLIC-TUNNEL-RUNBOOK.md` 并更新 OpenSpec `tasks.md` 的 3.1 任务行；其他文件不碰。根据 Cloudflare 2026 官方文档，为用户写可直接跟着点的 Dashboard `Networking > Tunnels` → Create Tunnel → Public Hostname/Published application → HTTPS hostname（候选 `lineage.johnzhang-dataforge.site`），Docker/systemd `cloudflared` origin 部署选项、真实 gateway地址/端口待 M2 固定、无公网端口转发/无 token 入 Git、DNS 冲突预检、验证不同浏览器和 GET/POST负向测试、停用 route / 停 cloudflared 回退和访问故障排查。特别写出 Pages 与 Tunnel 是两条互不相同的部署路线：本次不配置 Pages；不要把原 NodePort 30999、PG14 或 Marquez API 当 Service URL。仅文档调研，不要操作 Cloudflare 控制台、K8s 或部署；提交独立 PR 和可核验官方文档链接，等待主 Session 合并与用户手动执行。
