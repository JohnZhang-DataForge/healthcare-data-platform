# Tasks — Fabric OMOP Foundation

## F0 — Warehouse inventory and connection

- [x] 0.1 用户创建现有 Warehouse `dw-omop-5.4` 并提供 SQL Endpoint（用户提供，尚未以 REST 独立读回）。
- [x] 0.2 创建独立 OpenSpec Proposal / Design / Delta Spec / Tasks，冻结与 G5 和 Local DP 的边界。
- [x] 0.3 Self-Runner 已完成受信任 main OIDC REST + SQL SELECT 只读探针，含离线正反测试；PR #483/#484 已合并，静态 CI PASS。
- [x] 0.4 **真实只读连接 PASS**：Self-Runner [Run #41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691) 完整 SUCCESS，目标 Controller SHA `ef9a0ef224c09a037452e3a9e016a0baf62431e9`；自建 `dw-runner-set` 以 OIDC 执行 Fabric REST 可见性读回；独立托管 Ubuntu 使用相同 Entra SP / ODBC Driver 18 / SQL Audience 执行固定 `SELECT DB_NAME(), CURRENT_USER, 1`。真实 Warehouse Item ID `7a6d08da-278d-4603-8a3b-28640110984c`，`DB_NAME()=dw-omop-5.4`，`SQL_SELECT_PASS=TRUE`。没有运行 DDL/DML/Capacity 操作。
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

## F0 real execution evidence — 2026-11-03

- [Healthcare OpenSpec PR #632](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/632) merged SHA `99d71e3966bc05183683be5b8637fcb2561f77ec`. OpenSpec validation, Change Gate and link CI PASS; unrelated Workers preview failure was not interpreted as F0 acceptance.
- [Self-Runner probe PR #483](https://github.com/JohnZhang-DataForge/Self-Runner/pull/483) merged SHA `a72932e3f0044e58ae5f08cec94fa35fe8cdd9fe`. First [Run #41645029049](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645029049) **FAIL** before REST/SQL due `python3 -m pip` unavailable on self-hosted Runner; Warehouse SQL auth was not yet tested. Original failure preserved.
- [Self-Runner fix PR #484](https://github.com/JohnZhang-DataForge/Self-Runner/pull/484) merged SHA `ef9a0ef224c09a037452e3a9e016a0baf62431e9`. Two-stage job: no-pip self-hosted REST + ephemeral hosted ODBC SQL SELECT. [Run #41645575691](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41645575691) completed **SUCCESS**: offline unit tests PASS; REST `FABRIC_WAREHOUSE_REST_VISIBLE=PASS` for exact Warehouse GUID; SQL encrypted TDS `SQL_SELECT_PASS=TRUE`, target DB match, authenticated SP observed. Logs contain no OMOP business rows.
- **Bounded PASS**: Workspace item visibility + SQL connectivity only. **NOT_YET_DONE**: official CDM 5.4 SQL Project, DDL deployment, schema physical readback, Vocabulary, Identity Map, Writer and Gold transactions. These remain explicit tasks 0.5/0.6, F1/F2/F3.
