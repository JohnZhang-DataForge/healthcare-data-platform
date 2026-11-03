# Tasks — Fabric OMOP Foundation

## F0 — Warehouse inventory and connection

- [x] 0.1 用户创建现有 Warehouse `dw-omop-5.4` 并提供 SQL Endpoint（用户提供，尚未以 REST 独立读回）。
- [x] 0.2 创建独立 OpenSpec Proposal / Design / Delta Spec / Tasks，冻结与 G5 和 Local DP 的边界。
- [ ] 0.3 在 Self-Runner 单独实现主分支授权的 OIDC Fabric REST + Warehouse SQL SELECT 只读 probe，离线正反测试 PASS；关联对应 PR/Run。
- [ ] 0.4 真正 Self-Runner 运行：GET 精确 Warehouse item、SQL Token、SQL SELECT、DB_NAME/identity 读回 PASS；如失败记录明确信息与安全后续动作。**截至当前未运行**。
- [ ] 0.5 绑定官方 OHDSI CommonDataModel v5.4 版本、建立完整 Fabric SQL Project/迁移与静态校验，不用猜测 DDL。
- [ ] 0.6 经独立部署许可、冲突与 Capacity Gate 后首次创建正式 `cdm`、`etl` 等对象，独立 Schema 读回 PASS。

## F1 — Independent identity and vocabulary

- [ ] 1.1 设计 Fabric-only Identity Map、稳定分配策略、院区隔离、唯一键、并发与恢复语义。
- [ ] 1.2 导入有版本与校验的正式 Vocabulary；Concept/有效日期/域验证真实 PASS。

## F2 — Transactional Gold writer

- [ ] 2.1 实现 Warehouse Writer、Ledger 与原子事务；Person/Visit 真实插入、重放及负向校验。

## F3 — Approved G4 to Gold E2E

- [ ] 3.1 使用已批准的 G4 Silver Patient/Encounter，真实 100 Patient / 5,918 Encounter 输入执行并对账。
- [ ] 3.2 独立 SQL readback、DQ/FK/Replay PASS，最后再与 G5 Pipeline 明确集成。
