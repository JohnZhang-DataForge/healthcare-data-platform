# Tasks — Fabric dbt project ownership governance

## P1 — 本轮文档手续
- [x] 1.1 核对 Main、开放 PR、HL7 真实代码位置、Native Items、Shared Engine、现存可信结构检查冲突。
- [x] 1.2 在 OpenSpec 中确定唯一 `azure-fabric/dbt/` 父目录、`hl7-canonical` 命名、标准工程骨架和未来项目准入规则。
- [x] 1.3 更新 Agent 强制入口、开发规则、Fabric 导航和独立 dbt 组件规范文档，明确“目标路径尚未创建”。
- [x] 1.4 文档治理 [PR #811](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/811) 合并到 Main `16bf09baff3ae150a8ba551d9f13aaf6bddde502`；四项受保护 Required Checks 全部 SUCCESS（[Change](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843811)、[Component paths](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843544)、[Fabric deployment](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843615)、[OpenSpec validate](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/42426843584)），文档链接检查亦通过。外部 Cloudflare Workers Build 失败不属于四项 Required Gates，本次 PR 未改 Portal 或部署代码。

- [x] 1.5 将现有 HL7 文件逐项标记“业务保留 / 冻结参考且待退役 / 混合依赖需复核 / 回归测试需改接”，同步新 dbt 项目规则及开发策略；仅文档更新，不删除或搬动源码（已由 [PR #813](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/813) 合并 Main `de7e904ba9efd28cc8484fdc2097f44be1bfb546`；受保护四项 Required Gates 与 OpenSpec/文档链接检查 PASS）。

## P2 — 受保护门禁前置（独立治理 PR）
- [ ] 2.1 只为已审 dbt 原生 SQL `tests/` / `.gitkeep` 设计可信 Layout Gate 精确例外（独立 [permit-dbt-native-sql-test-layout](../permit-dbt-native-sql-test-layout/tasks.md)）；在安全维护窗口更新 checker 并验证正反用例与真实 Required Check，不放宽一般自动化测试目录禁令。

## P3 — 标准工程真正实施（独立源码 PR）
- [ ] 3.1 门禁例外完成后，在 `azure-fabric/dbt/hl7-canonical/` 创建**完整标准骨架**，直接按 dbt 分层开发；旧 SQL/config/profile **冻结供参考而非先迁移**。新工程在验收/切换前仅为 Candidate，不能形成第二个正式生产入口。
- [ ] 3.2 新 dbt 工程真实本地 Delta + dbt compile/run/test、Replay、Patient 18/Encounter 27 Contract/负向语义读回 PASS；必要业务扩展按原单独 HL7 Consumer Change 跟踪。
- [ ] 3.3 在受控切换 PR 中审查全部活跃 Workflow/Self-Runner/源码/配置/文档引用，改接唯一新 dbt 工程并复验，不因新 SQL 可以运行就删除旧文件。
- [ ] 3.4 切换确认后**另一个清理 PR**删除旧 dbt models/project/profiles，更新旧 HL7 CODE、新 Fabric dbt CODE、CI/依赖及全部导航；Python Parser/Intake/Delta Writer 与必要测试继续保留，混合 requirements 按消费者拆分，不做全目录删除。
- [ ] 3.5 同步 Current Spec 的**真实执行 Owner 和迁移状态**；未来 FHIR/业务项目仍走独立 OpenSpec 准入，不预建。

## 已采用治理规则

- 2026-11-07：P1 规则随 PR #811 在 Main 生效；Current Spec 正式采用至 `openspec/specs/fabric-dbt-project-layout/spec.md`（与本次 P1 关闭记录配套）。**仅目录/AI 治理生效；P2 可信 Gate 例外和 P3 物理项目迁移仍 OPEN。**
