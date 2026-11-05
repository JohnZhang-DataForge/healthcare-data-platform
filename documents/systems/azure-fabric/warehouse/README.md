---
status: active
scope: azure-fabric-warehouse-component
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

# Fabric OMOP Warehouse — 组件职责与文档导航

当前 Warehouse 为 Fabric Workspace `healthcare-omop` 的实际 **Workspace-only** Item `dw-omop-5.4`（GUID `7a6d08da-278d-4603-8a3b-28640110984c`）。Git 中没有、也不得伪造 `*.Warehouse/` Native Item 目录。DDL/Identity Schema 资产归 `azure-fabric/deployment/warehouse/`，Writer/Identity 业务 Python 仍归 `azure-fabric/warehouse/omop-foundation/writer/`。完整导航由 [CODE.md](CODE.md) 管理。

## 当前已实证与未完成边界

- **F0 CDM 5.4**：39 张基表、432 个字段的 Warehouse schema 部署并独立读回 [Run #41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578)。
- **F1 Vocabulary**：九表 28,703,753 行及来源对账 [Run #41770643994](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41770643994)；仍需 Source Release/License/CPT4 审核。
- **F1 管理表**：五张管理表创建/Schema 读回 [Run #41820260817](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41820260817)；验收时为空。
- **F2 Transaction**：受控合成六表同事务写入后显式 ROLLBACK，独立 SQL 连接读回零行 [Run #41824079608](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41824079608)。这是回滚演练，**不是临床 Gold COMMIT**。

## 独有技术合同（唯一详细入口）

- [CDM 5.4 DDL / Vocabulary](CDM54-SCHEMA-AND-VOCABULARY.md)：上游固定 SQL Blob、转换规则、39/432、F0/F1 证据及未完成的标准词表审计。
- [F1 Identity / Audit schema](IDENTITY-AND-AUDIT-SCHEMA.md)：五张管理表、全 Warehouse INT allocator、Source Key、Ledger、版本/许可审计。
- [F2 Writer Preview → Commit](WRITER-PREVIEW-TO-COMMIT.md)：可重复性、Hospital Scope、唯一 Writer、事务、读回与 Replay/HOLD；当前 SOURCE_ONLY。
- [ID Allocation State Machine](ID-ALLOCATION-STATE-MACHINE.md)：显式 Single-Writer Fence、INT 上限、Snapshot Isolation、丢失 Commit ACK 时的独立读回。

所有实际 Warehouse 写入、容量启动、Connection 或临床数据处理均需独立业务 OpenSpec 与授权；整理 Markdown 不授予执行权限。
