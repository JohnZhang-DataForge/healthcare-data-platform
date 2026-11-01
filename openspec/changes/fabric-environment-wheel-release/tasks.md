# Tasks — P3 Environment Wheel release

- [x] 1.1 核实两个 GitHub main 的既有资源、唯一 Wheel 构建/暂存流程、历史 Readback Run 和独立运行时门禁。
- [x] 1.2 确认 Microsoft Fabric 官方 release 版 Environment APIs、Git staging 与 Publish 区分，并记录 HTTP 404/历史 Publish Success 的不确定性。
- [x] 1.3 记录 Source / staging / published / binding / runtime 分阶段设计、已知 Notebook 显式绑定缺口与不可跨越的安全边界。
- [x] 2.1 Self-Runner PR #382 merged at `21b3a658`; offline CI Run #41313930494 PASS；正式版只读 API 对 `published HTTP 404` 稳定分类 UNKNOWN，Notebook 环境元数据提示和正负单测 PASS。
- [x] 2.2 Trusted Self-Runner/main live GET-only Run #41314090759 全部执行成功：Notebook/Pipeline 安全读回 PASS、staging Wheel=True、published HTTP 404 / `HOLD_PUBLISHED_LIBRARIES_UNKNOWN`、历史 Publish Success、Notebook ipynb metadata `NOT_DECLARED_IN_IPYNB`；Publish 当前 Wheel/Runtime Binding/Spark import 均 HOLD/NOT_RUN。
- [x] 2.3 Python 3.13 / PySpark 4.1.1 / Java 21 **源码兼容性**：Healthcare PR #584 [CI Run #41314613170](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41314613170) PASS：纯 Python FHIR/Canonical 13/13，Spark DataFrame 2/2；既有 Py3.11/PySpark3.5.7 Wheel job PASS。**0.1.0 metadata 仍 <3.13：发布仍 BLOCKED；尚未构建/安装兼容的新版 Wheel。**
- [ ] 2.4 **当前 PR：Shared Engine 0.1.1 源码/Wheel 构建定义候选，等待 CI 结论**。`pyproject.toml`/`__version__` 版本一致，声明 `>=3.10,<3.14` 和依 Python 版本分流的 PySpark extras；要求 Python 3.11/3.13 独立 Wheel 安装、PySpark 3.5.7/4.1.1 测试、Python 3.11 两次 byte-identical 构建并记录 SHA256。只有所有 CI PASS、已记录精确 Git SHA / Wheel digest 后方可勾选；此任务不更改 Fabric Environment staging/Publish，也不执行 Notebook。
- [ ] 2.5 由固定 0.1.1 Wheel SHA 独立 staging PR 安全替换 Git Environment 中旧 0.1.0（必须始终只有一个 Wheel），经过 CI、Review 合并后验证 Fabric staging；不同步自动 Publish。
- [ ] 3.1 仅在新授权并完成影响审查后执行 Fabric Publish，保存 LRO 与新 published library 证据；不重复触发未知操作。
- [ ] 3.2 经另行授权绑定 Notebook 的 `env_healthcare`，新的 Spark Session 中验证已安装目标依赖；禁止业务数据写入。
- [ ] 3.3 完整记录 Wheel 内容 hash/provenance、effective publish、binding 与非写入 runtime import 的各自证据；未验证项标为 NOT_RUN/HOLD。
