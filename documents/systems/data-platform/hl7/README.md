# HL7 Raw Intake → local Delta staging → dbt Canonical Candidate

**状态：正式 Healthcare 源码开发中；离线可执行，不等于 Azure 真实 HL7 已被本 Adapter 消费。**

## 已确定的执行链路
```text
HL7 v2.5.1 A01/A03 Raw + Manifest (Azure immutable Landing)
  → 经过独立授权的只读下载/提供本地原始字节（暂未接入）
  → Python hl7apy Parser + Manifest/Raw SHA/Source/Clinical Gate
  → Spark local Delta table hl7_staging.hl7_events
  → dbt Core + dbt-fabricspark method=session (local Spark)
  → hl7_candidate.canonical_patient / canonical_encounter local Delta
  → [未来] Shared Contract/DQ/Approval/Single Silver Publisher
  → 统一 Canonical Silver Delta → Shared OMOP Mapper/Identity/Gold
```

**重要：** Parser 只把 HL7 转换为**结构化字段/数据行**，不是转换成 FHIR。历史 Self-Runner 实验曾为了使用 `dbt seed` 在 Parser 后生成 CSV；这是测试用输入方式，不是生产必须的中间数据格式。正式路线已改为本地物理 Delta staging + dbt `source()`。本地计算不消耗 Fabric Spark CU，但经批准写 Fabric Silver 仍需使用 Capacity 与共享 Writer。

## 运行范围与隔离
- 当前只认实际已审核的 Johns Creek Hospital B OIE V2 `JOHNSCREEKB`、MSH-10、A01/A03 和 CDCREC OMB Code/Display 范围，不臆造医学值。来源 Manifest、所有对象 SHA/大小/医院身份必须完全一致，缺 A03 的 completed Encounter HOLD。
- `write_staging_delta.py` 仅从**调用方已合法取得的本地 Raw HL7**读取，不做 Azure GET/OIE POST；目标只接受本地 `file:` warehouse URI。已有相同 Delta 数据重跑 SKIP，不同内容 HOLD。
- 运行时按已有 POC 固定 Python 3.11、Java 17、Spark 3.5.5、Delta 3.3.2、hl7apy 1.3.5、dbt-fabricspark 1.13.2；这不代表 Fabric Spark 4.1 兼容性已被确认。
- `.github/workflows/hl7-local-delta-dbt-offline.yml` 只在 GitHub-hosted Runner 上使用真实 OIE JS Mapper **生成全新合成样例**，然后本地物理 Delta/dbt/Contract readback。不会使用 2026-11-07 P3 Azure 的 42 条已提交数据。
- 未来真实 Raw GET、共享 Approval/Publisher/Silver 需要对应 OpenSpec 和精确权限审批，不能直接复用本地配置写 Fabric。

本组件的源码和测试唯一导航：[HL7 CODE](CODE.md)。OpenSpec 实施计划：[implement-hl7-local-delta-dbt-canonical](../../../../openspec/changes/implement-hl7-local-delta-dbt-canonical/tasks.md)。
