# Tasks — Operational OIE HL7 v2.5.1 ADT source

> 目标是 **可真实运行且消息语义正确的医院 HL7 Producer/Feed**，不是声称实现 HL7 所有子协议。当前仅旧 OIE A01 Channel 的实机历史证明；A03 / Raw Blob / MLLP / Fabric HL7 均尚未验收。每项任务以 SHA + CI/Run + 独立读回判定；不因用户说“继续”而绕过 SAFE-OPERATIONS 的实际资源写入审核。

## Phase 0 — 设计与维护既有事实
- [x] 0.1 只读核对 Main OIE 4.7.0 Channel、FHIR→ADT^A01、已有 OIE Derby/PVC 及 Writer=none、Legacy 历史实机证据。
- [x] 0.2 核对 Canonical Patient/Encounter v1 必填信息、Self-Runner dbt POC 和隔离边界，规定 A01/A03 原始 HL7 → dbt → ONE Silver。
- [ ] 0.3 合并 docs/spec-only 提案 PR，严格不部署、不执行 OIE/Blob/Fabric。

## Phase 1 — OIE ADT Producer 可操作语义（offline first）
- [ ] 1.1 评审源 Patient FHIR Profile；实现 PID-7 DOB、PID-8 gender、PID-10 Race、PID-22 Ethnicity 的真实字段映射及缺失/未知/编码系统 Fail-Closed，保留独立 Stable Identity。
- [ ] 1.2 完成 versioned `ADT^A01` + `ADT^A03` 业务生成、明确时序及 `PV1-44/45`；现有已部署 A01 Channel ID/字节行为保持不动。
- [ ] 1.3 新测试 `.github/quality/tests/data-platform/clinical-producers/oie/` 覆盖历史完整、in-progress A01-only、编码缺失、重复/冲突、负时间、时区和转义，并通过实际 Node/HL7 parser 交叉校验。
- [ ] 1.4 对应更新系统 CODE owner、人类 OIE 文档与本 Change tasks；合并经 CI 验证的正式离线源码 PR。

## Phase 2 — Channel、原始传输、Blob（尚未授权实机）
- [ ] 2.1 构建 versioned OIE 多事件单消息控制 Channel/Router（新 Channel ID；禁止覆盖现有），独立导出/import 校验及内存队列/持久化策略。
- [ ] 2.2 设计 OIE 真实 HL7 raw bytes 出口及 Publisher（manifest-last、SHA256、独立远端 GET、source/proc/publication identities、replay/冲突 HOLD）；与现有 Azure Publisher 主线复用，禁止新造平行 Source Authority。
- [ ] 2.3 对 OIE persistent state / Session Coordination / 新 Batch 进行只读审计与显式有副作用操作审批，之后才允许真正 Channel 导入、Blob PUT、K8s 工作负载操作。
- [ ] 2.4 真正 OIE A01/A03→raw HL7 Blob 的完整实机验收及独立读回；禁止旧完成 Batch 重放。

## Phase 3 — 增强的医院接口能力（独立验收）
- [ ] 3.1 评审 A08 Patient/Encounter update 事件类型与生命周期，规划更新版本/Replay/HL7 profile。
- [ ] 3.2 评审并实现内部限定 MLLP/ACK/NAK 接口，用隔离地址检查 AA/AE/AR、重试/未知 ACK 和权限；非公开暴露；未运行不能标记为“支持”。
- [ ] 3.3 复核 HELD/QUARANTINE 统计、存储保留/重启恢复、事务证据与 Lineage；如需授权真实运行单独评估。

## Separate product handoff
- [ ] H.1 HL7 open-source Parser+dbt source-specific Candidate → One Canonical Silver Publisher 与 FHIR 汇合；dbt backend (DuckDB/Local Spark/remote Fabric) 选型保持 **PENDING**，此 Change 不实现 OMOP Mapper 或写正式 Silver。
- [ ] H.2 完整上线验收前必须有正反向、故障注入、来源合成、独立 OIE 消息和远端 Blob readback 证据；不因 Phase 1 完成就宣称 E2E 成功。
