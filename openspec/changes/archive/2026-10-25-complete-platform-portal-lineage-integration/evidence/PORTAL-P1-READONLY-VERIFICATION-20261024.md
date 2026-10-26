# Portal P1 — 2026-10-24 当前服务只读验证与历史血缘缺失

> **双重结论（不可混淆）**：基础设施与服务接口 **PASS**；历史 Marquez Job/Run/Dataset 持久化 **EMPTY / NOT PASS**。这不是完整 Portal E2E 验收，更不表示所有业务事件都被成功收集。

## Baseline

- 日期：2026-10-24 EDT（Workflow 于 2026-10-24 12:13 UTC 完成）。
- Healthcare 实测源码/Main：`26e2eb4f2bdc5835eb79ea0b6c96f2891a45c1ee`（P1 GET-only 资源检查器已并入）。
- Self-Runner 控制 Workflow PR [#244](https://github.com/JohnZhang-DataForge/Self-Runner/pull/244)：实施 HEAD `f6e59183f1b426d13049d2783cd14ffa026a34f3`；Squash Main `bd521563776d9fc7362e0a4d32c77b6b019ed1a9`。
- 最终真实只读执行 [Run #40093060512](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40093060512)，Job `120869536930`，结论 `SUCCESS`。GitHub Artifact `portal-p1-readonly-actual` 保存当时的 K8s/HTTP/PG14 输出；原始失败 Run 保留。
- 使用已有 Self-Runner `src/ci/local_dp_incluster_kubeconfig.py`，并以不可变 Main SHA `18d6f0bea73bf04b36413126408bea4868e74983` 获取既有已测组件。临时 Kubeconfig **tokenFile 引用** Runner Pod 挂载的 ServiceAccount Token，权限 `0600`，不复制/打印 Token，无 ServiceAccount/RBAC/Secret 修改。
- 无当前活跃/排队的 Actions Run 作为启动前只读协调线索；未知集群内其他 Sessions/Jobs 不能仅凭 Actions 状态否认。

## Executed checks — exact observed outcomes

| 检查项 | 当前实测结果 | 证据上限 |
| --- | --- | --- |
| 既有 in-cluster kubeconfig | PASS：`local-dp-incluster` | 只证实本次 Runner 具备执行这些明确操作的权限 |
| Kubernetes fixed GET-only inventory | **10/10 PASS**：`dw-marquez` namespaces/deployments/services/endpoints；`dw-postgre14` PG14 Pod/PVC/service | Ready/Bound/Endpoint，非浏览器公网可达 |
| Marquez Web HTTP | `/healthcheck = OK` | 当前内部 HTTP 健康 |
| Marquez API / Web proxy | HTTP 200；Web Proxy Namespace 与 API 返回一致；共 **3 Namespaces** | 当前 API/Web 读取工作 |
| PostgreSQL14 | DB `marquez`，`server_version_num=140024` (PostgreSQL 14.24)；READ ONLY transaction 生效；**37** public metadata tables | Schema 存在及可读，不证明有血缘数据 |
| REST Job listing | `default`、`healthcare-platform-airflow`、`healthcare-platform-spark-probe`：各 **0 jobs** | 旧 Event/Job 缺失；不是连接错误 |
| REST A3 Task Run | `observe_runtime`、`confirm_runtime`：各 **0 COMPLETED Runs** | 当前未找到历史 A3 Run |
| PG14 精确 COUNT(*) | `namespaces=3`, `jobs=0`, `runs=0`, `lineage_events=0` | **数据库本身**当前无 Job/Run/Event 行；不是仅 API 查询显示问题 |
| PG14 relation statistics | job/run/dataset/event 相关表 `n_live_tup=0`（估算） | 仅辅助，精确 COUNT 优先 |
| Runtime side effects | **NO** 部署/重启/新增 SparkApplication/触发 Airflow/SQL 写入/S3 删除/修改 Secrets/RBAC | 临时只读查询、`kubectl exec` 启动只读 Python/psql，以及受控临时 kubeconfig 产生了有限进程/本地临时文件 |

`kubectl exec -i` 在既有 Airflow Scheduler 容器内只执行内部 HTTP GET Python，在 PG14 容器执行 `BEGIN TRANSACTION READ ONLY ... ROLLBACK` 的 `psql`；**不是**无远程执行权限要求的纯 API GET。PG17 OMOP 没有被查询或修改。

## Four preceding attempts and resolution

| Run | 结果 | 确切症状 / 修复 |
| --- | --- | --- |
| [#40091736238](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40091736238) | FAILURE | Self-Runner 无 `kubectl` |
| [#40091775325](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40091775325) | FAILURE | 已修 Python stdin、仍无 kubectl |
| [#40091844026](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40091844026) | FAILURE | kubectl SHA256 安装 PASS，但无 `current-context` |
| [#40092803163](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40092803163) | FAILURE（有新事实） | 用户同意复用现有 SA Helper 后，K8s 10/10、HTTP Web/API PASS，但 REST 历史 Job 0 导致 fail-closed；尚未执行 PG14 |
| [#40092901888](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40092901888) | SUCCESS（有异常） | PG14 READ ONLY 37 张表 PASS；HTTP 历史 Jobs 0 如实输出 |
| [#40093002701](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40093002701) | SUCCESS | PG14 `pg_stat_user_tables` job/run/event 相关估算 0，名称/Schema 列表 |
| [#40093060512](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/40093060512) | SUCCESS / P1 最终 HEAD | PG14 精确 COUNT(*) 证实 0 jobs、0 runs、0 lineage_events |

历史 A3 和 A4 的原始正常及异常验收来自 2026-10-13/14 文档、不可修改的 Git/Run 记录；本次不能因此猜测数据库是何时、由谁或为何清空，也不执行数据库重建或人工 POST 虚假 Event。

## P1 closeout and next dependency

- **P1 的当前服务验证与异常登记任务（OpenSpec 2.2 / 2.3）已做完**：`MARQUEZ_INFRA_API_PG14=PASS`，`HISTORICAL_LINEAGE_DATA=EMPTY`。
- **不能**把 P1 的 Run SUCCESS 扩大为 A3、A4、真实 Person/Visit 血缘、完整 Writer COMMIT 或历史资料仍在 PG14。历史事件为空将成为 P2/P3 要用**新生成的真实事件**验收的独立关注点。
- P2/P3 **尚未启动**：恢复 Provider/Listener 事件发出、Job/Run 关联与 Dataset I/O 时先做 scoped 最小新事件测试；不能用构造的 `COMPLETED` JSON POST 回填、不能推断下游作业成功。
- 外部互联网/浏览器到 NodePort 30999、备份恢复和数据曾被删除的原因均**不在本次验收**，当前 `NOT_VERIFIED`。
