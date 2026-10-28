# Tasks — Reuse Native Marquez Public Showcase

> ACTIVE / DOCS AND OFFLINE DEVELOPMENT FIRST. 初始方案批准不等于 Kubernetes/Tunnel/Marquez 公网实际部署授权。PR Body 必须单独声明 `OpenSpec-Change: reuse-marquez-public-showcase` 与本 Change 中唯一一个任务 ID；所有实现 PR 同步修改自己的任务行。跨 Session 合并由 Coordinator 执行。

## 0. Formal Change & Coordination
- [x] 0.1 确认用户选择现有官方 Marquez Web 作为公网只读首版，核对 2026-10-25 内网 Table/Column 真实证据、GitHub 最新 Main、OpenSpec/Agent 规则；创建 Proposal/Design/Specs/Tasks/并行 Agent 分工及手工 Cloudflare 初稿。本项仅文档 CI/Main readback 闭环。
- [ ] 0.2 主 Session 在旧 `healthcare-on-demand-live-demo` 标记首版静态 Web/Marquito 路线被本 Change 取代（不勾选旧任务为真实 Done），保留 Blob Relay、Fabric HOLD 和后续按需触发；关闭或暂缓过时的 Agent A PR #518/#519，保留历史研究 PR #526。

## 1. Native Marquez UI / API Audit (Agent M1)
- [ ] 1.1 只读核对现有 Marquez 0.51.1 原生 Web/API 的真实请求矩阵、必要静态资源、Home/Jobs/Run/Dataset/Table/Column 功能及已知展示不完整边界，输出有代码证据的审核报告，不动既有 Helm/K8s。
- [ ] 1.2 确认首版是否 **零 UI 代码更改**即可交付；仅如必要，再独立建议最小 UI 调整和禁用按钮，但不把隐藏按钮当后端保护。

## 2. Read-only Showcase Gateway (Agent M2)
- [ ] 2.1 在 `platform-portal/marquez/showcase-gateway/**` 实现独立轻量 HTTP 网关，转发已审核的 HTML/资源/GET(HEAD) 请求，默认拒绝全部修改方法/未许可路径；只访问现有内网 Marquez Web，不连接 PG14，不改业务运行。
- [ ] 2.2 完成标准/负向测试与无真实外网依赖的 Fake Web：POST/PUT/PATCH/DELETE、GraphQL/admin、URL 双重编码/目录穿越、错误时 fail closed、不能通过页面或直连绕过 Gateway；审计敏感 GET 元数据披露，不将“请求只读”当作“输出字段已经审核”。

## 3. Cloudflare Tunnel (Agent M3 docs + user manual)
- [ ] 3.1 准备可按 UI 实际操作的 `documents/systems/platform-portal/marquez/PUBLIC-TUNNEL-RUNBOOK.md`，Tunnel 仅指 Gateway，不映射 NodePort、API、PG14；Token 本地保存，含测试、诊断和一键撤销方案。
- [ ] 3.2 **用户手工执行** Cloudflare Dashboard Tunnel/DNS/域名及 origin cloudflared 安装；前提是 M1/M2 Gate 合格并独立授权具体公网发布动作，不由 Agent 擅自部署。

## 4. Acceptance / Release (Coordinator + user)
- [ ] 4.1 用户授权后在可控窗口串行测试浏览器 GUI 的真实 Patient/Encounter Table/Column、Job/Run，独立验证写请求不可达、必要 API 读请求可达及敏感字段披露范围；记录 exact Main SHA、环境、时间和可回滚证据。
- [ ] 4.2 只有 4.1 满足后才批准稳定域名对匿名访客上线；用户证实访问成功后记录真实 URL/域名。若环境断网，诚实显示不可用，**没有自动静态快照回退**。不虚构 Always-on SLA。
