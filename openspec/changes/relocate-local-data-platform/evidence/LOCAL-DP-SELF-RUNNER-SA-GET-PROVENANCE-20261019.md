# Local DP 4.4 — Self-Runner SA / kubeconfig / GET-only provenance（2026-10-19）

## 冻结引用与授权边界

- Healthcare OpenSpec 权威：`openspec/changes/relocate-local-data-platform/tasks.md` §4.4（继续 PARTIAL，未完成）。
- 本次证据更新的 Healthcare 起始 Main：`818f0f10d5ec2a68d9107bca30f6edb263866472`；只添加文档证据，**没有修改 Local DP 源码**。
- Self-Runner 原 Main：`ffd0eccecbf0148183b956e6e4416d4b8d99002b`。
- Self-Runner 实验 [PR #137](https://github.com/JohnZhang-DataForge/Self-Runner/pull/137) 已关闭、未合并。最终发布 [PR #138](https://github.com/JohnZhang-DataForge/Self-Runner/pull/138) 已 Squash 合并为 Main `1d5dc09c1c4c39d7a7ffc51dd584ecf0e0077b30`；正式合并只包含 **6 个代码、测试、文档文件**，不含任何一次性 `requests/**` 文件。
- 正式执行入口：`Self-Runner/.github/workflows/generic-task-executor.yml` 接收匹配 `requests/taskNNN/stepNN/run-NNN.json` 的 `push feature/**`；固定 `scripts/ci/run-task.sh task990 step01 validate`，调度 `dw-runner-set`，不是调用 `workflow_dispatch` API。当前 GitHub 连接并无直接 Actions Dispatch 操作接口，但 GitHub 提交成功触发 Runner。
- SA 事实：Self-Runner `docs/development/PLATFORM-DEVELOPMENT-OPERATIONS-v1.0.zh-CN.md` 说明开发 ARC Runner 使用高权限 ServiceAccount；本轮代码仍把 **允许的 API 调用严格限制为 GET/LIST**。未修改 SA、RBAC、Deployment 或 Pod。

## 三轮诊断失败 → 定因 → 一次边界明确的修复验证

| 执行 | Self-Runner 精确 SHA / Run | 验证结论 |
| --- | --- | --- |
| 1 | [#39340645481](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39340645481) | Request/Runner 触发和离线测试 4/4 PASS；`kubectl get` 失败，原始错误未输出；HOLD |
| 2 | [#39340760663](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39340760663) | `dw-airflow/pods` GET 失败，脱敏类别 `KUBE_API_UNREACHABLE`；HOLD |
| 3 | [#39340900578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39340900578) | Runner 内 `KUBERNETES_SERVICE_HOST=PRESENT`、ServiceAccount Token Mount=PRESENT，`KUBECONFIG=UNSET`、`kubectl config current-context=UNCONFIGURED`；证明不能直接使用默认 kubectl 配置；依三轮规则暂停 |
| 修复验证 | Self-Runner HEAD `5c907173f3100dca9b8ea0ea3d710d234cb4cc31` / [Run #39341833708](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39341833708) | **Run completed SUCCESS / FINAL_STATUS=PASS**；新增 4 项 kubeconfig 安全测试与原 4 项探针测试，**8/8 PASS**；`RUNNER_KUBECTL_CONTEXT=INCLUSTER_SERVICEACCOUNT`；真实 GET 完成 |

失败根因是 **ARC Runner 容器没有默认 kubeconfig/current-context**，不是 K8s 集群被证明离线，也没有证据证明 RBAC 授权失败。修复在 `RUNNER_TEMP` 写入临时 `0600` kubeconfig，引用投射式 `ca.crt` 与 **`tokenFile` 路径**；不读取、打印或复制 bearer token 的内容；用后删除临时文件。本次只读权限得到了实际证明，但 SA 是否具备集群管理员 RBAC 未通过本轮额外验证（仅依据仓库操作规范说明）。

## 实际 GET-only 来源清单（2026-10-19 Run）

- Airflow `dw-airflow`：**4 个 Running Pods**。API Server 没检测到 GitSync 容器；`dag-processor`、`scheduler`、`triggerer` 各检测到 `git-sync-init` 和 `git-sync` 容器及 DAG 挂载。
- Spark `dw-spark`：**27 个 SparkApplications**，**26 个含源码型 key 的 ConfigMaps**。报告为每个 `.py` / `.sh` source key 输出 **SHA256，不输出源码正文**。历史 SparkApplication 的 `COMPLETED` / `FAILED` 状态不能取代当前 Runtime 验证。
- Runner Output：`K8S_MUTATION=NOT_PERFORMED`、`RAW_CONFIGMAP_EXPORT=NOT_PERFORMED`。无 Kubernetes `exec/create/apply/patch/delete`、PostgreSQL/S3/镜像 Push 或业务 DAG/SparkApplication 启动。只将脱敏报告存入 Run Artifact [generic-task-report](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39341833708)。

## 仍未通过 / 不得外推

- **GitSync 实际 checkout Commit SHA = NOT_VERIFIED**：PodSpec 中有 git-sync sidecar 不等于实际 checkout 版本；本只读 GET 不能证明文件系统内活动 checkout 的 SHA。
- **Spark Driver 实际 import/module.__file__ = NOT_VERIFIED**：仅有 SparkApplication/ConfigMap 的对象与源码 hash 不代表 Driver 此刻运行哪个文件。
- **ConfigMap 与当前 Healthcare Main 的逐文件 SHA 比对 = NOT_VERIFIED**：此阶段输出了 ConfigMap 源码哈希，但尚未绑定具体 Main Git 文件且没有应用级比较 Gate。
- **TASK004 新批次 E2E/Writer/PG/S3 读回 = NOT_EXECUTED**：本证据不是运行级 E2E。
- 4.4 PARTIAL / HOLD；4.1、4.8、4.9、4.10 均未因此解锁。历史脚本候选已批准删除数量仍为 **0**；不得重跑历史全量审计来代替动态消费闭包。

## 后续安全步骤

用同一个通过验证的 Request Push 控制通道，在 **独立受控只读任务** 中进一步核对活动 GitSync revision 和目标 Spark 主程序的文件来源；如果需要 `kubectl exec` 进入只读容器以获取实际 checkout SHA，必须显式区别于本轮严格 GET-only 范围并审核授权、副作用和脱敏条件。每个新运行绑定固定 Self-Runner SHA、Healthcare SHA、Run ID 与证据目录。与当前清理审计有关的历史脚本删除继续 HOLD。
