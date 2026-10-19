# Tasks

> **2026-10-18 追溯建档**：本 Change 是在 PR #225–#227 合并以后补建。前面标记 `[x]` 的事项由其原 PR、Git Tree / CI 证据支撑，**不表示当时已有 OpenSpec 事前审批**。未来运行调试尚未执行，不得把目录检查 PASS 记为 Runtime PASS。

## 1. 溯源与独立备份（已实施）

- [x] 1.1 记录命名试点 `adopt-local-data-platform-naming` 及原始 Main SHA `eb216b544381ab0e73bd221cd54d8887f77b9a10`。
- [x] 1.2 在独立私有 Healthcare-Specs 仓库 Main 保存 393 个业务文件及原始相对路径与 Blob 清单；393/393 一致、0 差异，备份 PR #2 / Merge `6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`。
- [x] 1.3 记录备份既非代码工作树中的第二套可导入源码，也不是数据库/S3/K8s 的数据备份。

## 2. 物理源码与仓库结构（已实施，按历史事实）

- [x] 2.1 复制并核对 393 个原始业务文件的 Blob；在隔离分支移除对应根目录业务文件，PR #225 / Merge `377df7c9fae770cde985f6e7bcbc47d40ecfa355`。
- [x] 2.2 在 Main 核对 `local-data-platform/` 有 393 个内容一致的业务文件，原有根目录业务路径无残留；保留独立的 `azure-fabric/`、`platform-portal/` 等系统边界。
- [x] 2.3 **如实登记未通过的 Gate**：PR #225 Component Code Naming Run #39160915562 FAIL；OpenSpec Run #39160915519 SUCCESS；该次 Merge 不代表运行兼容完成。
- [x] 2.4 更新文档与 CODE.md 导航，PR #226 / Merge `3af772f60c8ce5aac6f474cf8b291b13d82d3d88`，适用三项 CI PASS。
- [x] 2.5 将 3 个全仓检查器和 3 个质量单测迁入 `.github/quality/`；修 CI、模块加载和文档，PR #227 / Merge `7e969718cfad9368fd13866053636c787e24ca7e`，三项 CI PASS；根目录 `scripts/`、`tests/` 已退出。

## 3. OpenSpec 正式补建与当前事实同步（本轮）

- [x] 3.1 将已实施事项以**追溯**形式写入本 Change 的 Proposal / Design / Tasks，标明原始 PR、SHA、Run、失败和权限边界；不伪造事前审批。
- [x] 3.2 维护不变性要求与恢复边界：目录内容一致不等于 DAG/镜像/Writer 运行完成；`skip_specs: true` 不新建无证据的业务 Spec。
- [x] 3.3 在追溯文档 PR #228 的最终 HEAD `e684ba67f9081f171b11c650d45d067a892920bd` 上完成 [OpenSpec 1.14.3 Strict Run #39169339352](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39169339352) SUCCESS（Active Changes = 1，Current Specs = 0，Validate Exit 0）及 [Docs Links Run #39169339318](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39169339318) SUCCESS（67 Markdown、1,039 链接、0 缺失）；没有触发 Component Code Naming，此 PR 仅为 OpenSpec/事实文档更新。
- [x] 3.4 [追溯建档 PR #228](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/228) 已合并 Main SHA `866065757d1d311cd44d3055cdeee9f4ad88dba0`；`openspec/changes/relocate-local-data-platform/` 保持 **Active**，不是 Archive。此项仅关闭“追溯建档”环节，不表示第 4、5 节的运行兼容/E2E 门槛完成。

## 4. 待完成：新路径兼容与运行验证（后续独立 PR）

> 本轮追溯完成后，下一阶段仍须建立单独实施 PR。不得将已关闭的追溯建档任务视为迁移最终验收。
>
> **2026-10-18 方案扩展（用户确认）**：完成路径兼容的同时清理经证实无用的历史脚本、Probe、实验生成器、重复代码及失效测试；不删有效回归测试、不重构业务语义。**本方案更新 PR 不清理任何文件、不执行 Runtime**。实施次序：**4.1 → 4.8 → 4.2–4.4 → 4.9–4.10 → 4.5–4.7 → 5**；根据依赖先验证再删除。

- [ ] 4.1 在新的 Main 完整 SHA 上重新清点 `local-data-platform/` **全部当前 tracked 文件**，以“**A Active Runtime / B Required Engineering / C Historical Only / D Obsolete-Duplicate / E Unknown**”逐文件分类，记录 Owner、Blob SHA、有效使用者、动态依赖、测试价值、去留及证据；另建立旧路径引用矩阵和缺失路径负向断言。检查 Python、Shell、Actions/Self-Runner、Airflow GitSync、Spark、Docker COPY/Context、镜像生成器、部署配置及文档导航。393 是迁移前备份数，**不得当作今天的实际数量**。
> **4.1 首轮只读清点（PARTIAL，不打勾）**：已对固定 Healthcare Main `52237e773941def7625de72c6cecb2533f11e5d8` 获取未截断 Git Tree，确认 `local-data-platform/` **393 个 tracked 文件**，建立[393 行全量路径/Blob/候选职责 HOLD 矩阵](evidence/LOCAL-DP-FILE-INVENTORY-20261018.md)；[入口预检证据](evidence/LOCAL-DP-REFERENCE-PREFLIGHT-20261018.md) 记录 **8 个 Dockerfile、5 个核心 Build Workflow、10 个历史 Task004 Workflow、8 个 Self-Runner 示例**的静态扫描与已确认的旧路径不匹配。原备份与本轮 Main 从 #225 至今对比无 Local DP 变更；**并未验证全部间接依赖、当前部署/GitSync、全部 Self-Runner 或 Runtime，也没有批准任何删除**。下一步继续 4.1 动态依赖和双仓全量覆盖，随后 4.8 备份/逐文件去留审计。

- [ ] 4.2 按目标 SHA 修复 Python / Script / Workflow 入口路径，跑单元测试、Contract、静态质量门，验证新源码来自唯一根目录且无旧源可回退误导。
- [ ] 4.3 按镜像确定并记录 Build Context（优先以 `local-data-platform/` 为本地平台 Context，逐项审核例外）、Docker COPY、生成器和 immutable 镜像来源；保留无必要变化的容器 RUNTIME_ROOT / DAG / Batch 持久身份。完成绑定新 SHA 的真实 Clean Build、容器 `module.__file__` / Import/Entrypoint Smoke、旧来源负向验证，保存镜像 Digest。
- [ ] 4.4 验证 Airflow DAG Parse、稳定 DAG ID/依赖/Schedule 与 GitSync 单一加载路径；验证 Spark manifests / SparkApplication 包装和模块来源。
- [ ] 4.5 使用非业务写入或隔离依赖完成固定数据比较；若需共享资源执行，先单独审批、检查并行作业和 Writer Fencing。
- [ ] 4.6 经授权完成隔离端到端 NEW_ONLY 路线、独立 PostgreSQL/S3 Readback 和安全同 Batch SKIP，记录 SHA、Run、Batch、镜像 Digest 与结果；不得重放已经成功的历史批次。
- [ ] 4.7 对所有修复与清理结果进行受控接入、负向路径/已删除源码依赖测试及必要运行验证，明确未覆盖范围。发生同一问题三轮失败即 HOLD 并保存证据。

### 4A. 新增：业务无关历史文件清理（尚未实施）

- [ ] 4.8 根据 4.1 逐文件清单提供“保留 / 候选删除 / HOLD”建议，查明每个候选的实际直接与间接消费者、现有测试覆盖和历史恢复路径；对比 [Healthcare-Specs 固定备份](https://github.com/JohnZhang-DataForge/Healthcare-Specs) 的 393 个旧 Blob 与当前 SHA，针对后续新增或修改的文件确认固定 Git 恢复 Commit 及按需独立增量备份。审计报告/证据绑定 SHA，未经验证一律 E=HOLD；**此步骤不删除任何文件**。
- [ ] 4.9 在 4.2–4.4 适用兼容 Gate 通过后，按组件/依赖簇分批移除确认为 C/D 的历史 Shell、Probe、一次性生成器、重复旧实现；每一小 PR 同步受影响 CODE.md、导航、Workflow、生成器及不可变历史链接，记录恢复 SHA、证据和负向检查。A/B/E 禁删，历史 `taskNNN` 名字本身不构成删除理由。
- [ ] 4.10 审核过期测试与当前有效回归保护：只删除无独有价值的历史测试，必要时将关键断言移入现行组件 Unit/Contract/Regression Test；对被移除源码确认无有效 Import/Build/DAG/CI 引用，持续保持功能安全门槛，提交清理前后测试矩阵和适用 Clean Build/DAG 验证。**不以删除所有 `tests/taskNNN` 为目标**。

## 5. 结束条件（暂不归档）

- [ ] 5.1 复核清理后 `local-data-platform/` 仅保留当前业务及其必要的构建、测试、部署、Contract、安全/运维工程文件；C/D 已审计删除，E 有显式 HOLD 和理由，历史文件均有经核验的恢复引用；核查文档、CODE Map、CI、唯一源码/构建入口和实际运行验收证据，更新唯一项目状态文档和本 Tasks。
- [ ] 5.2 核实无行为变化时维持 `skip_specs: true`；确实有可观察行为变化则另行讨论 Delta Spec/Change，不擅自写 Current Specs。
- [ ] 5.3 满足适用回归与运行读回后再 Archive；保持与独立命名试点归档互不混淆。

## 6. 已核实的历史证据索引

| 事项 | PR / Main SHA | 实际验证 |
| --- | --- | --- |
| Backup | Healthcare-Specs [PR #2](https://github.com/JohnZhang-DataForge/Healthcare-Specs/pull/2) / `6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5` | [Run #39158372198](https://github.com/JohnZhang-DataForge/Healthcare-Specs/actions/runs/39158372198) SUCCESS；393 个 Blob 全匹配 |
| Physical move | Healthcare [PR #225](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/225) / `377df7c9fae770cde985f6e7bcbc47d40ecfa355` | [OpenSpec #39160915519](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39160915519) SUCCESS；[Component #39160915562](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39160915562) **FAIL**；无 E2E |
| Doc/CODE links | Healthcare [PR #226](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/226) / `3af772f60c8ce5aac6f474cf8b291b13d82d3d88` | [Docs #39162992543](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992543)、[Component #39162992540](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992540)、[OpenSpec #39162992541](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992541) SUCCESS |
| Repo quality tools | Healthcare [PR #227](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/227) / `7e969718cfad9368fd13866053636c787e24ca7e` | [Docs #39163725180](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725180)、[Component #39163725249](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725249)、[OpenSpec #39163725294](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725294) SUCCESS；38 单测、1,035 文档链接无失效 |
