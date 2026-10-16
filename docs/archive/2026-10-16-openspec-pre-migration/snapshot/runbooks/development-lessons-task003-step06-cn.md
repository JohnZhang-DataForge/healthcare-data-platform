# TASK-003 STEP06 开发经验

> 来源：TASK003 Visit ID allocation 与 `cdm.visit_occurrence` materialization 的真实开发和恢复过程。
> 建议路径：`docs/runbooks/development-lessons-task003-step06-cn.md`

---

## 1. ID allocation 与 CDM materialization 必须分开

TASK003 最终明确：

```text
Processed Candidate
  ↓
Visit ID allocation
  ↓
authoritative mapping
  ↓
Candidate + mapping
  ↓
CDM materialization
```

ID 分配本身不能顺便写 `cdm.visit_occurrence`。

这样可以分别验证：

- business key；
- stable ID；
- sequence；
- target row shape。

---

## 2. Identity 列显式插入需要正确语义

第一次正式 Visit ID allocation 因目标列：

```text
GENERATED ALWAYS AS IDENTITY
```

拒绝显式 ID。

正确语法：

```sql
OVERRIDING SYSTEM VALUE
```

旧 mutation 不允许盲目重跑。

---

## 3. Sequence gap 是合法状态

失败事务里第一次 `nextval()` 已消费 ID 1。

表 mutation rollback，但 sequence 没回滚。

最终：

```text
Visit IDs = 2..5800
Sequence = 5800|true
```

ID 1 gap 永久保留。

原则：

```text
稳定
唯一
可追溯
```

比：

```text
连续无洞
```

更重要。

---

## 4. 禁止自动 rewind sequence

一旦 sequence state 与真实历史一致：

```text
不要 setval 回旧值
不要为了“好看”补 gap
```

否则可能造成未来重复 ID 或破坏历史。

---

## 5. `COLUMNS` 是危险 Shell 变量名

Schema discovery 中使用了：

```text
COLUMNS
```

结果与终端宽度冲突。

以后使用：

```text
TARGET_COLUMNS_FILE
SCHEMA_COLUMNS_FILE
```

避免 shell 内建名称。

---

## 6. Pipe + `python3 -` + heredoc 冲突

以下形式错误：

```bash
producer | python3 - <<'PY'
...
PY
```

因为 Python source 和 producer data 都想使用 stdin。

以后使用临时文件或显式文件参数。

---

## 7. Spark driver log 不是可靠数据通道

CDM payload 最初通过日志 marker 抽取。

一条 Log4j 记录混入 payload 区域导致解析失败。

真正 Spark workload 已成功。

恢复方式是：

```text
复用已有 Driver log
按明确 payload prefix 过滤
重新校验 row count + SHA
不重跑 Spark
```

以后结构化 artifact 应尽量直接写文件 / S3。

---

## 8. PostgreSQL boolean 表示必须 canonicalize

脚本期待：

```text
5800|t
```

实际输出：

```text
5800|true
```

数据库正确，但 wrapper 误判。

以后 SQL 输出统一 canonical representation。

---

## 9. `grep -F '^COMMIT$'` 是错误组合

`-F` 不支持 regex anchor。

应使用：

```bash
grep -xF 'COMMIT'
```

或者：

```bash
grep -E '^COMMIT$'
```

---

## 10. COMMIT uncertainty 绝对不能 blind retry

真实 materialization 已经：

```text
INSERT 5799
COMMIT
```

但 Bash classifier 因 boolean 格式问题报告 ambiguity。

如果此时重新执行 INSERT，会造成真实业务事故。

恢复原则：

```text
停止 mutation
↓
独立 read-only reconciliation
↓
核对 target / map / person / sequence / SHA
↓
确认 commit state
```

TASK003 最终确认真实 mutation 已成功。

---

## 11. Rehearsal 对高风险数据库写入非常重要

最终 CDM materialization 之前：

```text
TEMP stage
typed load
validation
INSERT SELECT
ROLLBACK
```

先 rehearsal。

确认：

- 5799 rows；
- ID 2..5800；
- schema compatible；
- FK valid；
- sequence 不变化。

之后才执行 real mutation。

---

## 12. payload 必须先冻结

真实写库不能边算数据边写。

TASK003 先冻结：

```text
5799 x 17 typed payload
SHA256
mode 0444
```

之后 rehearsal 和 real materialization 都使用同一个 frozen payload。

这样才能证明：

```text
演练的数据
=
正式写入的数据
```

---

## 13. Independent reconciliation 必须与 mutation wrapper 分离

正式 mutation 完成后，不直接信任同一个脚本自己的结论。

使用全新的 read-only reconciliation：

- CDM rows；
- unique IDs；
- map rows；
- person rows；
- sequence；
- mapping SHA；
- row-shape SHA；
- FK missing counts。

这样能发现 wrapper 逻辑错误。

---

## 14. 最终冻结需要 canonical verifier

TASK003 最后不是只保留“某次运行 PASS”。

而是生成：

```text
verify_committed_cdm_visit_materialization.py
result contract
tests
canonical verification runner
Git checkpoint
```

以后任何人都可以对历史 committed state 做 read-only 验证。

---

## 15. STEP06 的最大经验

数据库 mutation 必须遵循：

```text
preflight
↓
contract
↓
rehearsal
↓
single mutation
↓
independent reconciliation
↓
canonical freeze
```

并永久遵守：

```text
NO BLIND RETRY
```
