# Design

## Scope & authority

已确认的跨云目标架构详见 [长期设计](../../../documents/infra/HEALTHCARE-ON-DEMAND-LIVE-DEMO.md)。本 Change 是后续唯一开发/测试/验收任务载体；真正组件事实分别仍由 Local DP、Fabric、Marquez 的运行配置和有效 Contract 管理。设计批准不等于任何公网服务已上线或云端 Notebook 已部署。

## Decisions

1. **入口分层**：GET 只返回历史成功快照；首次有效真人会话可以提交固定 POST。Cloudflare Worker 服务端验证 Turnstile、Geo=US、HMAC IP 日限额 3、全局上限、请求幂等及 single-flight，必要时 fail-closed。全站每日 6 次只作初始建议的保守默认，最终须依据免费 POC 成本审查。全球用户仍可读静态展示。
2. **控制隔离**：管理员 Self-Runner Workflow 独立修改开关 OFF/ON/Emergency OFF；网页无权传执行命令或 GitHub Token，触发器映射唯一 allowlisted Workflow。自动触发控制与付费 ARM Capacity lifecycle 是**两个独立 Gate**。保留上次成功快照，运行状态依据真实证据推进。
3. **双 Spark**：标准 PySpark ETL core + Fabric Notebook / K8s SparkOperator 适配；比较冻结输入、DQ、Delta 协议、OpenLineage Event 与成本，先复用已授权的免费 Fabric 资源。最终计算后端为 UNDECIDED，避免用受限 F2 和付费 Resume/Pause 直接作为生产前提。
4. **同格式血缘**：两个后端都发布真实 OpenLineage 事件，不强制消费 Fabric Item Relations。非 Spark Generator/OIE/Publisher/Pipeline 要独立埋点或明确标记 gap；统一 Dataset ID 不仅是统一 JSON，跨平台边需要真实 Blob Manifest/URI。
5. **可靠持久层**：不可变 Azure Blob Event + commit Manifest，K8s Consumer 校验/重试/去重/持久 Checkpoint，再通过 Marquez Ingestion API 写既有 PG14。Azure 不直连 PG14，不向公网暴露 Marquez 写端点；不同于业务 Delta Tables，血缘不再启动专用 Delta 写入 Notebook。
6. **公开展示**：经白名单脱敏的 JSONL 或图快照由 Cloudflare Pages 只读加载。当前 Marquito 作者源码的许可未知，必须取得明确许可或选用替代图形库；不能因其在线可访问而认为允许复制代码。

## Data contracts & idempotency

- 统一运行身份：request_id（匿名公开采用脱敏表示）、generation batch_id、Source Manifest SHA、Spark backend、OpenLineage Job namespace / name、runId、Dataset namespace / name、事件 Schema 版本、Blob 对象 SHA。
- Producer 对同一个事件路径条件创建，不允许改写不匹配内容；成功事件列表 Manifest 最后提交，失败不得发布成功标记。
- Consumer 只处理成功 Manifest，按稳定事件标识去重，POST Marquez 成功后需独立 GET Job/Run/Dataset 读回，再落 Checkpoint；断网仅重放事件，不重跑业务 Batch/OMOP Writer。
- 所有历史 E2E / Portal A4/P4 未解决边界仍有效：不能以 Application START 事件替代真实业务 COMPLETE，不能以 CascadeDelete 关系替代数据流。
- 工作流状态和管理员 Email 按 request_id 幂等；公开数据白名单，不显示 SQL 源、患者标识、凭据、内网 URI 或个人真实 IP。

## Runtime compatibility and cost

- Fabric Runtime Spark/Scala/Python/Delta/OpenLineage JAR 与 Local Spark 镜像逐项明确版本矩阵；Notebook 专用 notebookutils、Lakehouse 默认路径、Token、abfss/wasbs/S3 连接等只能在 Adapter 层。
- 在免费 Fabric / 现有本地 K8s 做配对 POC；使用同一冻结测试输入读取、业务字段对账、表级及列级血缘实测，记录真正 CU 与每轮启动/处理/收尾用时。
- Trial 容量仅用允许的免费操作；付费 F2 需要新的资金/权限明确批准，不随配置开关自动启用。Azure/Cloudflare 费用和公网安全审查属于上线 Gate。

## Security & failure cases

- 单 IP 配额只防普通误用，不等于实名或绝对防 VPN；须叠加全站上限、成本熔断、速率限制、人机校验、单并发。原子状态协调禁止仅用最终一致 KV 防超额。
- Runner、Marquez、家用网络/Cloudflare Tunnel 不可用时，自动触发拒绝或安全超时，Blob 保留已提交事件，网站保留历史成功快照；不得谎报 LIVE SUCCESS。
- 非法 Event、签名失败、旧/不一致 Manifest、重复完成记录、未授权计费、未确认开源许可 -> FAIL CLOSED。
- 邮件发件人/收件人凭据通过受控 Secret 管理，不允许访问者任意收件或发送。

## Evidence, rollback, out of scope

本地真实 Marquez 匿名化 JSONL 输入 Marquito 作者 parser 的成功证据为 [Self-Runner #40321797660](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40321797660)：190 Events / 48 Jobs / 23 Datasets / 44 Table Edges / 176 Column Edges。非浏览器 UI 和非 Fabric 事件验收。Fabric 原生 Item Relations GET [#40251306511](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40251306511) 只读成功，但仅结构依赖，非 Spark Bloodline。跨 Azure Spark Listener、Blob 中转、Cloudflare 自动触发仍未验证。

本轮仅 Git 文档/Spec，无 Runtime 可回退事项。未来按 Emergency OFF → 不再受理 → 保留只读快照 → 按单独授权检查 paid Capacity 状态恢复。不得自动删除旧 Blob、PG14 或已有业务数据；后续代码实现需拆分有界 PR，按最小功能的 Task 逐项交付。
