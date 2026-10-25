# Atlanta DIRECT FHIR → Azure Blob：2026-10-25 只读预检与手工 E2E 入口证据

> **状态：CONTROLLED READONLY PASS / E2E NOT EXECUTED。** 本记录不批准共享 K8s Job/ConfigMap 创建，也不证明 Azure Blob 已写入。下一阶段运行仍需按照 Safe Operations/Session Coordination 完成具体操作的授权与实时资源冲突检查。

## 精确版本与并发边界

- Healthcare 当前核验 Main：`36bd4ee903f627bd851ab6a30444d9dd62767788`；受控 Publisher 源码基线 `b92ccc9b7976e740d9dd77994a0725b115693705`，二者差异仅 Portal P6/Marquez/文档，无 Generator、Profile、Publisher 源码或 K8s 模板变化。
- Self-Runner [PR #295](https://github.com/JohnZhang-DataForge/Self-Runner/pull/295) **已合并** Main `08df04da30c538cc6141fbb52e1f7297eeaae15e`；手工执行脚本及源码在此 Main；PR Hosted 静态模板实际双重渲染与 Python 编译 [Run #40219797240](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40219797240)：**SUCCESS**（无 Azure/K8s 写入）。
- Publisher 镜像 `ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:06324ae6571a6f72f3b317a1ba577851952bb421fc33ef1d87b4718acfcea4e6`，先前 GHCR Main [Run #40148148246](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40148148246)；新 GitHub 提交不代表此 Digest 自动更新，必须绑定代码零漂移校验。
- Generator 既有镜像 `ghcr.io/johnzhang-dataforge/healthcare-synthea-new-generator@sha256:7aeb7dab50611a39953e59eb8032446087208fed8d01fb4795580138bb040f7e`；不变更旧 K8s 镜像使用方。

## 真实只读预检

- [Self-Runner #40218904158](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40218904158) **SUCCESS**：worker01 Ready、压力状态检查通过；`dw-synthea/synthea-new-generator-state` Bound，`ReadWriteOnce`、StorageClass `synthea-local`；全集群活动 Job = 0；OIE 内网 Service/Deployment/PVC 通过；旧 `dw-az-blob` 未恢复。
- `dw-synthea/azure-blob-publisher-identity` 已存在，Secret Type=Opaque，恰好 `tenant-id`、`client-id`、`client-secret` 三个非空键，**未输出 Value**；并非创建或重新校验 Azure 认证成功。
- Atlanta Profile 源码 `local-data-platform/config/synthea-new-generator/atlanta-fhir.json` 验证：`demo-atlanta/demo-atlanta-fhir-r4`、Georgia/Atlanta、FHIR_R4→FHIR_R4、DIRECT。
- 当前 Profile JSON ConfigMap **0**；不可在不存在或未验证 Profile 的状态下运行 Publisher。
- 合并 Main 后再次执行的 [Self-Runner #40219870444](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40219870444) **SUCCESS**；同样确认活动 Job 0、PVC/Secret/Atlanta Profile PASS、Profile ConfigMap 0、`AZURE_BLOB_PUT_GET=NOT_YET_EXECUTED`。
- 本次两次只读预检以及 Hosted 测试均未创建 Pod/Job/ConfigMap、未读取输出 Secret 明文，也未执行 Azure PUT/GET。

## 合并至 Self-Runner Main 的手工 E2E

- Workflow：`Self-Runner/.github/workflows/azure-blob-publisher-atlanta-e2e-manual.yml`；Runner 脚本：`Self-Runner/scripts/azure_blob_atlanta_direct_fhir_e2e.py`。
- **只有** Main `workflow_dispatch` 且 `confirmation=PUBLISH_ATLANTA` 才会运行共享资源步骤；PR 仅 Hosted 静态检查。禁止把本次 PR CI 成功视为真实 E2E。
- 手工 Workflow 固定新的 `atlanta-fhir-gh-<run_id>` Request，校验 Main 祖先和 Publisher/Generator/Profile/模板与镜像基线零漂移；读取 worker01、RWO PVC、全部活动 Job 与同 Namespace Pod、现有 Secret Keyset、K8s RBAC，再创建**仅本 Run 名称**的 Profile/Request ConfigMaps，独立 GET 精确校验内容。
- 新 Generator Job 固定 worker01，在**已有** `synthea-new-generator-state` 写入新请求；独立 Source 审计 Job **只读挂载同 PVC** 并输出外部冻结 Source Manifest SHA；随后 Publisher Job 用现有 K8s 长期 Secret 认证和只读 PVC 向现有 `johnzhang/landing` 进行条件不可变写入。
- Publisher 的最后提交 Manifest 对每个 FHIR Bundle 提供 SHA256/ETag/GET；Runner 以**独立 Azure Storage OAuth** 再 GET/HEAD 验证对象、类型、元数据、SHA/ETag 与 Manifest；再用同请求重试验证 `ALREADY_MATCHING`、ETag 不变；再用故意错误 pinned Manifest SHA 的 Job 验证 fail-closed 且 Azure GET 校验零变化。
- 成功后仅清理本次标识的临时 Jobs/ConfigMaps，保留 PVC 上的冻结 Request 和 Azure immutable 对象；失败报告 `HOLD`、禁止盲目重跑或清理可能已写入的持久对象。临时清理不触碰原 Generator PVC、OIE、Airflow、Spark、PG17。
- 有效权限、运行时其他 Session 是否真正空闲和本轮具体共享写操作授权，是**每次运行前**独立 Gate。当前用户已批准继续自主静态开发与只读检查；**没有在本证据记录内触发共享写入**。

## 尚未验收

1. 当前并无新 Atlanta FHIR Request 的真实生成、实际 Publisher Token/Blob PUT+GET、Manifest ETag/GET、幂等重试的 Run 证据：**3.1 / 4.2 继续 OPEN**。
2. 错误 SHA/冲突对象/非法路径的既有离线合同测试不等于共享 Azure 上的完整负向 E2E；需要按可控安全场景补齐证据，不得人为覆盖生产对象。
3. Johns Creek OIE scoped HTTPS/CA/消息 ID 的新消息验收与 HL7 路线仍 **OPEN**，不可重放历史 32 条 OIE 消息。
4. Client Secret 有期限，4.7 的 Rotation 运行方案和首个真实 Publisher Job 读写仍 **OPEN**。不创建或改写原 Identity/RBAC/Secret。

**下一步**：运营方完成实时 Session 资源协调与 `dw-synthea` scoped Job/ConfigMap + `OMOP/johnzhang/landing` 新不可变 Blob 写入授权后，从 Self-Runner Main **手动**触发 `Atlanta DIRECT FHIR to Azure Blob - Manual E2E` 并填 `PUBLISH_ATLANTA`；读回 Run/Request/SHA/Blob 清单后才勾选对应 OpenSpec Task。

**故障保全**：工作流失败、超时或日志缺失不等于 Azure 未写入；先按本次新 Request ID 查询可能已创建的对象与最终 Manifest，再决定是否恢复或重新触发，且禁止覆盖原 Blob。
