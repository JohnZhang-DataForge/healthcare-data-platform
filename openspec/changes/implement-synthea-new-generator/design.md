# Design

## Context / baseline

- 本次只读核对 Healthcare Main `26e2eb4f2bdc5835eb79ea0b6c96f2891a45c1ee`。现有 `apps/synthea/new_only/generate_new_only.py` 冻结请求与随机 Seed/State，限制人口 1–100，明确打开 CSV、关闭 FHIR，且依赖既有 NEW_ONLY 身份/18 CSV 合同；`images/synthea/Dockerfile` 固定 Synthea v3.3.0 commit `995cf2fd33e67918d4e33110d9f68ad248002221`。这些均不是新通用接口。
- `apps/synthea/new_only/publish_v2_verified.py` 含特定 S3/Consumer release 约束；不能直接移入新 Generator 或用于 Azure。
- 目标：独立合成医院来源 Atlanta (FHIR) 与 Johns Creek (HL7)，Local DP 继续作为现有 OMOP 集成平台，不能宣称当前数据被固定为 Atlanta 医院或已完成 OMOP 云导出。
- 本 Change 从一开始就有可验证行为 Spec；当前状态仅 PLANNED。

## Decision 1 — responsibilities and minimal runtime

`synthea_new_generator` **只执行新合成数据生成**：校验参数 → 冻结请求 → 调用版本固定的 Synthea JAR → 检查本地输出 → 冻结本地 generation Manifest。独立模块不访问 SeaweedFS/Azure、OIE、Airflow、Spark 或 PG；不包含 hospital-b/hospital-c 分支，不持有 Storage Secret。

采用现有 Synthea 基础镜像为 parent，创建独立的 `synthea-new-generator` 镜像（至少独立应用代码与 ENTRYPOINT）。首版仅新建 Kubernetes Job，明确不同 PVC/工作路径，不重用/清空 `synthea-new-only-state` PVC。不设计常驻 Deployment、微服务 API、Registry DB 或自定义事件总线。

外部调用者按医院 Profile 构造统一请求；Generator 可在请求元数据中保留来源引用标识，但不根据 `hospital_id` 或 `feed_id` 在内部选择生成逻辑。调用者自己负责批次路由和文件发布。

## Decision 2 — parameter contract / frozen request

版本化请求最小字段：
- `request_id`：合法、唯一、不可随意替换；生成目录唯一键。
- `generation_mode`：首版只允许 `NEW_ONLY`；`UPDATE_ONLY` 与 `MIX_DATA` 明确拒绝，不假装已支持。
- `population`：正整数、受配置上限保护；具体安全阈值由实现/资源验证确定，不继续借用旧 NEW_ONLY 1–100 限制作为隐含合同。
- `state`：合法的 Synthea State；`city` 可选，若指定必须验证实际 Synthea 支持的地理位置；无效地点 fail closed，不能默默退化为全州。
- `seed`、`clinician_seed`、`reference_date`：生成时明确传入或在首次请求冻结，重试复用已冻结值；记录 Synthea 版本/commit、生成器代码 revision。
- `output_formats`：非空集合，允许 `CSV`、`FHIR_R4` 或同时两者；默认策略由调用者/Profile 决定，不写死医院。
- `output_root`：受限本地工作/持久卷位置；路径校验、无目录穿越和跨请求删除。

规范化请求要有确定性 Hash。已有 `request_id` 携带不同规范化参数或源版本时拒绝；如果已经生成并验证，重复请求只读核对已有 manifest/file/hash 并返回相同资产，不启动新的 Synthea 进程。首次失败的半成品保持诊断，不发布成功标志；重试策略显式、隔离临时目录并在持久化操作前检查已有资产。不同请求可用各自不同 Seed/参数创建独立患者群体，但**不能仅凭 Seed 宣称跨医院身份关系或字节级重复生成保证**。

## Decision 3 — output contract / local validation

建议持久化布局：
`requests/<request_id>/request.json`、`requests/<request_id>/payload/csv/*`、`requests/<request_id>/payload/fhir/*`、`requests/<request_id>/generation-manifest.json`。实际 Synthea 文件组织允许适配，但 Manifest 必须以**实际文件相对路径**声明文件、format、size_bytes、sha256、记录数量/Resource 数量与 provenance，并按安全相对路径限制；不得推断所有版本都恰好 18 CSV 或一定每患者一个 FHIR 文件。

FHIR R4 输出应验证 JSON 可解析、明确 `resourceType=Bundle`、至少含合法 Patient；需要测试时验证 Encounter/Reference 一致性，不能默认每个患者都有住院事件。禁止把 Synthea Bundle 直接视作已投影了真实 Emory 医院身份；临床医院标签、患者内部标识、HL7 消息身份由下游 Profile/Adapter 负责。CSV 可以单独或联合生成，使用专门的通用生成合同而不是现有 OMOP 的严格 18 CSV v2 Consumer 契约。

生成成功的本地 Manifest / ready marker 只能表达 `SOURCE_GENERATED_VALIDATED`，不是 `BLOB_READY` 或 `FABRIC_PROCESSED`。任何失败、缺文件或 Hash 不符均不能标记成功。

## Decision 4 — two fixed caller profiles, one reusable generator

- Atlanta FHIR Profile：`state=Georgia`、`city=Atlanta`、`output_formats=[FHIR_R4]`、配置化 population/seed/request_id；本地生成资产交给 FHIR Validator 和独立的 Azure Publisher。
- Johns Creek HL7 Profile：`state=Georgia`、`city=Johns Creek`、`output_formats=[FHIR_R4]`、独立 population/seed/request_id；**先**生成本地 FHIR R4，**再由外部** OIE 读取并转换为 HL7 v2 消息。若该 city 未获 Synthea 运行验证，启动前列为 BLOCKER 或用明确批准的区域替代，不悄悄把 city 删除。
- Profile 包含 `hospital_id`、`feed_id`、地理参考和格式/交付约束，但不生成虚假的真实 Emory 医疗来源断言。可将 `Emory` 作为模拟地理故事参考，所有患者为纯合成数据、所有医院 ID 为模拟身份。
- 即使以后同一医院增加另一种 Feed，也不复制 Generator 源码；只加 Profile 并按约定进行输出/转换。

## Decision 5 — FHIR-to-OIE is a downstream proof gate

FHIR 由 Synthea 原生导出；OIE 不生成 Synthea 的 FHIR。首个 OIE PoC 应对真实生成的 FHIR Bundle 做 `Patient`/`Encounter` 关联、入院等临床事件判定、`MSH-10` 稳定 ID、`PID-3` 与 `PV1` 映射、HL7 v2.5.1 解析回读，并验证无效/无法对应 ADT 的 Encounter 被拒绝或忽略有据。

仅“JSON 可作为 OIE Source Connector 输入”不等于“任意 FHIR Bundle 自动变 HL7”；OIE Channel 仍需事件识别/映射规则。若直读 FHIR Bundle 复杂度或兼容性不符合 PoC，允许另起受控的轻量 `FHIR→Clinical Event` Adapter 变更；**不得因此污染新 Generator**。OIE Channel、持久 spool、Blob Publisher、E2E 属于后续独立 Change，不得在此标 PASS。

## Implementation slices / verification

1. P0：本 Change 文档/Delta Spec、明确旧实现边界和静态 PR 门槛。
2. P1：Request parser、Profile→Request builder、freeze/replay 本地文件合同；正常/错误参数、重复请求及并发目录冲突单测。
3. P2：固定 Synthea JAR 的实际 CLI 参数与有效州/城市、CSV / FHIR / 双输出 Smoke；校验 Patient/Encounter/Reference、provenance、SHA，记录真实运行时镜像版本。
4. P3：独立镜像、受限 K8s Job、独立 PVC/输出路径、两个 Profile、CODE Map、配置与测试；先静态 PR CI 后受控实际 Job。
5. P4：生成结果被 FHIR 独立读取，Johns Creek 生成文件与 OIE PoC 的输入合同衔接；OIE 实际 HL7 转换由独立 Change 追踪，不冒充本 Change 完成。

每个实施 PR 必须同时更新 `tasks.md` 与对应组件 `CODE.md`，声明 `OpenSpec-Change: implement-synthea-new-generator` 和实际 `OpenSpec-Task: <n.n>`。只检查仓库/测试与本地生成不会授予共享集群运行授权。

## Risk / rollback

- 旧 NEW_ONLY 和 OMOP Writer/Claim/历史 Batch/SeaweedFS 不能修改或重放；新旧 PVC / Request ID / 容器镜像完全分开。
- 固定 Synthea 版本、参数/城市有效性及输出结构应以真实运行证实，不用 README 或 Mock 推断。日期、随机/生成 ID 的可重复行为未证实前按显式冻结结果处理。
- 大人口数内存/磁盘超限、文件数溢出、部分运行退出必须有上限和状态留痕；失败不破坏已有成功资产。
- 不将任何患者 JSON、敏感 ID、Blob Credential 写入 Git、PR Artifacts 或公开日志；只提交 Schema、模拟参数与脱敏统计。
- 回滚只撤销新增应用/Profile/Job 引用，不删除原 NEW_ONLY、OMOP PG、S3，亦不随意清理新生成 PVC 或已经交付的 Batch。所有非只读环境操作需单独安全检查与授权。
