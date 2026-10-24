# Design

## 1. Current baseline / evidence boundary

Healthcare `main` 只读冻结 SHA：`e6a70193428bc995a86619617dc802a70ae85572`（2026-10-24 检查时的仓库 HEAD，最后 Git commit 时间 2026-10-22 UTC）。本次创建 Change 不等于集群在线检查。

历史事实（详细出处见 `documents/systems/platform-portal/README.md`）：
- Marquez 0.51.1 API/Web + `dw-postgre14` PG14（历史 37 张 metadata 表）、`dw-marquez/marquez-web-lan` Web-only NodePort 30999 曾验证成功。
- Airflow 3.2.2 + OpenLineage Provider 2.17.0 A3 `platform_portal_openlineage_probe` 的真实 Task Run 已读回，但仅 Probe。
- Spark A4：隔离 `SparkApplication` 与计算完成，Marquez 收到 Spark Run，但业务 Job 的 `latestRun` 为空、Run 挂 `unknown`、输入/输出 DatasetVersion 计数均为 0。原 Live Workflow 失败，后续只读验收部分 PASS；不能抹掉原失败。
- Local DP `new_only_omop_consumer` 用 KubernetesPodOperator 调用 `task004-runtime` 控制容器，再创建真正的 SparkApplication。仅给 Airflow KPO 打标**不能**替代实际 Spark Listener。
- `dw-postgre` PG17 OMOP 与 `dw-postgre14` PG14 Marquez 必须保持隔离。

## 2. Integration boundary and ownership

```text
Synthea batch + immutable S3 manifest
  -> Airflow new_only_omop_consumer / real DagRun
     -> KPO control pod (existing task004-runtime identity)
        -> SparkApplication Person / Visit / Reconcile
           -> real S3 Landing/Processing Dataset I/O
     -> gated OMOP Writer -> PG17 (independent COMMIT readback)
Airflow Provider / Spark Listener -> Marquez API -> PG14 -> official Marquez Web
```

- Airflow：以目前真实 DAG ID `new_only_omop_consumer` 做 selective enable；保留任务结构、XCom、schedule、Claim 和 commit 许可语义。核实事件产生所在 Scheduler/Worker 组件的有效 Provider 与 Transport，避免仅修改 Scheduler 后以为全链路覆盖。不要把 Airflow task_id API 字段与历史 `task004` 项目标识混为一谈。
- Spark：先修隔离 Probe 再接业务。考察 Listener 实际生成的 START/COMPLETE、namespace、name、run UUID、facets 与输入/输出 Dataset；根据真实事件定位 `unknown` 原因而非凭猜测重命名；在现有 SparkApplication 渲染模板按 job 注入所需配置，不全局改 Operator。
- Parent association：先验证 Airflow DagRun/Task 与 Spark job 的稳定关联键；若采用 OpenLineage parent facets，应先验证当前 Provider/Listener 版本支持的精确配置和实际 emitted event。不合适时保留外部可读 Batch/Run 映射证明，不能手工伪造 Airflow parent 或 POST 成功事件来填洞。
- Dataset：优先使用真实 S3 Landing/Processing 的可读取输入和实际持久化 Parquet 输出，在 Marquez API 查询两个 Dataset 的 input/output edges 与 versions；归一化真实 URI/namespace 并避免把随机临时文件、临时 ConfigMap fixture 当生产数据。不要把 Batch SHA、PG 密码、患者行内容、凭证置入公开 facets。
- Writer：Spark 完成不等于业务 COMMIT。Writer 执行状态以其已验证成功的合同、PG17 `etl` Ledger 和独立 read-only Person/Visit/FK/Checkpoint 读回为准；Marquez 中如需要业务终点映射，应有真实被授权写入所产生的事件/读回支撑，不允许外部伪造 COMPLETE。

## 3. Implementation slices and rollout

A. **P0 Static Spec**：建立 Active Change 和静态基线；本 PR 不执行共享 Runtime。
B. **P1 Runtime health inventory**：先检查跨仓活动 PR/Run、共享 DAG/Job 占用；经资源范围协调后才用只读 K8s/HTTP/PG14 metadata 查询服务及版本/EndPoint，既有 `marquez/tests/verify.sh` 会做短暂 port-forward，必须评估实际动作后方可执行；不运行 `deploy.sh` / `recover-web.sh` / `configure-scheduler.sh` 作为健康检查。
C. **P2 Airflow**：局部启用业务 DAG，单独验证真实 Job/Run 与 selective boundary，保留其他 DAG 默认行为。
D. **P3 Spark isolated**：最小独立真实文件输入/输出、确定 Listener 版本兼容、修复 Job/Run/Dataset 关联；static/unit tests 与受控 Live 是两个 Gate。
E. **P4 Business integration**：修改最少量的实际 SparkApplication 模板/控制容器打包，不改变 Person/Visit/Reconcile 算法；逐一验证事件，并验证 Airflow ↔ Spark 运行对应。
F. **P5 Fresh batch E2E**：全新 Batch 的 immutable READY、exact selection、Spark Person/Visit/Reconcile、Writer 原子 COMMIT、PG 独立读回、同批安全 SKIP 与 PG 零变化；Marquez 事件和 Dataset graph 可独立查询。若两个独立新 Batch 可经济运行则优先 2 个，否则至少 1 个真实 Batch 并明确残留覆盖缺口。
G. **P6 LAN showcase**：官方 Marquez Web 展示，形成可重复的只读演示指引；公网/自研前端在独立 Change 审核。

每个实质性 Slice 用局部 PR，`OpenSpec-Change: complete-platform-portal-lineage-integration` + 实际 `OpenSpec-Task` 引用该 Change，修改 `tasks.md` 并同步组件 `CODE.md`；适用 CI/测试通过后合并，再取新 Main/Digest 做 Run，不将 PR 的绿灯视为实机验收。

## 4. Safety / rollback

- 不执行旧 `modernize-legacy-task-code` 的 Fresh-State、DAG/镜像/SQL 重命名；保留现有 `task004` 外部消费者身份。
- Marquez Web NodePort 30999 仅 LAN 受控范围；Web 可能代理 API，不能直接作为无认证的公网只读应用。
- PG14 Retain PVC 非备份，严禁为排查 A4 删除/重建 PG14、覆盖 Secret/Helm 资源；OMOP PG17 与业务 S3/Claim 不得被 Portal Probe 写入。
- Live K8s/Airflow/Spark/S3/PG 操作前查活跃 Session/Run/Pods/DagRuns、实际脚本副作用、精确允许资源/身份，得到相应授权；失败或未知提交状态停止盲目重试。
- 新 Listener 导致 Spark 失败、事件身份偏差、Provider 设置扩散或数据泄露时，回退该局部观测配置/镜像引用；保留现场及错误 Run，先证明业务不受影响，再进入下一步。回滚配置不等于回滚已提交业务数据。
- 观测服务不可用不得绕过现有 Writer 授权；需明确和测试监听器不可用时的失败策略，不把无血缘的 Batch 宣称 Portal E2E PASS。

## 5. Evidence matrix

| Gate | 必须收集 |
| --- | --- |
| Static | Main/PR SHA、diff、OpenSpec Strict/Trusted Gate、CODE/Docs 链接、单测 |
| P1 | Namespace/Deployment/Service/Endpoint/PVC 的只读读回、Marquez health/API、PG14 metadata、日期与执行环境 |
| Airflow | selected DAG/Task run_id、Provider/Transport/Selective settings、真实 Marquez namespace/Job/Run 查询 |
| Spark | 精确 SparkApplication/image/JAR、真实 START/COMPLETE Run 及正确 Job 关联、真实输入/输出 Dataset |
| Business E2E | 唯一 batch_id、manifest SHA、GitSync SHA、Pod imageID/Digest、Spark run、Marquez graph、PG17 独立 commit/checkpoint/person/visit、same-batch SKIP PG 零变化 |

## 6. Known unknowns

当前 Kubernetes/PG14 服务是否在线；Spark A4 `unknown` 的真实原因；Spark 3.5.7/Scala 2.12/JAR 1.47.1 当前网络和兼容情况；Listener 对真实 S3A Parquet Dataset 的自动采集质量；Airflow-initiated Spark parent facets 的兼容传递方式。全部必须用对应读取/测试而不是文档推断。

## 7. 2026-10-24 Local-dev versioning simplification (current decision)

用户确认当前先优化迭代速度：Portal P2 的 Airflow OpenLineage 是 **GitSync DAG + Provider/Transport 的选择性接入**，不用新建第九个镜像，也不为 `portal-v1.0` 单设另一套 DAG 镜像引用。已有业务 KPO 控制容器主要使用 `:latest` 与 `image_pull_policy=Always`，GitSync 更新与镜像重构是两种不同操作，不能混同。

P2：维护未合并 PR #416 的源代码和独立验证，避免意外触发 Writer；从代码变更传播到共享 DAG 解析有独立部署和运行 Gate，不依赖镜像 Build。

P3：先在隔离 Spark Probe 修复 Listener Job/Run/Dataset 真正血缘；只有 Listener JAR/渲染代码需要打包进某个镜像时，才识别精确受影响的 Dockerfile/父子依赖。不能为了演示把全部 8 镜像重构。

P4：若 Spark 控制/Writer 应用变更影响现有镜像，则手动单镜像 `validate` → 明确批准 `publish-latest`，保存唯一 SHA/Run tag、上个 Latest Digest 的回退 Tag、新 Digest、来源 SHA/Run。保留原 DAG `:latest` 引用，不增设候选标签切换参数。历史候选 `portal-v1.0` 可以为未来稳定发布保留，但不是当前 Local 测试依赖。

P5：开始真实 Batch 前确认无其它 Session 的冲突 Run、GitSync 版本、各新建 Pod 真实 imageID/Digest、Marquez 事件与 PG17 Readback；单独批准业务副作用。发布 `:latest` 会影响**未来**新建 Pod，已运行 Pod 不自动换镜像；GHCR 保留历史版本也不代表回滚自动发生。镜像发布和共享 Airflow/Writer Live 操作仍互不默认授权。
