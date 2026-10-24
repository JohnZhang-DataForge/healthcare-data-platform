# Tasks — Independent synthea_new_generator

> **状态：ACTIVE / SPEC FIRST。** 当前只创建 OpenSpec，不声明 Python、K8s、FHIR→OIE、Azure Blob 或 Fabric 已完成。原 `apps/synthea/new_only/` 及 OMOP 链路绝不因本 Change 改写。

## 1. P0 — OpenSpec design and baseline

- [x] 1.1 只读核对当前 Healthcare Main、旧 `generate_new_only.py`、Synthea 基础镜像、旧 S3 发布合同与 OpenSpec/命名/CODE Map 治理；明确旧 NEW_ONLY 不动。
- [x] 1.2 建立本独立 Change 的 Proposal、Design、Delta Spec、Tasks；冻结 `synthea_new_generator` 参数化/本地生成接口、Atlanta/Johns Creek 两 Profile 和下游 OIE 边界。
- [ ] 1.3 本 OpenSpec PR 在精确 Head 上通过 Strict Validation、Trusted Change Gate、文档链接等适用检查；合并后核对 Main 与 PR/CI 证据。**仅规划成功，不等于业务实现。**

## 2. P1 — Request and frozen-generation core

- [x] 2.1 定义 `contracts/synthea/new-generator/` 的 request-v1 / generation-manifest-v1 JSON Schema；验证 request_id、mode、人口、州/城市、日期/Seed、输出格式、路径、版本与 fingerprint。
- [x] 2.2 新增 `apps/synthea/synthea_new_generator/` 的统一 CLI、参数解析与 Synthea v3.3.0 CLI argument builder；仅 NEW_ONLY，CSV、FHIR 或两者可选。
- [x] 2.3 实现独立持久请求冻结、本地隔离临时输出、完整文件核验、Manifest-last 和失败/重试逻辑，禁止同请求参数漂移及静默覆盖。
- [x] 2.4 单元/合同负向测试：非法值、模式拒绝、重试、SHA 篡改、半成品、不同请求/并发隔离和无外部云/数据库调用。

## 3. P2 — Real Synthea formats and hospital profiles

- [ ] 3.1 使用固定 Synthea 版本实际运行 CSV-only、FHIR_R4-only、CSV+FHIR，核验 Bundle/Patient/Encounter/Reference、真实文件清单与计数；记录不支持的 Synthea 参数或输出差异。
- [ ] 3.2 为 Atlanta/FHIR 和 Johns Creek/HL7 两个**独立生成请求**建立外部配置 Profile，均从 FHIR R4 起步；运行验证 Georgia Atlanta/Johns Creek 地理参数，不暗中回退州/城市。
- [ ] 3.3 验证不同医院 Profile/请求重试互不影响，新医院 Profile 不要求修改 Generator 代码；保持医院/Feed ID 与文件交付元数据由外部组件管理。

## 4. P3 — Package and isolated Kubernetes jobs

- [ ] 4.1 建 `images/synthea-new-generator/`，引用固定 Synthea parent digest/commit；只安装最小 Runtime 依赖，无 OIE/Azure/PG 客户端或 Credential。
- [ ] 4.2 建 `kubernetes/manifests/synthea/new-generator/` 独立 Job/存储配置、最小权限、资源限制、显式镜像 Digest；不动 `synthea-new-only-state` 和旧 NEW_ONLY 工作负载。
- [ ] 4.3 按仓库强制源码地图规则同步 `documents/systems/data-platform/synthea/CODE.md`、相关组件文档和适用 CI；绑定真实 PR Head、镜像构建/测试证据。
- [ ] 4.4 经授权和资源协调运行最小真实 K8s Job，核对输出 Manifest/Hash/Count、错误路径及同请求重跑零漂移；未做实机则保持未验证。

## 5. P4 — Handoff and finish

- [ ] 5.1 定义 Producer 本地完成状态与 FHIR 下游读入合同；验证 FHIR Generator 本身不依赖 OIE、Blob Publisher、Fabric。
- [ ] 5.2 与后续 FHIR→OIE PoC Change 约定实际 FHIR Bundle 输入与 ADT 事件映射验收，真实转换未证实前不宣称 HL7 生成成功。
- [ ] 5.3 由独立 Change 更新现有多来源总体设计中已过时的共享 Cohort/三医院叙述、建设 FHIR/HL7 Publisher/Fabric；在本 Change 仅记录其新生成器边界被覆盖，不伪造上下游运行状态。
- [ ] 5.4 全部代码、适用测试、实际运行证据和最终 Main 验证完成后，才考虑同步 Current Spec / Archive。

**执行规范**：后续每个实施 PR 在 PR Body 单独声明 `OpenSpec-Change: implement-synthea-new-generator` 与真实 `OpenSpec-Task: n.n`，且同 PR 更新本 `tasks.md`。静态/本地测试无需写共享 K8s；对共享环境操作必须先读 Safe Operations / Session Coordination 并取得相应明确授权。


### P1 实施记录（本 PR）

- 已实现源文件：`apps/synthea/synthea_new_generator/{request,generator,entrypoint}.py`，v1 JSON Schemas、本地 Manifest/冻结/幂等安全检查及 Stub/负向单测。
- 新增仅 CPU 的 PR 工作流 `.github/workflows/synthea-new-generator-unit.yml`；此处不依赖真实 Java Synthea、Kubernetes、Azure/OIE/Fabric。
- P1 的 `2.1–2.4` 已覆盖源码、Mock/负向/并发单测；本 PR 最终 HEAD 的 CI 结论另以实际 Run 校验，不将 Stub 执行视作真实 Synthea/JAR、FHIR Bundle、州/城市匹配或镜像/K8s 的验证。P2/P3 仍保持未完成。
