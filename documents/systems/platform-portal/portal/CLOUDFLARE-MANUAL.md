# Cloudflare Pages 人工配置指南 — Portal 只读网站

> **预备步骤，不表示已上线。** Cloudflare 完全由用户手工操作；这些步骤**只能在 Web Agent 的可合法发布源码与 Exporter 的公开数据包通过验收后执行**。所有界面名称可能随 Cloudflare UI 版本稍有变化。不得为方便操作将本地 Marquez/PG14、Azure 私有 Blob、Token 或访问内网的 API 直接暴露到浏览器。

## 0. 先收齐 Agent A/B 的交付
- Agent A 提供合法可发布的 Marquito Web 源码及编译成功记录：`platform-portal/portal/web/`；确认作者源代码的复用/再发布许可。用户拟主动向作者发邮件。
- Agent B 提供静态 `data/latest.json` 及经检查的 JSONL 事件：`data/lineage/latest.jsonl`（候选补充端点；须先由 Coordinator 批准）。确认实际上传文件位于 Next.js 的 `public/data/` 或构建产物 `out/data/` 中；绝不能从私有 Marquez API 动态拉取。
- 确认 `npm ci && npm run build` 在 Web 源码目录成功，并有 Next.js `output: 'export'` 配置和 `out/index.html`。这是作者源码已知的构建方式；**我们自己的 Web 尚未实现，所以目前不能假设此构建会通过**。

## 1. 手动创建 Pages
1. 登录 Cloudflare Dashboard → **Workers & Pages** → 创建应用 → **Pages** → **Connect to Git** / 导入仓库（界面字样可能变化）。
2. 授权 Cloudflare 访问 GitHub 的 `JohnZhang-DataForge/healthcare-data-platform` 仓库，只选需要的仓库权限。
3. 选生产分支 `main`；项目名可用 `healthcare-portal`（仅建议，可调整）。
4. **Root directory**：`platform-portal/portal/web`（如果界面不支持该设置，让 Agent A 提供仓库根目录可执行构建命令后再继续）。
5. **Build command**：`npm run build`；**Build output directory**：`out`（相对于项目 Root）；Node 版本采用 Agent A 构建验证所用版本，切勿猜测版本。
6. 不为匿名只读静态页面创建 Worker、D1、R2、Turnstile 或 GitHub PAT。不要填写数据库、Azure/K8s 等凭据。
7. 点部署；记下 Pages 提供的 `*.pages.dev` URL 和实际构建日志。主 Session/Agent A 验证成功后再绑定自定义域名（如有）。
8. 浏览器匿名打开站点：页面、Table/Column Lineage、`/data/latest.json`、获准发布的 `/data/lineage/latest.jsonl` 均应只读可见；核实 Mock/Verified 和最后成功时间准确。
9. 断开本地 Marquez 连接/模拟后台不可用，网站应仍可显示已发布快照；刷新、爬虫、GET 不会启动任何 Spark/Fabric Workflow。
10. 若出现敏感内部元数据、许可问题、虚假 VERIFIED 状态或实际公开路径不符，撤销当前部署并通知主 Session，不手工在 Cloudflare 粘贴原始 Marquez API Token 或修补秘密数据。

## 2. 后期真实自动触发 Demo（不在当前阶段）
用户将来启用访客触发时，需要单独部署受控 Worker，并在服务端配置 US geo、Turnstile、每日限额、原子计数、single-flight、管理员 OFF/ON/Emergency OFF 和预算 Gate。**手工配置 Worker 也不能代替服务端控制逻辑审查**。任何成功/失败邮件、Azure Trial/付费或 GitHub dispatch 均另行授权验收。

## 3. 向主 Session 回报什么
提交 Pages URL、部署时间、对应 GitHub Main 40 位 SHA、构建结果、实际测试过的静态资源、是否出现公开访问风险；不要提供 Dashboard Token/密码。主 Session 只在有真实页面读回时将 OpenSpec 7.8 标记 Done。
