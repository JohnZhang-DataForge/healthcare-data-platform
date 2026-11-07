# Tasks — Fabric dbt project ownership governance

## P1 — 本轮文档手续
- [x] 1.1 核对 Main、开放 PR、HL7 真实代码位置、Native Items、Shared Engine、现存可信结构检查冲突。
- [x] 1.2 在 OpenSpec 中确定唯一 `azure-fabric/dbt/` 父目录、`hl7-canonical` 命名、标准工程骨架和未来项目准入规则。
- [x] 1.3 更新 Agent 强制入口、开发规则、Fabric 导航和独立 dbt 组件规范文档，明确“目标路径尚未创建”。
- [x] 1.4 文档治理 [PR #811](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/811) 合并到 Main `16bf09baff3ae150a8ba551d9f13aaf6bddde502`；四项受保护 Required Checks 全部 SUCCESS（[Change](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843811)、[Component paths](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843544)、[Fabric deployment](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843615)、[OpenSpec validate](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843584)），文档链接检查亦通过。外部 Cloudflare Workers Build 失败不属于四项 Required Gates，本次 PR 未改 Portal 或部署代码。

## P2 — 受保护门禁前置（独立治理 PR）
- [ ] 2.1 只为已审 dbt 原生 SQL `tests/` / `.gitkeep` 设计可信 Layout Gate 精确例外；在安全维护窗口更新 checker 并验证正反用例与真实 Required Check，不放宽一般自动化测试目录禁令。

## P3 — 标准工程真正实施（独立源码 PR）
- [ ] 3.1 创建完整 `azure-fabric/dbt/hl7-canonical/` 骨架（空目录保留 `.gitkeep`），将现有 HL7 dbt 源迁移为唯一正式工程，Parser/Writer 保留原位直到独立决议。
- [ ] 3.2 同步 Workflow、Self-Runner、CODE Maps、所有引用、依赖及合同；重做物理本地 Delta/dbt/Replay/独立读回验收。
- [ ] 3.3 迁移后同步已采用 Current Spec 的**真实源码路径和实施状态**；未来 FHIR/业务项目仍按独立 OpenSpec 准入，不预建。

## 已采用治理规则

- 2026-11-07：P1 规则随 PR #811 在 Main 生效；Current Spec 正式采用至 `openspec/specs/fabric-dbt-project-layout/spec.md`（与本次 P1 关闭记录配套）。**仅目录/AI 治理生效；P2 可信 Gate 例外和 P3 物理项目迁移仍 OPEN。**
