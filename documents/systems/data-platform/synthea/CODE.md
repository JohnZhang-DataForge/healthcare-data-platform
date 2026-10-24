---
status: active
scope: synthea-apps-source-map
last_verified: 2026-10-16
source_sha: d019429332e794e412426cf9c5053bafa043c05e
---

# Synthea Producer — CODE / 源码导航

> 本页是该组件的**唯一源码地图**。基于上述 Git SHA 的源码和功能边界分类；不重复当前项目状态或运维 Runbook。组件概览见 [README.md](README.md)，运行安全门槛见 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。

## 独立 NEW_ONLY Producer（正式入口）

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`entrypoint.py`](../../../../local-data-platform/apps/synthea/new_only/entrypoint.py) | 独立 NEW_ONLY 多阶段运行入口；显式 fail-closed |
| [`generate_new_only.py`](../../../../local-data-platform/apps/synthea/new_only/generate_new_only.py) | 固定请求与 Seed 的本地 CSV 生成器；不发布 READY |
| [`preflight.py`](../../../../local-data-platform/apps/synthea/new_only/preflight.py) | Producer 的 K8s / 存储只读预检 |
| [`prepublish_gate.py`](../../../../local-data-platform/apps/synthea/new_only/prepublish_gate.py) | 生成后、上传前的本地发布安全校验 |
| [`publish_v1_verified.py`](../../../../local-data-platform/apps/synthea/new_only/publish_v1_verified.py) | NEW_ONLY v1 S3 不可变发布 |
| [`publish_v2_verified.py`](../../../../local-data-platform/apps/synthea/new_only/publish_v2_verified.py) | NEW_ONLY v2 S3 不可变发布 |
| [`verify_v1_ready.py`](../../../../local-data-platform/apps/synthea/new_only/verify_v1_ready.py) | v1 READY 的全对象校验与只读读回 |
| [`verify_v2_ready.py`](../../../../local-data-platform/apps/synthea/new_only/verify_v2_ready.py) | v2 READY 的 18 CSV 和 Manifest 只读读回 |

## 历史 Producer / S3 发布兼容代码

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`validate_synthea_batch.py`](../../../../local-data-platform/apps/task001/validate_synthea_batch.py) | 历史 TASK001 18 CSV/Schema/SHA 验证 |
| [`publish_synthea_landing.py`](../../../../local-data-platform/apps/task004/publish_synthea_landing.py) | 历史 v1 发布模块，仍为部分 NEW_ONLY 路径复用 |
| [`validate_generated_synthea_batch.py`](../../../../local-data-platform/apps/task004/validate_generated_synthea_batch.py) | 历史 TASK004 生成数据本地校验与 Manifest 构造 |

## 关联入口

[独立镜像](../../../../local-data-platform/images/synthea-new-only/Dockerfile) · [K8s Job 模板](../../../../local-data-platform/kubernetes/manifests/synthea/new-only) · [Synthea Contract](../../../../local-data-platform/contracts/synthea/producer-batch-identity-v1.json) · [Producer Tests](../../../../local-data-platform/tests/synthea_new_only)

`publish_synthea_landing.py` 的旧版接口仍被新的 v1 路径复用，不能为了重排目录改变它。

## 版本化 Synthea Contracts

| 源文件 | 角色 / 安全边界 |
| --- | --- |
| [`csv-contract-v2.json`](../../../../local-data-platform/contracts/synthea/new-only/csv-contract-v2.json) | NEW_ONLY v2 CSV 数据集、Manifest 和 Patient/Encounter 必须非空约束 |
| [`ready-publication-policy-v1.json`](../../../../local-data-platform/contracts/synthea/new-only/ready-publication-policy-v1.json) | READY Manifest-last 的发布门槛、Consumer 兼容验收记录 |
| [`producer-batch-identity-v1.json`](../../../../local-data-platform/contracts/synthea/producer-batch-identity-v1.json) | Synthea Producer Batch ID / Legacy / NEW_ONLY / 后续模式的版本化身份 |
| [`csv-contract.json`](../../../../local-data-platform/contracts/synthea/v3.3.0/csv-contract.json) | Synthea 18 CSV Inventory/Header v1；原有非空行规则 |

**Contract 治理**：这些机器可读协议不能为了文档整理而改写。冻结版本中如有旧的 `state`、`consumer_compatibility` 记录，代表该版本写入时的判断；现在的 Runtime 是否验收应以真实 Commit/Run/Readback 证据为准。修改身份、Headers 或 CSV 策略必须先做生产者和消费者兼容性评估，必要时创建新版本。

独立 NEW_ONLY 镜像新 GHCR 包名：`ghcr.io/johnzhang-dataforge/healthcare-data-platform-local-dp-synthea-new-only`；旧 `healthcare-synthea-new-only` 作为历史回退，不再是当前源码自动发布目标。

## 镜像构建 / Entrypoint（Synthea）

| 源文件（直接链接） | 用途与运行边界 |
| --- | --- |
| [`Dockerfile`](../../../../local-data-platform/images/synthea-new-only/Dockerfile) | 独立 NEW_ONLY Generator/Publisher：BASE_IMAGE 注入本轮 Synthea 父镜像、v1/v2 合同和 Readback |
| [`Dockerfile`](../../../../local-data-platform/images/synthea/Dockerfile) | 历史 Synthea v3.3.0 多阶段构建：固定上游 Commit + 本地 CSV Validator |
| [`entrypoint.sh`](../../../../local-data-platform/images/synthea/entrypoint.sh) | 历史 Synthea Generator 入口：Seed、日期和 18 CSV 校验，只生成本地 Manifest |

## 独立 NEW_ONLY / 历史 Task Job、PVC 和 StorageClass

| 源文件（直接链接） | 用途与运行边界 |
| --- | --- |
| [`job.yaml.tpl`](../../../../local-data-platform/kubernetes/manifests/synthea/new-only/job.yaml.tpl) | 早期 NEW_ONLY 生成 Job 模板：worker01、只读 ConfigMap、持久化 PVC；需完整参数渲染 |
| [`publish-v1-job.yaml.tpl`](../../../../local-data-platform/kubernetes/manifests/synthea/new-only/publish-v1-job.yaml.tpl) | 历史固定 v1 S3 发布模板；使用 Digest Pin / Secret / 显式只读来源 Gate |
| [`pvc.yaml`](../../../../local-data-platform/kubernetes/manifests/synthea/new-only/pvc.yaml) | Synthea 生成请求持久化 PVC：dw-synthea、synthea-local、5Gi；不是 SeaweedFS PVC |
| [`runtime-generate-job.yaml.tpl`](../../../../local-data-platform/kubernetes/manifests/synthea/new-only/runtime-generate-job.yaml.tpl) | 独立 NEW_ONLY generate 阶段 Job：固定请求 ID、Digest、worker01 和 Synthea State PVC |
| [`runtime-landing-job.yaml.tpl`](../../../../local-data-platform/kubernetes/manifests/synthea/new-only/runtime-landing-job.yaml.tpl) | 独立 NEW_ONLY 发布/校验 Job：S3 Secret 引用、SOURCE/PG 审计 Gate；不授权业务写库 |
| [`storageclass.yaml`](../../../../local-data-platform/kubernetes/manifests/synthea/new-only/storageclass.yaml) | synthea-local StorageClass：Retain、WaitForFirstConsumer；实际 nodePathMap 与文件系统需 Live 核实 |
| [`synthea-generate-only-job.yaml.tpl`](../../../../local-data-platform/kubernetes/manifests/task004/synthea-generate-only-job.yaml.tpl) | 旧 TASK004 单独生成 Job：固定批次参数、worker01、历史验收兼容模板 |
| [`synthea-generate-publish-job.yaml.tpl`](../../../../local-data-platform/kubernetes/manifests/task004/synthea-generate-publish-job.yaml.tpl) | 旧 TASK004 生成并 S3 发布 Job：旧入口和 Secret、不可当 NEW_ONLY 独立模式 |

**部署约束**：这些文件不是一键集群重建清单；Job `*.yaml.tpl` 必须按受控 Request、Batch、Digest、Namespace 和 PVC 渲染后审查。`synthea-local` 的 `Retain` 不代表实际硬盘隔离或备份；`dw-synthea` Secret、PVC/StorageClass 和历史 Job 的使用须先核实真实集群。当前独立 Generator 与 Legacy Task 模板并存不代表可以重新执行已完成批次。

## 历史 Shell / 脚本导航（由 synthea 组件负责）

> 本清单是历史 Step Shell 的**代码索引，不是按顺序执行的 Runbook**。这些文件可能使用固定 Git SHA/Batch ID、操作 S3/PG/K8s、修改仓库源码或生成本地报告；任何执行须先读脚本全文并核对 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。新脚本必须按组件/能力命名，不能新增 `taskNNN` 路径。

## 历史 task001（1 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`01-validate-build-draft.sh`](../../../../local-data-platform/scripts/task001/01-validate-build-draft.sh) | [PREPARE / may write] 历史 TASK001 validate build draft 脚本 |

## 历史 task004（5 个入口）
> **2026-10-21 Task 4.9 单轮清理**：两个旧一次性生成器不再是活动源码入口；正式 `images/synthea/`、`apps/task004/`、`tests/task004/` 与 `.github/workflows/build-synthea-image.yml` 保留并由当前源码/CI 维护。历史可恢复：[`01-prepare-synthea-generator-image-source.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/6ed31d9a0c3998a653eaf587cde64cb13281ffb8/local-data-platform/scripts/task004/01-prepare-synthea-generator-image-source.sh)、[`02-prepare-synthea-ghcr-workflow.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/6ed31d9a0c3998a653eaf587cde64cb13281ffb8/local-data-platform/scripts/task004/02-prepare-synthea-ghcr-workflow.sh)。这是历史生成脚本退役，不允许覆盖新源码来重放。


| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`03a-prepare-synthea-generate-only-runtime.sh`](../../../../local-data-platform/scripts/task004/03a-prepare-synthea-generate-only-runtime.sh) | [PREPARE / may write] 历史 TASK004 prepare synthea generate only runtime 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`03b-run-synthea-generate-only.sh`](../../../../local-data-platform/scripts/task004/03b-run-synthea-generate-only.sh) | [PREPARE / may write] 历史 TASK004 run synthea generate only 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`04a-prepare-synthea-landing-publisher.sh`](../../../../local-data-platform/scripts/task004/04a-prepare-synthea-landing-publisher.sh) | [PREPARE / may write] 历史 TASK004 prepare synthea landing publisher 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`04b-sync-s3-secret-to-synthea.sh`](../../../../local-data-platform/scripts/task004/04b-sync-s3-secret-to-synthea.sh) | [HIGH / review] 历史 TASK004 sync S3 secret to synthea 脚本；涉及跨 Namespace Secret，须独立授权 |
| [`04c-run-synthea-generate-publish.sh`](../../../../local-data-platform/scripts/task004/04c-run-synthea-generate-publish.sh) | [PREPARE / may write] 历史 TASK004 run synthea generate publish 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |

## 源码维护约定

**新增、删除、重命名或移动本组件负责的 `apps/`、`contracts/`、`sql/`、`images/`、`kubernetes/` 或 `scripts/` 源文件，必须在同一个 PR 更新本 CODE.md。** CODE.md 只做导航，不能当作重新执行历史脚本的授权。历史 `taskNNN` 程序仍可能被 Docker COPY、Import 或冻结 Contract 引用；先看 [Legacy 重构计划](../../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)。



## 新的参数化生成器（独立于既有 OMOP NEW_ONLY）

本组件位于新的 `apps/synthea/synthea_new_generator/`，只负责本地、参数化的 NEW_ONLY CSV/FHIR R4 数据生成、冻结与校验；不依赖旧 `new_only/` 的 18 CSV S3 Publisher/PG Writer，也不自行调用 OIE 或上传 Blob。当前阶段单元/合同验证；真实 Synthea 运行和 Kubernetes 部署仍待 OpenSpec P2/P3 验收。

| 源文件 | 说明 |
| --- | --- |
| [`request.py`](../../../../local-data-platform/apps/synthea/synthea_new_generator/request.py) | 请求参数校验、规范化、版本绑定与 fingerprint |
| [`generator.py`](../../../../local-data-platform/apps/synthea/synthea_new_generator/generator.py) | Synthea CLI 参数、不可变请求、输出清单/Manifest、重试与本地数据检查 |
| [`entrypoint.py`](../../../../local-data-platform/apps/synthea/synthea_new_generator/entrypoint.py) | 离线/容器均可复用的本地生成 CLI；不拥有云写权限 |
| [Request Schema](../../../../local-data-platform/contracts/synthea/new-generator/request-v1.schema.json) | 参数化 NEW_ONLY v1 输入合同 |
| [Manifest Schema](../../../../local-data-platform/contracts/synthea/new-generator/generation-manifest-v1.schema.json) | 本地生成成功标记、文件 SHA/数量/来源指纹 |
| [Generator tests](../../../../local-data-platform/tests/synthea_new_generator/test_generator.py) | 纯离线/Stub Java 执行路径、错误请求、重复请求、数据损坏与 FHIR 关联测试 |
| [Unit workflow](../../../../.github/workflows/synthea-new-generator-unit.yml) | 无云、无集群、无 PostgreSQL 权限的 PR 单测 |

实施入口：[`implement-synthea-new-generator`](../../../../openspec/changes/implement-synthea-new-generator/tasks.md)。
