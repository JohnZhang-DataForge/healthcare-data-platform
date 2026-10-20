# Local DP 4.4 — 运行中 GitSync 的真实 Git HEAD 只读取证（2026-10-19 EDT）

## 证据范围与冲突识别

此次继续此前在 [Self-Runner PR #140](https://github.com/JohnZhang-DataForge/Self-Runner/pull/140) 已合并的只读来源验证，不重跑 TASK001–003、不触发已有 Batch、不调整 Airflow/Spark 部署。

本次实验控制分支 [Self-Runner PR #141](https://github.com/JohnZhang-DataForge/Self-Runner/pull/141) **已关闭、未合并**。采用已验证的 `generic-task-executor.yml` Request Push → `dw-runner-set`，通过临时 ServiceAccount `tokenFile` kubeconfig，固定名单读取 `dw-airflow` Scheduler 与 DAG Processor 中实际 Git 工作树的 `.git` 指针和 `HEAD` 文件。使用 `kubectl exec -i -- python3 -B -`，读取 Git 元数据但不调用业务 DAG、SparkApplication 或 Writer。没有 K8s 资源写入，不读取 Secret 原文，不输出 Git 配置凭据。

## 三轮真实执行与 FAIL / PASS 的区别

| GitHub Run | 具体事实 | GitHub Job 终态 |
| --- | --- | --- |
| [#39349013821](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39349013821) | 离线安全测试 10/10 PASS；静态固定旧 SHA `72c1c40c7faecb3c816a7ccb000c7b0595f8d897` 工作树读取失败，报告 `METADATA_READ_FAILED` | **FAIL** |
| [#39349180383](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39349180383) | 10/10 离线测试 PASS；两个 Pod 均报告 `MISSING_AT_WORKTREE_LOOKUP`，表明原固定旧版本目录不存在 | **FAIL** |
| [#39349393543](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39349393543) | 10/10 离线测试 PASS；改从活动 `repo` symlink 解析 worktree，**两个 Pod 成功只读 `.git/HEAD`**，实际 SHA 和活动工作树目录 SHA 均相同 | **FAIL（原固定 SHA 门禁过期）** |

第三轮 `2026-10-20T00:44:22Z` 真实输出中的关键字段：

```text
POD=dw-airflow-scheduler-654d89576c-bkm8m CONTAINER=scheduler GIT_METADATA=DETACHED_HEAD ACTIVE_PATH_SHA=f0290ca1bea87e054794576bc5803e8f1e060ac8 ACTUAL_HEAD=f0290ca1bea87e054794576bc5803e8f1e060ac8
POD=dw-airflow-dag-processor-c94497ff5-lvtrx CONTAINER=dag-processor GIT_METADATA=DETACHED_HEAD ACTIVE_PATH_SHA=f0290ca1bea87e054794576bc5803e8f1e060ac8 ACTUAL_HEAD=f0290ca1bea87e054794576bc5803e8f1e060ac8
DIRECT_GITSYNC_HEAD=HOLD
FINAL_STATUS=FAIL
```

随后通过独立 GitHub Main Ref 查询，确认为 **`f0290ca1bea87e054794576bc5803e8f1e060ac8`**（该 commit 的提交时间 `2026-10-20T00:41:17Z`，早于本轮 Pod 读取），因此：

- **可证实的运行环境事实**：两个已存在 Airflow 组件直接读取到的 Git HEAD 都是 `f029...`；同一工作树活动目录 SHA 也为 `f029...`；该值与取证时 GitHub Main 相同，证据比单纯依赖路径名称更强。
- **不能把第三轮的 GitHub Job 记录为 PASS**：诊断控制脚本的 `PIN=72c1...` 没有随着 Main 更新，因此 `DIRECT_GITSYNC_HEAD=HOLD` / `FINAL_STATUS=FAIL` 是**陈旧版本验收条件失败**，不是 HEAD 读取失败。保留原始失败，禁止事后改写为成功运行。
- 固定 Git Compare `72c1c40c7faecb3c816a7ccb000c7b0595f8d897...f0290ca1bea87e054794576bc5803e8f1e060ac8`：共 15 个变更文件，**`local-data-platform/` 下 0 个文件变化**；其他变更主要是 Azure/Fabric/OpenSpec 文档和隔离 DagBag Workflow。这解释了为何之前的两份 DAG 内容 SHA256 与旧 Commit 的 4/4 一致证据仍有效，同时 GitSync 可以切换到更新的 Git HEAD。此比对以被查询的两端 Commit 为准，不推断未来 Main。

## 操作与后续门禁

- 按同一问题 **三轮停止规则**，本轮到此停止，没有第四次 Live 探针。实验 PR #141 关闭未合并；不存在因本轮合并而自动重放请求的风险。
- 将来需要可复用的直接 HEAD CI Gate，应在独立控制变更中**于任务开始时绑定当前 Healthcare Main 的精确 40 位 SHA**，记录查询前后 Main 是否移动，动态解析活动 `repo` 链接，并将 Pod HEAD、活动路径 SHA 与已锁定目标 SHA 对比；测试失败即 HOLD，而不是直接重试共享运行资源。这一未来控制器**尚未在 Main 发布，也未验收**。
- 不把 `HEAD` 一致宣称为所有 DAG 加载/任务成功，Spark 历史 Driver 的真实 `module.__file__` 仍然 **NOT_VERIFIED**；不能为了这个证据重跑历史 Spark Writer。适用的其它 4.2–4.7 门禁仍需完成。

**结论：4.4 有新的 LIVE 读回证据，但整体 PARTIAL；4.9 和 4.10 未解锁，批准删除历史文件仍为 0。**
