---
name: healthcare-platform-stepwise-development-cn
description: Healthcare Data Platform 项目中文开发规范。定义一步一验、临时 Shell、canonical source、运行证据、Mutation 安全、Git checkpoint、文档治理、TASK/STEP lessons 维护以及 Pod/Image/Airflow 平台化开发方式。
---

# Healthcare Data Platform 开发 Skill（中文）

> 建议路径：`docs/skill/SKILL-cn.md`
> 本文件属于开发治理资料，主要用于项目开发期保持统一规则。项目成熟后可转为归档资料，不属于生产运行依赖。

---

## 1. 目标

本 Skill 用于约束 Healthcare Data Platform 项目的开发方式。

目标不是让某条命令“这次能运行”，而是让每个完成的步骤都具备：

- 可复现；
- 可验证；
- 可独立执行；
- 可恢复；
- 可安全重跑；
- 可进入 Git；
- 可被后续开发者理解；
- 不依赖聊天历史。

---

## 2. 固定路径

Git 项目：

```text
/data/spark/healthcare-data-platform
```

历史已验证基线：

```text
/data/spark/phase3c
```

临时开发 / 修复 Shell：

```text
/data/spark/temp_shell
```

`phase3c` 为保护区，不因新 V2/V4 开发随意修改。

---

## 3. 一次只做一个可验收步骤

标准工作方式：

```text
设计
  ↓
修改 canonical source
  ↓
静态检查
  ↓
tests
  ↓
真实执行
  ↓
验证真实状态
  ↓
FAIL → 修同一步
  ↓
PASS
  ↓
冻结
  ↓
Git checkpoint
```

当前 STEP 没 PASS：

- 不跳过；
- 不把 PLANNED 当 COMPLETE；
- 不因为下游急着做就掩盖失败。

---

## 4. Shell 交付规则

用户在 `runner01` 执行命令。

默认一次提供：

```text
一个完整可直接粘贴的 Bash code block
```

不要：

- 一次给多个互相依赖的半截脚本；
- 要用户手工拼代码；
- 把 binary/base64 当常规交付方法。

临时 helper Shell：

```text
/data/spark/temp_shell/
```

正式执行脚本：

```text
scripts/taskNNN/
```

---

## 5. Source guard

所有可能被用户误 source 的 helper / runner 推荐加入：

```bash
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo 'ERROR: execute with bash; do not source'
  return 2
fi
```

---

## 6. 严格模式

不要让用户直接在交互式 root Shell 中执行：

```bash
set -Eeuo pipefail
```

应写进 child script。

原因是 interactive shell 状态可能被永久修改，影响之后手工排错。

---

## 7. 输出格式

每一步必须打印：

```text
#### TASKNNN STEPXX ... OUTPUT BEGIN ####
...
RESULT=PASS/FAIL
EXIT_CODE=...
#### TASKNNN STEPXX ... OUTPUT END ####
```

使用 `EXIT trap` 保证失败也有 END 和 exit code。

没有真实输出：

```text
不能声明 PASS
```

---

## 8. Runtime truth 优先

不能因为以下任意一项就宣称完成：

- 文档写了 PASS；
- 上一轮聊天说完成；
- YAML 存在；
- `kubectl apply` 成功；
- `_SUCCESS` 存在；
- shell exit 0；
- 文件目录存在。

完成状态由该 STEP 定义的真实 evidence 决定。

---

## 9. Canonical source 与临时 installer

临时 installer 可以生成：

```text
Python
YAML
JSON
SQL
tests
permanent shell
docs
```

但是 Git 中真正权威的是生成后的 canonical source。

历史 repair helper：

```text
03b-fix
04c-repair
...
```

不能成为永久执行链的必要条件。

---

## 10. 生成器必须同步修复

如果 canonical source 是由永久 generator 生成：

```text
generator
↓
generated source
```

那么修复必须同步：

```text
修 generator
+
重新生成
+
验证生成结果
```

不能只 patch 生成产物。

---

## 11. 大型 Markdown 文档交付

大型 Markdown 不通过超长 heredoc 直接交付。

标准流程：

```text
生成独立 .md
↓
提供下载
↓
用户放到指定 repo 路径
↓
短 Shell 验证路径 / 内容 / SHA
↓
Git
```

避免浏览器复制导致 code fence / heredoc 损坏。

---

## 12. 文档语言规范

### 对外 / 架构文档

使用两份独立文件：

```text
xxx.zh-CN.md
xxx.en.md
```

中文供内部阅读。

英文供 GitHub、面试、外部人员查看。

### 开发治理文档

当前先统一中文，并使用：

```text
-cn.md
```

例如：

```text
development-lessons-cn.md
development-lessons-task003-step04-cn.md
SKILL-cn.md
```

如果未来需要对外展示，再单独生成英文版。

---

## 13. Development Lessons 维护规则

每个重要 STEP 可以产生：

```text
docs/runbooks/development-lessons-taskNNN-stepNN-cn.md
```

这些历史文件永久保留。

同时维护总表：

```text
docs/runbooks/development-lessons-cn.md
```

定期把跨 STEP 可复用经验整理进去。

原则：

```text
STEP lessons = 原始开发历史
总 lessons = 归纳后的长期规则
```

不能因为总表已经吸收而删除 STEP lessons。

---

## 14. Task / Step 命名规则

`TASK` 表示业务任务。

例如：

```text
TASK002 = Person
TASK003 = Visit
```

`STEP` 表示 TASK 内部开发阶段。

交流和文档中应尽量同时写：

```text
TASK003 STEP06C4E
```

避免只写“Step 5”导致跨任务歧义。

---

## 15. Permanent scripts 顺序

一个 TASK 的永久执行链推荐：

```text
00-reset-taskNNN.sh
01-...
02-...
03-...
...
NN-validate-taskNNN.sh
```

临时修复脚本不进入永久链。

---

## 16. Reset 安全规则

`00-reset-taskNNN.sh` 是持续维护的脚本。

默认允许清理：

- 当前 runtime work；
- 当前临时 report；
- task-specific 临时 Pod / Job；
- Python cache；
- failed local temporary state。

默认禁止删除：

- `/data/spark/phase3c`；
- source datasets；
- verified Landing；
- published Raw；
- published Processed；
- OMOP CDM；
- stable ID maps；
- Secrets；
- PVC/PV；
- namespaces；
- buckets；
- Git source。

持久删除必须：

```text
显式参数
+
精确目标校验
+
非默认行为
```

---

## 17. Idempotency

每个生产级步骤都必须定义 rerun 行为。

例如：

```text
same input + same batch_id
→ reuse
```

```text
same business key
→ same stable OMOP ID
```

```text
rerun load
→ row count 不膨胀
```

如果重跑产生 duplicate，就是失败。

---

## 18. Conflict 规则

同一个 logical identity，如果内容不同：

```text
same batch_id
+
different SHA256
=
CONFLICT
```

必须 STOP。

不能静默 overwrite。

---

## 19. Publish boundary

Partial output 不允许伪装成正式产品。

例如：

```text
data written
≠
DQ passed
≠
published
```

正式 publish marker / manifest 必须最后生成。

下游只能读取批准状态的数据。

---

## 20. Mutation 安全模型

数据库或其他高风险持久 mutation 必须尽量采用：

```text
read-only discovery
↓
preflight
↓
mutation contract
↓
rehearsal
↓
real mutation
↓
independent reconciliation
↓
freeze
```

---

## 21. No Blind Retry

如果一次 mutation 之后客户端状态不确定：

```text
禁止直接重跑
```

必须先：

```text
独立 read-only reconciliation
```

例如核对：

- row count；
- ID mapping；
- sequence；
- SHA；
- FK；
- target state。

数据库真实状态优先于 wrapper 状态。

---

## 22. Sequence 规则

Sequence：

```text
不要求 gapless
```

失败 transaction 可能消耗 ID。

只要求：

- unique；
- stable；
- non-reassigned。

禁止为了补洞随意 `setval` rewind。

---

## 23. Spark / Log 规则

SparkApplication 完成之后：

- 不因为 wrapper parser 错误就立即重跑 Spark；
- 先复用 driver logs 和已有 artifact；
- 普通 log 不视为结构化数据传输通道；
- 结构化 payload 应使用 prefix / file / S3 artifact。

---

## 24. Shell parser 规则

注意：

```text
readarray + process substitution
python3 - + stdin
grep -F + regex anchors
special Bash variables
```

这些都已经在真实开发中造成过误判。

关键 parsing 必须检查：

- producer exit；
- expected fields；
- types；
- counts。

---

## 25. Git checkpoint 规则

STEP PASS 后：

```text
git status
↓
确认预期文件
↓
git add exact files
↓
检查 staged inventory
↓
确认 runtime 未 staged
↓
git diff --cached --check
↓
commit
↓
push
↓
验证 remote HEAD
↓
确认 clean worktree
```

不能直接：

```bash
git add .
```

除非已经明确确认整个 worktree。

---

## 26. 文件结尾规则

正式 text file：

- 无 trailing whitespace；
- EOF 保留标准单 newline；
- 不额外增加空白行。

避免：

```text
new blank line at EOF
```

---

## 27. Runtime 不进 Git

默认禁止提交：

```text
runtime/
config/local.env
credentials
kubeconfig
raw CSV
Parquet
temp_shell/
Secrets
```

除非有单独明确的 sanitized evidence 需求。

---

## 28. TASK Closeout

TASK 只有在：

- 所有核心 STEP evidence 验证；
- canonical verifier 通过；
- 最终文档完成；
- Git checkpoint 完成；

之后才可 CLOSED。

---

## 29. TASK003 作为 Reference Implementation

TASK003 是第一套完整：

```text
Canonical
→ Raw
→ Processed
→ Stable ID
→ CDM
→ Reconciliation
```

Reference Implementation。

后续业务表：

```text
condition_occurrence
procedure_occurrence
drug_exposure
measurement
observation
```

复用它的架构。

不要复制它所有 Bash。

---

## 30. 通用化方向

逐步提取：

```text
canonical/
processed/
ids/
cdm/
reconciliation/
evidence/
```

实体只负责：

```text
contract
business key
mapping
target columns
FK
DQ
```

Condition 阶段开始抽公共组件。

Procedure 阶段应逐步 configuration-driven。

---

## 31. Pod / Image 规则

当前平台化优先于立即增加更多业务表。

计划 image：

```text
healthcare-data-platform-synthea
healthcare-data-platform-runtime
```

Synthea image：

```text
生成 synthetic batch
发布 Landing
生成 checksum / manifest
```

Runtime image：

```text
validation
DQ
manifest
ID allocation
DB loader
reconciliation
Python control utilities
```

Spark 暂时继续使用已验证 Spark runtime，之后再做项目 Spark image。

---

## 32. Airflow 目标

第一版优先跑：

```text
Generate Synthea
↓
Landing Validate
↓
Person
↓
Visit
↓
Reconcile
```

使用新生成的小 batch：

```text
population_size=20/50
```

而不是对已冻结 TASK003 历史 batch 盲目重新 materialize。

---

## 33. Batch 与 Pipeline Run

严格区分：

```text
batch_id
```

表示数据批次。

```text
pipeline_run_id
```

表示某次处理运行。

一个 batch 可对应多个 run。

---

## 34. Agent 行为规则

参与项目开发的 agent 应：

- 一次只做 bounded change；
- 根据真实输出继续；
- 不猜 credentials；
- 不输出 Secret；
- 不未经确认做 destructive action；
- 遇到 unexpected persistent state 立即停止；
- 保留 known-good state；
- 清楚区分：

```text
PLANNED
RUNNING
PASS
FAIL
NOT RUN
```

- 不把未来架构描述成已经实施。

---

## 35. 本 Skill 的维护方式

每次出现新的、已经被真实开发证明有价值的方法：

1. 先写 STEP development lessons；
2. 如果具有长期价值，整理进总 lessons；
3. 如果属于开发行为规范，再同步进入本 SKILL；
4. 不把只适用于某一个 run 的临时参数写成通用规则。

本文件随项目开发逐步完善。
