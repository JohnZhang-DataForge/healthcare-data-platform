# TASK004 v1.0 — 独立 Synthea 数据生产与 Airflow S3 消费（2026-10-13）

> **2026-10-13 运行进度：真实 `landing_batch_discovery` DAG 已完成经安全历史批次 opt-in 的 S3→Claim Guard→Spark Person/Visit→Processing Reconciliation 闭环，详见 [Spark Live Closeout](../tasks/LANDING-SPARK-PROCESSING-LIVE-CLOSEOUT-2026-10-13.zh-CN.md)，最后 [Run 38476079452](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38476079452) 8 Tasks SUCCESS。** 每 15 分钟默认仍只观察/读取 Ledger，手动指定已处理历史批次才触发 Spark；真正新数据 Claim、Spark 自动消费和 PostgreSQL OMOP COMMIT 尚未完成。下方原始“只读 Discovery 尚无 Spark”说明为旧阶段验收，不是当前运行事实。

> **2026-10-13 当前运行时事实更新：** [Discovery→PostgreSQL Claim Guard 实际 Airflow 验收](../tasks/LANDING-DISCOVERY-TO-CLAIM-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) 已实现 S3 → 独立 Scan KPO → XCom → 独立 Claim Guard KPO → 专用 PostgreSQL Ledger SELECT 的**真正定时 DAG 双任务**，真实两个 TaskInstance success；PG Claim 仍显式关闭，Spark/Writer 未实现，旧 Synthea 生产 Job 不参与。下文初期“只扫描没有 Claim 接线”描述为历史阶段；现在应区分**Claim 读/决策接线 PASS** 与 **Claim 实际写入未启用**。


> **2026-10-13 运行时进度更新：独立 S3 Discovery Core + Airflow 定时发现 DAG 已真实完成。** [Airflow Live Closeout](../tasks/LANDING-BATCH-DISCOVERY-AIRFLOW-LIVE-CLOSEOUT-2026-10-13.zh-CN.md) 验证 gitSync exact source、每15分钟 Cron 已启用、实际人工 DagRun KPO SUCCESS；此时**只能 INVENTORY**，仍未实现 atomic Claim、Spark 自动消费、动态 OMOP COMMIT；Generator 三 Pod 仍是已批准设计而非部署。下文早期“consumer 尚未实现”指的是完整消费/入库闭环，不应否认只读 Discovery 已通过。

> **状态：DESIGN ACCEPTED / IMPLEMENTATION PENDING。** 这是 2026-10-13 用户明确确认的 **新目标架构**，优先级高于 2026-10-10 V4 架构中“Airflow 自己运行 generate_publish”的历史决策。本文仅是设计与开发边界，不表示新的 Pod、PVC、DAG、Writer 或 S3 生成已经部署/验证。
>
> **实施顺序唯一：先 NEW_ONLY 独立生成并验证 → 再 EXISTING_ONLY → 最后 MIXED。** 不得在第一阶段合并三种业务代码，更不得一次性部署后两种模式。TASK004 Person/Visit 动态 CDM 完整入库/重放仍 IN PROGRESS；TASK005 Condition ON HOLD。

## 1. 核心决策：Producer 与 Consumer 彻底解耦

```text
[独立生产域：dw-synthea / worker01]             [独立消费域：dw-airflow + dw-spark]
    Synthea NEW_ONLY Job/Pod
       （未来 EXISTING_ONLY Job/Pod）
       （未来 MIXED Job/Pod）
              │
      CSV 完整验证 / SHA256
              │
      S3 health-landing 的独立 Batch 前缀
       上传 payload/csv/*.csv → S3 校验
       最后发布 verified manifest.json
              │
              └──────────────────────────────► Airflow 定时扫描 / 发现 READY Manifest
                                                    │
                                              Claim & ledger（防重复）
                                                    │
                                         Person/Visit Spark Processing
                                                    │
                                       Canonical → OMOP 映射/写入
                                                    │
                                        PostgreSQL 独立 Reconciliation
                                                    │
                                        结束批次、可重试/重放
```

**协议只有“不可变 Landing Batch + verified Manifest（含批次 ID、URI、SHA256）”。** Generator 不调用 Airflow；Airflow 不启动/重试 Generator、不给 Generator 传 Seed、State、人数、日期，也不要求 Generator 在线。Generator 和 Airflow 可各自定时或手工启动；Airflow 可以消费任意先前已完成但尚未处理的合法 S3 Batch。

- **生成器责任**：创建唯一 producer batch_id / 生成请求 identity、选择或读取固定生成参数、生成/验证 18 CSV、计算 checksum、发布 verified Manifest、管理自己的运行恢复和（未来）Cohort 状态。
- **SeaweedFS/S3 责任**：持久保留原始 CSV 与不可变 Manifest；提供消费者数据交换。Manifest 是 READY 标志，任何没有最终 verified Manifest 的半成品 **不可消费**。
- **Airflow 责任**：周期性 discover READY、验证 source/contract/checksum、领取尚未处理批次、管理自己的 retry/状态、调用 Spark + CDM Writer + Reconciliation。**Airflow Retry 永远重读相同 S3 Batch，不重新生成。**
- **PostgreSQL OMOP 责任**：Person/Visit 身份映射、同批次内容对账、幂等提交、拒绝非授权漂移。已有 `BLOCKED:EXISTING_TARGET_DRIFT` 防护不能关闭。
- **新旧边界**：已通过历史验收的 `airflow/dags/task004_processing_pipeline.py`（包括 `generate_publish`）保持冻结且不再是**新架构正式入口**。将来新增**独立**的 S3-discovery/processing DAG，先 opt-in 实测，确认完整 DB replay 才能切换入口。不得声称目前已切换。

## 2. 用户确定：三种独立 Job/Pod，业务代码不能混在一起

**不是同一个 Generator 脚本用 `mode` 分支切三种方式。** 长期分别维护三套有边界的入口、构建源/镜像和 Kubernetes Job/CronJob 定义，彼此可以单独发布、调试和回滚：

| 独立工作负载 | 代码目录/构建边界（建议） | 输入依赖 | 当前状态 |
|---|---|---|---|
| **NEW_ONLY** | `apps/synthea/new_only/`、`images/synthea-new-only/`、`kubernetes/manifests/synthea/new-only/` | 随机参数 + Synthea jar，无历史患者读取 | **第一且唯一开发目标** |
| **EXISTING_ONLY** | `apps/synthea/existing_only/`、`images/synthea-existing-only/`、`kubernetes/manifests/synthea/existing-only/` | 历史 Cohort 状态、生成参数；可能需要 Snapshot | **ON HOLD（设计占位，不创建源码/Job）** |
| **MIXED** | `apps/synthea/mixed/`、`images/synthea-mixed/`、`kubernetes/manifests/synthea/mixed/` | NEW + EXISTING 生成结果组合、去重、合并契约 | **ON HOLD（设计占位，不创建源码/Job）** |

三套是**独立 Pod 模板/Job 定义 + 独立业务入口**，而不是一个 Pod 内同时跑三种逻辑。后续可共享小型、已稳定的 S3 Manifest/校验工具库与 Synthea 基础层（避免重复协议），但**不共享模式判断、运行状态机或业务主入口**。正式镜像名、目录可在实施 PR 中定稿，不能误认这些建议路径已经存在。

运行方式：**Kubernetes Job 创建短生命周期 Pod**；可由独立 CronJob、手工或外部调度触发，与 Airflow DAG 无依赖。NEW_ONLY 跑在 `dw-synthea`、硬性调度到 **worker01**；任务结束不依赖容器文件系统存活。

## 3. 独立 LocalPath 存储 / 物理磁盘

用户选择先为 Synthea 在 worker01 分配**专用持久化空间（可为独立物理盘）**，使用 LocalPath PVC/PV 挂载到 `/synthea-state`。本设计不用新增数据库作为 Generator 的前置依赖。

```text
worker01: 专用磁盘 / 挂载点（例如 /data/synthea-state；实施前确认实际设备、mount）
  └─ dedicated synthea-local PV/PVC（Retain；绑定 worker01 的 node affinity）
       ├─ new-only/requests/<generation_request_id>/params.json   # 随机值仅生成一次
       ├─ new-only/requests/<generation_request_id>/state.json    # atomic 写入
       ├─ new-only/requests/<generation_request_id>/work/         # 任务暂存
       ├─ existing-only/cohorts/...                                # 未来
       └─ mixed/...                                                # 未来
```

- **必须检验实际 StorageClass、LocalPath provisioner 的目录、reclaim policy 和 node affinity**，不能误以为创建 PVC 就自动独占一块物理磁盘。建议专用目录/独立挂载点或独立静态 local PV；避免与现有 SeaweedFS PVC 的物理目录/卷发生交叉或覆盖。只在经过容量/现有 PVC 审计后分配；实施时保留旧 PV，不做清理/迁移。
- 推荐专用 **RWO PVC**、`Retain`、明确的 worker01 节点约束、资源配额与最小存储权限；LocalPath 是**单节点持久化**，worker01 丢失时**不能自动跨节点恢复**。以后保存 Snapshot 时必须有备份策略。
- **Source-of-truth 分层**：LocalPath 供 Generator 自身任务请求、重启恢复、工作目录和未来 Snapshot；**发布后批次事实以 SeaweedFS verified Manifest + 对应 CSV 为准**。重要的生成参数应同时记录在不可变 Manifest，不能只有 PVC 有。
- **不要把 S3 当作 LocalPath 的替代或把 LocalPath 当作已发布 Landing 的替代**；两者生命周期与故障恢复职责不同。第一阶段只需本地运行状态与 S3 Manifest，Snapshot 尚未实施。
- 初次部署创建 PVC 及后续 Job 为真正 K8s mutation，须按独立实施 STEP 经授权执行；**本轮未实际创建磁盘、StorageClass、PV 或 PVC**。

## 4. 第一阶段 NEW_ONLY：自主随机、完全无 Airflow 参数输入

```text
独立 Kubernetes Job 触发（唯一 generation_request_id）
   → 检查 /synthea-state 上是否已记录该 request
   → 未记录则生成 1..100 的目标人口数、美国有效州、随机 seed/clinician_seed、
     本次创建日期/模拟截止日期；一次性**持久化冻结**到 params.json
   → 已记录则无条件恢复这些固定参数；禁止再次随机化
   → 在 worker01 调用已 pin Synthea v3.3.0 JAR
   → CSV/18-CSV Contract/Person ID 全局碰撞/数目校验
   → S3 健康检查、上传完整 payload、逐对象 checksum readback
   → **最后**发布不可变 verified manifest.json
   → 返回 batch_id / manifest_uri / manifest_sha256（仅 Generator 内部结果、日志或 S3）
```

- `generation_request_id` **由独立生产者调度方生成**，必须在同一个 Kubernetes Job 重试/续跑中稳定（建议关联 Job UID 或明确的 request ID，不能用易变化的 Pod UID）。**它与 Airflow run_id 无关**。新生成请求使用新 ID；同 ID 失败恢复不得替换此前冻结的随机参数。写入需原子创建、锁/冲突检测、文件落盘；多 Pod 并发时必须 fail-closed 或使用统一原子状态协调，不能同时写同一请求。
- `population_size` 随机范围**目标 1～100**，用户希望最终 **实际 `patients.csv` <=100**；已有 Synthea `-p 20` 可能输出 23 人（overflow），因此先验证 `-o false` 语义，再读取 `patients.csv` 核验实际数量，超过 100 必须不发布。严禁把 `-p` 当作实际已生成行数。现有 Generator 入口目前限制 20/50、且 18 CSV validator 要求某些 CSV 非空；**需要新增 NEW_ONLY 独立入口/契约测试才能支持 1～100，不能直接复用旧限制并声称 PASS**。若小人口生成不足合同要求，要制定明确契约版本策略和真实验收，不得简单关闭所有验证。
- `state` 从版本固定且经过合法性校验的美国州名单中随机选择；**每个 NEW_ONLY Job 批次一个随机州**，不是单个 Batch 内患者各自随机州。城市选空/由 Synthea 处理。州、人口、Seed、生成时间等须写入 Manifest `source_parameters`，记录 `generation_mode=NEW_ONLY` / producer_version（新增字段时使用版本化契约、保持消费端兼容检查）。
- 参考时间：以**批次实际创建时**的 UTC 日期为默认 Reference Date / End Date，并固定在参数文件与 Manifest；历史患者生日和模拟就诊日期仍由 Synthea 决定，不会简单全部变成当天。新 Job 跨日重启必须复用原日期。
- Seed 保证“尝试独立随机”**不等于数学上零碰撞**；发布前与已接收的源 ID registry/映射独立对账或使用额外严格的命名空间方案，遇到既存 Person Source ID 立即 BLOCKED，绝不绕开 Writer 漂移门槛。碰撞恢复须在新生成请求中重新生成、不可偷偷改写已冻结请求。
- 任何永久 S3 prefix / Manifest 不得被覆盖；生成器重试遇到已验证 Manifest **返回既有结果**，不同 payload/同 batch_id 一律 BLOCKED。完成前不可暴露 READY。

## 5. Airflow：独立 S3 消费者与批次幂等处理

新建的 Consumer DAG（计划命名 `task004_s3_batch_consumer`，尚不存在）按周期轮询或使用 S3 Sensor；不需要读取 Synthea 的随机参数，也不依赖 Generator 是否在线：

1. 列出 `health-landing/source=synthea/source_version=v3.3.0/.../batch_id=.../manifest.json`；只识别 **INTAKE_VERIFIED / 18-CSV / checksum/readback valid** 的 Batch；列表迭代必须分页并考虑上游晚到/重试，不得把一个目录存在就视为 READY。
2. 按 `(source_system, batch_id, manifest_sha256)` 原子 **claim**，并记录 `DISCOVERED / PROCESSING / COMPLETED / FAILED`、租约/心跳及失败恢复。已完成相同 SHA = SKIP；同 batch ID 不同 SHA = BLOCKED；正在处理的不重复启动（锁/租约过期的恢复要安全）；失败相同源可 RETRY。Ledger 可以设计为与现有 `etl.task004_batch_ledger` 兼容的扩展，但**不能在未查真实 schema/权限前直接改表或复用有不同语义的字段**。
3. 将**已存在的** Manifest URI+SHA/固定 batch_id 送入 Spark Person/Visit、Processing Reconciliation、Person CDM、Visit CDM 和最终独立 DB Reconciliation；Person FK 先于 Visit、保留 Existing Target Drift gate。
4. 仅数据库事务/独立对账确认成功后标记 `COMPLETED`，不可把 Spark 成功当作最终成功；未知 COMMIT 必须查询真库，不可盲目重写。Airflow 重试始终读取**同一 immutable Batch**，不会触发 Generator。
5. Airflow 的重试不要求 Generator 保存原 Seed，但 Generator 自己的中途失败与可重现性仍要保存参数；**二者幂等边界各自独立**。

历史既有 DAG `task004_processing_pipeline` 原带 `generate_publish`，仅作为历史已验证实现保留；不能把它“现在已经解耦”写成 PASS。需要另一个 STEP 开发、部署/验证新 Consumer DAG，之后再考虑停用旧 DAG。

## 6. 第二、三阶段的界限（本轮绝不实施）

### EXISTING_ONLY — 未来

- 不用扫描 S3 就假设 Synthea 能自动“记住以前的人”。它没有跨 Pod 的无限期全局患者记忆；必须从 **持久化 Cohort Registry / 生成元数据** 或 Snapshot 恢复既有患者。
- 对于一个历史 Cohort，可尝试固定 seed/state/reference_date 并**推进 simulation end_date**，也可用 Synthea v3.3.0 `-i` / `-u` / `-t` 读取与保存 Java Population Snapshot。先真实验证患者 ID 和事件 ID 的一致性、Snapshot 的兼容性、历史累积数据的重输出行为。个人抽样、不同州 Cohort 的组合不是原生单个 Snapshot 自动实现的。
- “老患者有更新”不等于生日随日历漂移：既有患者 Person 核心身份不能悄悄改变；明确 INSERT/UPDATE/SKIP、Versioning 和 Snapshot commit lineage 后才实现。

### MIXED — 最后

- 在 NEW_ONLY、EXISTING_ONLY 都成功后，由单独 `synthea-mixed` Job/Pod 做两条已验证路径的受控组合、源 ID 去重、批次不变性、总人数上限、原有 Visit 对账与安全合并。不能靠一个模式参数在 NEW_ONLY 入口里临时分支实现。

## 7. 明确的第一实施闭环与验收（只做 NEW_ONLY）

**NEW-01（准备/检查）**：只读检查 worker01 可用专用挂载/容量、local-path provisioner/Retain 策略、dw-synthea namespace/权限、旧镜像 Synthea v3.3.0 校验、S3 Contract 非空限制。选定 PVC 方案，不修改既有 SeaweedFS。

**NEW-02（独立源码 + 构建）**：只建 NEW_ONLY 专用源码、Job 模板、独立镜像与测试；未创建 EXISTING/MIXED 的业务代码。测试随机 1..100 / 州合法/种子类型、参数冻结重启/并发、无 Manifest 半成品/覆盖保护、18 CSV 合同、源 ID 防撞和实际 100 人上限。

**NEW-03（单次端到端真正生产）**：经单独授权创建 PVC、Job 以及一批真实 Synthea CSV，验证 worker01 运行、PVC 重启保持、S3 Manifest 最后发布及 readback/checksum PASS。测试失败最多三轮则暂停排查。不得自动将产出加载 OMOP、不得运行未来旧/混合模式。

**NEW-04（消费端解耦验收）**：在 NEW_ONLY 数据与真实 Manifest 通过后，单独开发/验证 Airflow S3 discover→claim→Spark→Person/Visit CDM→DB reconciliation→same-source replay，保持原冻结 DAG 不变；实际 DB COMMIT 必须有对应安全授权。两次 Generator 产生不同新批次、同批次 Airflow 重放无重复、独立失败重试安全，才能宣布新架构 TASK004 的完整闭环通过。

**通过标准**：不是“Pod Running”或“生成了 CSV”，而是至少有一次 **Generator 在无 Airflow 参与下独立生成并上传 S3** 的真实 PASS，有固定参数+校验报告、verified Manifest、无患者 Source ID 冲突。然后再单独判定 Consumer / CDM 的进度，不能混写 PASS。

## 8. Git/Agent 接力

- **Healthcare 为 Generator/Consumer 真正业务源码唯一仓库**；Self-Runner 仅用于指定 SHA 的受控部署、运行与证据收集。
- 每个 STEP 应含至少一个可验证闭环（写代码→测试/Job→读回/证据），但分轮控制规模；循环失败超过 3 次暂停。
- Feature branch → PR/exact SHA → Self-Runner/ARC 真证据 → merge main → 需要时 post-merge 确认 → docs checkpoint。
- 不猜测 PVC/StorageClass/Namespace 已就绪；不手工要求用户在机器上执行长 Shell 替代已采用的 Runner 模式。
- 旧 2026-10-13 Source-ID Drift 23/23、`BIRTHDATE +1 天` 已在 [根因验收](../tasks/TASK-004-STEP04F-SYNTHEA-SEED-REFERENCE-DATE-ROOTCAUSE-READONLY-CLOSEOUT.md) 确认。这是为什么要分离固定历史 Seed 的有据可查的动机，但**本轮没有实施代码变更或新的数据生成**。

**最终权威状态：Generator/Consumer Decoupling DESIGN ACCEPTED；NEW_ONLY IMPLEMENTATION NEXT；EXISTING_ONLY/MIXED ON HOLD；TASK004 IN PROGRESS；TASK005 ON HOLD。**
