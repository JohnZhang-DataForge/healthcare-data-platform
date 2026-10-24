# Design

> 状态：2026-10-22 **DESIGN / NOT IMPLEMENTED**。本文件取代本 Change 2026-10-18 的“保留旧 DAG/PG/镜像身份、各模块长期兼容”实施方案，历史文档与 Runtime 结果不作修改。用户允许丢弃开发合成业务数据，因此采用 **Clean Slate Business State + Functional Rename**，不是重建整套基础设施。

## 1. Baseline & non-goals

- 冻结只读基线：Healthcare Main `b99c5e8d4f3e5e4481facde3f7196569645125fb`；Self-Runner Main `79464c92cf244508d81c99fc25be9cd90820bad1`。当前 Local DP Git Tree 360 tracked，234 个路径带 `task001`–`task004`（12 / 19 / 121 / 82）；该计数不是最终重命名矩阵。
- 既有 NEW_ONLY 与 Discovery 最新有效 E2E / 定时调度证据见 [Local DP relocation](../relocate-local-data-platform/tasks.md)；清理后 5 个新 Batch 真实 COMMIT/PG readback/同 Batch SKIP，证明现有业务链路可运行，**不**证明改名后可运行。
- 现有 `modernize-legacy-task-code` 旧 R2–R5 是原先为保留历史业务接口设定的路线，在本方案下**不再要求**兼容适配层、历史 CDM 记录迁移或旧 Batch replay。保持算法、Schema 语义、幂等、Fencing/Permit、异常/事务边界；不是重新设计 Writer、Spark、Airflow 或 Portal。

## 2. Rename inventory contract

执行前在 **同一次**冻结最新双仓 Main SHA 上生成 machine-readable old→new matrix：
`old_identifier, kind, old_path, proposed_new_identifier, owner, direct_consumers, dynamic_consumers, persisted_state, external_consumers, collision, test_coverage, deletion_scope, decision`。

扫描对象包括：
- `local-data-platform/` 全部 Git tracked 路径及文件内容，Python import/importlib/entrypoint、脚本与 Shell source、SQL DDL/DML/function/GRANT、Airflow DAG/task_id/XCom/Jinja、Spark manifest 和 S3 URI/Batch 字段；
- 8 个 Dockerfile（父子镜像、Build Context、COPY、`PYTHONPATH`、`/opt/task004`、ENTRYPOINT）、GHCR Workflow 的 package/tag/digest、Helm GitSync 和 Airflow parse paths；
- 两仓 GitHub Actions/Self-Runner workflow、`workflow_dispatch` 手动入口、K8s YAML/Template/RBAC/SA/Secrets 引用、CODE.md 和源码静态断言；
- PostgreSQL PG17 的 `etl.task004_*` 等现行**实际对象**与 FK、sequence、role、function、legacy ledger；确切表清单来自 SQL 源码和只读系统 catalog，不由示例名推断 Live 资源；
- Airflow 已部署 DAG ID 与运行中 DagRun、S3 Bucket/Prefix 所有权、旧镜像/K8s 消费者、Marquez/Portal 观测引用。

例示目标命名（不是已执行的唯一映射）：

| Legacy identifier | Proposed functional target | Remarks |
| --- | --- | --- |
| `apps/task001/` | `apps/intake/` 或 `apps/landing/` | 逐文件按职责拆分 |
| `scripts/task002/` | `scripts/person/` | canonical & OMOP 前置 |
| `apps/task003/` | `apps/visit/`、`apps/omop_writer/` | Visit/Writer 各归其职 |
| `apps/task004/` | `apps/orchestration/`、`apps/landing/`、`apps/omop_writer/` | 不机械改成一个大目录 |
| `airflow/dags/task004_processing_pipeline.py` | `airflow/dags/synthea_processing_pipeline.py` | 新 DAG ID，旧 DAG 后退役 |
| `healthcare-data-platform-task004-runtime` | `healthcare-orchestration-runtime` | 更新 8 镜像构建闭包与消费端 |
| `task004-control-runtime` | `healthcare-orchestration-control` | 名称/RBAC/SA 同步 |
| `etl.task004_batch_ledger` | `etl.pipeline_batch_ledger`（候选） | 先验名冲突、DDL/访问控制；不能覆盖已存在 Landing Ledger |

`task_id` 是 Airflow 原生 API 的合法字段，不能被“禁止 Task 编号”误删；历史 Git 提交、OpenSpec Task 编号、文档史料、已完成 Run 和已生成日志不要求改写。对真正参与业务身份的版本/Hash/Batch 字段，按 Contract 逐项审查，不替换用户数据内容。

## 3. Fresh-state isolation and cutover

**推荐路径 A：同一 PG17 实例内独立的新开发业务数据库（例如 `omop_naming_v2`）**。该库包含自身完整的 `cdm`、`etl`、Landing Claim 业务表及必需的函数、Sequence、GRANT/Role 授权；S3 使用明确归属的新测试 Prefix/唯一 Batch；DAG 用新 ID，Kubernetes 业务资源用新名称；运行配置指向新开发库，不与旧 OMOP/ETL 表形成跨库共享 ledger。保留同一 PostgreSQL **实例**、SeaweedFS、Airflow 服务、Spark/K8s 集群，绝不重建底层存储或系统数据库。创建新 DB 需要检查现有连接权限、硬编码 dbname、Schema 初始化脚本及 DB Role/GRANT；未验证前不得声称 A 一定能零改动实施。

**备选路径 B（若新库不经济/依赖过重）**：在被明确识别的开发业务数据库里计划一次排他切换窗口；先停止旧 DAG/Job/Writer 并确认无在途 COMMIT，再按确切 DDL reset 允许销毁的 OMOP/ETL 业务对象、重新初始化新命名的业务 Schema，最后新 E2E。**B 无“新旧数据库同时可运行”的承诺**；同库 `cdm.person` 等没有物理隔离就不得双写，更不能在新 Batch 成功后清空共用 CDM 表误删新数据。

无论 A/B，按以下规则处理：
1. 旧 DAG 在新自动调度启用前暂停，确认旧 Pod、Spark、Job、Writer、Ledger 独占；新代码先只允许隔离/手动测试，禁止旧新并发处理同一 Batch。
2. 初始化新 DDL 与权限、FK/Sequence、Ledger/Claim/Checkpoint/ID Map；**不导入旧数据**。保留新的空库初始状态检查，元数据清理仅选中明确归属的旧 DAG ID。
3. S3 清理必须依据 Bucket/Prefix 精确列举和 ownership manifest，保留新 Batch 的对象；禁止 Delete Bucket、删除 SeaweedFS PVC 或盲目 `rm -rf`。
4. 旧表的 DROP 必须显式 allowlist，对比新旧数据库/Schema 名称，先独立读回新表成功，再删除旧对象；绝不使用未经枚举的广域 CASCADE。
5. 旧 GHCR 包/镜像版本、K8s SA/RBAC/Job/ConfigMap、旧触发 Workflow 经真实消费者查询后才退役；保持旧 SHA、PR、Run 和事故证据可检索。

## 4. Ordered implementation

**Phase 0 — Spec approval / no runtime**：本 PR 修订现有 OpenSpec 的 Proposal/Design/Specs/Tasks；原正式代码、旧数据和环境保持原样。执行前读取 `AGENTS.md`、`SAFE-OPERATIONS.md`、`SESSION-COORDINATION.md`，并按最新双仓 SHA 重扫。

**Phase 1 — Inventory + exact mapping**：制作全部活跃 Task/Step 源、导入、SQL/DAG/K8s/GHCR 和 Self-Runner 消费者矩阵；确定 A/B 隔离方案、所有新名、表/role/FK/存储范围；先检查名称冲突和所有权。把业务字符串与历史证据区分，避免误改 Airflow `task_id` 等正式 API。

**Phase 2 — Rename implementation PR(s)**：允许少量按依赖闭包的 PR 或单次有界 PR，同步代码、CODE.md、SQL/bootstrap、Docker、CI、Airflow DAG 与资源声明；保持原始业务代码算法和版本 Contract。构建8/8无缓存镜像（5 parents + 3 children），全量 module import/entrypoint/跨仓消费者负向检查。此时可以先合并已过 CI 的完整源码与声明，不声称 Live E2E。

**Phase 3 — Deploy fresh business state**：按已核准目标在现有 PG17/S3/K8s/Airflow 上准备隔离业务数据库/前缀、DDL、Grants/RBAC，新镜像与新 DAG；防止旧 DAG 与新自动调度同时运行。核对真实 GitSync SHA 与 Pod imageID/digest，完成新 DAG 手动受控执行，然后检查新 Discovery 正常定时行为。

**Phase 4 — Prove and retire**：至少 2 个*全新唯一* Synthea Batch，验证生成及完整 18 CSV、Manifest/Hash、S3 READY、Airflow exact selection、Spark Person/Visit/Reconcile、Writer Atomic COMMIT、独立 PG CDM/FK/Ledger/Stage/ID Map/Checkpoint 读回；每 Batch 第二次运行 SKIP 且零 PG 变化。另验证错误 Manifest、重复 Batch、Writer Fencing、multi-part Parquet、race mapping、Discovery preview 上限及自动调度的负向/边界合同。全部通过后，生成**精确旧资源 DELETE allowlist**；删除旧 DAG 元数据、旧 PG 业务对象、S3 旧测试 Prefix、K8s/GHCR 资源前再核对实时消费端，删除后确认没有旧业务标识被当前运行入口消费。

**Phase 5 — Closeout**：新代码路径/标识的保留性静态断言、组件 CODE/导航、项目状态、跨仓 PR/Run、Source SHA/实际 Digest/Batch/Manifest/independent readback 证据同步；完成后才将 Change Archive。旧 Change `relocate-local-data-platform` 独立记录其剩余 scope，不将新迁移替代为旧 Change 的虚构“完成”。

## 5. Failure / rollback model

- **静态/Build 失败**：不发布 `:latest`、不启新 DAG；修复代码 PR 或恢复 Git SHA。原生产式流水线仍为开发环境基线。
- **新状态 E2E 失败**：不删旧资源；保留失败 Run、新 S3/PG 状态做独立只读核对；未知 Commit 禁止盲重试同 Batch。只可清理已确定的新测试业务状态并重建新唯一 Batch。
- **已停旧但尚未删除**：回滚到旧 Git/image/DAG 配置并重新检查资源独占，不能在旧数据库/新数据库同时自动启动消费。
- **旧资源已经删除**：业务数据有意不保留，允许从 Git/DDL 和新合成 Batch 全新重建；**不承诺恢复旧合成数据、旧 DAG history 或旧 PG ledger**。Git revert 不等于 DB/S3 rollback。
- 任何未能证明归属的 DB/S3/Airflow 元数据、PG14/Marquez、Azure/Fabric、底层 PVC/StorageClass、Secret 及无关系统均为 **HOLD**。如其它 Session/Run 活跃，必须协调并延期有副作用动作。

## 6. Acceptance & evidence gates

静态：精确 Main/PR SHA、双仓全量 ref matrix、旧运行标识的生产入口负向扫描、组件 CODE.md、Docs links、OpenSpec strict、DagBag、Unit/Contract、8/8 Clean Build+Smoke+Import、Writer 多 Parquet/Native Race/Selection/Claim/Fencing 负向回归。所有适用 CI 在最终 PR HEAD PASS 才合并代码。

真实：记录新 DAG ID、真正执行的 DagRun、GitSync SHA、每个 Pod imageID/Digest、环境/DB/Schema/S3 前缀、每 Batch ID + Manifest SHA + S3 Readback、PG 前后 Person/Visit 计数及 Ledger/Commit/Checkpoint 独立证据、SKIP 零变化；至少一次新 DAG 的真实定时 Discovery 成功或记录未验证阻断。旧资源删除须有逐资源 allowlist 和删除后的缺失/无消费者证据。

**本规划 PR 的可证实结论上限**：OpenSpec 方案已写入分支、Schema/链接/治理 PR Gate 是否通过；绝不宣称 Rename、空库初始化、E2E、S3 删除或旧 DAG 清理已经发生。
