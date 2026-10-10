# Healthcare Data Platform 开发经验汇总

> 文件定位：项目开发期长期维护的经验总表。
> 语言：中文。
> 维护规则：各 TASK / STEP 的原始经验文档长期保留；其中具有普适价值的经验定期汇总到本文件。
> 建议仓库路径：`docs/runbooks/development-lessons-cn.md`

---

## 1. 文档维护规则

开发过程中，每个重要阶段可以产生独立经验文档：

```text
development-lessons-taskNNN-stepNN-cn.md
```

例如：

```text
development-lessons-task003-step04-cn.md
development-lessons-task003-step06-cn.md
```

这些阶段文档用于保留当时真实的问题、修复、恢复过程和上下文，不因为内容已经汇总到本文件就删除。

本文件：

```text
development-lessons-cn.md
```

负责定期提炼跨 TASK、跨 STEP 都适用的工程经验。

维护原则：

1. STEP 文档保留真实历史。
2. 本文件只吸收具有长期复用价值的规则。
3. 已过时规则应标明原因，不静默删除历史背景。
4. 真实运行结果优先于旧文档和聊天记录。
5. 本文件属于开发治理资料，不是生产运行依赖。

---

## 2. 开发节奏：一步一验

项目开发采用小步、可验证、可冻结的方式。

标准节奏：

```text
设计
  ↓
生成 / 修改 canonical source
  ↓
静态检查
  ↓
单元测试 / 负向测试
  ↓
在 runner01 真实执行
  ↓
验证真实结果
  ↓
失败 → 修当前 STEP → 重跑同一步
  ↓
PASS
  ↓
冻结
  ↓
Git checkpoint
  ↓
下一 STEP
```

核心原则：

- 一次只推进一个可验收的小步骤。
- 当前步骤失败时不跳到下一步。
- 已冻结 PASS 的步骤不因为后续失败而随意重做。
- 不以“脚本退出码为 0”代替真实验收。
- 必须根据实际数据、数据库、S3、Kubernetes 和日志状态判断。

---

## 3. 临时 Shell 与正式源码分离

开发时允许通过一个可直接粘贴执行的 Shell 来交付修改。

临时 Shell 放：

```text
/data/spark/temp_shell/
```

正式源码放 Git 项目：

```text
/data/spark/healthcare-data-platform/
```

临时 Shell 只是“安装器 / 修改器 / 修复器”。

真正需要进入 Git 的应是：

```text
*.py
*.sh
*.yaml
*.yml
*.sql
*.json contract
tests/*
docs/*
```

正式 Git 历史不能依赖：

```text
01b-fix-...
03c-repair-...
temporary installer
聊天记录中的补丁顺序
```

修复通过后，必须把最终正确逻辑写回 canonical source。

---

## 4. 大型 Markdown 不再通过超长 heredoc 交付

实际开发中已经出现过浏览器复制超长 Shell 时：

- heredoc 被截断；
- Markdown code fence 与外层 Shell code fence 相互干扰；
- Shell 进入 `>` 等待状态；
- 文档正文串入命令；
- 文件生成不完整。

因此以后大型文档采用：

```text
生成独立 .md 文件
    ↓
用户下载
    ↓
放到明确 repo 路径
    ↓
短验证 Shell 检查
    ↓
Git add / commit
```

不再把上千行 Markdown 包进聊天中的大型 heredoc。

---

## 5. Shell 安全规则

### 5.1 不在交互 Shell 直接执行 `set -Eeuo pipefail`

严格模式应放在子脚本中。

推荐：

```bash
cat > /data/spark/temp_shell/step.sh <<'SCRIPT'
#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi

set -Eeuo pipefail
...
SCRIPT

bash /data/spark/temp_shell/step.sh
```

这样避免用户把严格模式残留在当前交互 Shell。

### 5.2 每一步必须有完整输出边界

推荐：

```text
#### TASKxxx STEPxx OUTPUT BEGIN ####
...
EXIT_CODE=0
#### TASKxxx STEPxx OUTPUT END ####
```

通过 `EXIT trap` 确保失败时也能输出退出码和 END。

### 5.3 `bash -n` 只证明语法正确

它不能证明：

- 代码完整；
- heredoc 未被截断；
- 业务流程可执行；
- 运行结果正确。

仍需检查：

- 文件结构；
- 关键入口；
- 测试；
- 实际执行；
- 真实持久状态。

---

## 6. Bash 特殊变量冲突

TASK003 曾使用变量名：

```text
COLUMNS
```

它与 Bash / terminal 内建状态冲突，最终错误地产生了名为终端宽度的文件。

以后避免使用容易与 shell 内部冲突的通用变量。

推荐：

```text
TARGET_COLUMNS_FILE
SCHEMA_REPORT
COLUMN_METADATA
```

变量名应体现业务含义。

---

## 7. stdin 只能有一个来源

以下模式错误：

```bash
git show ... | python3 - <<'PY'
...
PY
```

`python3 -` 使用 stdin 读取 Python 源码；pipe 也试图向 stdin 提供数据，两者冲突。

以后使用：

- 临时文件；
- 文件名参数；
- 独立文件描述符；
- 环境变量。

不要让 Python 源码和业务输入同时争用 stdin。

---

## 8. `grep -F` 不处理正则锚点

错误示例：

```bash
grep -F '^COMMIT$'
```

`-F` 表示固定字符串，因此 `^` 和 `$` 不具有正则含义。

正确选择：

```bash
grep -xF 'COMMIT'
```

或：

```bash
grep -E '^COMMIT$'
```

固定字符串匹配和正则匹配不能混用。

---

## 9. 结构化数据不要依赖普通日志通道

TASK003 曾经从 Spark driver log 中提取 5799 行结构化 payload。

中间混入一条 Log4j 日志，导致外层 parser 误判失败，但 SparkApplication 本身已经成功。

以后：

1. 结构化输出增加唯一前缀。
2. 只过滤明确前缀。
3. 校验行数。
4. 校验 SHA256。
5. 更成熟阶段直接写受控 artifact，而不是从普通 application log 重建。

日志是日志，数据 artifact 是数据 artifact。

---

## 10. S3 空结果不能只认一种返回形式

TASK003 STEP04 遇到过合法空列表返回：

```json
{"RequestCharged": null}
```

没有：

```text
Contents
KeyCount
```

旧逻辑把缺少 `KeyCount` 判断为非法。

经验：

- 允许已确认的合法空形态；
- 明确拒绝真实非空；
- 明确拒绝错误类型；
- 网络 / 权限错误不能被 `|| true` 吞成空目录；
- 兼容不是“任意 JSON 都视为空”。

---

## 11. “数据写入完成”不等于“产品发布完成”

TASK003 STEP04 中曾出现：

```text
Parquet 已存在
DQ 尚未发布
manifest 尚未发布
```

这不是完整成功。

推荐发布边界：

```text
data 写入
  ↓
data readback
  ↓
DQ 发布
  ↓
DQ readback
  ↓
APPROVED manifest 最后发布
```

下游只能读取被批准 manifest 指向的数据。

以下都不能单独代表正式发布完成：

```text
目录存在
_SUCCESS 存在
Parquet 存在
Spark job COMPLETED
```

---

## 12. 恢复已有 run，禁止无意义重跑

当 wrapper 失败但下游持久状态可能已经存在时：

不要立即：

```text
删除目录
重新分配 run_id
重新跑 Spark
重新写数据库
```

先检查：

```text
已有 SparkApplication
driver logs
S3 object listing
DQ
manifest
数据库状态
runtime evidence
```

如果已有产物正确，优先恢复和继续。

TASK003 STEP04 已证明：

```text
existing run recovery
same-run replay
```

可以比盲目重跑安全得多。

---

## 13. 幂等必须通过重复执行证明

“代码看起来支持重跑”不等于幂等已经成立。

验收至少应该比较：

```text
第一次运行结果
第二次运行结果
对象数量
数据库数量
SHA256
stable ID
manifest
```

例如：

```text
same input + same logical identity
→ reuse verified object
```

不能变成：

```text
same input
→ duplicate rows
→ new IDs
→ silently overwrite
```

---

## 14. PostgreSQL Identity 与 Sequence

### 14.1 `GENERATED ALWAYS AS IDENTITY`

显式插入 identity 值时需要：

```sql
OVERRIDING SYSTEM VALUE
```

TASK003 第一次 Visit ID allocation 因缺少该语法而失败。

### 14.2 Sequence 不等同于事务表数据

事务回滚后：

```text
table rows rollback
```

但已经调用的：

```text
nextval()
```

可能已经消费 sequence。

因此 ID 1 被消费但未写入 mapping。

最终 Visit ID：

```text
2..5800
```

这是合法状态。

永久原则：

- 不自动 rewind sequence；
- 不追求 gapless surrogate ID；
- 只要求稳定、唯一、可追溯。

---

## 15. 数据库输出必须先规范化再比较

TASK003 中 PostgreSQL 输出：

```text
true
```

而 shell 逻辑期待：

```text
t
```

数据库已经正确 COMMIT，但 wrapper 误判。

以后 SQL 输出应规范化：

```sql
CASE
  WHEN is_called THEN 'true'
  ELSE 'false'
END
```

脚本比较 canonical representation，不比较客户端显示习惯。

---

## 16. Wrapper FAIL 不等于数据库 FAIL

最重要的数据库原则之一：

**客户端失败不能直接证明数据库没有提交。**

如果 COMMIT 状态不确定：

```text
禁止 blind retry
```

正确流程：

```text
停止 mutation
  ↓
开启全新 read-only session
  ↓
读取 authoritative persistent state
  ↓
核对 row count / mapping / SHA / sequence
  ↓
判断真实状态
```

TASK003 real materialization 就是通过 independent reconciliation 确认已经成功 COMMIT。

---

## 17. Mutation 必须分阶段

对于高风险持久 mutation：

```text
设计
  ↓
静态验证
  ↓
冻结输入 payload
  ↓
rehearsal
  ↓
real mutation
  ↓
independent reconciliation
  ↓
canonical verification
  ↓
Git freeze
```

不要把：

```text
设计 SQL
真实写库
验收
恢复
```

全部塞进一个无法观察的大步骤。

---

## 18. Runtime evidence 与 Git source 分离

Git 管理：

```text
实现
contracts
tests
docs
runbooks
canonical scripts
```

`runtime/` 管理：

```text
真实执行 report
snapshot
payload
Spark log
reconciliation
临时 evidence
```

原则：

> Git 说明系统应该如何工作。
> runtime 说明某一次真实执行发生了什么。

`runtime/` 默认不能进入 Git。

---

## 19. 失败资源不要立即清理

失败后应暂时保留：

- SparkApplication；
- Driver Pod；
- ConfigMap；
- logs；
- reports；
- payload；
- database snapshot。

原因：

```text
wrapper failed
≠
workload failed
```

过早删除会丢失恢复证据。

---

## 20. Reset 必须有明确边界

默认 reset 可以清：

```text
当前 STEP runtime work
临时 Pod / Job
cache
临时生成文件
```

默认不能清：

```text
历史 Landing
已发布 Raw
已发布 Processed
stable ID
OMOP CDM
Secrets
PVC/PV
namespace
bucket
Git source
```

持久删除必须使用：

- 明确参数；
- 明确目标；
- 明确验证。

---

## 21. Git checkpoint 规则

PASS 后 Git checkpoint 前：

1. 检查 `git status`。
2. 只 stage 预期文件。
3. 检查 staged inventory。
4. 保证 runtime 没进入 Git。
5. 执行：

```bash
git diff --cached --check
```

6. 再 commit。
7. push 后核对 remote HEAD。
8. 最终确认 clean worktree。

### EOF 规则

Markdown / source 文件结尾：

- 保留标准单个 newline；
- 不额外增加空白行；
- 不留 trailing whitespace。

避免：

```text
new blank line at EOF
```

---

## 22. Runtime truth 优先

以下都不能单独证明完成：

```text
文档说完成
YAML 已存在
kubectl apply 成功
脚本退出 0
Spark _SUCCESS
旧聊天说已经 PASS
```

真正完成依赖当前 STEP 定义的真实 evidence。

---

## 23. TASK003 的工程意义

TASK003 不只是做完：

```text
cdm.visit_occurrence = 5799
```

它建立了第一个完整 reference implementation：

```text
Source
  ↓
Canonical
  ↓
Raw
  ↓
Processed
  ↓
Stable ID
  ↓
CDM
  ↓
Reconciliation
```

后续实体应该复用架构，而不是复制 TASK003 的代码量。

---

## 24. 后续实体开发方向

未来：

```text
condition_occurrence
procedure_occurrence
drug_exposure
measurement
observation
```

应逐步转向：

```text
generic framework
      +
entity-specific config / mapping
```

而不是每个实体重新生成几千行 Bash。

建议抽象：

```text
canonical/
processed/
ids/
cdm/
reconciliation/
evidence/
```

---

## 25. Pod / Image / Airflow 的下一阶段原则

当前优先目标从：

```text
继续堆更多 ETL 表
```

调整为：

```text
先把平台真正运行起来
```

建议：

```text
Synthea Generator Image
        ↓
Kubernetes Job
        ↓
Landing publication
        ↓
Airflow
        ↓
Person
        ↓
Visit
        ↓
Batch reconciliation
```

初期采用两个项目 image：

```text
healthcare-data-platform-synthea
healthcare-data-platform-runtime
```

Spark 暂时可以继续使用已经验证的 Spark runtime。

---

## 26. Synthea Generator 的设计原则

Synthea 应作为可参数化 batch generator。

参数例如：

```text
population_size=50
seed=10001
state=Georgia
city=Atlanta
```

生成的是：

```text
50 patients
+
与这 50 patients 关联的 encounters / conditions / procedures / ...
```

而不是“总共 50 行”。

调试阶段：

- population_size 固定；
- seed 固定；
- 输出可重复。

平台稳定后再考虑随机 population 和增量场景。

Generator 成功不能只看进程 exit 0，还要验证：

```text
expected CSV set
non-empty files
headers
SHA256
manifest
S3 upload
manifest LAST
```

---

## 27. Batch ID 与 Pipeline Run ID 分离

建议：

```text
batch_id
= 数据批次身份
```

```text
pipeline_run_id
= 某一次处理运行身份
```

一个 batch 可以被多个 pipeline run：

- 首次处理；
- read-only verification；
- recovery；
- replay test。

不能把两者混为一个 ID。

---

## 28. 文档治理规则

### 架构文档

重要架构文档采用：

```text
xxx.zh-CN.md
xxx.en.md
```

中文用于内部阅读，英文用于外部展示。

### 开发治理文档

开发期内部资料目前先使用中文，并统一后缀：

```text
-cn.md
```

例如：

```text
development-lessons-cn.md
development-lessons-task003-step04-cn.md
SKILL-cn.md
```

未来如果需要对外，再单独生成 `-en.md`。

---

## 29. 本文件的维护方式

每完成若干 STEP：

1. 保留对应 STEP lessons。
2. 找出可跨任务复用的规则。
3. 整理进本文件。
4. 不重复粘贴只对某个 run 有意义的 runtime ID。
5. 将具体历史和抽象规则分开。

本文件会随项目演进持续更新。
