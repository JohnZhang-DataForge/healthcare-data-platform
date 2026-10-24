# Design — Shared Azure Blob Publisher and Atlanta/Johns Creek Routes

## 1. 已验收的入口与未验收的出口

```text
dw-synthea / worker01  (同 namespace 只读挂载已有 Generator PVC)
 existing generator frozen FHIR Bundle + Manifest
     │
     ├─ source_handoff.verify_handoff(profile=Atlanta) ── FHIR object ──┐
     │                                                               │
     └─ source_handoff.verify_handoff(profile=Johns Creek)             │
             └─ verified Patient+Encounter events ──┐                 │
                                                      ▼                 │
                                          dw-oie / worker01            │
                                          existing OIE 4.7 Channel     │
                                          1 IMP→A01, AMB→SKIP          │
                                                      │                 │
                                          HL7 independent readback    │
                                                      ▼                 ▼
                                           Common immutable Blob Publisher
                                                      │
                                            existing Azure Blob Landing
                                           objects → independent GET
                                                     → commit manifest LAST
```

- Generator PVC 是 `dw-synthea` namespaced，不跨 Namespace 挂到 `dw-oie`。需要读源数据的 Producer Job 在 `dw-synthea`、worker01 上运行，明确 `readOnly: true` 访问现有 PVC；由受控 ClusterIP HTTPS 访问 `dw-oie`。未获批准不得修改 Generator PVC、创建新的持久存储或扩大网络端口。
- FHIR 验证仍使用 `apps.clinical_producers.source_handoff.verify_handoff()`，验证冻结请求、Manifest、profile、每个 FHIR 文件大小及 SHA256；不重新生成 P0–P3 或伪造 READY。
- Johns Creek 使用既有 OIE Channel 定义和 `hl7_readback.verify_adt_against_fhir()`；生产前应配置仅能处理/读取该 Channel 消息的 OIE 用户，**不复用 PoC 管理员凭证**作为长期 Producer 凭证。已经验收的 32 条 Derby 消息属于历史证据，**不重放**；正式发布使用新冻结 Request。
- OIE 的原 `Channel Writer none` 是转换 PoC，不是发布目标。Publisher 作为显式下游步骤负责上传，并单独记录 HL7 byte payload/Message Control ID 与源 FHIR ID，不以 OIE HTTP 2xx 或 Derby Source TRANSFORMED 状态宣称 Azure 已交付。

## 2. 共享 Publisher 接口 / 不可变对象

输入是按医院 Profile 验证的交付清单（hospital_id/feed_id/request_id/source_manifest_sha256、source/target format、对象 byte payload、真实 SHA256、FHIR 文件源路径或 HL7 Encounter ID/MSH-10、可审计的 event/skipped 计数），没有固定医院 if/else 分支。

建议可配置前缀：`<prefix>/<hospital_id>/<feed_id>/<request_id>/<FHIR_R4|HL7_V2>/<safe-file-name>`。变量必须满足路径安全约束，不允许 `..`、反斜线、绝对路径或不受控 URL。实际 Azure Storage Account URL、Container 和 Prefix 运行时注入，**不得把现有 SeaweedFS `health-landing` bucket 名直接假定成 Azure Blob 容器名**。

Publisher 的操作顺序：

1. 只读校验源请求、资源身份、大小/SHA256 和 Profile。预先计算全部目标对象的确定性 blob key 与字节散列。
2. 对每个数据对象使用 Azure Blob **conditional create**（`If-None-Match: *`，SDK 等价 `overwrite=False`）；保留服务端 ETag/Version ID 等真实收据信息。重复请求遇到已存在对象，必须 GET 原对象，校验实际 SHA256 和精确契约 metadata；完全一致可记 `ALREADY_MATCHING`，不同立即 fail-closed；绝不覆盖。
3. 上传完成后实际 HEAD/GET 目标对象，验证字节 SHA256、大小、预期 Format 和版本/ETag；只有真正从远端读取的内容可标记 `BLOB_OBJECT_VERIFIED`。若网络/权限失败则不得写成功 Manifest，数据对象可以留待严格幂等恢复。
4. 按确定性路径**最后提交**包含源 Manifest SHA、对象列表、每个目标 Blob 校验信息、跳过数、请求/医院标识的 `landing-manifest.json`。同样 immutable create + GET readback，状态 `BLOB_MANIFEST_COMMITTED` 才允许后续 Fabric 消费。不要覆盖半成功批次或标记伪成功。
5. `SAME request_id + changed source_manifest_sha256 OR content SHA256` 一律 HOLD；相同不可变源、对象、Manifest 经远端逐字节校验后允许安全重复调用且不会产生第二份不同内容。

不引入单独 Ledger DB；在单 Blob Container 内的不可变对象及最终 Manifest 是交付身份边界。注意：单个 Blob 的条件写入是原子的，但多 Blob **不是跨对象事务**；先验证数据、再写 Manifest 的协议显式规避“部分写入被当完成”。

## 3. 认证/权限/Secrets 与成本

- MVP 优先使用单独的 Azure Entra Service Principal，分配**目标 Landing 容器所需的最小** Storage Blob Data Contributor 权限；K8s Secret（`dw-synthea`）以只读方式供 Publisher 使用。能建立安全托管工作负载身份时可替换，但必须在设计外单独评审。不要将 Azure client secret/SAS、Bearer token、真实 Patient Data 写到 GitHub 或日志。
- 复用现有 Azure Landing Storage Account/Container；不创建新 Storage、Fabric Capacity 或新收费资源。真实出网、API 次数和对象存储可能有成本，运行前需明确授权。
- Self-Runner 执行仅批准范围。每次操作先核对 Health/Self-Runner Main、并行 Session、活动 Jobs/DagRuns、worker01/OIE/Generator PVC 与 Azure 目标，绝不清空任何已有 Blob。
- 初期代码 CI 使用 mock Azure Blob client 与离线模拟服务（例如 Azurite，前提是镜像/许可证审过）；任何 Azure Live Test 必须是可唯一识别的合成新 Request，证明 GET 读回、冲突和 retry 路径，并保留 Run/receipt。失败保存现场，不盲目重跑。

## 4. 验收边界

- Atlanta 必须在**实际 Azure Landing**得到原始 FHIR R4 bytes 和 Manifest 的独立读回，源数与 SHA 与 frozen Generator Manifest 一致。
- Johns Creek 必须对新 FHIR Request 经过真实 OIE Channel 的可审计消息记录和独立 HL7 读回，只发布合法 A01；门诊跳过计数不等于发送了 HL7。实际 Blob 中 HL7 内容与 MSH-10/源 Encounter 校验一致。
- 两条路线分别验证错误凭据、缺失数据、错医院 Profile、SHA 冲突、重复请求、部分上传失败、远端目标内容不同，以及不调用 Fabric/OMOP/旧 Local DP 的保护边界。
- Fabric Notebook/Pipeline 消费 Landing 是后续 Change；不在本 Change 实施。
