# Proposal: Export Local OMOP snapshots to Azure Blob

## Why

本地 `dw-postgre` 保存 OMOP CDM 5.4 数据；现有 `dw-synthea` Blob Publisher 已具备 Azure 条件创建、独立 GET/SHA256/ETag 读回及 Manifest-last 机制。需要把 **数据**（不是本地 ETL / Airflow / K8s 源码）生成可审计的 Azure 副本，供备份与 Fabric 后续 Golden Dataset 对账。

## What Changes

- 复用 `dw-synthea` 中现有 Azure Blob Publisher 镜像、Azure SDK backend、既有身份边界；新 OMOP 专属 Runtime/Job，不改变医院 FHIR/HL7 Landing 协议。
- P1：从 `dw-postgre` 以只读 PG 角色执行 `pg_dump -Fc -n cdm`，只导出 OMOP `cdm` schema 内的对象及数据；通过 Job 内 ephemeral `emptyDir` 交接到 Publisher；写入独立 `omop/snapshots/<snapshot_id>/` 前缀，最后提交只含非敏感摘要的 Manifest。
- P2：在独立后续 Task 中输出非空 OMOP 表的 Parquet、Schema 和行数 Manifest，保持同一不可变上传协议，用于 Fabric 的 Golden Dataset 对账；不将 pg_dump 当作 Fabric 可直接查询的数据表。
- 单次 Snapshot ID 固定，不覆盖、不删除、不重放任何原有批次；数据文件上传后必须远端 GET/完整 SHA256 核验，Manifest 最后提交。

## Capabilities

### New Capabilities
- `omop-azure-blob-export`: 本地 CDM 只读快照和不可变 Azure Blob 交付。

## Impact

- 业务源码与静态 Job 模板均位于 Healthcare `local-data-platform/`；本轮不修改 Self-Runner、现有 FHIR/HL7 Publisher、Fabric Notebook/Pipeline/Environment，也不创建额外 Azure Storage Account。
- 真实部署需要单独核实 `dw-postgre` 的 PostgreSQL Service、`dw-synthea` 中**独立只读 PG Secret**、Azure 容器权限、镜像 digest、节点/活动 Job、容量及数据范围。Git 中不得保存任何凭据或病人行数据。
- P1 的 `pg_dump` 是 PG 原生恢复格式；P2 的 Parquet 是面向 Fabric 的表级格式。两者的测试及 Runtime 验收独立，不虚报已完成。
