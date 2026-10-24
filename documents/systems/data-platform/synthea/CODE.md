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

本组件位于新的 `apps/synthea/synthea_new_generator/`，只负责本地、参数化的 NEW_ONLY CSV/FHIR R4 数据生成、冻结与校验；不依赖旧 `new_only/` 的 18 CSV S3 Publisher/PG Writer，也不自行调用 OIE 或上传 Blob。P1 单元/合同测试与 P2 固定版本真实 Synthea FHIR/CSV 生成已通过；P3 独立镜像已在 GitHub-hosted CI 真实验证，**尚未发布 GHCR 或部署共享 Kubernetes**。

| 源文件 | 说明 |
| --- | --- |
| [`__init__.py`](../../../../local-data-platform/apps/synthea/synthea_new_generator/__init__.py) | 新生成器独立 Python package 的入口标识 |
| [`request.py`](../../../../local-data-platform/apps/synthea/synthea_new_generator/request.py) | 请求参数校验、规范化、版本绑定与 fingerprint |
| [`generator.py`](../../../../local-data-platform/apps/synthea/synthea_new_generator/generator.py) | Synthea CLI 参数、不可变请求、输出清单/Manifest、重试与本地数据检查 |
| [`entrypoint.py`](../../../../local-data-platform/apps/synthea/synthea_new_generator/entrypoint.py) | 离线/容器均可复用的本地生成 CLI；不拥有云写权限 |
| [Request Schema](../../../../local-data-platform/contracts/synthea/new-generator/request-v1.schema.json) | 参数化 NEW_ONLY v1 输入合同 |
| [Manifest Schema](../../../../local-data-platform/contracts/synthea/new-generator/generation-manifest-v1.schema.json) | 本地生成成功标记、文件 SHA/数量/来源指纹 |
| [Generator tests](../../../../local-data-platform/tests/synthea_new_generator/test_generator.py) | 纯离线/Stub Java 执行路径、错误请求、重复请求、数据损坏与 FHIR 关联测试 |
| [Unit workflow](../../../../.github/workflows/synthea-new-generator-unit.yml) | 无云、无集群、无 PostgreSQL 权限的 PR 单测 |

实施入口：[`implement-synthea-new-generator`](../../../../openspec/changes/implement-synthea-new-generator/tasks.md)。


## 医院/Feed 调用配置（P2，不属于 Generator 内部）

Atlanta/FHIR 和 Johns Creek/HL7 Profile 仅构造 FHIR R4 新生成请求；OIE 转换和 Blob 发布是独立下游能力，本节不表示 OIE 已运行。

| 入口 | 作用 |
| --- | --- |
| [`__init__.py`](../../../../local-data-platform/apps/clinical_producers/__init__.py) | 医院调用组件包 |
| [`hospital_profiles.py`](../../../../local-data-platform/apps/clinical_producers/hospital_profiles.py) | 医院/Feed 配置 → Generator Request；不改变 Generator 内部 |
| [Hospital Profile Contract](../../../../local-data-platform/contracts/synthea/new-generator/hospital-profile-v1.schema.json) | 独立医院和交付类型合同 |
| [Profile tests](../../../../local-data-platform/tests/synthea_new_generator/test_hospital_profiles.py) | 医院配置、隔离和异常路由离线测试 |
| [Real source smoke](../../../../.github/workflows/synthea-new-generator-real-smoke.yml) | GitHub-hosted 真实 Synthea CSV/FHIR 测试；不写任何共享资源 |


## P3 — 独立镜像与 K8s 部署模板（尚未部署）

**安全边界**：新容器只复制 `synthea_new_generator`；基础 Synthea 镜像必须作为经过版本核对的 `@sha256:` 不可变构建参数传入。Job 模板里的镜像和请求 ConfigMap 均须由独立 Workflow 严格渲染。所有 Job 使用新 PVC `synthea-new-generator-state`；不会复用或清理旧 `synthea-new-only-state`。镜像编译/CI PASS 不代表共享集群已运行。

| 文件 | 责任 |
| --- | --- |
| [`Dockerfile`](../../../../local-data-platform/images/synthea-new-generator/Dockerfile) | 独立镜像（仅生成器代码）、必须传入不可变 BASE_IMAGE |
| [`pvc.yaml`](../../../../local-data-platform/kubernetes/manifests/synthea/new-generator/pvc.yaml) | 独立 Synthea 新生成器 PVC，部署前核实 StorageClass/节点容量 |
| [`generate-job.yaml.tpl`](../../../../local-data-platform/kubernetes/manifests/synthea/new-generator/generate-job.yaml.tpl) | 带占位符的 Kubernetes Job，只读请求、受限资源与不可变镜像 |
| [`test_p3_packaging.py`](../../../../local-data-platform/tests/synthea_new_generator/test_p3_packaging.py) | 镜像/模板隔离和基本安全策略静态单测 |
| [`synthea-new-generator-image-smoke.yml`](../../../../.github/workflows/synthea-new-generator-image-smoke.yml) | GitHub-hosted 独立镜像 Clean Build，read-only root + network=none 真实 FHIR 生成、Manifest SHA 读回及重试；不会推镜像或 Apply K8s |

准备实际部署时先核验 `dw-synthea`、`worker01`、`synthea-local`、旧 PVC、当前并行 Job、GHCR Release Image Digest 和本 Change 的 4.4 安全许可；未授权一律 HOLD。Job 所需的 ConfigMap 必须具有 `request.json` 键，按 Profile 创建不同 Request ID。生成状态 `SOURCE_GENERATED_VALIDATED` 不是 Blob READY，也不是完成 HL7。

**P3 证据与边界（2026-10-24）**：[PR #420](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/420) 的 GitHub-hosted 独立 Docker Smoke 使用父镜像 `ghcr.io/johnzhang-dataforge/healthcare-data-platform-synthea@sha256:2ef13ae77d476983ea88a5377570190859f253c9f98eb0652ebc793ef685b6b1`，实际验证 Atlanta 1 Patient/43 Encounter、Johns Creek 1/31、同请求重试与独立 Manifest SHA256 读回。镜像只在临时 Runner 本地构建，未推送 GHCR；模板也没有在 `dw-synthea` 应用。下一步的 4.4 K8s 操作必须完成 Session Coordination / Safe Operations 资源、授权和身份核对。

## P3.4 — Main-only GHCR Release

| 文件 | 用途 |
| --- | --- |
| [`synthea-new-generator-ghcr-release.yml`](../../../../.github/workflows/synthea-new-generator-ghcr-release.yml) | 仅在 Main push/手动执行时构建新生成器镜像，真实独立 FHIR 生成与 SHA 读回成功后发布 `git-<SHA>`，禁止修改 `latest`；不自动部署 K8s |

**分界**：GHCR 发布不代表已在 `dw-synthea` 运行；实际 PVC/Job 和持久化读回须走单独 Self-Runner 运行验收，前置安全门禁止占用时执行。

**2026-10-24 ConfigMap 安全兼容性修正**：Kubernetes ConfigMap 按目录挂载时文件是符号链接，Generator 的 `load_request` 拒绝符号链接。新 Job 模板使用 `subPath: request.json` 单文件只读挂载，生成前即冻结输入。该改变不涉及旧 NEW_ONLY 目录或 PVC，真实 Job 验证参见 OpenSpec 4.4。

## 新生成器 P3.4 实际部署验收（2026-10-24）

原 P3 镜像在 CI 的状态描述属于当时历史边界，**当前新生成器已发布并在共享集群受控验证**。源码保留旧 `apps/synthea/new_only/` 不动。

- [Healthcare PR #421](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/421) 发布 `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-generator@sha256:7aeb7dab50611a39953e59eb8032446087208fed8d01fb4795580138bb040f7e`，只发布 SHA 标签，不覆盖 `latest`。
- [Healthcare PR #423](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/423) 修复新 K8s Job 的 ConfigMap 单文件 `subPath` 挂载，以匹配 Generator 严格的拒绝符号链接策略。
- [Self-Runner Run #40100347980](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40100347980) 验证 `worker01` 生成 1 Patient / 43 Encounter / 1 FHIR Bundle，同请求重试以及新 PVC 内文件 SHA 读回 PASS。独立新 PVC `synthea-new-generator-state` 保留、Bound / Retain；临时 Job、ConfigMap 和 Pull Secret 清理完毕；旧 NEW_ONLY PVC 身份不变。
- **未完成**：OIE 将 FHIR 转为 HL7、Blob Landing Publisher、Fabric 消费者；本 Run 不构成这些环节的通过证据。

## P4.1 — FHIR 下游只读交接

| 文件 | 责任与边界 |
| --- | --- |
| [source_handoff.py](../../../../local-data-platform/apps/clinical_producers/source_handoff.py) | 下游只读核验冻结 Request/Manifest/实际 FHIR 文件与医院 Profile；仅输出交接 JSON，不发布云端或 HL7 |
| [source-handoff-v1.schema.json](../../../../local-data-platform/contracts/synthea/new-generator/source-handoff-v1.schema.json) | 源文件交接 JSON v1 机器协议 |
| [test_source_handoff.py](../../../../local-data-platform/tests/synthea_new_generator/test_source_handoff.py) | 本地正常、漂移/篡改、符号链接、重试/只读测试 |
| [SOURCE-HANDOFF.md](SOURCE-HANDOFF.md) | 交接布局、CLI 与接收方复验规则 |

OIE/Blob 发布不属于 P4.1；其 Runtime 成功不能由离线校验测试推出。

## OIE ADT 最小映射 — external Johns Creek Producer

| 文件 | 责任 |
| --- | --- |
| [adt_a01.js](../../../../local-data-platform/apps/clinical_producers/oie/adt_a01.js) | 供 OIE Channel 使用的通用 FHIR Encounter IMP → HL7 ADT^A01 ES5 纯映射逻辑，当前仅离线测试 |
| [test_oie_adt_a01.js](../../../../local-data-platform/tests/clinical_producers/test_oie_adt_a01.js) | Node.js HL7 字段、拒绝、跳过、稳定 ID 与 VM 兼容测试 |
| [README.md](../../../../local-data-platform/apps/clinical_producers/oie/README.md) | 使用方式与尚未完成的 OIE Channel/运行态边界 |
| [oie-adt-mapping-unit.yml](../../../../.github/workflows/oie-adt-mapping-unit.yml) | GitHub-hosted 离线 PoC 映射门禁，无 K8s/云连接 |

OpenSpec：[`implement-oie-fhir-to-hl7-adt-poc`](../../../../openspec/changes/implement-oie-fhir-to-hl7-adt-poc/tasks.md)。

## OIE / worker01 独立部署候选（静态）

| 文件 | 作用及边界 |
| --- | --- |
| [OIE Kubernetes README](../../../../local-data-platform/kubernetes/manifests/oie/README.md) | `dw-oie` 前置审批、独立 PVC/Secret/镜像与真实安全门 |
| [namespace.yaml](../../../../local-data-platform/kubernetes/manifests/oie/namespace.yaml) | 拟建 `dw-oie`，尚未 Apply |
| [pvc.yaml.tpl](../../../../local-data-platform/kubernetes/manifests/oie/pvc.yaml.tpl) | 独立 `oie-state`，需确认 worker01 StorageClass Retain |
| [statefulset.yaml.tpl](../../../../local-data-platform/kubernetes/manifests/oie/statefulset.yaml.tpl) | 单副本、固定 `worker01`、Digest/Secret 占位符，不可直接 Apply |
| [service.yaml](../../../../local-data-platform/kubernetes/manifests/oie/service.yaml) | OIE 8443 ClusterIP 管理端口；不暴露公网 |
| [OIE manifest tests](../../../../local-data-platform/tests/clinical_producers/test_oie_k8s_manifests.py) | 静态隔离与 YAML 解析测试 |
| [OIE static workflow](../../../../.github/workflows/oie-manifest-static.yml) | GitHub-hosted 不访问 K8s 的 Worker01 模板 CI |

## OIE 临时调试安装（持久化延后）

| 入口 | 作用 |
| --- | --- |
| [debug/deployment.yaml.tpl](../../../../local-data-platform/kubernetes/manifests/oie/debug/deployment.yaml.tpl) | `dw-oie`/worker01 非持久化 Deployment；`emptyDir` + 固定 Digest/UID/GID 占位符，不申请 PVC |
| [debug/service.yaml](../../../../local-data-platform/kubernetes/manifests/oie/debug/service.yaml) | 临时 OIE 内网 HTTPS Service |
| [debug/README.md](../../../../local-data-platform/kubernetes/manifests/oie/debug/README.md) | 安全调试步骤、失效数据边界以及持久化延后约束 |
| [OIE debug template tests](../../../../local-data-platform/tests/clinical_producers/test_oie_debug_manifest.py) | 非持久化模式 YAML/节点/Secret 边界测试 |
| [OIE debug static CI](../../../../.github/workflows/oie-debug-manifest-static.yml) | 无集群调用的 GitHub-hosted 静态门禁 |

## OIE 4.7.0 固定源码镜像隔离 Smoke

| 文件 | 作用 |
| --- | --- |
| [OIE pinned build README](../../../../local-data-platform/images/oie/README.md) | 上游 v4.7.0 精确 Commit、原 Dockerfile target/依赖与 GHCR 交付边界 |
| [OIE 4.7 isolated image smoke](../../../../.github/workflows/oie-470-isolated-image-smoke.yml) | GitHub-hosted 官方源 Clean Build 与启动测试，不推送镜像、不改共享环境 |

## OIE 4.7 GHCR 固定镜像发布

| 文件 | 作用 |
| --- | --- |
| [oie-470-ghcr-release.yml](../../../../.github/workflows/oie-470-ghcr-release.yml) | 仅 Main、正式 4.7.0 上游精确源码及临时容器启动 PASS 后推送 `healthcare-oie:git-<MainSHA>`，独立 Digest 读回，不改 `latest` 或共享 K8s |

## OIE 非持久化 Live 安装验收（2026-10-24）

[Self-Runner Run #40120249619](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40120249619) 已将 `dw-oie/oie-debug` 真正安装在 worker01。使用独立 GHCR OIE 4.7.0 固定镜像 Digest、嵌入式 Derby 和 `emptyDir`，Pod Ready、版本与临时存储独立读回 PASS；`dw-oie` PVC=0。后续 PVC 由用户在内网另行配置，切换前不得删除现有 PVC，也不得把临时环境测试当作 HL7 Channel 已验收。对应 [OIE OpenSpec](../../../../openspec/changes/implement-oie-fhir-to-hl7-adt-poc/tasks.md) 中 2.4/2.5/2.6.3 仍 OPEN。

## OIE worker01 单目录持久化 /data/oie

| 路径 | 作用 |
| --- | --- |
| [persistent/storageclass.yaml](../../../../local-data-platform/kubernetes/manifests/oie/persistent/storageclass.yaml) | 专用 `oie` StorageClass: local-path, worker01 路径 /data/oie, Retain, WaitForFirstConsumer |
| [persistent/pvc.yaml](../../../../local-data-platform/kubernetes/manifests/oie/persistent/pvc.yaml) | 唯一 10Gi `dw-oie/oie-state`，挂 OIE `/opt/engine/appdata`，独立数据库/运行数据 |
| [persistent/README.md](../../../../local-data-platform/kubernetes/manifests/oie/persistent/README.md) | 热加载事实、安全切换路径与一次性 PVC 验收原则；无需第二个文件存储卷 |
| [persistent static test](../../../../local-data-platform/tests/clinical_producers/test_oie_persistent_static.py) | 专用 SC、PVC、安全切换静态校验 |
| [persistent static CI](../../../../.github/workflows/oie-persistent-static.yml) | GitHub-hosted，无 K8s 副作用 |

## OIE appdata 持久化真实验收（2026-10-24）

- [Live PV/PVC/Derby #40121734522](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40121734522)：`oie` SC + `dw-oie/oie-state` 10Gi，`/data/oie` 实际 PV，Retain、worker01、Derby RW PASS；未重启 local-path。
- [Pod 重建后的数据读回 #40122005828](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40122005828)：`oie-debug` 单次 Recreate 后读回 PVC 相同数据 PASS，测试文件已清理。一个卷同时承担 Derby 与 appdata，不需要第二个文件持久卷。OIE clinical Channel/FHIR→HL7 与 Azure Blob 路线尚待单独验收。


## Johns Creek OIE importable Channel MVP (not live yet)
| Path | Role |
| --- | --- |
| [OIE bundled upstream raw reader](../../../../local-data-platform/apps/clinical_producers/oie/upstream-raw-reader.xml) | OIE v4.7.0 official test-export Channel XML, preserves XStream structure |
| [OIE Channel builder](../../../../local-data-platform/apps/clinical_producers/oie/build_channel.py) | Replaces only channel identity and preprocessor JS using canonical ADT mapping |
| [FHIR event splitter](../../../../local-data-platform/apps/clinical_producers/oie/fhir_events.py) | Pure read-only Patient+Encounter per event, clinical classification is done inside OIE |
| [OIE import PoC notes](../../../../local-data-platform/apps/clinical_producers/oie/CHANNEL-POC.md) | Message API and runtime gates, no public listener |
| [OIE import static tests](../../../../local-data-platform/tests/clinical_producers/test_oie_channel_build.py) | XML parse and event slicing contract tests |
| [OIE channel static CI](../../../../.github/workflows/oie-channel-static.yml) | Hosted-only Channel build test; does not import/deploy |


## OIE 4.7 channel import isolated debug gate
[GitHub-hosted Channel import smoke](../../../../.github/workflows/oie-channel-isolated-import.yml) uses a throwaway OIE 4.7.0 official-source image/Derby and diagnostic Java 21 module access to expose the actual channel-create failure. Never touches `dw-oie` PVC or uses patient data; API import acceptance still requires a separate live Run.


## OIE HL7 2.5.1 independent message readback
| Path | Role |
| --- | --- |
| [HL7 source readback](../../../../local-data-platform/apps/clinical_producers/oie/hl7_readback.py) | Strict segment and source identity/control/time match for **actual OIE returned** ADT^A01 messages; no cloud code |
| [HL7 readback tests](../../../../local-data-platform/tests/clinical_producers/test_oie_hl7_readback.py) | Rejects wrong class, timestamp, version, control IDs, malformed segments |
| [HL7 readback CI](../../../../.github/workflows/oie-hl7-readback-unit.yml) | Isolated unit/contract tests; not OIE runtime acceptance |

## Disposable OIE real FHIR→HL7 runtime probe
[Runtime probe](../../../../local-data-platform/tests/clinical_producers/oie_channel_runtime_probe.py) reads only the SHA-pinned synthetic Johns Creek source artifact, sends 31 real Encounter FHIR events (1 IMP/30 AMB) plus identical-request IMP retry through a temporary OIE Channel Reader using local loopback API, and independently verifies returned message content using `hl7_readback.py`. [Isolated CI](../../../../.github/workflows/oie-channel-isolated-import.yml) runs on GitHub-hosted runner only, never on shared Kubernetes/PVC.

## OIE existing worker01 Channel live test mode
After confirming safety and permissions with the scoped Self-Runner runtime Workflow, run the existing probe with `--existing-channel`: it never calls Channel create/deploy, verifies exact persisted ID/name/script, rejects any preexisting Channel messages, and only then writes this verified Johns Creek synthetic test dataset (31 Encounters + 1 repeat), independently parses HL7 A01 and validates 32 message records. Do **not** point it at other Channels, actual patient data or unrelated namespaces. This mode was successfully executed once on worker01 [Self-Runner #40128211780](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40128211780), created 32 persistent OIE message records and must not be blindly rerun; no Azure Blob delivery in this gate.

## Johns Creek OIE persistent Channel live proof
- [Self-Runner #40127786353](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40127786353): Channel create/readback/STARTED PASS on worker01, Retain PVC kept.
- [Self-Runner #40128211780](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40128211780): true 31 real synthetic FHIR Encounter clinical mappings + IMP repeat, independent HL7 source readback and 32 Derby messages PASS; still no HL7-to-Blob delivery receipt. Do not replay this accepted source request without an explicit new strategy.

## Azure Landing immutable publish-plan contract（未发布）
| Path | Role |
| --- | --- |
| [blob_publish_contract.py](../../../../local-data-platform/apps/clinical_producers/blob_publish_contract.py) | 只校验 P4.1/OIE 验证状态、医院、Request、对象路径、原始 Bytes SHA256 与确定性 Blob key；**不上传** |
| [blob-publish-plan-v1.schema.json](../../../../local-data-platform/contracts/clinical_producers/blob-publish-plan-v1.schema.json) | 共享 Azure Blob 输入计划 JSON Schema，医院无关 |
| [test_blob_publish_contract.py](../../../../local-data-platform/tests/clinical_producers/test_blob_publish_contract.py) | 错医院、路径穿越、篡改、状态不匹配的 fail-closed 合同测试 |
| [azure-blob-publish-contract-unit.yml](../../../../.github/workflows/azure-blob-publish-contract-unit.yml) | Hosted-only static/unit，无 Azure/PVC 写入 |


## Shared Azure Blob Publisher（实现待 CI 验证；尚未执行真实 Azure）

| 路径 | 职责与运行边界 |
| --- | --- |
| [azure_blob_publisher.py](../../../../local-data-platform/apps/clinical_producers/azure_blob_publisher.py) | 通用 immutable conditional create、精确 metadata/SHA256、独立 Azure GET/HEAD、最终 `landing-manifest.json` 提交；导入无网络副作用，真实执行必须单独授权 |
| [requirements-blob-publisher.txt](../../../../local-data-platform/apps/clinical_producers/requirements-blob-publisher.txt) | 固定 Azure Blob/Identity SDK 版本，SP 凭证仅由运行时 Secret 提供 |
| [test_azure_blob_publisher.py](../../../../local-data-platform/tests/clinical_producers/test_azure_blob_publisher.py) | 纯离线 Fake Backend：幂等、冲突、部分失败/未知 ACK、远端独立读回和日志脱敏 |
| [test_azure_blob_publisher_azurite.py](../../../../local-data-platform/tests/clinical_producers/test_azure_blob_publisher_azurite.py) | 本地 Azurite SDK 测试：严格 `overwrite=False`、GET、Manifest 重试、冲突，无真实 Azure 存储 |
| [azure-blob-publish-contract-unit.yml](../../../../.github/workflows/azure-blob-publish-contract-unit.yml) | Hosted-only Mock + Azurite CI；不会创建真实 Azure Blob/PVC |

这只实现 shared publisher 传输层，**不是** Atlanta/Johns Creek live adapter 或 K8s→Azure E2E；`SOURCE_HANDOFF_VERIFIED` 和 `OIE_HL7_READBACK_VERIFIED` 必须由调用方独立认证、并提供已验证原始 bytes。无真实 Azure Account/Container/RBAC/Secret、工作负载身份和 Session Coordination Gate 时不得运行真实 PUT。
