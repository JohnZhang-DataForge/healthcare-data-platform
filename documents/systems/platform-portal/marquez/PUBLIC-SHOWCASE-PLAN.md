# Marquez-native Public Showcase — approved MVP direction

> **STATUS: DESIGN APPROVED, NOT DEPLOYED.** 用户在 2026-10-27 选择“复用现有 Marquez 原生 Web，尽快对外展示”的首版方向。实施/手工 Tunnel/外网发布尚未获实际 Runtime 验收；不要把旧局域网 GUI PASS 当作公网部署成功。

**新正式 OpenSpec Change**：[reuse-marquez-public-showcase](../../../../openspec/changes/reuse-marquez-public-showcase/proposal.md) · [Design](../../../../openspec/changes/reuse-marquez-public-showcase/design.md) · [Tasks](../../../../openspec/changes/reuse-marquez-public-showcase/tasks.md) · [Agent 分工](../../../../openspec/changes/reuse-marquez-public-showcase/parallel-workstreams.md)。

现状：Marquez 0.51.1、`dw-marquez` 的官方 Web UI、`dw-postgre14` 的持久元数据库、NodePort `30999` 局域网浏览、2026-10-25 P6 历史 Table/Column 真实验收。不改业务 ETL、不建第二套 Marquez、不再为了首版公网 UI 开发 React Flow/Marquito，也不依赖原 `portal.snapshot.v1` 或每次 JSONL Exporter 的发布过程。

**目标链路**：招聘人员 HTTPS → Cloudflare Tunnel（用户手操）→ 新轻量 read-only Gateway → 现有 Marquez Web（自身可代理 API）→ Marquez API / PG14。不能让 Tunnel 直接指向 Web NodePort `30999` 或 API；默认拒绝写方法和未核验的 API 路径。仅隐藏按钮不足以防止 API 写入，匿名公开前还需审核 GET 响应中可能暴露的 SQL/内部 URI。旧 Marquito 源码许可无须等待，因为首版不再引用它。

**当前无实际对外 URL**；域名 `lineage.johnzhang-dataforge.site` 是候选，不是已经配置的 DNS。Cloudflare Pages 旧手工指引是过时的静态网站分支，不适用于此 Tunnel MVP；未部署/未运行云资源。原 `healthcare-on-demand-live-demo` 的 Azure Publisher/Consumer 和 Fabric HOLD 与本 Change 无冲突。
