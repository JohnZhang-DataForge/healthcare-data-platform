# Hospital A / Hospital B 稳定身份整改验收（2026-10-25）

> **CODE/SCHEMA/CI/GHCR ACCEPTED；Kubernetes READONLY PASS；Azure Blob E2E NOT RUN。** 此整改避免将早期占位标识长期固化为 hospital/feed 业务身份。历史证据原样保留，不把旧请求、旧 OIE Channel 或旧 Blob 视为已经迁移。

## 正式新标识

| 平台路由 | Hospital ID | Feed ID | HL7 Assigning Authority |
| --- | --- | --- | --- |
| Atlanta DIRECT FHIR R4 | `atlanta-hospital-a` | `atlanta-hospital-a-fhir-r4` | n/a |
| Johns Creek OIE HL7 v2.5.1 | `johns-creek-hospital-b` | `johns-creek-hospital-b-hl7-v2` | `JOHNSCREEKB` |

医院 A/B 是稳定的**模拟机构**身份，不能冒充真实医院机构注册 ID；Synthea 合成属性由来源与对应 Contract 负责，不靠 `demo-` 前缀做业务分类。

## 改动源码边界和硬门禁

- [Healthcare PR #490](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/490) 合并 Main SHA `b033d7b8fd8cf752de7e64b240ea3dc83ce1fe7d`。两个医院 JSON Profile、`oie/build_channel.py`（含 HL7 assigning authority）、FHIR/HL7/Publisher 单元测试与 Source Handoff、Schema `hospital-profile-v1.schema.json`、`blob-publish-plan-v1.schema.json` 同步新身份。
- `hospital_profiles.validate_profile` 与 `blob_publish_contract.verified_plan` **运行时拒绝** `demo-` 开头的 Hospital/Feed ID；在 Azure SDK 实例化和写 Blob 之前即可 fail-closed；正负单元测试通过。
- GHCR 发布 CI 持久检测维护中的 `apps/clinical_producers`、`tests/clinical_producers`、`tests/synthea_new_generator`、`config/synthea-new-generator` 和 Workflow 是否再出现早期两医院 ID / 旧 HL7 Authority。历史 OpenSpec Evidence 不在代码扫描范围中，防止不诚实地篡改验收记录。
- [独立 OIE 4.7 CI Run #40225717610](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40225717610) **SUCCESS**。以前这项测试通过固定的旧 FHIR 事件包验收，产生与新 Channel 的不兼容；现改为 CI 即时产生新的 Johns Creek FHIR、校验 Source Manifest/Event SHA，然后在临时 OIE 中进行 FHIR IMP/AMB→HL7 ADT A01 转换、persisted readback、Skip 与重试测试；没有重放共享 `dw-oie` 的既有 32 条历史消息，失败原始 Run `#40225252968` 仍保留为真实排障记录。
- [Healthcare Publisher Release Run #40225880536](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/40225880536) **SUCCESS**，Main SHA-only Clean Build、非 root/no-network Smoke、GHCR 写入、独立 Image Digest：`ghcr.io/johnzhang-dataforge/healthcare-azure-blob-publisher@sha256:a92d06610813a38d3d9707133038f503f1f49b1d76a4144bc2500bded321e3da`。未修改 `latest`，旧 Publisher Digest `sha256:06324ae...` 不应再用于新医院身份的 E2E。
- [Self-Runner PR #297](https://github.com/JohnZhang-DataForge/Self-Runner/pull/297) 合并 Main `6b1ac1849b5277f647abdedd7f4ee77f526bffbb`：手工 Atlanta E2E 的独立 Source 审计、Blob Key、Manifest/GET、重试验证统一使用 Hospital A 身份；只读预检绑定新 Healthcare SHA 和新 Publisher Digest。此前 Self Runner 脚本独立 GET 的 HTTP ETag header 大小写也已修复。
- [Self-Runner PR Hosted Run #40226017942](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226017942) **SUCCESS**：Python 编译、两个 K8s 模板离线渲染、稳定 Hospital A 和新 Publisher Digest 静态断言；没有集群/Azure 写入。

## 最新真实只读运行环境

[Self-Runner Main Run #40226055238](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40226055238) **SUCCESS**：

- `worker01` Ready；`dw-synthea/synthea-new-generator-state` Bound、RWO、`synthea-local`；全集群 Active Jobs=0（仅 Run 当时快照）。
- `dw-synthea/azure-blob-publisher-identity` 原 Secret 存在、Opaque、`tenant-id/client-id/client-secret` 三个 Key 均非空；**没有输出值**。
- Atlanta Profile 身份与 FHIR DIRECT 模式通过；Profile JSON ConfigMap 仍为 0（未来由有权限的受控 E2E 按已冻结源配置创建）。
- `K8S_MUTATIONS=NO`、`AZURE_BLOB_WRITES=NO`。没有创建工作负载或云端对象。

## 后续受控验收

1. Atlanta 使用最新 Self-Runner Main 手工 `PUBLISH_ATLANTA`；前置检查并行 Session、worker01/PVC、ConfigMap、Secret、镜像 Digest 和云端 Prefix。仅对**全新 Request** Azure PUT，独立 GET/HEAD/SHA/ETag/Manifest，验证幂等和负向保护后才可以将 3.1/4.2 勾选。尚未触发。
2. Johns Creek 真实 `dw-oie/oie-debug` 既有 Channel **不会**因为源码重命名自动更新。要先只读审计实际安装的 Channel 配置与已验收消息，再走单独受控新 Channel/配置、Scope/CA/User 与**新的** FHIR 请求做 HL7 E2E。禁止重放过去的 32 条、盲目更新已有 OIE Derby/Channel。
3. 旧 Hospital ID 相关历史资料、已生成的源文件和原始 CI Run 只读保留，不能为了“改干净”伪造过往事件；将新医院 ID 视为新不可变业务身份，不对旧 Request 做就地 rename/overwrite。

**Task 3.4 = CODE / CI / GHCR / READONLY ACCEPTED；Tasks 3.1、3.2、4.2、4.7 的真实业务 E2E/轮换范围继续 OPEN。**
