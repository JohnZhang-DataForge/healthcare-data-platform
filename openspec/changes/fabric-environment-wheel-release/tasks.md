# Tasks — P3 Environment Wheel release

- [x] 1.1 核实两个 GitHub main 的既有资源、唯一 Wheel 构建/暂存流程、历史 Readback Run 和独立运行时门禁。
- [x] 1.2 确认 Microsoft Fabric 官方 release 版 Environment APIs、Git staging 与 Publish 区分，并记录 HTTP 404/历史 Publish Success 的不确定性。
- [x] 1.3 记录 Source / staging / published / binding / runtime 分阶段设计、已知 Notebook 显式绑定缺口与不可跨越的安全边界。
- [ ] 2.1 仅增强现有 Self-Runner GET-only 预检，稳定分类 `published HTTP 404`（不能标 PASS），补充元数据绑定可证实性和负向测试；记录真实 Run/Commit。
- [ ] 2.2 在 P3 报告中区分 SOURCE_BUILD、GIT_STAGING、PUBLISH、NOTEBOOK_BINDING、RUNTIME_IMPORT，未知状态必须是 HOLD。
- [ ] 3.1 仅在新授权并完成影响审查后执行 Fabric Publish，保存 LRO 与新 published library 证据；不重复触发未知操作。
- [ ] 3.2 经另行授权绑定 Notebook 的 `env_healthcare`，新的 Spark Session 中验证已安装目标依赖；禁止业务数据写入。
- [ ] 3.3 完整记录 Wheel 内容 hash/provenance、effective publish、binding 与非写入 runtime import 的各自证据；未验证项标为 NOT_RUN/HOLD。
