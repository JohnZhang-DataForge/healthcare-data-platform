---
status: draft
scope: healthcare-on-demand-live-demo
decision_date: 2026-10-26
implementation_status: design-only; not-deployed
source_sha: 37ba38ce0cc23f2c6f324c30a2d5cea0c4e2eb3c
---

# Healthcare On-Demand Live Demo — Emory 按需真实 E2E 展示

> **用户确认的目标方案，尚未实施。** 本文件是跨云 Demo 专项基础设施设计入口；开发与验收任务只在 [Active OpenSpec Change](../../openspec/changes/healthcare-on-demand-live-demo/tasks.md) 跟踪。本文不授权购买云容量、执行 Notebook、修改 K8s、写 PostgreSQL 或发布公网入口。

## 1. 目标与已确认决策

面向 Emory 招聘经理和其他匿名访客：打开 Cloudflare Demo 页面，无需账号便能看到**最近一次真实成功的 E2E 结果、表/列级血缘和完成时间**。当访客满足地区、真人和配额条件、自动触发开关为 ON 时，可以按需启动一轮新的真实流程。避免固定每 15 分钟运行 Fabric Spark 导致长期容量费用。

- **双 Spark 兼容**：FHIR/HL7 ETL 的标准 PySpark 业务核心在本地 Kubernetes Spark Operator 与 Microsoft Fabric Spark Notebook 之间共享；环境相关代码采用 Adapter。**后端最终选择待免费真实测试**，目前不锁定 Fabric、Local 或付费 F2。
- **血缘统一**：Local/Fabric Spark 都计划使用 OpenLineage 标准 Run Events，包含真实 Job/Run、Dataset Inputs/Outputs 和可用 ColumnLineage Facets，避免把 Fabric Item Relations JSON 转成假事件。
- **Blob 中转**：Azure Blob 持久化不可变 OpenLineage JSON/JSONL，本地 Consumer 可靠同步到现有 Marquez Ingestion API，再由 Marquez 写本地 PostgreSQL 14；无需为了血缘另建 Delta Table。**业务 Bronze/Silver Delta Table 仍然保留**。
- **展示方案**：优先评估 Marquito-style 静态交互前端，Cloudflare Pages 匿名只读，从经审查脱敏的血缘快照加载；不修改现有 Marquez Server/Web/PG14。原 Marquito 源码没有已确认复用许可证，正式复制/部署前必须取得授权，或使用明确许可的 React Flow 等库独立实现。
- **费用边界**：免费 F4 / 已有试用额度用于 POC；付费 F2、自动 Resume/Pause 需要独立预算和用户授权。Trial 不得假定支持 paid ARM 生命周期接口。

不包含：向公众开放 Marquez Admin/POST API、真实患者数据、升级业务 Writer、自动创建收费 SKU、强行解决已延期的 A4/P4、重写已有 Terraform Workspace 所有权或声称 Fabric Listener 已验收。

## 2. 目标数据与控制路径

~~~text
Emory 匿名访客 -- GET（仅缓存结果） --> Cloudflare Pages
      |
      +-- 有效真人会话 / Server-side Turnstile / POST
                 |
         Cloudflare Worker
         US-only + 3/IP/UTC-day + 全站预算 + single-flight
         独立自动触发开关：默认 OFF
                 |
         固定授权 Dispatch -> Self-Runner
                 |
         全新 Synthea Batch (5–10 合成患者)
                 |
         FHIR/HL7 Source Handoff + Publisher
                 |
         Azure Blob Landing / READY Manifest
                 |
       +---------+-----------------+
       |                           |
  Fabric Notebook             Local K8s Spark
       |                           |
       +--- 同一 PySpark 业务核心 ---+
                 |
         Bronze/Silver 业务结果 + DQ Readback
                 |
       OpenLineage Event JSON/JSONL
                 |
       Azure Blob: immutable events + commit manifest
                 |
       Local Consumer (validate/retry/dedupe/checkpoint)
                 |
       Marquez POST /api/v1/lineage -> PG14
                 |
       Read-only sanitized Exporter -> 静态快照
                 |
       Cloudflare Pages / Marquito-style Lineage Graph
                 |
       真实进度、失败状态、管理员 Email
~~~

**PG14 不接受 Azure 直接写入**；Marquez 承担 OpenLineage 事件的持久化与查询。家中网络断开时已成功提交 Blob 的血缘事件保留，Consumer 恢复后幂等补发，绝不因此重新生成患者、重复 Publisher 提交或重跑 OMOP Writer。

现有 Local Marquez 的历史数据可以只读 GET 导出，校验事件结构后转存 Blob；Fabric 侧 OpenLineage Listener、Transport 和 Azure Blob 持久化尚未验证。不同事件 Producer 的 Schema/Run Version、Delta/Blob URI 要经过统一规范和真实 Manifest 验证才能合成跨平台数据流。Fabric Item Relations 的 CascadeDelete 等结构依赖不能假装是业务血缘。

## 3. 匿名访客、触发开关和安全限制

**页面 GET、爬虫、链接预览、刷新一律不得触发收费任务。** 保留“有效访客到访可自动触发”的体验：网页完成真人会话验证后，由客户端发起单独 POST；Worker 必须在服务端核验 Turnstile token、地区、配额、幂等键、开关与预算，才能向后台发出固定目标的执行请求。通过不了就只展示上次成功快照。

| 门槛 | 目标设计 |
| --- | --- |
| 查看静态展示 | 全球匿名，始终可用 |
| 能够触发 | 美国 IP + Turnstile 实际通过 |
| 每 IP 每日 | 最多 3 次；UTC 日窗口 |
| 全站每日 | 初始建议最多 6 次，后续免费测试可进一步压低 |
| 同时运行 | 全站最多一个 Active E2E |
| 自动触发 | 默认 OFF；独立管理员 Self-Runner Workflow 控制 OFF/ON/Emergency OFF |
| 付费容量 | 默认 DENY，不能由自动触发开关顺带开启 |
| 邮件 | 管理员地址配置、被接受/成功/失败事件按 request_id 去重 |
| 费用熔断 | 月预算/单次时长/连续失败阈值/总执行上限，异常关闭入口 |

美国 IP 检查使用 Cloudflare 服务端可信国家属性，但地理规则不等于防 VPN 的强身份认证。每 IP 限额按带密钥 HMAC 的 IP 摘要维护，不将访客真实 IP 放入公开日志或邮件；IPv4/IPv6 和公司共享 NAT 必须处理。原子配额/单实例调度用 Cloudflare D1 事务或 Durable Object 的一致性协调，不用不具强原子性的 KV 单独充当计数锁。拒绝或重复请求不得再次 Dispatch。前端不得持有 GitHub Token、Azure Client Secret、任意 workflow/ref/shell 执行权限；后台固定允许的 workflow + 最小权限短期凭据。

状态来自真实执行与独立读回：ACCEPTED → GENERATING → BLOB_READY → SPARK_RUNNING → QUALITY_PASSED → LINEAGE_SYNCED → SNAPSHOT_PUBLISHED → COMPLETE，也可 FAILED/EXPIRED。**不是动画假进度**；页面永远可以展示最近成功快照及时间，任务失败不覆盖旧成功结果。

独立运行开关与收费容量兜底：Runner 宕机时 Worker 仍可以 Emergency OFF；已有 paid SKU 如果将来获批，必须具有独立暂停/验证资源最终状态的失败路径。Trial F4 不自动调用 paid ARM suspend/resume。

## 4. Local/Fabric 双 Spark 可移植性及测试矩阵

共享 PySpark 转换模块负责 Patient/Encounter 等字段规范化、FHIR/HL7 解析后的表映射、DQ 和输出；Fabric Notebook Adapter 负责身份、Notebook 参数、OneLake/Blob I/O；K8s SparkApplication Adapter 负责镜像提交、Secret 和 Azure Blob I/O。**普通 PySpark 核心可复用，但整份 Fabric Notebook 不一定原样可运行在自建 Spark**；须处理 notebookutils、默认 Lakehouse 路径、认证、Spark/Scala/Python/Delta/OpenLineage 版本与 abfss 驱动依赖。

两端对照同一固定 Source Manifest 测试：数据行数与关键字段映射、唯一 ID、重复执行、失败回退、Delta 读写/协议、数据源连接；产生 START/COMPLETE/FAIL、真实 Inputs/Outputs、Schema/Column Lineage；测量启动时延、端到端时长、Fabric CU 与本地资源用量。只有业务对账、标准事件和可靠投递三个门槛都 PASS，才可将后台标记为 VERIFIED。正式常态后端保持 **UNDECIDED**，由后续免费实测与用户最终选择确定。

OpenLineage 只能自动采集它实际覆盖的 Spark 行为。非 Spark 的 Synthea、OIE、Azure Publisher、Fabric Pipeline 调度仍需要独立标准事件和准确 Parent/Run/Dataset 关联，不能编造完整端到端边。

## 5. Blob 事件、可靠同步、公开快照

复用已存在的 Azure Storage，但血缘新对象与现有业务 Landing RAW/READY 和 Terraform State **逻辑隔离**。建议前缀（仅设计，不代表已创建）：

~~~text
lineage/events/v1/source=<local|fabric>/utc_date=YYYY-MM-DD/
  request_id=<id>/run_id=<id>/<sha256>.json
lineage/manifests/v1/<request_id>/commit.json
~~~

一个对象对应不可变事件，条件创建、SHA256/长度读回，成功 Manifest 最后提交；不可把多个并发 Spark Writer 直接追加同一个 Blob。可按顺序汇总成 JSONL（每行完整 OpenLineage Run Event）给展示解析。Consumer 只消费 committed Manifest，校验 Schema/Hash，以 producer+job+run+eventType+eventTime+内容摘要去重，Marquez GET 独立读回后写入 checkpoint；网络中断、重放、乱序、部分写入均需 fail-closed 和幂等测试。跨平台 Dataset 相同身份必须有 Blob URI/Manifest 证据，不允许靠显示名称连接两条假边。

**原始 OpenLineage 不直接公开**：Facets 可能包含内部 URL/SQL/路径/患者属性。发布 Exporter 需要字段白名单、稳定匿名化、批次授权、版本和快照时间戳，且公开页面不得访问 PG14、Marquez 私有 API、私有 Blob 或 Cloudflare/GitHub 凭据。系统只使用合成患者。

## 6. 已验证事实与明确待验证范围

- Local Marquez → Marquito 作者实际 TypeScript Parser：[Self-Runner #40321797660](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40321797660)；从真实事件中生成 190 条匿名化事件，解析得到 48 Jobs、23 Datasets、44 条 Table Edges、176 条 Column Edges，**仅证明解析兼容，不是部署、浏览器渲染或授权**。
- Fabric 原生 Item Relations GET：[Self-Runner #40251306511](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40251306511) 已通过，但观察到的 Lakehouse→SQLEndpoint CascadeDelete 为结构依赖，不是业务 OpenLineage。
- Fabric Spark Listener、Blob 持久化、Local 同步、云端 Notebook FHIR/HL7、Cloudflare 真人触发与 Email 均属于 **PLANNED / NEEDS_LIVE_VERIFICATION**。
- [原有本地 Portal 关闭和 A4/P4 延后项](../architecture/design/LOCAL-PORTAL-MVP-CLOSEOUT-AND-DEFERRED-FOLLOWUPS.md)、[FHIR/HL7 设计](../architecture/design/FHIR-HL7-MULTISOURCE-MVP-DESIGN.md)、[Fabric 系统说明](../systems/azure-fabric/README.md) 的既有事实不变。

## 7. 后续分层 Gate（具体勾选仅在 OpenSpec）

A. 本设计/OpenSpec + 文档导航/Schema/Trusted Change Gate 静态通过（仅本轮）。

B. 在**免费 Fabric 环境**隔离小型 Notebook 验证 Spark Listener、Blob 事件、Column Facet、CU 成本与真实读回；真实执行需单独 Safe Operations 协调。

C. 同一 Transform 模块于本地 K8s 运行、独立对账、OpenLineage 完整性与端到端成本对比；决定常态 Spark backend 之前不开 paid F2。

D. Blob 不可变事件及 Manifest、Consumer 失败恢复/重复/乱序与 Marquez PG14 真实同步读回。

E. 确认 Marquito 源码许可证（未确认不得复制）或合法的 React Flow 实现，先在 Cloudflare 测试环境验收真实静态图。

F. US/Turnstile、3/IP/日、全局预算、Single Flight、OFF/ON、Email、E2E 状态和支付熔断，通过真实成功/失败/重复请求负向测试；上线前还要完成公网隐私/权限检查。

所有 E2E 需关联准确 Healthcare / Self-Runner SHA、request_id、Source Manifest、Blob GET、Spark/DQ、OpenLineage JSONL、Marquez GET 与快照版本。用户尚未授权任何付费资源或共享写操作。本阶段文档回退只需 PR 修订，不存在云端副作用。

**正式实现任务单一入口：[Healthcare On-Demand Live Demo OpenSpec Tasks](../../openspec/changes/healthcare-on-demand-live-demo/tasks.md)。**
