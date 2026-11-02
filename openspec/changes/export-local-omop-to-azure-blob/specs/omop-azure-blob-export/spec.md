# OMOP Azure Blob Export

## ADDED Requirements

### Requirement: Export only LocalDP OMOP data via read-only PostgreSQL snapshot

系统 SHALL 通过 `dw-postgre` 的受限只读账号导出 `cdm` schema 中的 OMOP 数据和 PostgreSQL 结构，而不打包 Airflow、Spark、ETL、K8s 代码，亦不得修改 PostgreSQL 持久数据。

#### Scenario: A snapshot is exported
- **GIVEN** 有效的唯一 snapshot_id 和只读 PG 连接
- **WHEN** 在 `dw-synthea` Job 内执行 PostgreSQL custom-format dump
- **THEN** 只生成 `cdm` 范围的 dump；失败不得产生 Blob 完成 Manifest

### Requirement: Reuse shared Blob transport while isolating OMOP from hospital Landing

OMOP Publisher SHALL 复用现有 Azure Blob 后端、Scoped Secret 和条件创建/GET 核验能力，但 MUST 使用独立 OMOP prefix、Manifest schema、Runtime 和 Job，不得改变或伪装医院 FHIR/HL7 Landing 交付。

#### Scenario: OMOP and FHIR paths are isolated
- **GIVEN** Publisher 可以访问现有 Azure Blob 容器
- **WHEN** 上传 OMOP snapshot
- **THEN** 目标位于 `omop/snapshots/<snapshot_id>`，FHIR/HL7 的 Landing keys、合同、来源 PVC 均不被修改

### Requirement: Immutable files and manifest-last success

Publisher SHALL 在任何上传前验证 Snapshot 文件与 Key，使用条件创建；独立远端 GET 实际字节和 SHA256/metadata/ETag，通过后最后写入不可变 `snapshot-manifest.json`。冲突或部分故障不能返回成功。

#### Scenario: Identical retry
- **GIVEN** 同一 snapshot_id 的同一数据对象已存在
- **WHEN** 尝试重新交付完全相同的字节
- **THEN** SHALL 校验既有远端对象并返回 matching 状态，不覆盖或删除

#### Scenario: Different dump under same snapshot ID
- **GIVEN** 相同 snapshot_id 下已有不相同的数据或提交 Manifest
- **WHEN** 提交发生
- **THEN** MUST fail-closed，不能覆写任何已有 Blob

#### Scenario: Interrupted publication
- **GIVEN** 数据对象写入或 GET 校验失败
- **WHEN** Job 失败
- **THEN** MUST 不得写完整成功 Manifest，保留现有对象以供安全核查

### Requirement: Separate table-level Parquet reference dataset

在后续 P2，系统 SHALL 支持从同一只读数据库快照枚举 OMOP `cdm` 业务表，导出 Parquet、Schema、行数和散列信息，以独立不可变身份供 Fabric 数据对账；空表不必生成数据文件。

#### Scenario: Golden Dataset
- **GIVEN** 本地 CDM 已有 Person/Visit 等真实合成测试记录
- **WHEN** 后续 P2 发布表级参考数据
- **THEN** Fabric 可独立读取、对账，而不要求加载 PostgreSQL `.dump` 文件或迁移本地 ETL 代码

### Requirement: Shared runtime writes are separately gated

Merge 或 OpenSpec 设计批准 MUST NOT 自动部署 K8s Job、增加 Secret、执行 PG dump 或 Azure PUT。共享环境实际运行须经资源预检、准确镜像 Digest、独立授权与读回证据。

#### Scenario: No live authorization
- **GIVEN** 未确认 PG reader Secret 或未批准 Azure PUT
- **WHEN** 离线 CI 通过
- **THEN** 系统 MUST 保持真实 K8s/PG/Azure 工作负载未执行

### Requirement: Bounded export-only PostgreSQL identity lifecycle

导出 SHALL 使用本次 Run 专用的 cdm READ-ONLY Role，绝不扩大共享 `cdm_reader` 或传送 PG 超级用户身份给 `dw-synthea`。若实际运行中创建临时 Role/Secret，系统 MUST 限制为 cdm USAGE/SELECT，并在作业完成和读回后撤销授权并清理 Role/Secret；失败必须核对活动作业和未知状态，不能直接重新使用身份或 Snapshot ID。

#### Scenario: Existing reader cannot access all OMOP tables
- **GIVEN** 共享只读 Role 仅有部分 cdm SELECT 权限
- **WHEN** 请求完整 `pg_dump -n cdm`
- **THEN** MUST 不扩大共享 Role 的权限，而是使用经过完整权限核验的受限 Snapshot 专用身份；若无法建立则 HOLD，不能使用数据库 admin 凭证执行 Publisher Job。
