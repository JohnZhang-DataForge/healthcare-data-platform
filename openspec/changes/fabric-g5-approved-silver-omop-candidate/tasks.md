# Tasks — G5

## 1. Scope / contract

- [x] 1.1 只读核对双仓当前 main、原生 Pipeline HALT、G4 物理 Silver Approval/Quarantine 与唯一 Shared Engine 的实际缺口（2026-11-03；本 Change 起始基线记录在 design.md）。
- [x] 1.2 建立独立 G5 Proposal/Design/Tasks；冻结 G4 原始两个 Request、分离 Candidate/Gold/WORM，定义 IdMap 不自动分配原则。
- [ ] 1.3 检查共享资源 Active Runs 与有效 Fabric Native Pipeline 定义，确认云端修改和执行窗口。

## 2. Pure Shared Candidate

- [x] 2.1 从既有 Local Mapper 抽离唯一无 I/O 的 OMOP Person/Visit Candidate DataFrame 逻辑；稳定 ID Map、Concept Profile、原始 v1/v5.4 Contract 由调用者验证/注入；Candidate-only，不改变 Local Writer。
- [ ] 2.2 正负向单测：已验证合成 P1/E2、G4 P99/Q26 Approval-denied、跨医院 FK、重复/缺失 ID、未知 Concept、重放一致性；待增加完整 P100/E5918 fixture/映射 Profile 实测，不生成假临床值。
- [ ] 2.3 更新 Shared CODE-map、边界 CI 与 Wheel 版本；单独构建固定 hash 的新 Wheel，Published Environment 读回后才能进行真正 Fabric import。

## 3. Fabric Candidate and Pipeline

- [ ] 3.1 原生 Notebook 保留 HALT 与 Fabric cell 格式，增加 approved Silver 真正独立读回入口；要求精确批次 SHA/processing/Approval，不触碰已通过 G4 数据。
- [ ] 3.2 Candidate-only 物理 Delta 首次写入、独立完整重读、Approval-last fence、异常/HOLD 与 replay SKIP；不冒充 OMOP Gold。
- [ ] 3.3 原生 pl_fhir_ingest 编排 fail-closed read-only → Candidate；无 schedule、retry=0、默认 HALT；Pipeline SUCCESS 不代替 Candidate 读回。
- [ ] 3.4 Native + Notebook + Pipeline 代码/参数的离线 CI/安全负向测试 PASS，并完成云端真实 definition 独立读回。

## 4. Live E2E / closure

- [ ] 4.1 真正 Fabric Notebook Spark 原始 G4 P100/E5918 的 Silver fence→Candidate 执行，记录完整 Job UUID、精确物理路径/行数、readback。
- [ ] 4.2 真正 Fabric Pipeline Run、独立读回及同 Request Replay SKIP；容量建立 Spark Session 前的失败单独记录，POST uncertain ACK 先 GET。
- [ ] 4.3 检查 PR Required CI / 目标 SHA 后合并 main，准确写入实际 Run/Artifacts，不提前核销未实机验证的 Task。
- [ ] 4.4 Gold Warehouse 单事务与 Azure WORM / Blob 漂移 / 真实网络 ACK 均作为独立后续验收；不把本 Change Candidate PASS 标为 Gold COMMITTED。

## 2026-11-03 G5 Shared Engine candidate offline evidence (NOT Fabric deployment)

- [PR #629](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/629) on feature branch; Python 3.11 + PySpark 3.5.7 synthetic **23/23 PASS**, independent built Wheel 0.1.2 reproducible byte comparison and isolated package import PASS; Python 3.13 + PySpark 4.1.1 added G5 Candidate **8/8 PASS**, installed Wheel 0.1.2 import PASS.
- [GitHub Actions Shared Engine Wheel Offline Validation #41619656145](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41619656145), exact source head `b11be171d787abd73f40e2540a87d65fe87b78b6`, both jobs SUCCESS. Earlier #41619502401 Python3.13 workflow failed due literal shell `\\n` between commands; fixed in `b11be171...`; original failure not a candidate mapper failure and remains historical.
- Verified tests use a synthetic-only profile, not a reviewed live FHIR→OMOP clinical Concept profile. Real Fabric environment is **still Wheel 0.1.1**, Notebook/PL default HALT and Candidate physical Write/Readback NOT_RUN. This OpenSpec change remains ACTIVE and unchecked tasks MUST NOT be inferred PASS by main merge.
