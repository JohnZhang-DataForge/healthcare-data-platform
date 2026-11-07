# Tasks — Fabric dbt project ownership governance

## P1 — 本轮文档手续
- [x] 1.1 核对 Main、开放 PR、HL7 真实代码位置、Native Items、Shared Engine、现存可信结构检查冲突。
- [x] 1.2 在 OpenSpec 中确定唯一 `azure-fabric/dbt/` 父目录、`hl7-canonical` 命名、标准工程骨架和未来项目准入规则。
- [x] 1.3 更新 Agent 强制入口、开发规则、Fabric 导航和独立 dbt 组件规范文档，明确“目标路径尚未创建”。
- [ ] 1.4 PR 通过 OpenSpec / 文档链接 / GitHub Main 四项受保护 Required Checks 并合并，补录 PR、SHA 和证据。

## P2 — 受保护门禁前置（独立治理 PR）
- [ ] 2.1 只为已审 dbt 原生 SQL `tests/` / `.gitkeep` 设计可信 Layout Gate 精确例外；在安全维护窗口更新 checker 并验证正反用例与真实 Required Check，不放宽一般自动化测试目录禁令。

## P3 — 标准工程真正实施（独立源码 PR）
- [ ] 3.1 创建完整 `azure-fabric/dbt/hl7-canonical/` 骨架（空目录保留 `.gitkeep`），将现有 HL7 dbt 源迁移为唯一正式工程，Parser/Writer 保留原位直到独立决议。
- [ ] 3.2 同步 Workflow、Self-Runner、CODE Maps、所有引用、依赖及合同；重做物理本地 Delta/dbt/Replay/独立读回验收。
- [ ] 3.3 依据实现状态采用 Current Spec，并保持未获批准的未来 FHIR/业务项目为候选而非既成目录。
