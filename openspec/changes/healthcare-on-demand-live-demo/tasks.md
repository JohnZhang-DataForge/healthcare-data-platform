# Tasks

> **ACTIVE / TARGET DESIGN, NOT RUNTIME AUTHORIZATION.** 本次仅冻结人类可读架构与未来可测试需求；完成文档任务不表示 Fabric Spark Listener、Blob 同步、Cloudflare、付费容量或真实新 E2E 已部署。具体共享环境真实运行、云资源成本和公开发布仍需单独批准。唯一任务清单在本文件。

## 1. Architecture and specification baseline (this PR)

- [x] 1.1 核对 Healthcare/Self-Runner 最新 Main 与开放 PR/Running Workflows，阅读文档治理、现有 Fabric Capacity Trial 和本地 Portal 真实验收与延后边界，确定本轮纯文档影响范围。
- [x] 1.2 在 documents/infra/ 冻结 On-Demand Live Demo 目标、双 Spark 可移植策略、OpenLineage → Blob → Marquez/PG14、Marquito 风格展示、访问控制/预算/不实施边界。
- [x] 1.3 创建 OpenSpec Proposal、Design、Delta Specs（目标 Requirements/Scenario）及后续逐项验收 Tasks；文档索引必须链接唯一权威设计。
- [x] 1.4 设计基线 [Healthcare PR #508](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/508) 经 OpenSpec validate、Trusted Change Gate、Change Gate、Documentation Relative Links 四项 GitHub 检查 SUCCESS，2026-10-26（美国东部）已 squash merge 到 Main `a030d02d46c85bc6932ce7ddba73b5c609f25b58`，并独立从 Main 读回正式方案。设计关闭不等于后续实现或运行验收。

## 1A. P0 Portal contract foundation（2026-10-27，代码/Schema；尚未部署）

- [x] 1.5 为 P1–P4 冻结 Versioned Snapshot/Trigger/Status/Error JSON Schema v1，包含严格白名单、Mock/Verified Origin、证据门槛、不可用户指定 Workflow/Backend 的负向约束。正式约定见 [Portal P0](../../../documents/systems/platform-portal/portal/README.md)。
- [x] 1.6 提交只含虚构合成数字的 `platform-portal/portal/fixtures/*.mock.json`，显式 `MOCK ONLY`，用于前端/Exporter/Worker/部署的独立 Mock 集成；不冒充现有真实 P5 Batch。
- [x] 1.7 建立 P1–P4 独占目录、CODE 地图、Branch/PR 及共享资源协调边界，明确 GET 静态快照与 POST 控制接口契约。
- [x] 1.8 **CONTRACT FROZEN v1（仅机器契约，不代表部署）**：P0 [PR #513](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/513) HEAD `516721a055a2a0bb2babdf91102691c293cb68c1` 的 旧 CI（当时名称为 Showcase Contract Validation）、OpenSpec Static、OpenSpec Change Gate、Trusted Change Gate、Documentation Relative Links、Component Code Naming **6/6 SUCCESS**；Squash Merge `a5778f50b06f4cfb3051df3a1870b5be0dd97aee`，从 Main 实际重新读取 `snapshot-v1.schema.json` 和 `documents/systems/showcase/README.md` 并确认版本。后续 Schema 调整需版本/兼容审查；真实展示/Cloudflare/Runner 尚未部署。
- [ ] 1.9 Portal 后续实现/集成总 Gate（原 P1–P4 分工由下文第 7 节最新并行策略覆盖）。Web、Exporter、Azure Relay、访客 Control 与用户手工 Cloudflare 各自验收后方可关闭；P0 不包括实机部署。
- [x] 1.10 **Portal 命名/路径更正（Main 验收完成）**：原顶级 `showcase/` 与单独 `documents/systems/showcase/` 全量搬迁到 `platform-portal/portal/` 和 `documents/systems/platform-portal/portal/`，`schema_version` 改为 `portal.*.v1`，CI 改名并同步系统 README/CODE；[PR #515](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/515) 六项检查全部 SUCCESS，Main Squash `59a5ef8ab65aa3fa757ef710f4bdb96f0440d72b`；独立从 Main 读回 `portal.snapshot.v1`、新 CODE 与 CI，确认旧根目录及旧 Workflow 均不再存在。

## 2. Free-runtime compatibility proof (future separately authorized work)

- [ ] 2.1 固定跨 Fabric/Local 的 PySpark/Delta/OpenLineage 版本矩阵和冻结 FHIR/HL7 合成输入 Contract、测试账号/Workspace/费用 Gate。**已完成一部分实机只读证据**：[Self-Runner #40438541415](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40438541415) GET 成功：`healthcare-omop` 与 `johnzhang-test` 都是 Fabric Runtime 2.0 / Starter Pool；本地 dw-spark 27 个历史 SparkApplication 均 3.5.7，检查时 active=0；当前可见 Trial FTL4 Active。已提交隔离内存 PySpark 冒烟源码，**但尚未真正执行 Fabric Notebook / Local Spark 和 OpenLineage，故 2.1 保持未勾选**。
- [ ] 2.2 免费 Fabric 真实 Notebook POC：Listener/SDK 产生 START、COMPLETE、Input/Output、ColumnLineage；Blob readback；记录 CU/时长与失败。**部分实机证据 / HOLD**：FTL4 Trial 的 Notebook 三次 CREATE/RUN/DELETE 成功，但 DataFrame `exitValue` 缺失，无法确认转换输出；[#40439764059](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40439764059)、[#40440025579](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40440025579)、[#40440244737](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40440244737) 皆 FAILURE，已达到三轮停止规则。Notebook GetDefinition 返回 HTTP 202，需先处理 Create/Definition LRO 并独立读回真实源码；根因未确认。见 [兼容性实测报告](../../../documents/infra/SPARK-PORTABILITY-POC-20261026.md)。**未测 Fabric Listener/Blob、继续未勾选，未经用户决定不再重试**。
- [ ] 2.3 现有 K8s Spark Operator 同核心 ETL POC：业务 DQ、持久读回与 OpenLineage 一致性；不得回放冻结历史 OMOP Batch。**仅合成数据内存算子实机 PASS**：[Self-Runner #40439394218](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40439394218)，Spark 3.5.7 / 5 Rows / SHA256 `5c4add3c4976f2d894fd24da8477ea43c48a9069ef66eb2763d7d47f404eac1b`。真实 FHIR/HL7、业务持久读回和 OpenLineage 仍未测试；[报告](../../../documents/infra/SPARK-PORTABILITY-POC-20261026.md)，故此项**继续未勾选**。
- [ ] 2.4 两后端数据/性能/费用报告；用户依据证据选择正式常态 Backend 或保留双模式，不能推断付费 F2 已授权。

## 3. Immutable OpenLineage Blob relay (future)

- [ ] 3.1 独立 Blob 事件前缀/身份权限、Schema、Manifest/SHA/条件创建与无敏感字段输出的单测。
- [ ] 3.2 Local 与 Fabric 真实 Event 可靠传输，断网/部分失败/重复/乱序/幂等的受控测试。
- [ ] 3.3 本地 Consumer 仅对成功事件调用内网 Marquez POST，PG14 GET/Job/Run/Dataset 独立读回后 checkpoint；不能重跑业务 Writer。
- [ ] 3.4 Dataset URI/Manifest 证据跨 Runtime 对齐，不依赖 Fabric CascadeDelete 等资源依赖伪造业务边。

## 4. Read-only Portal (future)

- [ ] 4.1 核实 Marquito 源码许可或选取有许可的图形组件，使用真实脱敏 JSONL 在浏览器验证 Table/Column Lineage。
- [ ] 4.2 创建 Cloudflare Pages 匿名只读站点和版本化快照，验证数据字段白名单/脱敏，不能直接访问 Marquez/API/PG/Private Blob。
- [ ] 4.3 在失败、Runner/Cloud unavailable 和 AUTO_TRIGGER=OFF 下仍展示上次成功快照与时间，不伪装 LIVE。

## 5. Visitor trigger, control and budget (future)

- [ ] 5.1 服务端 Turnstile、US Geo、3/IP/UTC 日、全站上限、single-flight、请求幂等与原子计数；GET 与爬虫不触发。
- [ ] 5.2 独立管理员 Self-Runner OFF/ON/Emergency OFF Workflow；调用网站不得获得 GitHub/ARM 写权限或任意任务调度能力。
- [ ] 5.3 实际 E2E 状态证据、成功/失败管理员邮件、超时熔断、全站预算/异常关闭与恢复演练。
- [ ] 5.4 只在用户明确批准付费资源后开发 Paid F2 Resume/Pause；免费 Trial 必须走其独立受限策略。

## 6. Final acceptance (future)

- [ ] 6.1 验收真实新 5–10 患者批次：Source Manifest、Azure Blob、Spark ETL、DQ、OpenLineage Event、Marquez PG14 独立读回、公开快照与邮件/成本报告。
- [ ] 6.2 测试恶意/重复/非 US/IP 额度/跨日/并行请求，以及家用网络、Azure、Runner、Cloudflare 失败路径和回退。
- [ ] 6.3 仅达到全套 E2E 与代码、许可、权限、预算 Gate 后同步 Current Specs、按真实证据 Archive Change；OpenSpec 静态 PASS 不能替代验收。

## 7. 并行 Agent 实施与手工 Cloudflare（2026-10-27 最新分工）

> 详细角色、可复制 Agent 指令、代码所有权与冲突解决统一见 [parallel-workstreams.md](parallel-workstreams.md)。此节任务由主 Session 汇总；各 Agent PR 需关联对应**单独**任务行并只编辑自己的进度，不以其他 Session 的代码完成代替真实验收。**P4 Infra 源码模块已按用户决定取消**；原 4.x/5.x 是历史功能需求，并不构成自动运行授权。

- [x] 7.0 确定三个并行 Agent：A Marquito Web、B Marquez GET-only Exporter、C Azure OpenLineage Blob Publisher/Local Consumer；协调分支与独占代码路径，Cloudflare 改用户手工发布，暂缓访客 Control；完成本计划并由 CI/PR 入 Main（仅计划工作，不代表代码完成）。
- [ ] 7.1 **Agent A：Marquito 评估和依赖许可 Gate**。核查作者源码、静态构建和 JSONL 解析兼容；未获重发布授权前不得复制作者源码到 Public Repo 或公开部署。 **进度（Agent A，2026-10-27）**：已只读核对上游 Next.js 静态导出、JSONL parser、Table/Column 图及样例入口；[技术评估](../../../platform-portal/portal/web/UPSTREAM-REVIEW.md)。尚无适用的重发布许可，未在本环境执行原项目构建/浏览器测试，故不勾选；等待作者授权和主 Session 路径批准。
- [ ] 7.2 **Agent A：Portal Web 集成**。利用获得授权的 Marquito 代码/合法适配方式实现静态展示，解析导出事件，标明 MOCK / VERIFIED，离线浏览器验收 Table/Column Lineage。
- [ ] 7.3 **Agent B：Marquez 只读事件导出**。离线 Mock 与独立 API GET 适配，输出稳定 OpenLineage JSONL，字段检查保留表/列血缘；无 Marquez POST 或 PG 写入。
- [ ] 7.4 **Agent B：网站数据发布包**。生成冻结 `portal.snapshot.v1` 及对应可公开的 JSONL，验证源 SHA、Manifest、Run URL、数据一致性；失败不能替换最后成功快照，未通过的只保留为本地候选。
- [ ] 7.5 **Agent C：Azure OpenLineage 兼容设计**。研究 Fabric Runtime/Listener/SDK、固定事件格式和适配代码；Fabric 实机测试继续 HOLD，不启动新的 Notebook。
- [ ] 7.6 **Agent C：Blob OpenLineage Publisher（离线）**。不可变事件对象、SHA256/条件创建、最后发布 Manifest，Fake Azure 客户端及异常测试，不真实 Blob 写入。
- [ ] 7.7 **Agent C：本地 Blob→Marquez Consumer（离线）**。只消费 committed Manifest、校验/去重/重试/checkpoint，Fake Marquez readback 测试；真实 PG14/Marquez POST 另需授权。
- [ ] 7.8 **用户操作：Cloudflare Pages 手工发布**。等 A/B 构建与静态数据审核成功，按 [CLOUDFLARE-MANUAL](../../../documents/systems/platform-portal/portal/CLOUDFLARE-MANUAL.md) 配置项目、GitHub、构建目录、可选域名；主 Session 在用户读回反馈后验收，只读网站上线不代表控制 API 已启用。
- [ ] 7.9 **主 Session：全局联调与后续 Gate**。按各 PR CI/Main readback 核对 A/B 接口；C 离线测试单独读回，规划授权后的真实 Azure 测试；自动触发 Cloudflare Worker/配额/邮件在后续阶段再开。
