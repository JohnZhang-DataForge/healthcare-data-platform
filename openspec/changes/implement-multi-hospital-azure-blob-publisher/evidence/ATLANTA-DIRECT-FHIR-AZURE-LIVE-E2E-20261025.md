# Atlanta Hospital A — 真实 Azure Blob DIRECT FHIR E2E 验收（2026-10-25）

> **Task 3.1 E2E ACCEPTED**：基于用户授权，在共享 Kubernetes `dw-synthea/worker01` 运行一次全新的 Synthea FHIR R4 Request，生成 5 个 FHIR Object，写入现有 Azure Storage Account `johnzhang` 的 `landing` Container；对 Manifest 和全部 5 个 Object 完成独立 GET/HEAD、SHA256/ETag 校验，同批不可变重试和错误 SHA 负向测试均 PASS。**不是**双医院全流程验收；Johns Creek 真正 OIE→HL7→Azure E2E 尚未运行，Task 3.2 / 4.2 继续 OPEN。

## 不可变执行身份与已验证范围

| 字段 | 实际值 |
| --- | --- |
| Repository | `JohnZhang-DataForge/Self-Runner` |
| Workflow | [Atlanta DIRECT FHIR to Azure Blob - Manual E2E](https://github.com/JohnZhang-DataForge/Self-Runner/actions/workflows/azure-blob-publisher-atlanta-e2e-manual.yml) |
| 原始 GitHub Run | [#40238053772](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40238053772)，`workflow_dispatch`，Attempt 1，**SUCCESS** |
| Self-Runner SHA | `6b1ac1849b5277f647abdedd7f4ee77f526bffbb` |
| Healthcare Main at execution | `89a14d1949be91c9c5f934fb45962b4e2124630a` |
| Publisher/Generator/Profile/Template validated source base | `b033d7b8fd8cf752de7e64b240ea3dc83ce1fe7d`，Main 到 Base 的受保护输入路径 `git diff --quiet` **PASS** |
| Publisher image | `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:a92d06610813a38d3d9707133038f503f1f49b1d76a4144bc2500bded321e3da` |
| Generator image | `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-generator@sha256:7aeb7dab50611a39953e59eb8032446087208fed8d01fb4795580138bb040f7e` |
| Environment | Local K8s `dw-synthea` / `worker01` / PVC `synthea-new-generator-state`（Generator 可写、Publisher 只读挂载） |
| Hospital / Feed | `atlanta-hospital-a` / `atlanta-hospital-a-fhir-r4` |
| Source Request ID | `atlanta-fhir-gh-40238053772` |
| Source Manifest SHA256 | `468eb083d7db21dff2fa9336b587250c30f2cdfb853e8e1ee62c4f6537f15327` |
| Storage target | `https://johnzhang.blob.core.windows.net` / `landing`，`clinical/v1` 前缀 |
| Committed Manifest Blob key | `clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/atlanta-fhir-gh-40238053772/landing-manifest.json` |
| Remote Manifest SHA256 | `772bcc6bcce0ffc137df3af0602238f69db18f8418f62acbc865780957af6af7` |
| Remote Manifest ETag | `"0x8DF32E36D2AA68B"` |
| FHIR Blob Object count | **5** |

本次 **真实 Cloud durable writes** 为新 Request 对象和最终 Commit Manifest；并非对旧 Prefix/Request 进行更名或覆写。独立读回通过同一 Run 的单独 Python Azure Storage OAuth REST GET/HEAD 实现，不以 SDK Publisher 返回成功作为唯一成功依据；直接核对实际 GET Bytes、SHA、HTTP metadata、ETag。

## 原始 Job/Log 可审计 PASS

[Run #40238053772 Job 详情](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40238053772)：
- `Host-only gated workflow static check`（Job `121303782622`）**SUCCESS**：代码编译、精确镜像 Digest 与医院 Profile/渲染模板。
- `Exclusive run-scoped Generator - Publisher - independent Azure GET`（Job `121303814766`）**SUCCESS**：Main 人工确认 `PUBLISH_ATLANTA`、`GITHUB_RUN_ATTEMPT=1`、共享资源串行读回；实际执行以下每项。
- `HEALTHCARE_PUBLISHER_SOURCE_DIFF_ZERO=PASS`。
- `SHARED_RUNTIME_SERIAL_GATE=PASS`，多个业务阶段重检；`SCOPED_KUBERNETES_SECRET_KEYSET=PASS`，没有日志输出凭据值。
- `SCOPED_CONFIGMAP_INDEPENDENT_READBACK=PASS` ×2：新 Profile/Request ConfigMap 的精确源文本读回。
- `ATLANTA_NEW_GENERATOR_REQUEST_COMPLETED=PASS`，随后 `SOURCE_FHIR_OBJECTS=5`。
- `AZURE_PUBLISHER_OAUTH_STORAGE_AUDIENCE=PASS`；首次 Azure Blob Manifest COMMIT 的日志收据已由 E2E 解析和校验，未跳过。
- `AZURE_BLOB_INDEPENDENT_OBJECT_GET_SHA_ETAG=5`；`AZURE_BLOB_INDEPENDENT_MANIFEST_GET_SHA_ETAG=PASS`（首次提交、幂等重试和错误 SHA 后复核，各运行一次）。
- `SAME_REQUEST_BLOB_IMMUTABLE_IDEMPOTENT=PASS`：同 Request Publisher 的 Manifest 状态必须是 `ALREADY_MATCHING`，全部对象/Manifest ETag 前后一致，没有覆盖。
- `WRONG_PINNED_SHA_NEGATIVE=PASS`、`WRONG_SHA_NO_AZURE_MUTATION=PASS`：错误 Source Manifest SHA 被拒绝并确认远端对象 ETag 不变。
- `RUN_SCOPED_EPHEMERAL_RESOURCE_CLEANUP=PASS`：只清理由此 Run 创建的 ConfigMap/Job，不删除冻结 Synthea Request / 已提交 Azure Blob；`ATLANTA_DIRECT_FHIR_AZURE_BLOB_E2E=PASS`。
- `OIE_PG17_AIRFLOW_SPARK_MUTATIONS=NO`：本流程无 OIE/PG17/Airflow/Spark 修改。

## 后置独立环境审计

[Self-Runner 原只读预检 Run #40226055238 — Attempt 3](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238/attempts/3)：在真实 E2E 之后重新执行 **SUCCESS**，`K8S_ALL_ACTIVE_JOBS=0`、`EXISTING_PROFILE_JSON_CONFIGMAPS=0`、Publisher Secret Keyset/Atlanta Profile PASS；`K8S_MUTATIONS=NO`、`AZURE_BLOB_WRITES=NO` **仅指此后置只读审计本身**，不能错误解释成刚才的 E2E 没有写入。前置读回仅是当时快照，并非跨会话锁。

## 决策与剩余范围

- **3.1 已完成**：Atlanta FHIR R4 verified source → Azure immutable Publisher → 所有真实 Blob + commit Manifest 独立 GET/SHA/ETag + 幂等及负向保护通过。
- **4.2 仍 OPEN**：这是两医院独立真实 E2E 的合并门槛；Johns Creek 实际共享 OIE Channel 部署、受控新 FHIR Request、真实 ADT A01 独立读回及 HL7 Blob PUT/GET 尚未执行。
- **3.2 / 3.3 仍 OPEN**：只完成 Atlanta 前缀的隔离/幂等，不能替代 Johns Creek。
- **4.7 仍 OPEN**：独立 Publisher SP 的现有 K8s Secret 通过真实发布身份验证，但 Secret 内容轮换和相关完整生命周期/管理条款未作为本次测试实现。
- **4.1 / 4.3** 按原含跨医院、RBAC/证据归档的任务范围继续 OPEN，不因单侧成功自动全部收口。
- 这次没有向 Fabric Lakehouse 做 Notebook/Pipeline 读入，没有更改 Local DP OMOP Writer，也没有触碰过去 32 条 OIE 消息。不要重放同一 GitHub Run Attempt 作为新批次；未来要新批次应重新获得资源协调授权并使用新 Request ID。
