# Tasks — Export Local OMOP to Azure Blob

## 1. OpenSpec design / contract

- [x] 1.1 核对 `dw-postgre`、`dw-synthea` 现有实现、Publisher backend、静态 Job 模板与安全门槛；确定备份和 Parquet 的分阶段范围。
- [x] 1.2 建立 Proposal/Design/Task/Delta Spec；单独限定不可变快照、Readback、Schema-only 范围和不影响医院上传的边界。
- [ ] 1.3 在真实 CI 上校验 OpenSpec strict 与 Trusted PR Change Gate；记录 Run 和精确 SHA。

## 2. P1 — PG CDM snapshot + Blob transport

- [ ] 2.1 编写独立的 OMOP immutable snapshot publisher，复用 AzureSDKBlobBackend；含路径/Blob/Manifest 校验、已提交 preflight、幂等冲突门禁。
- [ ] 2.2 新增 `dw-synthea` Job 模板：Postgres17 initContainer 只读 `pg_dump -Fc -n cdm` + emptyDir + 既有 Azure Publisher 镜像；使用独立 PG reader Secret、不访问 Generator PVC。
- [ ] 2.3 新增纯离线 Fake Backend 正负向回归测试，并接入现有 Blob contract CI。
- [ ] 2.4 同步 CODE.md，运行源检查与 CI，创建可评审 PR；标注 Static/Unit 与未验收 Live 的区别。

## 3. P1 — scoped live validation (separate authorization)

- [ ] 3.1 核对真实 PG17 Service、只读访问账号、Snapshot 大小、可运行节点、资源负载、Azure container RBAC 和 K8s Secret 状态；未确认则 HOLD。
- [ ] 3.2 授权后发布 digest-pinned Image，执行一次新 ID 的只读 PG dump / Azure immutable PUT，独立 GET/SHA 和 Manifest commit 读回；仅报告合成数据摘要，不输出记录。
- [ ] 3.3 对相同快照进行**不重新 dump 数据**的 matching retry；下载并用 `pg_restore --list` 验证备份可被 PostgreSQL 识别。不恢复到当前 CDM。

## 4. P2 — OMOP table Parquet (follow-up)

- [ ] 4.1 同一只读数据库快照中按实际 `cdm` 数据表导出 Parquet、Schema 与 Table row_count/sha256，排除无关 `etl`、程序源码。
- [ ] 4.2 用既有 OMOP Snapshot Publisher 上传独立 Parquet Snapshot；Fake / CI 以及真实少量合成数据 Readback。
- [ ] 4.3 在 Fabric 使用 Golden Dataset 做 Person/Visit count/key 对账，并记录与 native Delta 差异；这不代替正式 Fabric FHIR 管道。
- [ ] 4.4 Runtime 完成且有独立证据后同步 Current Spec，单独进行 Archive 审查。
