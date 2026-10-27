# Tasks

> **ACTIVE / TARGET DESIGN, NOT RUNTIME AUTHORIZATION.** 本次仅冻结人类可读架构与未来可测试需求；完成文档任务不表示 Fabric Spark Listener、Blob 同步、Cloudflare、付费容量或真实新 E2E 已部署。具体共享环境真实运行、云资源成本和公开发布仍需单独批准。唯一任务清单在本文件。

## 1. Architecture and specification baseline (this PR)

- [x] 1.1 核对 Healthcare/Self-Runner 最新 Main 与开放 PR/Running Workflows，阅读文档治理、现有 Fabric Capacity Trial 和本地 Portal 真实验收与延后边界，确定本轮纯文档影响范围。
- [x] 1.2 在 documents/infra/ 冻结 On-Demand Live Demo 目标、双 Spark 可移植策略、OpenLineage → Blob → Marquez/PG14、Marquito 风格展示、访问控制/预算/不实施边界。
- [x] 1.3 创建 OpenSpec Proposal、Design、Delta Specs（目标 Requirements/Scenario）及后续逐项验收 Tasks；文档索引必须链接唯一权威设计。
- [x] 1.4 设计基线 [Healthcare PR #508](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/508) 经 OpenSpec validate、Trusted Change Gate、Change Gate、Documentation Relative Links 四项 GitHub 检查 SUCCESS，2026-10-26（美国东部）已 squash merge 到 Main `a030d02d46c85bc6932ce7ddba73b5c609f25b58`，并独立从 Main 读回正式方案。设计关闭不等于后续实现或运行验收。

## 1A. P0 Showcase contract foundation（2026-10-27，代码/Schema；尚未部署）

- [x] 1.5 为 P1–P4 冻结 Versioned Snapshot/Trigger/Status/Error JSON Schema v1，包含严格白名单、Mock/Verified Origin、证据门槛、不可用户指定 Workflow/Backend 的负向约束。正式约定见 [Showcase P0](../../../documents/systems/showcase/README.md)。
- [x] 1.6 提交只含虚构合成数字的 `showcase/fixtures/*.mock.json`，显式 `MOCK ONLY`，用于前端/Exporter/Worker/部署的独立 Mock 集成；不冒充现有真实 P5 Batch。
- [x] 1.7 建立 P1–P4 独占目录、CODE 地图、Branch/PR 及共享资源协调边界，明确 GET 静态快照与 POST 控制接口契约。
- [x] 1.8 **CONTRACT FROZEN v1（仅机器契约，不代表部署）**：P0 [PR #513](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/513) HEAD `516721a055a2a0bb2babdf91102691c293cb68c1` 的 Showcase Contract Validation、OpenSpec Static、OpenSpec Change Gate、Trusted Change Gate、Documentation Relative Links、Component Code Naming **6/6 SUCCESS**；Squash Merge `a5778f50b06f4cfb3051df3a1870b5be0dd97aee`，从 Main 实际重新读取 `snapshot-v1.schema.json` 和 `documents/systems/showcase/README.md` 并确认版本。后续 Schema 调整需版本/兼容审查；真实展示/Cloudflare/Runner 尚未部署。
- [ ] 1.9 P1–P4 各自独立 PR 实现/集成（对应原 4.x/5.x 验收要求），P2/P3 真实访问及 P4 公网发布均须各自通过安全/费用 Gate；P0 不包含实际部署。

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

## 4. Read-only showcase (future)

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
