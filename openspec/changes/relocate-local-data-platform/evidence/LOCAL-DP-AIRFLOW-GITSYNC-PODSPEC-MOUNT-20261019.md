# Local DP §4.4 — Airflow GitSync 与 DAG 目录实际 PodSpec 卷挂载核对（2026-10-19 EDT）

## 版本和真实运行证据

- Healthcare 开工时 Main `457e05c8d96de255a4401039f0035f91d84af37d`，文档分支基于合并前新 Main `5ffaccc76be12ea18b2632732e6f9bd37ae6a452`。中间并行提交仅影响 Fabric Bootstrap，不更改 `local-data-platform/` 或本 OpenSpec。
- Self-Runner 正式只读诊断通过 [PR #149](https://github.com/JohnZhang-DataForge/Self-Runner/pull/149) 合并 Main `836ab98d00cb8731b9129fa60a845b8e737efb5d`；新增 [Airflow GitSync mount auditor](https://github.com/JohnZhang-DataForge/Self-Runner/blob/836ab98d00cb8731b9129fa60a845b8e737efb5d/src/ci/local_dp_airflow_gitsync_mount_audit.py) / 独立单测 / `scripts/ci/tasks/task990/step07.sh`，正式 Main **没有** `requests/**` 实验触发文件。
- 实验 [Self-Runner PR #148](https://github.com/JohnZhang-DataForge/Self-Runner/pull/148) 已关闭且未合并；单次 Request commit `1f1986dfaa376b51669e15c4c2bc036cfb490b25` 触发 [Generic Task Executor Run #39359914196](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39359914196)，`dw-runner-set` + 固定 `validate`，**13/13 GitSync 正/负单测 + 4/4 临时 SA kubeconfig 测试 = 17/17 PASS**，`FINAL_STATUS=PASS`、`PODSPEC_GATE=PASS`。发布到 Main 的三份源码 Git Blob 与本实验所测完全相同。

## 两个现存 Airflow Pod 的脱敏 GET 读回

| Kubernetes Pod | Container | Phase | 配置 DAG Folder | GitSync 共享 DAG Volume | DAG 重叠挂载 |
| --- | --- | --- | --- | --- | --- |
| `dw-airflow-scheduler-654d89576c-bkm8m` | `scheduler` | Running | `/opt/airflow/dags` | True | 0 |
| `dw-airflow-dag-processor-c94497ff5-lvtrx` | `dag-processor` | Running | `/opt/airflow/dags` | True | 0 |

读取方式只限 `kubectl --request-timeout=20s -n dw-airflow get pods -o json`，在 Runner 进程内判定 PodSpec 后仅输出白名单的布尔值、Pod 名、已公开的 DAG 配置路径和状态。每个角色要求**恰好一个运行中 Pod**，主容器 DAG Folder 有且只有一个父级卷挂载、该卷也装载于至少一个 GitSync 容器、PodSpec 中不得存在重叠 DAG 根挂载；Scheduler 与 DAG Processor 声明路径必须一致。

**真实界限**：
- `REPO_DECLARATION=NOT_VERIFIED`（两 Pod）：本轮没有从经过限定的显式 GitSync Repo Env 获得可核实的 GitHub 来源；不能假设它已经确认或修改运行中的 GitSync 配置。其他来源例如 Helm release 实际 values、InitContainer 参数、启动配置这轮均未独立闭合。
- `ACTUAL_SINGLE_DAG_SOURCE=NOT_VERIFIED`：PodSpec 没有证明卷内不存在第二个可扫描目录、附加符号链接、进程运行参数覆盖或旧路径文件。
- `GITSYNC_ACTIVE_HEAD=NOT_VERIFIED`：本轮没有执行 `kubectl exec`，也没有再尝试之前三轮失败的 Git HEAD 取证；它们已有独立 [失败及后续修复证据](LOCAL-DP-AIRFLOW-DIRECT-GIT-HEAD-20261019.md) 与 [最终快照式 HEAD PASS](LOCAL-DP-GITSYNC-MAIN-SNAPSHOT-GATE-PASS-20261019.md)。这些 Run 的结论属于各自所测时点，不能冒充本轮再次确认最新 Main。
- Airflow DAG Parse 的隔离 CI 仍是另一级验证；这里没有导入任何 DAG、调度、生成 SparkApplication、更新 Helm、修改 Secrets、访问 PG/S3 或重放已完成业务 Batch。

## 4.4 与后续工作边界

本次已确立 **双 Airflow Pod 的 PodSpec DAG 卷挂载配置一致性 PASS**，但 `repo/目录真实唯一加载` 尚未完全闭合，`4.4` 必须保留 **PARTIAL**。

下一步不要再次重复相同的 HEAD/Driver 读回。先**纯静态检查**受限的 `Helm chart values` 与当前源码树中 DAG 根目录参数、实际部署入口和旧目录引用；没有获得当前 release 的可核查配置时标记 `REPO_CONFIG=NOT_VERIFIED`，不猜测。对于 4.1/4.8 历史文件清理仍需逐文件消费者证明、备份定位和否定性检查；`4.9/4.10 HOLD`，历史源码删除及批准删除数仍 **0**。
