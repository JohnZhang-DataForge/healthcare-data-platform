# Portal 多 Session 并行开发协议 — 2026-10-27

> **ACTIVE COORDINATION / NOT DEPLOYMENT AUTHORIZATION.** 本文件是已有 Active Change `healthcare-on-demand-live-demo` 的并行实施任务说明；唯一勾选进度在同目录 `tasks.md`，不是新 Change 或独立 Session Handoff。目标仓库是公开的 `JohnZhang-DataForge/healthcare-data-platform`，所有新代码仍在该仓库。网站属于现有 `platform-portal/portal/` 组件。

## 用户最新决策（覆盖旧 P4 独立开发分工）
- **网站**：复用现有 Marquito 展示逻辑和 UI，不重写血缘图。原作者仓库 `mdrakiburrahman/spark-sandbox/projects/marquito`（Next.js/React，`output: 'export'`）。许可证尚未核实；非商业用途不自动构成复制/公开再发布许可。授权之前可独立检查/设计集成/测试原仓库及我们自有适配层，**不得将作者受版权保护的项目源码复制到本公开仓库或发布上线**；用户计划联系作者取得授权。必要时将依赖问题报告主 Session，不擅自改成重写前端项目。
- **数据**：从现有本地 Marquez 只读导出 OpenLineage JSONL，并产生 P0 `portal.snapshot.v1` 摘要。Synthea 为纯合成数据；公开前仅检查 OpenLineage Facets 的内部地址、运行参数、SQL、Secret 等元数据，尽可能保留 Dataset namespace/name、RunID 和表/列血缘一致性。禁止把未经检查的原始 Event 或凭据直接公开。
- **Cloudflare**：用户自己手工配置 Cloudflare Pages、GitHub 连接、域名、构建与需要时的环境绑定；**不做独立 P4 Infra 源码模块、不自动部署**。已准备人工操作指南：[`documents/systems/platform-portal/portal/CLOUDFLARE-MANUAL.md`](../../../documents/systems/platform-portal/portal/CLOUDFLARE-MANUAL.md)。
- **访客 Trigger/Control**：暂不并行实施。只有静态只读站点和 Azure 事件同步验收后，主 Session 才编排原 5.x 受控触发功能；GET、访客访问不能启动业务运行。
- **Azure**：Fabric / Local Spark 业务代码可移植性仍 `HOLD`；前三次 Fabric Notebook 验证失败，用户未授权第四轮；Agent C 仅离线编码和静态/单测，绝不调用 Fabric Notebook、Terraform apply、K8s/Spark/Marquez POST 等共享 Runtime 修改。实际 Azure 集成另立 Gate。

## 三个独立 Agent 与代码唯一所有权

| Agent | 人话范围 | 可变更的源代码位置 | OpenSpec Task | 不可碰 |
|---|---|---|---|---|
| A — Marquito Web | 网站、静态 JSONL 读取、图表、空数据/错误/上次成功 | `platform-portal/portal/web/**` | 7.1、7.2 | Exporter、Azure Relay、P0 Schema、Cloudflare 配置 |
| B — Marquez Exporter | Marquez GET → 事件字段检查 → JSONL 和 `portal.snapshot.v1`、批次证据 | `platform-portal/portal/exporter/**` | 7.3、7.4 | Marquez POST、PG14 修改、Web、自行发布公网 |
| C — Fabric/Blob Relay | Azure Event Publisher + Blob Manifest、Local Consumer 去重/重投，离线测试 | `azure-fabric/openlineage/**`、`platform-portal/openlineage/blob-relay/**` | 7.5、7.6、7.7 | Notebook live、Fabric Trial、K8s、业务 Writer、Web |
| Coordinator — 主 Session | P0 Contract、共享接口约束、CODE 系统导航、PR 顺序、手工 Cloudflare 指南、最后联调 | `platform-portal/portal/contracts/**`、`documents/systems/platform-portal/portal/README.md`、`documents/systems/platform-portal/portal/CODE.md`、此 OpenSpec 共享计划 | 7.0、7.8、跨组件 Gate | 未授权的共享 Runtime |

**开工顺序**：每个 Agent 先从最新 Main SHA 创建**不同**的功能分支，检查当前开放 PR。A、B、C 可以同时完成静态源代码与测试；真实环境操作必须另外批准、核对并发，不属于此次授权。

## 接口冻结 / 协同细节

- P0 现有 `platform-portal/portal/contracts/*.schema.json`、`fixtures/*.mock.json` 是唯一可信的 Snapshot/API 合同，`schema_version=portal.snapshot.v1`。所有者仅 Coordinator；Agent 不单独修改。
- A 与 B 约定网站静态文件候选地址 `/data/lineage/latest.jsonl`（Marquito JSONL 用途），摘要仍 `/data/latest.json`；这是一条 **补充候选接口**，在 A/B 同意并由 Coordinator 做兼容性审查前不算正式 P0 v1 已验收发布合同。实现时不得改变 P0 已冻结字段。
- B 使用合成患者的真实历史事件时，须区分 `MOCK` vs `VERIFIED_EXPORT`：后者必须满足源提交、Manifest SHA、GitHub Run 证据以及独立校验，不能因为解析成功就冒充完整 Azure/三医院 E2E。
- A 的首版可以用现有 Mock 和经过校验的离线样本做视觉开发；不能说 Mock 是真实 Batch。
- C 保留 OpenLineage 标准事件中的 Job/Run/Dataset/Column Facet，不凭名称编造跨 Local/Fabric 的 Dataset 边；Blob 事件对象不可变、SHA256 验证、最后提交 Manifest；本地 Consumer 只向 Marquez 投递血缘，不触碰 OMOP 数据处理。

## OpenSpec 同步与 PR 冲突控制（硬规则）
1. **每个 Agent 的任何实质性源码 PR 都必须在 PR 正文分别写独立两行**：`OpenSpec-Change: healthcare-on-demand-live-demo` 和且仅一行 `OpenSpec-Task: 7.n`。任务 ID 必须来自 `tasks.md`，并在该 PR 同步更新其对应的**唯一任务行**。若只完成部分，仅添加有证据的进度，不勾选未完成内容。
2. **禁止**三个 Agent 同时整体重写 `tasks.md`、`design.md`、共享 P0 Schema、`documents/systems/platform-portal/portal/CODE.md`；每个 Agent 只在任务行与所拥有的组件代码做最小修改。因 CI 要求新增源码同步 CODE 地图，必须通知 Coordinator，让其在相关 PR 前确定 CODE 变更；优先在 PR 中仅追加本人代码导航条目并在合并前对最新 Main rebase，绝不覆盖别人。
3. 每个 Agent 从主分支独立 Branch/PR，不自行合并 Main；主 Session 检查代码、CI、OpenSpec Tasks、下游影响后协调依序 Merge。若工作跨多个 PR，沿同一 Task 逐 PR 留下不同 HEAD/Run 证据；不要勾选“全部完成”直到实际达到验收。
4. Agent **必须**在 PR 描述/评论写：`DONE / NOT DONE / NEXT`、HEAD 40 位 SHA、CI 链接、确切运行副作用、遇到的 HOLD。暂时停止或阻塞时更新 PR/Issue，不创建平行 Session Handoff。主 Session 用户再来问进度时，从 GitHub 开放 PR/Main SHA/Actions/Tasks **按需重新读取**，不会异步自主监控。
5. 跨 Agent 的共同接口、Marquito 许可、任何 Cloudflare 实际上线、Azure 实机写入，先由主 Session 单点作出决定。禁止 Agent 通过直接修改他人的文件“顺手修复”。

## Agent A 可复制工作指令 — Marquito 网站

你是 Healthcare Portal **Agent A（Web）**，在 Public 仓库 `JohnZhang-DataForge/healthcare-data-platform` 内独立工作；主协调 Session 通过同一 OpenSpec Change 和 PR 审核。先阅读 `AGENTS.md`、`documents/README.md`、`documents/engineering/development/AGENT-RULES.md`、`documents/engineering/development/SESSION-COORDINATION.md`、`documents/systems/platform-portal/portal/README.md`、此计划与 `tasks.md`；读取 Main 完整 SHA 和开放 PR 后新建自己的 Branch。你仅负责 `platform-portal/portal/web/**`（新增源码必须在同 PR 同步 CODE 导航），对应 `OpenSpec-Task: 7.1`（作者项目评估、许可证、静态可运行性）及后续 `7.2`（集成）。目标是复用作者现有 Marquito 而**不从零设计/重写血缘图**；检查 `mdrakiburrahman/spark-sandbox/projects/marquito` 的 Next.js `output: export`、JSONL parser、DataSourcePicker、Jobs/Table/Column 图。许可证未确认且用户拟联系作者，勿将其受版权保护源码复制到本仓库或发布公网；可以进行只读分析、使用我们自己写的兼容适配代码/Mock、准备 PR 或报告明确的授权 blocker。设计静态 `/data/lineage/latest.jsonl` 与 `/data/latest.json` 的读取方案，与 Agent B 对齐；页面刷新与 GET 永远不会触发 E2E，展示 MOCK 标签和最后真实成功时间，断网保持已发布静态内容。静态/单测优先，不部署 Cloudflare、不修改 P0/Exporter、不开启任何云资源。提交独立 PR，正文单个 OpenSpec Task 行，`tasks.md` 只更新自己的 7.1/7.2 行，提供 HEAD SHA/测试/阻塞/下一步，合并由主 Session 协调。

## Agent B 可复制工作指令 — Marquez 出口

你是 Healthcare Portal **Agent B（Exporter）**；从 `JohnZhang-DataForge/healthcare-data-platform` 最新 Main 创建独立 Branch，阅读根 `AGENTS.md`、工程规则、Portal README/CODE、已有 OpenSpec Change 及本计划后开始。仅修改 `platform-portal/portal/exporter/**` 和本人单条 `tasks.md` 进度（必要 CODE 导航作最小增量并通知主 Session），任务为 `7.3` 和 `7.4`。开发**只读** Marquez API 导出，获取真实 Job/Run/Dataset/上下游及 Column Lineage，输出 Marquito 兼容的 OpenLineage JSONL 和 P0 `portal.snapshot.v1`。首先离线用 Mock/合成 fixture 完成单测、跨引用、ID/Namespace 保持、空数据/失败/重复输入稳定结果和字段检查；Synthea 病人为合成数据，但公开前检查事件 Facet 的内部 URI/SQL/令牌/敏感运行参数，避免改坏 Dataset/Column 边。不能把 Marquez 只读 API 的“成功读取”等同于某个新 Azure 运行或完整 E2E；VERIFIED_EXPORT 必须满足证据门槛。明确与 Agent A 对齐 `/data/lineage/latest.jsonl`、`/data/latest.json`，需要更改 Schema 则申请主 Session 审核，不自行改合同。不得向内网 Marquez POST、改 PG14、重跑 Synthea、写 Writer、发布公网。独立 PR、CI、OpenSpec 每 PR 一条 Task 标签，报告 DONE/NOT DONE/NEXT、40位 SHA 与精确证据，主 Session 审核后合并。

## Agent C 可复制工作指令 — Azure OpenLineage 和 Blob Relay

你是 Healthcare 的 **Agent C（Azure 血缘事件桥）**；最新 Main → 独立 Branch，阅读 `AGENTS.md`、OpenSpec 本计划、`documents/infra/SPARK-PORTABILITY-POC-20261026.md`、`documents/engineering/development/SESSION-COORDINATION.md` 和安全操作规则。唯一代码范围 `azure-fabric/openlineage/**`、`platform-portal/openlineage/blob-relay/**`，更新本人的 `tasks.md` 行和相关 owning CODE 文档最小条目（如果需要共享 CODE 文件则告知主 Session）。任务 `7.5`：研究 Fabric Spark 4.1 / Scala 2.13 vs 本地 Spark 3.5.7 OpenLineage Listener 兼容与必要配置；`7.6`：开发离线 OpenLineage 事件上传到 Blob 的 Publisher，条件创建/SHA256/最终 Manifest；`7.7`：开发本地可靠 Consumer，Manifest 检查/幂等去重/失败重试/独立 readback checkpoint，使用 Fake Blob、Fake Marquez 的测试，绝不因事件重投而重跑 OMOP Writer。**严格不做真实 Fabric Notebook 重试、不操作免费 Trial/付费容量、不调用真实 Blob 写入、不改 Marquez/PG14、不运行共享 K8s/Spark**；此前 Fabric 三次 Notebook 尝试失败，当前仍 HOLD。需要真实授权时仅提交需求和风险给主 Session。PR 正文每次仅一个 `OpenSpec-Task: 7.n`，同时关联 `OpenSpec-Change: healthcare-on-demand-live-demo`，包括 DONE/NOT DONE/NEXT、HEAD、测试、阻塞、未运行的实机项目；主 Session 决定合并与集成阶段。

## 给主 Session 的合并顺序与复核清单

1. Main 新增本计划和 7.x 任务，且 CI 验证通过。
2. A/B/C 独立启动。先审查 B 的 JSONL 字段/契约，再检查 A 对解析的消费；C 只离线推进，可与 A/B 同时进行。
3. 每次 PR 先查 CHANGE Gate、OpenSpec Static、Trusted Gate、源码 CODE、目标 HEAD 的测试；只有通过并真正 Merge 才给 `tasks.md` 该项 Done。
4. A/B 有真实可用的静态构建产物、JSONL 公开字段核验和网站验证后，将 [手工 Cloudflare 指南](../../../documents/systems/platform-portal/portal/CLOUDFLARE-MANUAL.md) 交用户执行；Cloudflare 资源设置由用户确认后再更新 7.8。
5. C 完成离线 Publisher/Consumer 后，独立讨论 Fabric HOLD 与一次可控的真实集成验证。访客自动触发控制器排到后续一期，不影响第一版网站发布。

## Agent D — Website Alternative Research (NEW, 2026-10-27)

**Trigger:** Marquito source redistribution/public website deployment authorization is **not yet granted**. Agent A #518 assessed upstream, and #519 retained a first-party GET-only static data adapter after rollback of upstream copyrighted files; #519 is **DRAFT/HOLD**. Neither PR has merged Main. Do not interpret the rollback as license clearance, or immediately commission a new UI implementation.

**Task:** OpenSpec **7.10**. D is a **research-only** Agent. Exclusive report location: `documents/systems/platform-portal/portal/FRONTEND-ALTERNATIVES.md` (create as the only maintained research artifact). Agent D must not modify `platform-portal/portal/web/**`, `platform-portal/portal/exporter/**`, `platform-portal/portal/contracts/**`, `documents/systems/platform-portal/portal/CODE.md`, or existing Agent A PRs. No extra deployment/tool installation, real data access, or shared runtime work. Agent D can minimally update only its own 7.10 line in `tasks.md` to pass the OpenSpec PR gate. The Main Session manages any plan or contract change and the final choice.

**Research goal:** Find the fastest **legally reusable** way to create a publicly viewable, static, read-only, attractive healthcare OpenLineage showcase for Emory recruiters; prioritize ready-made existing OpenLineage/Marquez display products **if** their licenses permit copying/modifying/redistributing, then mature graph libraries with explicit usable licenses if full products are unsuitable. Do not blindly assume a noncommercial use exemption. Do not transplant third-party source into our public repo while permission is unclear.

**Inputs:** Main portal P0 schema `portal.snapshot.v1` (`/data/latest.json`), Agent B exporter sanitized OpenLineage JSONL candidate (`/data/lineage/latest.jsonl`), original first-party Agent A data source adapter, and known upstream Marquito limitations (job map keyed only by job name, which can collide across namespaces). Do not fabricate runtime evidence.

**Minimum source-verified comparison:**
1. Compare at least **5 concrete candidates**: full website / lineage visualization tools (including ready-made Marquez GUI and any other genuinely relevant OpenLineage/SQL-lineage frontends) plus library-based options such as React Flow + Dagre/ELK, Cytoscape.js, or an appropriate Apache-licensed graph library; separate finished website vs drawing library. Only include candidates with a currently documented license and official link; mark any uncertain license **HOLD/NOT ELIGIBLE** rather than assume MIT.
2. For each: exact repo, LICENSE permalink/term relevant to commercial and non-commercial redistribution, active maintenance/release, browser-only/static-build/Cloudflare Pages support (no secret server), input adapter scope (OpenLineage JSONL), Table/Column lineage, Namespace collision handling, expected implementation workload, CSS/design maturity, GitHub security/dependency risk and actual runnable demos.
3. In one matrix rank by **fastest time to legally deploy**, completeness for recruiters, low refactor cost, zero-cost static hosting, and maintenance burden. State whether sample screenshots/code/README are actually verified vs inferred.
4. Propose a minimal offline proof method with Agent A's own synthetic fixtures: job namespace + name identity, two datasets, two real column edges, jobs table, timeline, error and stale snapshot, without fabricating any public VERIFIED_EXPORT. No new core code unless the Coordinator explicitly assigns a subsequent implementation task.
5. Output a single clear recommendation and a second fallback, plus a day-by-day small-step handoff for Agent A. If source reuse permission arrives, compare licensed Marquito against the alternatives using the same criteria; do not overwrite A's original work.

**Safety/PR:** Read `AGENTS.md`, engineering/Session Coordination, Portal README/CODE and OpenSpec tasks/design, existing Agent A #518/#519, Agent B merged #523. Start a new branch from latest Main. Report-only PR uses `OpenSpec-Change: healthcare-on-demand-live-demo` and `OpenSpec-Task: 7.10`, changes the research report and **only 7.10** task line, passes CI, does not self-merge. Include DONE/NOT DONE/NEXT, exact HEAD and links. The Main Session reviews and selects architecture.

**Copy-ready Agent D kickoff:**

> 你是 Healthcare Data Platform **Agent D — 公网血缘展示替代品调研**。仓库 `JohnZhang-DataForge/healthcare-data-platform`，OpenSpec `healthcare-on-demand-live-demo` 任务 **7.10**。这是独立 Research Session，不开发或部署前端。先读根目录 `AGENTS.md`、`documents/systems/platform-portal/portal/README.md`、`documents/systems/platform-portal/portal/CODE.md`、`openspec/changes/healthcare-on-demand-live-demo/{tasks.md,design.md,parallel-workstreams.md}` 和工程/Session Coordination 规则，再看 Agent A #518/#519（#519 Draft/HOLD）及已合并的 Agent B #523。Marquito 上游作者尚未授权公开复制和部署，绝不能复制其未获授权的源码到我们的 Public Repo；不因非商业用途推定许可。请直接研究并比较至少 5 个真实的、具备明确许可证的现成 OpenLineage/数据血缘前端或图组件，包含 Marquez GUI 和 React Flow/Cytoscape.js 等备选；区分“现成可用网站”和“只有绘图组件”。逐项核实官方仓库、LICENSE、维护活跃度、Next.js 静态输出/Cloudflare Pages、无后端公网依赖、OpenLineage JSONL 解析适配、Table/Column Lineage、Namespace 同名 Job、运行时间轴、界面成熟度、预计工作量及成本。优先最少代码、最短上线时间、最适合 Emory 招聘人员浏览且可合法再发布的方案。提出一个推荐、一个备选、最小合成数据 PoC 验收步骤与 Agent A 接手任务。只允许创建 `documents/systems/platform-portal/portal/FRONTEND-ALTERNATIVES.md` 调研报告，必要时仅更新 OpenSpec `tasks.md` 中的 7.10 行；其他 Web/Exporter/CODE/P0 文件不改，不触碰 Azure/Marquez/Cloudflare 实机、不操作共享环境。最新 Main 独立 Branch、单独 PR，正文必须逐行写 `OpenSpec-Change: healthcare-on-demand-live-demo`、`OpenSpec-Task: 7.10`，CI 通过后把链接、HEAD SHA、研究证据、DONE/NOT DONE/NEXT 返回主 Session；不要自行合并 Main。
