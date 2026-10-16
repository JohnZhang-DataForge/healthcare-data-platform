# TASK004 STEP04E — Person / Visit 联合数据库对账验收

**状态：STEP04E READ-ONLY JOINT RECONCILIATION PASS。固定批次的数据已验证，Airflow 端到端 DAG 仍待接入。**

## 执行证据
- [Self-Runner 38394192928](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38394192928)：SUCCESS，固定 Healthcare SHA `eee54b8bb5ff22d7344b2a9600f258f0bdf70fe2`，单元测试、Kubernetes PostgreSQL 的真实只读事务、独立 count/业务字段/外键验证。
- 首轮 [38394078883](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38394078883) 的 SQL 验证值**全部符合预期**，失败原因为从上一工作流复用的无关 `grep -q 'on'` 标记；修正后第二轮 SUCCESS，实际对账门禁不变。
- 数据源/写库前提：Person [38390404434](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38390404434)、Visit [38393486251](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38393486251) 实际 PostgreSQL COMMIT 和同批次 replay 已验收。

## 同批次 PostgreSQL Readback（2026-10-13）

| 指标 | 实测 | 门禁 |
|---|---:|---|
| Immutable batch Manifest SHA / ledger identity | 1 | PASS |
| Person VERIFIED commit checkpoint | 1 | PASS |
| Visit VERIFIED commit checkpoint | 1 | PASS |
| `cdm.person` | 136 | PASS |
| `cdm.visit_occurrence` | 9391 | PASS |
| Person ID map (synthea) | 136 | PASS |
| Visit ID map (synthea) | 9391 | PASS |
| Batch-scoped Person stage | 23 | PASS |
| Batch-scoped Visit stage | 3592 | PASS |
| **Person Stage→Map→CDM exact full field equality** | **23** | PASS |
| **Visit Stage→Map→CDM exact full field equality + Person FK** | **3592** | PASS |
| Orphan Visit FK | 0 | PASS |
| Person / Visit duplicate ID map business keys | 0 / 0 | PASS |
| Person / Visit ID map without CDM target | 0 / 0 | PASS |
| Other (non-batch) Person maps | **113** | PASS |
| Other (non-batch) Visit maps | **5799** | PASS |

All SQL executed inside `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`. No PostgreSQL writes, no Airflow DAG triggered, no S3 mutation. `JOINT_BATCH_RECONCILIATION=PASS`.

## 保留的验收边界
- 本次联合对账将当前批次的 `canonical_payload` 全字段重建后和 CDM 逐行完整比对，**不是简单只比数量**。因此当前 23 Person 和 3592 Visit 的全部业务字段比对 PASS。
- 历史非批次 Mapping 数量为 113/5799，孤儿与重复键为 0；但没有写前冻结的全量历史字段哈希，因此不能宣称历史全部内容已做字节级前后对比。
- 未执行整条 Airflow DAG 的重放、失败恢复、并发测试。数据库固定批次 replay 已分别在 STEP04C/D 完成，不等同 DAG-level replay。
- STEP04F 必须把受限事务性 Person/Visit Loader 编排进 DAG，先后顺序严格保持 Person→Visit→Joint Readback；锁定 immutable batch/manifest 和 Processing URI；测试失败不得触发下游表变更。
- STEP04G 必须验证同批次 DAG replay NO-OP、未知 COMMIT 恢复及失败注入；TASK005 仍 ON HOLD。

**STEP04E CLOSED / STEP04F NEXT。**
