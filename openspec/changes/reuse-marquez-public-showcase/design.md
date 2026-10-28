# Design: Native Marquez Public Read-only Showcase

## 1. 已知事实和目标

- 官方 Marquez Web 及 PG14 已存在：`dw-marquez` / Marquez 0.51.1；Web ClusterIP，另有 `marquez-web-lan` NodePort 30999（仅内部访问）。真实 Chrome LAN GUI 在 2026-10-25 已验证 Patient/Encounter Table/Column 血缘，Reconcile 全图、物理 RDD START-only 等边界仍未消失。
- Source evidence: [Marquez README](../../../documents/systems/platform-portal/marquez/README.md)、[SHOWCASE RUNBOOK](../../../documents/systems/platform-portal/marquez/SHOWCASE-RUNBOOK.md)。外部文档：[Marquez deployment/auth](https://marquezproject.ai/docs/deployment/)、[Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/get-started/)、[Marquez Apache-2.0 license](https://github.com/MarquezProject/marquez/blob/main/LICENSE)。
- **新增目标**：让陌生访客在浏览器通过稳定域名查看既有 Job / Dataset / Run / Table / Column Lineage。只读，不需要在页面触发生成数据；无 Cloudflare Pages 前端编译，无复制数据库。

## 2. 网络与信任边界

```text
Public browser
  -> Cloudflare HTTPS hostname (user config)
  -> cloudflared outbound Tunnel (origin must target Gateway)
  -> SHOWCASE GATEWAY : (new component, default-deny method + route)
  -> EXISTING Marquez Web ClusterIP / configured localhost-safe internal route
  -> existing Marquez API (via Web's API proxy) -> existing PG14
```

- Gateway 源代码唯一模块 `platform-portal/marquez/showcase-gateway/**`，独立测试。Cloudflare Dashboard 和 Tunnel Token 由用户手工持有，不放 Git。Gateway 拒绝的方法/路径需要在请求被转发至 Marquez Web 之前生效，因为原 Marquez Web 可能对 `/api/v1` 透明转发。
- 不能用 Tunnel 直接指向 `30999`、Marquez API `5000`、PG14，不能开放家用路由端口。真实部署/重配置前由用户授权并核对共享资源状态。
- 原生 UI 可能使用 POST 作只读筛选，需审计 **确切版本的 Web 调用**。首版 Gateway 默认仅支持受审 GET/HEAD 与严格路径前缀/必要静态资源；如果任何 POST 为显示血缘必需，不能凭“它看起来是查询”就放行；先标记 BLOCKED 并让主 Session 评审精准端点与请求体只读证明。拦截 GraphQL、admin/metrics、任意管理端点，明确阻止路径编码、双重编码、`..`、大小写/方法绕过、Host 重定向、响应携带可变更资源。
- **重要限制**：GET-only/路径白名单只能阻止变更，不会自动隐藏原始 Job Facets 中的 SQL、内部 URI、名字和上下文。M1 审阅必须提供 GET 端点+字段清单；如果展示内容不适合公开，优先拒绝暴露该端点或限制可访问者；不得在未审核情况下将原始 Marquez GET 一股脑放行。Cloudflare Access 限定邀请访问可作为很快的降风险选项，但不等同匿名招聘演示。

## 3. 是否需要修改 UI

**默认零修改。** 先使用官方 GUI 原样运行，证明 Home/Job/Run/Dataset/Table/Column 可经 Gateway 完成。隐藏按钮只是审美或减少误触，不能作为 Security Gate。如果要改 UI，另开小 PR：只改品牌标题、默认入口、隐藏已由 Gateway 禁止的操作，不重做图/前端架构、不升级整套 Marquez 版本。尽量使用现有容器直接展示。

## 4. 最小可复现验收

- M1：研究 0.51.1 原生 GUI 资源/API 调用（包括 Web 自带 proxy）；列出完整 Pages / Job / Dataset / Run / Table / Column 和其 GET/HEAD/POST 请求矩阵，具体到路径和方法；标识内容敏感/未知字段，指出哪些 UI 功能会因 Gateway 拦截被影响。静态源码审计与旧验收证据不得冒充新公网验收。
- M2：Gateway 离线测试包括：正常 HTML/JS/CSS 和必需 GET 行为，明确的 403/405 拒绝 POST/PUT/PATCH/DELETE、未知路径、GraphQL/admin/metrics、编码绕过与失败安全；不让前端猜测直接访问私有 API。无真实 Marquez / Azure/K8s 写入。
- M3：用户人工 Tunnel 配置步骤（Cloudflare `Networking → Tunnels → Create Tunnel → Published application`）、Tunnel token 本地保管、源地址只指 Gateway、零入站端口开放、关闭/回滚按钮，包含 staging 和匿名访问验证步骤。Agent 不替用户部署。
- 主 Session：取得用户对公网发布动作的授权后，分步骤实际验证源日志、HTTP 负向访问、访客可看到真实 Patient/Encounter 表/列级映射和 Run 状态；检查公开内容，不误标 Complete，不暴露 Blob 原始事件和 Secret。
- 退出/回滚：关闭 Tunnel route / 停止 cloudflared 即可撤掉公网入口；内部 Web/PG14 不变。若公开字段敏感、写请求可达、首页/图无法使用或 UI 混入未审计 API，则停止公开上线。

## 5. 拆包与变更顺序

主 Session 合并本 Change 基线后，M1/M2/M3 从最新 Main 并行，各自独占文件。M1 为 M2 提供精确端点范围，但 M2 可先完成网关基础逻辑。M3 手工流程可独立写文档，直到网关端口实测前使用占位。三个 Agent 不修改同一文件；Openspec `tasks.md` 各自仅改本人任务行并 rebase 最新 Main；涉及 CODE 共享文件时由主 Session 协调。真实 Tunnel/K8s/Marquez 操作只允许用户明确授权后由单一 Session 串行执行。

## 6. 长线功能不变

原 `healthcare-on-demand-live-demo` 的 Azure Blob Publisher/Consumer 和 Fabric Listener/HOLD 状态继续有效，只是**公网首版展示后端已换成 Marquez Web API**；不会为了首版网页而要求先交付 Blob 数据同步、静态 Exporter、自动触发和邮件。公共数据访问和实时执行是独立概念。
