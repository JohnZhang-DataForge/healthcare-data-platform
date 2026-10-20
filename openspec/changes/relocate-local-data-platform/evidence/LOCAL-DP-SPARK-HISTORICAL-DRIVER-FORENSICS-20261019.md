# Local DP §4.4 — 历史 Spark Driver GET-only 来源取证（2026-10-19 EDT）

## 版本、触发与已验证范围

- 本轮起点 Healthcare Main `54284166dc473dbb132d9559383fde90ad75a9cb`；核对时更新到 `0db2556040f75ba9053c078ef2e37e782b821a4f`，随后最新开工 Main `c930c429da8d4539cd4194c039b1c50f7531d022`。两段 Git Compare 的文件变更仅涉及 Fabric Bootstrap，没有触及 `local-data-platform/` 或本 Change 的 `tasks.md`。本轮证据 PR 只更新本 Change 文档，不修改业务源码。
- Self-Runner 起点 Main `c4dc322274f7f98b1fe1ae23ec9c892be6020a6c`；正式 [PR #145](https://github.com/JohnZhang-DataForge/Self-Runner/pull/145) 已合并至 Main `1beb89e0bac5af298ad66e4273c976c4ed6b253d`。该 PR 发布固定的 GET-only 探针 `src/ci/local_dp_spark_historical_driver.py`、单测和 `scripts/ci/tasks/task990/step05.sh`，并更新操作规范。正式 PR **不包含**一次性 Request。
- 实验 [Draft PR #144](https://github.com/JohnZhang-DataForge/Self-Runner/pull/144) 的一次性 `requests/task990/step05/run-001.json` 提交 `e3a3c080492d71a7828e7bc5bd5aa23d65d09f4b`，触发现有 `generic-task-executor.yml` / `dw-runner-set` 的 `validate`；真实 [Run #39352931142](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39352931142) **SUCCESS / FINAL_STATUS=PASS**。实验 PR 已关闭未合并；无 Request进入正式 Main。
- 7/7 Spark 探针离线正/负向测试 + 4/4 临时 ServiceAccount kubeconfig 测试：**11/11 PASS**。Kubernetes 调用限 `dw-spark`：三个固定 SparkApplications、对应三个 ConfigMaps、Pod 列表的 `kubectl get -o json`。无 `exec` / `logs` / `apply` / `create` / `delete`；无 DAG、Spark 作业、Writer、PG、S3 或镜像操作。只将允许字段、哈希和状态写入 Runner Artifact，不导出原始资源 JSON / Secret / Token。

## 实际核验：三个已完成应用（只读 GET）

| SparkApplication | Driver Pod 当前 Phase | MainApplicationFile basename | 源码 SHA256 与此前固定 Git 来源 | Driver ConfigMap mount 声明 |
| --- | --- | --- | --- | --- |
| `task003-encounter-20261008t234726z-1658454` | `Succeeded` | `synthea_encounter_adapter.py` | `c042109b6f20939bcd82f037617f2c93599e564adb98ff6ce7006ea597f5ce8e` MATCH | PASS |
| `task003-encounter-raw-20261009t005128z-1681690` | `Succeeded` | `publish_canonical_entity.py` | `360f587e60af0875a70499fbff2e028fa73f1650c0fcd3e131bf59233f223e9a` MATCH | PASS |
| `visit-proc-write-72858de1ee39bd1eeb3e` | `Succeeded` | `run_visit_processed_writer.py` | `8d2c855c364b2cec366f92236145109e2eb11a6c44c924c14bb192a51910f8a5` MATCH | PASS |

每个 Application 均为 `COMPLETED`，`mainApplicationFile` 精确匹配 `local:///opt/spark/app/<basename>`。上述初轮探针对 Driver mount 的判断仅是 **SparkApplication spec 声明**；以下后续 Run #39354098106 已单独核对历史 Driver Pod 实际 `spec.volumes` 和 `container.volumeMounts`，不把初轮历史报告改写为当时已验。固定源码哈希出自已核对 [Run #39347241695](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39347241695) 与固定 Healthcare Git Commit `72c1c40c7faecb3c816a7ccb000c7b0595f8d897` 的比对，不代表新的 Spark Image 构建。

## 后续新增：实际 Driver PodSpec 独立取证 PASS（美东 2026-10-19）

- **正式 Self-Runner 来源**：[PR #147](https://github.com/JohnZhang-DataForge/Self-Runner/pull/147) 已合并 Main `4c83fd269b147cb5459fd4f700b15090fb7ed35a`，新增 `src/ci/local_dp_spark_driver_podspec.py`、`tests/ci/test_local_dp_spark_driver_podspec.py`、`scripts/ci/tasks/task990/step06.sh` 和操作证据说明。正式 PR 仅包含与测试 HEAD 完全相同的三个代码 Git Blob；不包含 `requests/**`。
- **实验真实执行**：[Generic Task Executor Run #39354098106](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39354098106) / 实验 commit `babad9ce1f99d52f179a73a7726dd8041818e98c`，固定 `validate` + Self-Runner `dw-runner-set`，15/15 专项正负测试 + 4/4 SA tokenFile 安全测试（**19/19 PASS**），`PODSPEC_GATE=PASS`、`FINAL_STATUS=PASS`。实验 Draft [PR #146](https://github.com/JohnZhang-DataForge/Self-Runner/pull/146) 已关闭且**未合并**，一次性 Request 无法因 Main Push 再次触发。
- **真实只读行为**：每个固定历史 Application、ConfigMap 和与 `status.driverInfo.podName` 绑定的 `<app>-driver` Pod 各一次 `kubectl get -o json`，只读检查 `dw-spark`。严格限制 Pod 命名、目标 Application、驱动容器身份；无 Pod exec/logs、无 Secrets、无 Spark Submit、Job、PG/S3、业务 Writer 或 GHCR 发布；不导出原始 PodSpec、Container args/env、ConfigMap 原始内容。
- **结果范围**：三个历史 Driver Pod 均为 `Succeeded`；3/3 **实际 Pod** 的 ConfigMap 卷与驱动容器 `/opt/spark/app` 目录挂载（或安全支持的同文件 `subPath`）一致；3/3 Pod 容器镜像引用与 SparkApplication 指定的镜像引用相同；3/3 容器状态含不可变运行镜像身份 `sha256:8ca5526e00dbbe4b360245ced4ac2da6f60d195e05d9e088b9eb1426259d93a6`；3/3 Pod 启动参数中可见与 `mainApplicationFile` 对应的预期主程序路径。
- **重要区别**：`IMAGE_PIN_GATE=NOT_PINNED`：当时声明使用镜像 Tag，并非 `@sha256` 不可变引用；运行时镜像 Digest 是独立的可追溯事实，不能倒推声明曾被 Digest 锁定。启动参数和挂载只证明 PodSpec 元数据，不等于历史 Driver 内 Python 进程实际导入；`HISTORICAL_DRIVER_MODULE_FILE=NOT_VERIFIED`，绝不宣称 Import Runtime PASS。

## 更新后的证据等级 / 未通过范围

**已经证实**：三个历史 SparkApplication `COMPLETED`、各 Driver Pod `Succeeded`；三份 ConfigMap 源码 SHA256 与冻结 Git Commit `72c1c40c7faecb3c816a7ccb000c7b0595f8d897` 字节比对一致；`mainApplicationFile` 来源与对应 ConfigMap、**实际 PodSpec** 挂载、启动参数均一致；三个观察到的运行镜像 Digest 相同。上述属于 **历史对象的声明/Pod 元数据核验 PASS**，并不是实时运行或业务 E2E。

**仍未证明**：
- 历史 Python 解释器真正的 `module.__file__`，因为 Driver 已结束；PodSpec、ConfigMap、哈希与镜像均不能事后重新构建 Interpreter 的在内存导入状态。
- 原镜像声明的不可变 Digest Pin（明确 `NOT_PINNED`）、所有 Spark 模块完整调用链、其它历史消费者、全部 Airflow DAG 的实际业务 E2E、4.2–4.7 全部 Runtime/E2E 兼容以及 4.1/4.8 动态消费者完全排除。
- 后续以新代码、新镜像、新 Batch 执行的业务兼容性；老 Driver 的 Pod 元数据不能代替未来新 Driver 的实时导入验证。

## 下一安全动作及历史源码冻结

当前不需要为了完善旧 Driver 元数据再部署新的 SparkApplication，也不能通过重跑历史 Driver 获取已丢失的解释器运行态。下一步先在已有静态+Runtime 兼容证据上审查 **4.4 是否仍有其它可只读闭合项**（Airflow DAG 唯一加载与其余 Spark manifests 消费者），并开展 4.1/4.8 的动态依赖/HOLD 分类。若确有新的 Driver `module.__file__` 实时验证需求，必须先另行审批独立的无业务 Secret、无 PG/S3、无 Writer、无业务 Volume mount 的隔离 smoke 设计；不得偷换为旧 Batch 重放。

**OpenSpec 4.4 继续 PARTIAL；4.1/4.8 OPEN；4.9/4.10 HOLD；本次及累计已批准历史文件删除 = 0。**
