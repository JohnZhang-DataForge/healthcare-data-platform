# TASK-003 STEP04 开发经验

> 来源：TASK003 STEP04 Canonical Encounter → Raw publication 的实际故障、恢复、重放和 Git 操作。
> 建议路径：`docs/runbooks/development-lessons-task003-step04-cn.md`

---

## 1. S3 空列表响应不能只判断 `KeyCount`

实际出现合法空列表：

```json
{"RequestCharged": null}
```

没有：

```text
Contents
KeyCount
```

旧逻辑把缺失 `KeyCount` 判断为异常。

正确做法：

- 明确支持已经验证过的合法空结果；
- 明确拒绝真实非空结果；
- 类型矛盾时失败；
- CLI 本身失败时失败；
- 权限、网络错误不能用 `|| true` 吞掉。

---

## 2. 文件写完不等于正式发布完成

STEP04 曾出现：

```text
Raw Parquet 已写入
DQ 尚未发布
manifest 尚未发布
```

正确状态应该描述为：

```text
data exists
publication incomplete
```

正式发布顺序：

```text
data write
  ↓
readback
  ↓
DQ publish
  ↓
DQ readback
  ↓
APPROVED manifest LAST
```

下游只消费 approved manifest 指向的数据。

---

## 3. 已有 run 应优先恢复

当 Raw data 已正确存在而外层 orchestration 失败时：

不要盲目：

```text
删除旧数据
重新生成 run
重新跑 Spark
```

应检查：

- SparkApplication 状态；
- Driver logs；
- source lineage；
- Raw listing；
- DQ；
- manifest。

如果数据与预期一致，应恢复 metadata publication。

---

## 4. 幂等必须实际重放证明

STEP04 的同 run resume 和 replay 验证证明：

```text
existing objects reused
metadata SHA unchanged
```

比“代码理论支持幂等”更可靠。

未来每个关键 publication 至少定义：

```text
new run
resume same run
replay same run
conflict case
```

---

## 5. 修复必须进入正式生成器

如果只修改生成出的 Python：

```text
generated source fixed
generator still old
```

那么未来重新运行 prepare 会把 bug 重新生成回来。

规则：

```text
canonical source 修
+
canonical generator 修
+
重新生成验证
```

三者必须同步。

---

## 6. Reset 不能破坏恢复依赖

STEP03 / STEP04 runtime 不只是日志，也是：

- lineage evidence；
- resume evidence；
- replay evidence。

因此 reset 默认只清：

- `__pycache__`
- 当前可安全清理的临时工作

并保留：

- S3 正式数据；
- runtime reports；
- stable IDs；
- database；
- Kubernetes 持久资源。

---

## 7. Shell failure propagation 要显式检查

以下模式需要谨慎：

```bash
readarray < <(python ...)
```

外层命令不一定正确传播 producer 的失败。

关键 parser 应检查：

- producer exit code；
- field count；
- required value；
- JSON type。

重要 S3 查询禁止：

```bash
... || true
```

因为这可能把真实错误伪装成“空目录”。

---

## 8. 大型 heredoc 存在粘贴截断风险

实际开发中曾发现：

- heredoc 不完整；
- BEGIN 有但 END 没出现；
- Shell 进入等待输入；
- 文件语法可能仍然看似正常。

以后大型内容：

- 拆成独立 artifact；
- 每段完成后验证；
- 不把几十 KB 文档放进一次终端粘贴。

---

## 9. `bash -n` 不代表实现完整

语法通过只能证明 parser 能读取脚本。

不能证明：

- 后半段存在；
- 所有函数存在；
- runner 真能运行；
- 数据状态正确。

仍需真实运行验收。

---

## 10. Git 认证与提交身份是两件事

`gh auth` 解决访问 GitHub。

`git user.name` / `git user.email` 决定 commit identity。

两者不可混为一谈。

另外自动化脚本建议：

```bash
export GIT_PAGER=cat
```

避免分页器造成“脚本卡住”的误判。

---

## 11. 全量替换 remote 不是日常流程

TASK003 早期曾有一次 repo tree replacement。

使用 ours merge 等方式只是针对历史迁移。

以后正常开发：

```text
feature branch
↓
review
↓
merge / push
```

不能把迁移操作当日常冲突解决方式。

---

## 12. STEP04 对后续的最大价值

STEP04 最重要的不是单次 5799 Encounter Raw 成功，而是建立：

```text
immutable publication
approved manifest
resume
replay
evidence
conflict detection
```

后续实体应复用这些机制。
