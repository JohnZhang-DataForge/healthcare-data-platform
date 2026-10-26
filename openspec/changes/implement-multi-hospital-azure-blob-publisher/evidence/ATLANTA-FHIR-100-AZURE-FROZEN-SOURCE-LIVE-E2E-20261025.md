# Atlanta Hospital A — 冻结 100 名患者 FHIR R4 → Azure Blob 真实 E2E 验收（2026-10-25）

**最终状态：Task 3.6 E2E ACCEPTED；只限 Atlanta Hospital A 的本次冻结源发布。**

## 真实发布绑定

| 项目 | 准确值或证据 |
| --- | --- |
| Healthcare 代码修复 | [PR #500](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/500)，Source Base `60d0ee58a050f62045881d169290d2d10a1325eb`；实际发布 Checkout Healthcare Main `18153b887a9dce033c4475c632878db1aa7c0324`，受保护源码路径未漂移 |
| Self-Runner 受控修复 | [PR #307](https://github.com/JohnZhang-DataForge/Self-Runner/pull/307)，执行 Main SHA `d9f195eabdc34a2075379677c47afaeacf0be2ea` |
| 身份绑定及静态 CI | [PR 静态 Run #40250470993](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40250470993) SUCCESS；GitHub vars/secrets 引用精确复用之前 5 人 E2E 已验收的主 Workflow；不包含凭据字节 |
| 真正 Azure 发布 E2E | [**Self-Runner Run #40250606505，Attempt 1，SUCCESS**](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40250606505)，Job `121341494782`；`push/main` 单次受控触发 |
| 运行前共享资源只读预检 | [#40226055238 Attempt 8](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238/attempts/8) SUCCESS，Active Jobs 0，PVC / Publisher Secret PASS |
| 运行后共享资源只读复核 | [#40226055238 Attempt 10](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238/attempts/10) SUCCESS，Active Jobs 0，Secret Keyset PASS，原失败 Run 残留 Profile ConfigMap 仍有 1 个；此后置 Run **不写 Azure/K8s** |
| Publisher 不可变新镜像 | `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:cfc94ce6ef7814925bfe46efa9e44730cd676d7210550ea0e21292648a342e25`，来源 [GHCR Clean Build #40247661319](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40247661319) |
| 来源 Hospital / Feed | `atlanta-hospital-a` / `atlanta-hospital-a-fhir-r4`；`dw-synthea`、`worker01`、现有 `synthea-new-generator-state` PVC |
| 冻结来源 Request | `atlanta-fhir-gh-40245591533`，没有重新运行 Synthea |
| Source Manifest SHA256 | `6d12659acff1fc59e7d0739410eeed9593323f36a6e5330b9608b1591e73b529`，Runner 独立审计与真实发布核对完全一致 |
| Azure Destination | `https://johnzhang.blob.core.windows.net` / `landing` / `clinical/v1` |
| Manifest Blob key | `clinical/v1/atlanta-hospital-a/atlanta-hospital-a-fhir-r4/atlanta-fhir-gh-40245591533/landing-manifest.json` |
| Remote Manifest SHA256 | `7f869bd9e9b9aefa4d6ddfebaf66ce011f53afa143d33b3731bc44dc53fa8c00` |
| Remote Manifest ETag | `"0x8DF32FA20C8FA9A"` |
| 真实发布 FHIR Bundle 数 | **100** |

## 实际 Job 原始 PASS 断言

[Run #40250606505 / 真正 runtime Job #121341494782](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40250606505) 中：

- `FROZEN_REQUEST_RECOVERY_MODE=NO_GENERATOR`、`SHARED_RUNTIME_SERIAL_GATE=PASS`、`SCOPED_KUBERNETES_SECRET_KEYSET=PASS`。
- `AZURE_PUBLISHER_OAUTH_STORAGE_AUDIENCE=PASS`、`AZURE_FROZEN_REQUEST_PREFIX_EXISTING_BLOBS=0`、`AZURE_PREFIX_READONLY_VERIFICATION=PASS`：**实际 PUT 前**使用独立 Storage OAuth，对冻结 Request 的 Azure 前缀进行只读 LIST，确认无其他对象或续页。
- `SCOPED_CONFIGMAP_INDEPENDENT_READBACK=PASS`、`SOURCE_FHIR_OBJECTS=100`、`SOURCE_MANIFEST_SHA256=6d12659...73b529`、`FROZEN_SOURCE_MANIFEST_OUT_OF_BAND_SHA=PASS`：同一原始冻结源已通过新 Publisher 镜像的 FHIR filename/字节安全合同。
- `AZURE_BLOB_INDEPENDENT_OBJECT_GET_SHA_ETAG=100` **连续 3 次**（首次提交、同 Request 不变重试后、错误 SHA 负向后），每次均核对 100 个远端对象的 GET 字节 SHA256、HEAD 元数据、Content-Type 和 ETag；`AZURE_BLOB_INDEPENDENT_MANIFEST_GET_SHA_ETAG=PASS` 同样连续 3 次。
- `SAME_100_FHIR_REQUEST_IDEMPOTENT=PASS`：同一来源重试必须 `ALREADY_MATCHING`、100 个对象和 Manifest 的独立 ETag 不变。
- `WRONG_PINNED_SHA_NEGATIVE=PASS`、`100_FHIR_WRONG_SHA_REMOTE_UNCHANGED=PASS`：错误来源 SHA 先拒绝发布、100 个实际 Blob 及 Manifest 没有改写。
- `RUN_SCOPED_EPHEMERAL_RESOURCE_CLEANUP=PASS`，`ATLANTA_FROZEN_100_FHIR_AZURE_BLOB_E2E=PASS`；`OIE_PG17_AIRFLOW_SPARK_MUTATIONS=NO`。仅清理这一次恢复创建的 ConfigMap/Job；保留原始冻结 PVC 数据及 Azure 对象。

## 失败历史保留，不更改旧 Run 结论

- [旧 Generator 原始 E2E #40245591533](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40245591533) 仍为 FAILURE：成功生成 100 人，但 2 个合法文件名因旧 ASCII 校验误拒，完全没有执行 Azure PUT。文件名问题由 Healthcare PR #500 修复。
- [第一次受控恢复 #40248357801](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40248357801) 仍为 FAILURE：恢复 Workflow 将 GitHub Vars/Secrets 表达式错误转为字面量，Azure Client ID fail-closed；未创建 Audit/Publisher Job，未 PUT。此问题由 Self-Runner PR #307 改用精确已验证变量绑定解决。
- 两次失败均没有被重跑覆盖或重写结论。最终成功是 **新 Run #40250606505** 读取**同一冻结 Source Request**、使用新版 Digest 正式提交 Azure。与此前 5 人 E2E 所用 Request 完全分离。
- 成功后 [Self-Runner PR #308](https://github.com/JohnZhang-DataForge/Self-Runner/pull/308) 已合并并退役单次 Main Push 自动恢复 Workflow；永久 5/100 主手工 Workflow 与受控源码保留。没有为此重新产生数据。

## 准确验收边界与待办

- **OpenSpec 3.6 CHECKED**：100 名患者 Atlanta FHIR Source 真实 Azure Blob immutable Manifest-last PUT→全部 GET/HEAD/SHA/ETag、重试、负向测试、清理均实际 PASS。
- **OpenSpec 3.2 / 3.3 / 4.2 仍 OPEN**：Johns Creek 共享 OIE→HL7→Azure 没有因此验收，也不能把单医院的成功视为双院完整流程。
- 本次不对全部 FHIR R4 Profile 运行官方 FHIR Validator，不表示 Fabric Notebook/Pipeline 成功装载或数据已转换为 OMOP。
- 旧失败 Run 的两个 Job/ConfigMap 不属于本次成功恢复的清理范围；运行后只读复核仍见 1 个历史 Profile ConfigMap，后续若要清理须单独只读核对标签/所有权和授权，**不要盲删冻结数据**。
