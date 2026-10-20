# Local DP 4.4 — 运行中的 DAG 与历史 Spark 源码交叉取证（美东 2026-10-19）

## 取证版本与运行身份

- 目标 Healthcare **固定源码 Commit**：`72c1c40c7faecb3c816a7ccb000c7b0595f8d897`（上一轮 4.4 Evidence 的 Healthcare Main）。**不是动态 Main**；后续 Main 变化需单独判断是否影响 DAG/Spark 文件。
- 本次文档 PR 从 Healthcare Main `7e72dfcfe1ad7a1955be09253769c25e373b9c11` 创建：与上述 Commit 相比，只新增/修改 Fabric OpenSpec 及文档 7 个文件，**无 Local DP 代码变更**。这仅是 Git Compare 范围结论，不表示当前运行 GitSync 的 `git rev-parse` 已完成。
- Self-Runner 正式源 [PR #140](https://github.com/JohnZhang-DataForge/Self-Runner/pull/140) 已合并 Main `bbf9cb4dfe6e80805a84c6e6b4209e7e0d59798b`（5 个受控脚本/测试文件 + 1 份开发规范说明）；试验 [PR #139](https://github.com/JohnZhang-DataForge/Self-Runner/pull/139) 已关闭未合并，**两个单次 Request 不在 Self-Runner Main**。
- 自动态触发：现有 `generic-task-executor.yml` 的 `requests/task990/step02/run-001.json` / `run-002.json` 提交事件 → `dw-runner-set`；`validate` 允许，`execute` 拒绝。ARC Runner 使用挂载式 ServiceAccount `tokenFile` 建立临时 kubeconfig。无业务 Pod、Job 或 ConfigMap 创建。
- 初轮 [Run #39346916824](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39346916824)，实验 HEAD `d594935ab3dce4d9d8a04e1cd7741149f37d2486`：9/9 离线安全测试 PASS，真实 `kubectl get` + 针对运行中 Scheduler/DAG Processor 的固定 `kubectl exec -i -- python3 -B -` 成功，发现工作树位置与文件哈希；仅非修改的 Python 文件系统读取及只读 Git 命令。
- 固定 Git 独立比对 [Run #39347241695](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39347241695)，精确 Self-Runner HEAD `06ce9279a6206e08102c3585d16451c1cd5a3687`，**GitHub Run SUCCESS、FINAL_STATUS=PASS**：新增 4/4 精确比对离线测试 PASS，加上 5/5 活动探针和 4/4 SA kubeconfig 测试，合计 **13/13**；独立从 GitHub 以固定 SHA 下载 Healthcare Git 源码并 `git rev-parse HEAD` 核对身份。

## Airflow 运行中源码路径与独立 Hash 比对

仅 `dw-airflow` 中正在运行、名称与指定容器都符合固定白名单的两个 Pod：

| Pod | 文件 | 实际 SHA256 与固定 Git 源比对 |
| --- | --- | --- |
| `dw-airflow-scheduler-654d89576c-bkm8m` | `landing_batch_discovery.py` | `29b78527a7415a097c1d4479410cefd2b94c4a5587ab8702c8e2301c897bed0d` = Git，PASS |
| 同上 | `new_only_omop_consumer.py` | `47f68d362849745600276cbd1f4effc980c72b2d318a415d74072aa7cc81e034` = Git，PASS |
| `dw-airflow-dag-processor-c94497ff5-lvtrx` | `landing_batch_discovery.py` | 同一 SHA256 = Git，PASS |
| 同上 | `new_only_omop_consumer.py` | 同一 SHA256 = Git，PASS |

两 Pod 文件的 `resolved_dir` 一致：

`/opt/airflow/dags/.worktrees/72c1c40c7faecb3c816a7ccb000c7b0595f8d897/local-data-platform/airflow/dags`

**可声称**：两个运行中的 Airflow 组件实际能读取目标迁移后的 DAG 路径，工作树路径携带固定 Commit，且 **4/4 活动 DAG 文件内容与该 Git Commit 精确一致**。已证明迁移后源文件的 Git→实际 Pod 内容匹配（仅上述 2 个 DAG × 2 个 Pod）。**不可声称**：Pod 内 `git rev-parse HEAD` 已独立成功（原探针显示 `GITSYNC_CHECKOUT_SHA=NOT_VERIFIED`）；全集群只有唯一 DAG root、所有 DAG 均加载成功、所有 DagRun 实际执行通过。先前 Airflow 3.2.2 隔离 DagBag Parse PASS 亦不可替代真实任务 E2E。

## Spark 历史 ConfigMap → Git 同 SHA 源码比对

| 已存在 ConfigMap Key | 与固定 Git 源 |
| --- | --- |
| `task003-encounter-app-20261008t234726z-1658454/synthea_encounter_adapter.py` | `MATCH` |
| `task003-encounter-raw-app-20261009t005128z-1681690/publish_canonical_entity.py` | `MATCH` |
| `visit-proc-runtime-72858de1ee39bd1eeb3e4ebb/run_visit_processed_writer.py` | `MATCH` |

相应历史 SparkApplication 的 `mainApplicationFile` 声明是 `local://...` 下上述主程序 basename，用户先前只读发现这些 Application 状态为 `COMPLETED`。**只证实 ConfigMap 内源码与固定 Git 字节一致、对应主程序声明存在；没有证明实际旧 Driver 运行期间的模块导入路径，更没有启动新 Driver。**

## 安全、资源、副作用

- K8s 读行为仅 `get` 和对两个已存在 Pod 使用固定 `python3 -B -` 读取源文件；不改 Pod/ConfigMap/SA、无 `kubectl apply/patch/delete/create`、没有 DagRun、SparkApplication、Job、PostgreSQL、S3 或 GHCR 操作。
- Python 用 `-B` 避免 .pyc 写入，输入是一段固定程序而非用户可指定命令。输出仅相对安全的目录/文件名、工作树 SHA、SHA256、资源名及历史状态，不上传 PodSpec 或 ConfigMap 原始内容/Secret。
- Runner 在自身临时目录读取固定 Git Commit、保存脱敏 JSON Artifact，不在集群写入。
- 单次 Request 留在未合并的 PR #139 分支；Self-Runner 正式 PR #140 **排除了这两份触发文件**，因此合并不重新执行。无本轮残留业务资源需要清理。

## 当前结论 / 下一关

**§4.4 = PARTIAL，§4.9 = HOLD，批准历史文件删除数量 = 0。**

本轮已从“只有 GitSync Pod/ConfigMap 名称”推进到 **活动 DAG 的固定 Git Commit 字节一致性证明 + 三份 Spark ConfigMap 的字节一致性证明**。未解决部分是旧 Driver 的实际 `module.__file__`（历史 Driver 可能已退出，不能为取证重跑业务）、所有 DAG 的单一加载路径/运行性、其它历史消费者及 4.5–4.7 的运行兼容与安全 E2E。若日后新建隔离 Spark smoke，必须新批准、选定非业务输入并防止 Writer 或共享状态变更，不能重播旧 Batch。本证据不会批准删除 `scripts/task003/{04-write-closeout-docs.sh,05-write-ae-freeze-doc.sh,05f2-write-freeze-doc.sh}`。
