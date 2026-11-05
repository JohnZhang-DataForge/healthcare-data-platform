---
status: active
scope: test-and-evidence
last_verified: 2026-10-16
source_sha: 63524cc244b64f784ff0e7887caa8e63fed5049f
---

# 测试、验收与证据规范（Testing & Evidence v1）

> **适用对象**：Healthcare 代码、Contracts、GitHub Actions、Kubernetes/Airflow/Spark/OMOP、Azure/Fabric、仅文档 PR。与 [Agent 规则](AGENT-RULES.md)、[开发工作流](DEVELOPMENT-WORKFLOW.md) 配合使用。本规范不要求普通改动执行无关的大规模 E2E。

## 1. 测试层级与可声明的结果

| 级别 | 证据 | 可以声称 | 不能声称 |
| --- | --- | --- | --- |
| REVIEW / STATIC | diff、链接/语法检查、`terraform fmt/validate`、DagBag parse | 源文件或静态合同满足被检查项 | 已部署、完成 DAG、业务入库 |
| UNIT / CONTRACT | 单测、负向用例、版本化 Contract 对账 | 测试范围内的规则与逻辑满足断言 | 真实 S3/PG/Airflow 联动成功 |
| BUILD / PACKAGE | Workflow Run、GHCR 推送、镜像 Digest、镜像内入口检查 | 指定 Source SHA 的可用产物已构建（限实际检查） | 运行环境已更新或持久化业务写入 |
| CONTROLLED RUNTIME | Runner/Pod/SparkApplication 的真实运行、日志、资源状态 | 对指定版本、环境和真实输入的本轮动作确实运行 | 未经读回便宣称数据完整提交或所有异步任务完成 |
| E2E / DURABLE | 实际 DagRun + 下游完整执行 + 独立只读 S3/PG 数据验证 + 必需幂等检查 | 对明确 Batch、版本与链路的验收通过 | 其他批次、所有并发故障和将来运行都必然通过 |

**准确表达**：`PLAN ONLY`、`NOT DEPLOYED`、`STATIC PASS`、`RUNTIME PASS`、`E2E ACCEPTED`。测试通过只对其覆盖的代码 SHA/配置/输入有效。GitHub Run 本身 SUCCESS 但业务断言失败时，不得将其当成业务成功；反之历史某个 Workflow 后置取证失败，也不能不检查真正业务动作就声称所有业务都失败。

## 2. 按变更选最小必要测试

- **纯文档 PR**：检查新链接、事实来源、状态/权威迁移、Git diff 的路径范围；不需要执行 Self-Runner、Spark 或 Terraform。
- **Python/SQL/合同变化**：相关单测、负向测试、Schema/版本、边界值、重复运行；涉及映射时检查稳定 ID 与 FK。
- **Airflow DAG**：DagBag/依赖图静态检查；变更影响调度或业务执行时另做受控真实 DagRun/Task 状态验证，不自动触发持久化 Writer。
- **PySpark**：输入读取、去重/Schema/结果确定性、输出前后行数与独立 S3 回读；必要时用固定版本 SparkApplication 做 Runtime 证明。
- **PostgreSQL Writer**：只读 Source/ID Map/Claim 预检 → 独立审批的事务实验/ROLLBACK 或受控 COMMIT → 独立连接核对 ledger/stage/ID map/CDM/reconciliation；必须检验重复批次不会二次写入，不以异常后猜测“应该没提交”。
- **Terraform/Fabric**：格式/Validate/Plan 的源版本、组件和远程 State 绑定；资源存在或 Fabric 功能生效必须另有 Apply/部署/独立验证证据；Plan 默认值不代表授权。
- **OpenLineage/Marquez**：Spark 计算成功、Marquez Run 存在、期望 Job 关联正确、Dataset I/O 血缘齐全是不同验收项；必须分别判断，不以 Smoke PASS 泛化。
- **冻结/敏感数据操作**：检查兼容性、受控授权、持久化前后差异和清理，禁止为了证明“可重复”重放旧的一次性批次。

## 3. 可追溯证据的最小结构

需要真实验证时，在 Run Artifact、PR 或相应 Closeout 中保留以下字段（按领域适用性）：

```text
REPOSITORY / BRANCH / EXACT_SOURCE_SHA=<full 40-digit sha>
CHANGE / TASK / STEP=<bounded change>
TEST_LEVEL=<static|unit|contract|build|runtime|e2e>
RUN_URL / RUN_ID=<real value when executed>
ENVIRONMENT / COMPONENT=<target>
BATCH_ID / MANIFEST_URI / MANIFEST_SHA / IMAGE_DIGEST=<if used>
EXPECTED / ACTUAL=<independent assertion values>
MUTATION=<none|temporary-resource|durable-write>
CLEANUP=<not-required|verified|pending>
FINAL_STATUS=<PASS|FAIL|BLOCKED|NOT_RUN>
NEXT_ACTION=<bounded next step>
```

**不能填写假运行号、猜测 SHA 或隐瞒 `NOT_RUN`**。报告用实际 Source SHA、Workflow Run/Artifact 和断言结果；不要求为普通开发或文档审查单独创建 Shell 输出格式。

**数据身份与执行身份分开记录**：`batch_id` 表示输入数据批次，`pipeline_run_id` 表示一次运行；同一 Batch 可被多次安全检查或消费。最终结果以 Contract、持久状态和对应 Run/Artifact 为证，不仅依据 Workflow 成功状态。

## 4. E2E 结果如何成为权威

E2E 最终验收必须说明具体运行范围：版本/Manifest/Batch、实际 Airflow Task 结果、Spark 数据范围、数据库最终状态、独立只读读回和重复批次处理。已完成的三个 NEW_ONLY Person/Visit 批次结论见 [TASK004 Final Acceptance](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)；该证据**不代表** Condition、复杂并发恢复或整个 Azure 业务管道已完成。

业务流程与验证可能在不同提交、不同会话完成；Final Acceptance 应分开列出历史已完成事实与最新版本需要重新证明的范围，避免把历史测试错误套在当前 HEAD。任何共享 Runtime 的再验证都需要符合审批和执行协调规则。

## 5. 完成条件与失败处理

- 一个 STEP 通过：规定的断言全部 PASS、必要副作用与数据后置状态可解释、真实证据可读、PR HEAD/测试对象匹配。
- 未满足则 `BLOCKED` / `PARTIAL`，明确阻塞点、已核实数据、下一步；不因准备了计划而宣布 COMPLETE。
- 失败后先区分测试代码缺陷、资源状态不符、环境中断、权限/凭据、真正业务处理错误。非幂等 COMMIT 或未知状态**先只读审计再决策是否恢复**。
- 不要求每个小型 STEP 都新建 Closeout：普通结果存 GitHub Run/Artifact 并在 PR 索引；重大里程碑及独立验收用简洁证据文档。


## 6. 新增自动化测试的唯一目录和 CI 实际发现门禁（P3）

- **唯一新路径**：`.github/quality/tests/<system>/<component>/test_<behavior>.py`；复杂组件可在 `<component>/` 下按真实能力再分层。系统例：`azure-fabric/notebook`、`azure-fabric/openlineage`、`azure-fabric/warehouse/omop-foundation`、`local-data-platform/spark`、`platform-portal/api`、`shared-data-engine/canonical`。测试归属以**被测代码实际唯一 owner** 而不是开发任务号 G3/G5/TASK 决定。
- **Fixture**：只将新建的非敏感合成测试数据放 `.github/quality/fixtures/<system>/<component>/`；已存在的源码路径 Fixture 不在 P3 未获批准的情况下移动。不得提交患者真实数据、密钥或账户数据。
- **正式质量脚本**：新增静态检测放 `.github/quality/scripts/`，并同步 [Developer CODE](CODE.md)；业务运行代码仍属于原组件，不能放到质量脚本目录。
- **现有历史例外**：Legacy 源码 `tests/` 仅能按 P1 精确 baseline 维护旧文件；迁移后旧路径必须删除，不能在旧目录复建。P3 不自动触及 Local/Portal/Shared 既存文件。
- **CI 必须发现并执行**：每组 workflow 的 `paths` 要覆盖新测试位置；运行时使用指定 `start_dir` 的 `unittest.TestLoader().discover()`，断言 `countTestCases() >=` 已验收基线、应有测试文件数符合库存、无导入错误，随后执行 `unittest.TextTestRunner` 并按结果使 job FAIL。不能以 `0 tests`、纯文件存在或全局根级发现 179 tests 证明子目录测试已运行。
- **迁移与退休**：先确认源码和真实调用方，再在同一 PR 同步目标 CODE.md、Workflow、文档与 OpenSpec；固定原始方法/文件清单和 Git SHA。仅在已证实重复/停用且不减少必需回归断言时才允许删测试，旧版本用 Git SHA/PR 追溯，不另建 `archive/tests/`。
- **执行边界**：GitHub Hosted 单测/离线 PySpark 不代表真实 Fabric DataPlane/DW 写入成功；真实云端测试、历史 Batch 回放或持久数据变更仍须独立授权及读回。
