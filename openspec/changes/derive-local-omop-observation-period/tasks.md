# Tasks — Local OMOP Observation Period from synthetic EHR encounters

## P0 — Provenance and OHDSI rule

- [x] 0.1 重新核对 Healthcare/Self-Runner Main、并行 PR/Actions、现有 ATLAS3 Results 实体、PG17 物理 Person/Visit/OP 及 OHDSI CDM 5.4 规则。
- [x] 0.2 只读来源 Map/Stage/Batch/Manifest SHA 与历史差额预检：19 个 Task004 Ledger、18 个 Landing 精确匹配，当前 Stage 1281/194757、完整 Person/Visit ID Map 1394/200556；历史 pre-Stage 113/5799 与未匹配 Batch 23/3592 均明确告警，不假装补完。
- [x] 0.3 只读核实 `44814724`（Period covering healthcare encounters）有效，1,394 个人的 event-bounded 候选全合法，2 个跨度 <30 天；禁止把推断观察期当作保险覆盖或全部长期完备病史。
- [x] 0.4 本独立业务 Change 的 OpenSpec Spec/Tasks/Design 已经通过 4 项正式 CI 并合并 Healthcare [PR #894](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/894)、Main `ddff8069dea7f0b97bcd066b78b1c59f7defb0a9`；本轮仅规划、尚未执行 OP 写入。

## P1 — candidate/writer and tests

- [ ] 1.1 在已有 OMOP 组件目录建立唯一 SQL Candidate/Writer 合同，不重建 FHIR/HL7/CSV Mapper；测试起止日期、概念类型、空表默认停、重复/并发/PK/权限/日期漂移的拒绝边界。**源码候选已提交至** `local-data-platform/apps/omop_writer/observation_period_encounter_v1.sql` 与 `tests/omop_writer/test_observation_period_encounter_v1.py`，仅 PR CI 通过并合并后可勾选；无真实 DB 写入。
- [ ] 1.2 用独立 Self-Runner 仅执行 READ ONLY 候选值与 PG 角色边界审计，固定源计数 1394/200556、全部 ID 映射且观察期确实为0；不记录任何原始病人字段。

## P2 — protected live backup and rollback

- [ ] 2.1 精确单表 `cdm.observation_period` Blob 私有不可覆盖快照、独立 Azure GET SHA/PG restore-list，保留可恢复证据；不可把过期 CDM 全量快照当成今天的全量备份。
- [ ] 2.2 PostgreSQL transaction ROLLBACK 实机演练，所有 1,394 新行在同事务可检验，回滚后表仍0、Person/Visit 未变。

## P3 — one-shot commit + readback

- [ ] 3.1 仅在 G0/G1/G2 PASS 与无竞态时执行一次受控 COMMIT，唯一目标 `cdm.observation_period`，日后更改数据源需另设 Change。
- [ ] 3.2 独立 PG17 新会话只读核对 1,394 OP、1:1 Person、0 端点越界/重复/无效概念，CDM Person/Visit/Vocab 和 ATLAS Results 不变。
- [ ] 3.3 归档实际 Run/PR/Main、故障恢复与 Refresh Runbook；真实 Cohort Generation 仍归独立 ATLAS 消费者验收，不伪称此项已通过。

**安全规则：** 任何失败都 HOLD，不自动重放；OpenSpec 本身不是运行授权，必须有版本固定、备份、真实事务预演、明确的执行选项和独立读回。禁止没有范围审计的 DELETE/UPDATE/UPSERT/ALTER、禁止重新运行历史 ACHILLES Job。
