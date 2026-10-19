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
> **4.1 第二轮只读依赖审计（PARTIAL，仍不打勾，2026-10-19）**：在 Healthcare Main `b5c49258d2102c21601ebd74bfd0aff8ba518df7`、Self-Runner Main `ffd0eccecbf0148183b956e6e4416d4b8d99002b` 基线下，已静态审阅 **21/21 Healthcare Workflows、14/14 `scripts/task004/`、24 个样本 Self-Runner Workflows、8 个样本 Task003 Shell、6 个测试及关键 DAG/Entrypoint**；发现当前五个业务镜像构建入口旧仓根路径、两份镜像测试误把仓库级 `.github` 定位至 Platform Root，以及旧镜像对 5 个 Task004 Shell 的直接依赖。历史固定 SHA 工作流不能直接当成 Main 旧路径故障。详见[第二轮跨仓依赖证据](evidence/LOCAL-DP-CROSS-REPO-CONSUMER-AUDIT-20261019.md)；尚未覆盖全部 **123 个 Self-Runner Workflows、94 个 Task003 Shell、105 个测试、Live GitSync**，任何清理均保持 HOLD，无 Runtime/构建/部署操作。继续 4.1，待完整消费者和恢复证明后再进入 4.8。


> **4.1 第三轮静态全量清点（PARTIAL，仍不打勾，2026-10-19）**：以 Healthcare `ea2d2e5ffd98c529c79626c7c926828a32fb7a7b`、Self-Runner `ffd0eccecbf0148183b956e6e4416d4b8d99002b` 为冻结基线，已逐文件读取并生成 **94/94 Task003 Shell**、**105/105 Local DP Tests**、**123/123 Self-Runner Workflows**、**32/32 Self-Runner CI 脚本**的文件级静态清单；见 [第三轮总结](evidence/LOCAL-DP-AUDIT-ROUND3-SUMMARY-20261019.md) 及其四个矩阵。静态发现 51 个生成器/历史复核候选（**非获准删除**）、2 个明确测试 Root 映射问题、65 个含旧路径的 Self-Runner Workflow（多数需按 frozen ref 正确认定）。尚缺生成器/间接调用闭包、测试实际运行、GitSync/Spark 真实来源证明，故保持 4.1 OPEN。

- [ ] 4.2 按目标 SHA 修复 Python / Script / Workflow 入口路径，跑单元测试、Contract、静态质量门，验证新源码来自唯一根目录且无旧源可回退误导。
> **4.2 首个局部修复（2026-10-19，待 PR 验收）**：两项 `tests/task004` 的静态测试已将仓库级 `.github/workflows` 定位到 `REPO_ROOT`，保留镜像/运行资源在 `PLATFORM_ROOT`。尚未消除工作流本身的旧根 Build Context / COPY / Path Filters 与测试旧断言；仅此修复不能标为 4.2 PASS，更不构成 4.3/4.4 验收。关联证据：`evidence/LOCAL-DP-TEST-ROOT-FIRST-FIX-20261019.md`。不执行 GHCR/K8s/PG/S3。

> **4.3 Synthea 构建路径首个修复 PR（2026-10-19，尚未通过 Clean Build）**：针对 `build-synthea-image.yml` 修正源文件 Trigger Paths、Docker Context=`./local-data-platform`、Dockerfile 路径，保持 Dockerfile 内 COPY 路径和容器内部绝对路径不变，并同步静态单测断言。实际 Build、Digest、Import/Entrypoint Smoke 均未执行；本 PR 已移除 Main push 自动发布，GHCR 仅可手动 Dispatch；PR 仍保持 Draft，直至源码验证和 Clean Build Gate 完成。证据见 [Synthea 构建路径修复](evidence/LOCAL-DP-SYNTHEA-BUILD-CONTEXT-20261019.md)。4.3 仍 OPEN。

- [ ] 4.3 按镜像确定并记录 Build Context（优先以 `local-data-platform/` 为本地平台 Context，逐项审核例外）、Docker COPY、生成器和 immutable 镜像来源；保留无必要变化的容器 RUNTIME_ROOT / DAG / Batch 持久身份。完成绑定新 SHA 的真实 Clean Build、容器 `module.__file__` / Import/Entrypoint Smoke、旧来源负向验证，保存镜像 Digest。
> **4.3 TASK004 Runtime 独立小批次（2026-10-19，PR 待验证）**：构建 Context 改为 `local-data-platform/`，镜像及 Shell COPY 源码按原 Platform Root 保持，静态源码检查不再执行过时的 `06a-prepare-unified-runtime-image.sh`（该脚本会覆盖 Workflow/Test/Dockerfile）。为防止 feature/main Push 自动发布 GHCR，将此 Runtime Workflow 暂定`workflow_dispatch` 或安全的 `pull_request` 源码测试（发布 Job 仅手动）；没有授权 Dispatch。PR 仅 Draft，Clean Build/Digest/Smoke 未验证。详见 `evidence/LOCAL-DP-TASK004-RUNTIME-CONTEXT-20261019.md`；4.3 继续 OPEN，4.9 HOLD。

> **4.3 隔离 Clean Build 验证（2026-10-19，实施中）**：新增独立 GitHub PR Workflow 对 Synthea 与 TASK004 Runtime 进行 `--pull --no-cache`、`--network none` Entrypoint 非业务 Smoke、COPY 来源检查与本地 Image ID 记录；禁止镜像 Push / GHCR Login / K8s / PG / S3。此前静态 CI 和源码单测 PASS 不等于此项 PASS；须依据当前 PR HEAD 的实际两个 Job 结果逐个更新，失败按三轮 HOLD。见 [隔离构建验证](evidence/LOCAL-DP-ISOLATED-IMAGE-BUILD-20261019.md)。

- [ ] 4.4 验证 Airflow DAG Parse、稳定 DAG ID/依赖/Schedule 与 GitSync 单一加载路径；验证 Spark manifests / SparkApplication 包装和模块来源。
> **4.4 Airflow 静态源文件预检（2026-10-19，验证 PR）**：新 GitHub PR Gate 对 `local-data-platform/airflow/dags/*.py` 进行 AST / compile（不导入 Airflow、无 DagBag、无调度或 Runtime），核对本地模块名称与静态 `dag_id` 唯一性，输出 `DAG_PARSE_RUNTIME=NOT_VERIFIED`。现存 `.github/workflows/task004-airflow-step03e-main-runtime-pin.yml` 的历史路径 `airflow/dags/...` 与迁移后位置不同，且限特定 feature 分支，不可当当前运行 PASS。真正 DAG Parse、GitSync 单一加载与 Spark Runtime 仍 HOLD。见 [Airflow 静态来源预检](evidence/LOCAL-DP-AIRFLOW-SOURCE-PREFLIGHT-20261019.md)。

> **4.4 DagBag 隔离 Parse 试验（2026-10-19）**：PR 新增 GitHub-hosted Runner 上的 `apache/airflow:3.2.2`、`--network none` / DAG 目录只读挂载的真实 `DagBag` 加载检查；不开 Scheduler、不执行 Task、不访问集群。镜像是否预装 Kubernetes Provider 尚不保证；若缺失或 API 不兼容按真实失败/HOLD 记录，绝不标记 PASS。无需改动任何业务 DAG。证据见 [DagBag 验证](evidence/LOCAL-DP-AIRFLOW-DAGBAG-20261019.md)。

> **4.4 来源闭包继续核对（2026-10-19，PARTIAL）**：PR #261 / Run #39295887624 Airflow 3.2.2 DagBag 真实离线 Parse PASS（isolated image 装入固定 `psycopg`）；仍未验证正在运行的 GitSync checkout、Helm DAG 挂载、Spark ConfigMap data SHA 与 `mainApplicationFile` 来源。任务 4.9 不得因此解锁。见 [GitSync / Spark 来源 HOLD 证据](evidence/LOCAL-DP-GITSYNC-SPARK-PROVENANCE-HOLD-20261019.md)。

> **4.4 来源探针准备（2026-10-19，未执行）**：添加手动 opt-in 的只读 `local-data-platform/scripts/quality/read-only-gitsync-spark-provenance.sh`；仅 `kubectl get` Airflow Pod / 指定 Spark ConfigMap，核对一个 ConfigMap Python key 与固定 Git 文件 SHA256，输出 GitSync 配置相关键名与挂载位置；**不证明实时 GitSync checkout SHA / Pod import __file__，不触发集群写入，未执行任何探针**。原始 JSON 需按敏感配置处理，不允许提交仓库。见 [只读探针使用与限制](evidence/LOCAL-DP-READONLY-LIVE-PROVENANCE-PROBE-20261019.md)，4.4 PARTIAL / 4.9 HOLD。

- [ ] 4.5 使用非业务写入或隔离依赖完成固定数据比较；若需共享资源执行，先单独审批、检查并行作业和 Writer Fencing。
- [ ] 4.6 经授权完成隔离端到端 NEW_ONLY 路线、独立 PostgreSQL/S3 Readback 和安全同 Batch SKIP，记录 SHA、Run、Batch、镜像 Digest 与结果；不得重放已经成功的历史批次。
- [ ] 4.7 对所有修复与清理结果进行受控接入、负向路径/已删除源码依赖测试及必要运行验证，明确未覆盖范围。发生同一问题三轮失败即 HOLD 并保存证据。

### 4A. 新增：业务无关历史文件清理（尚未实施）

- [ ] 4.8 根据 4.1 逐文件清单提供“保留 / 候选删除 / HOLD”建议，查明每个候选的实际直接与间接消费者、现有测试覆盖和历史恢复路径；对比 [Healthcare-Specs 固定备份](https://github.com/JohnZhang-DataForge/Healthcare-Specs) 的 393 个旧 Blob 与当前 SHA，针对后续新增或修改的文件确认固定 Git 恢复 Commit 及按需独立增量备份。审计报告/证据绑定 SHA，未经验证一律 E=HOLD；**此步骤不删除任何文件**。
> **4.8 部分备份证据（PARTIAL，仍不打勾，2026-10-19）**：已在冻结 Healthcare Main 与独立 Private Healthcare-Specs Main Git Tree 之间完成 **393/393 路径 + Git Blob SHA 双向读回一致、0 遗失、0 差异**，见[跨仓备份读回](evidence/LOCAL-DP-BACKUP-BLOB-READBACK-20261019.md)。这只证明对应两个 Git Commit 的源码恢复基础；每个删除候选的现行消费者和回归覆盖尚未得到负向证明，也未验证 K8s/PG/S3/镜像恢复，故 4.8 OPEN、批准删除数 0。

> **4.8 首批有据可查的 C 类退役候选（PARTIAL，2026-10-19；不执行删除）**：已在固定 Healthcare Main `f3b2d9e97d9afe4e7457a1d48fde9e655add47d7` 全部 **622/622 tracked 文件**及 Self-Runner SHA `ffd0eccecbf0148183b956e6e4416d4b8d99002b` **270/270 tracked 文件**中进行三个历史文档生成器的精确名称静态消费扫描，并核对三个脚本与独立备份 **3/3 Git Blob 一致**；锁定 `scripts/task003/{04-write-closeout-docs.sh,05-write-ae-freeze-doc.sh,05f2-write-freeze-doc.sh}` 为首批 **C / 推荐后续退役候选**。现行精确名称引用仅历史脚本自述、CODE.md 导航和 OpenSpec 审计材料，未发现正式 Workflow、DAG、镜像等直接字面调用；仍须排除动态路径/外部调用并通过 4.2–4.4 的 Build/DAG/回归门禁，才可在单独 4.9 PR 删除。见 [首批退役候选与恢复门槛](evidence/LOCAL-DP-FIRST-RETIREMENT-CANDIDATES-20261019.md)。**4.1 / 4.8 仍 OPEN，已删除 0，当前批准删除 0。**

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
