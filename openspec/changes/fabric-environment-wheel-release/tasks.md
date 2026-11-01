# Tasks — P3 Environment Wheel release

- [x] 1.1 核实两个 GitHub main 的既有资源、唯一 Wheel 构建/暂存流程、历史 Readback Run 和独立运行时门禁。
- [x] 1.2 确认 Microsoft Fabric 官方 release 版 Environment APIs、Git staging 与 Publish 区分，并记录 HTTP 404/历史 Publish Success 的不确定性。
- [x] 1.3 记录 Source / staging / published / binding / runtime 分阶段设计、已知 Notebook 显式绑定缺口与不可跨越的安全边界。
- [x] 2.1 Self-Runner PR #382 merged at `21b3a658`; offline CI Run #41313930494 PASS；正式版只读 API 对 `published HTTP 404` 稳定分类 UNKNOWN，Notebook 环境元数据提示和正负单测 PASS。
- [x] 2.2 Trusted Self-Runner/main live GET-only Run #41314090759 全部执行成功：Notebook/Pipeline 安全读回 PASS、staging Wheel=True、published HTTP 404 / `HOLD_PUBLISHED_LIBRARIES_UNKNOWN`、历史 Publish Success、Notebook ipynb metadata `NOT_DECLARED_IN_IPYNB`；Publish 当前 Wheel/Runtime Binding/Spark import 均 HOLD/NOT_RUN。
- [ ] 2.3 独立 Python 3.13 / Spark 4.1 Wheel 兼容性验证：现有 Runtime 2.0 Git Sparkcompute.yml 需要 Python 3.13，而 `pyproject.toml` 限制 <3.13。新增纯 Python 3.13 source probe，真实 CI 后再标记 PASS；不把纯源码测试当成可发布的 Wheel 证明。
- [ ] 2.4 为 Runtime 2.0 创建经 Py3.13/PySpark4.1 验证的新版 Shared Wheel（不能仅改 metadata），确定性 Hash/版本可追溯，独立评审后替换 Environment 中旧版 Wheel 并再次只读验证 staging。
- [ ] 3.1 仅在新授权并完成影响审查后执行 Fabric Publish，保存 LRO 与新 published library 证据；不重复触发未知操作。
- [ ] 3.2 经另行授权绑定 Notebook 的 `env_healthcare`，新的 Spark Session 中验证已安装目标依赖；禁止业务数据写入。
- [ ] 3.3 完整记录 Wheel 内容 hash/provenance、effective publish、binding 与非写入 runtime import 的各自证据；未验证项标为 NOT_RUN/HOLD。
