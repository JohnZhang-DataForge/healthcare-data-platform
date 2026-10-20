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

每个 Application 均为 `COMPLETED`，`mainApplicationFile` 精确匹配 `local:///opt/spark/app/<basename>`。探针对 Driver mount 的判断是 **SparkApplication spec 声明**，本轮还未对历史 Driver Pod 的实际 `spec.volumes` 和 `container.volumeMounts` 建立独立匹配证据，故不能把声明升格为已执行路径。固定源码哈希出自已核对 [Run #39347241695](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39347241695) 与固定 Healthcare Git Commit `72c1c40c7faecb3c816a7ccb000c7b0595f8d897` 的比对，不代表新的 Spark Image 构建。

## 证据等级 / 未通过范围

**已证明**：三个历史 Driver 对应的 SparkApplication 声明在真实集群存在并标记为 `COMPLETED`；当前历史 Driver Pod 仍有 `Succeeded` 资源记录；ConfigMap 数据哈希与先前 Git 固定版本吻合；Application 的 main 脚本路径和 Driver 挂载声明符合预期。实际的 GET-only Probe 与 11 个离线测试通过。

**尚未证明**：
- 这些已退出的 Python 进程当时实际 `module.__file__`；不能在退出后靠配置推断 Import 已发生。标记 `HISTORICAL_DRIVER_MODULE_FILE=NOT_VERIFIED`，不得声称历史 Driver Runtime Import PASS。
- 历史 PodSpec 的真实 ConfigMap volumeMount 及当时镜像 digest 绑定、Container 启动参数（尚未独立 GET 比对）；全部 Spark 模块、图片打包、后续新业务运行兼容与 E2E。
- Airflow 全集 DAG 唯一加载/实际 E2E、§4.2–4.7 完整闭包及 §4.1/4.8 动态消费者排除。

## 下一小步与清理冻结

1. **首先选纯只读**：基于历史 Driver Pod 仍存在这一新证据，下一独立 Gate 可定向 GET 对应三 Pod 的 **实际** Volume/VolumeMount、容器启动参数与 Image ID（仅安全字段、脱敏报告），与 SparkApplication/ConfigMap/source 的现有来源链交叉核对；仍不可宣称模块 `__file__`。先检查并行工作及源码，保持固定白名单和无原始 PodSpec 导出。
2. **Spark smoke 不是默认动作**：如果只读证据仍不能达到需要的 Runtime 证明，则先设计并审查 **独立非业务、无 Secret/PG/S3、无业务 Volume mount、禁止 Writer、固定 digest、隔离 namespace/ServiceAccount/资源上限** 的 Spark smoke，另行明确创建 Job/Pod 的授权；绝不为取证直接重跑历史 Batch。
3. **状态保持**：OpenSpec **4.4 PARTIAL**、4.1/4.8 仍 OPEN、**4.9/4.10 HOLD、历史源码删除 0、获批准删除 0**。新 Gate 的 metadata PASS 只是 §4.4 的一部分，不释放清理条件。
