# Local DP 4.4 — GitSync Main 快照门禁修复与真实验收（2026-10-19 EDT）

## 解决的问题

此前三轮实验 [Self-Runner PR #141](https://github.com/JohnZhang-DataForge/Self-Runner/pull/141) / [Run #39349013821](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39349013821)、[#39349180383](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39349180383)、[#39349393543](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39349393543) 的 **GitHub Job 都是 FAIL**，不得事后改写。第三轮其实已成功读取两个 Pod 的活动 Git 工作树 `.git/HEAD=f0290ca1bea87e054794576bc5803e8f1e060ac8`，与当时 Healthcare Main 匹配；但验收脚本仍强制比对旧 SHA `72c1c40c7faecb3c816a7ccb000c7b0595f8d897`，因此 `DIRECT_GITSYNC_HEAD=HOLD`。旧工作树已被 GitSync 版本切换清理，**不是 Kubernetes API、ServiceAccount 或 Git 元数据权限故障**。

用户明确同意基于此证据采用新的边界明确的控制修复并继续执行；该授权不涉及任何业务 DAG、历史 Spark Driver 或写入操作。

## 修复方案与防竞态验收门槛

- 既有 Self-Runner `generic-task-executor.yml` 的固定 Request Push 间接触发，`dw-runner-set`，`validate` 模式；新固定控制入口 `scripts/ci/tasks/task990/step04.sh` → `src/ci/local_dp_gitsync_main_head.py`。
- 在触碰 K8s 前以 **固定 Healthcare GitHub 仓库地址**运行 `git ls-remote --exit-code ... refs/heads/main`，得到本轮 40 位预期 Main SHA；不再依赖源码写死的历史 SHA，也不接受 Request 动态指定任意 Git URL。
- 使用已有挂载式 ServiceAccount `tokenFile` 创建临时 kubeconfig；只 GET `dw-airflow` Pods，对确切唯一的 Running Scheduler、DAG Processor 各执行一次固定、`python3 -B`、只读的 `kubectl exec`。跟随当前 GitSync `repo` symlink，限定在 DAG volume 范围内解析 `.git` 指针并读取活动工作树 HEAD。
- 两 Pod 查验后**再次读取 GitHub Main**，必须与开始的精确值相同，并且每个 Pod 的 `GIT_METADATA=DETACHED_HEAD`，`ACTUAL_HEAD=ACTIVE_PATH_SHA=开始锁定的 Main SHA`，才判 `PASS`。Main 中途推进、Pod 身份变化、双 Pod 分歧、Gitdir 越界、无元数据等均显式 HOLD，绝不强制清理工作树或自动重试。
- 新增 9 项固定行为和负向分支离线测试，另重跑 4 项 SA 临时 kubeconfig 测试。该门禁只证明所观察时窗中的配置同步，不证明未来 Main 永不变化，也不替代业务数据验收。

## 实际运行记录（新方案）

- **控制代码实验 HEAD**：Self-Runner `3d29e4501bd193531be19bcce030aee65e0d0123`。
- **真实运行**：[Generic Task Executor Run #39350724171](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39350724171)，**GitHub completed SUCCESS / `FINAL_STATUS=PASS`**。
- 离线安全测试 **13/13 PASS**（动态 Main+GitSync 9/9、ServiceAccount 4/4）。
- `MAIN_START=11128b17994d6c0226b86ae64ec616eceb44b9d9`。
- `dw-airflow-scheduler-654d89576c-bkm8m`：`GIT_METADATA=DETACHED_HEAD`，`ACTIVE_PATH_SHA=ACTUAL_HEAD=11128b17994d6c0226b86ae64ec616eceb44b9d9`。
- `dw-airflow-dag-processor-c94497ff5-lvtrx`：`GIT_METADATA=DETACHED_HEAD`，`ACTIVE_PATH_SHA=ACTUAL_HEAD=11128b17994d6c0226b86ae64ec616eceb44b9d9`。
- `MAIN_END=11128b17994d6c0226b86ae64ec616eceb44b9d9`，`GITSYNC_MAIN_GATE=PASS REASON=EXACT_MAIN_HEAD_VERIFIED`；这个 SHA 也是实验结束前已核实的 Healthcare Main。
- `CLUSTER_MUTATION=NONE`；无 K8s 新建/修改/删除、业务 DAG/SparkApplication/Writer、PG/S3/镜像 Publish；仅 Pod 内文件读取与 Runner 内固定 Git 远端只读查询。

## 正式发布、后续限制

- 实验 [Self-Runner PR #142](https://github.com/JohnZhang-DataForge/Self-Runner/pull/142) **关闭、未合并**，保留单次 `requests/task990/step04/run-001.json` 和实际 Run。
- 清洁发布 [Self-Runner PR #143](https://github.com/JohnZhang-DataForge/Self-Runner/pull/143) **已合并**，Main `c4dc322274f7f98b1fe1ae23ec9c892be6020a6c`；仅含经过真实 Run 验证的三个固定控制/测试文件 Git Blob 以及操作说明，**不包含 Request 文件**，不会因合并自动重跑。
- 本 Change **4.4 仍 PARTIAL**：本轮完成了现行 Scheduler/DAG Processor 的 Main HEAD 同步证明；并不证明所有 DAG 的真实调度/消费结果，也不证明历史 Spark Driver 的 `module.__file__`。此前 4/4 DAG 文件哈希、3/3 历史 Spark ConfigMap 哈希为独立的既有证据；不能混成 Spark Runtime E2E。
- 4.1 / 4.8 审计未收口、4.9 / 4.10 清理门禁仍 HOLD；**本次历史源文件删除 0，批准删除 0**。不得因 GitSync PASS 直接开始删除。
