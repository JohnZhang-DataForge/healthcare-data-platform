# Local DP — 三条历史 CDM GHCR 发布 Workflow 依赖分类与测试保护闭包

> 日期：2026-10-20（EDT）。只读审计基线 Healthcare Main `b440060c0f0f46053d7930b09b111ec92d803c7b`。OpenSpec Change：`relocate-local-data-platform`（4.1 / 4.2 / 4.3 / 4.8）。只允许 PR 范围的离线 CI，本文件不批准删除或触发任意 Workflow Dispatch/Push/部署。

## 1. 三条历史文件的逐项决策

| 历史 Workflow（Main 当前 Blob） | 原 Push 触发分支（GitHub branch search） | 原有离线测试 | Docker / GHCR 事实 | 分类 |
| --- | --- | --- | --- | --- |
| `.github/workflows/task004-cdm-rollback-image.yml`（`1151d15d3c96683e18f559e6c5b532408c88d290`） | `feature/task004-cdm-runtime-writer-rollback`（分支仍存在） | `test_step04f_cdm_writer_runtime_rollback.py`、`test_step04f_dynamic_pg_writer.py` | 旧根 `context: .`、`file: images/task004-cdm-runtime/Dockerfile`，Push 时 `push: true` | **E — Unknown/HOLD**（历史用途明确但分支及间接消费者未闭合） |
| `.github/workflows/task004-s3-writer-rollback-image.yml`（`672da82e4157cdd88aaaf7e2fd506b381473dc6a`） | `feature/task004-cdm-s3-to-writer-rollback`（分支仍存在） | `test_step04f_s3_writer_rollback.py`，另静态编译 CDM CLI | 相同 Dockerfile、旧根、Push `push: true` | **E — Unknown/HOLD** |
| `.github/workflows/task004-step04f-cdm-ghcr-publish.yml`（`e15ab8f2f3d4d76a83687953adc32b6c57d442f3`） | `feature/task004-step04f-cdm-ghcr-publish`（分支仍存在） | `test_step04f_cdm_runtime_packaging.py`、`test_step04f_dynamic_row_adapters.py`、`test_step04f_dynamic_source.py`、`test_step04f_dynamic_pg_writer.py` | 相同 Dockerfile、旧根、Push `push: true`，并固定 `origin/main=897cc15c514f635eedcb3cd7edc0c9765aafb757`，当前 Main 与之不同 | **E — Unknown/HOLD** |

这三条现有 Workflow 源码的 `push.branches` **都不包含 Main**，触发 `paths` 限各自 Workflow 文件；因此不是当前 Main Push 的自动发布入口。但专用 GitHub feature 分支**仍真实存在**，并不等于可以假设无历史 Dispatch/外部 `workflow_dispatch`（这些文件实际上只声明 Push）、无历史 OCI Digest 被容器引用或可以安全删除。这轮没有读取完整 Actions 历史（GitHub API 访问范围有限），未复核外部 Runner/API 消费者，必须保持 **E/HOLD**。

三条 Workflow 均不定义独有镜像 Dockerfile、Entrypoint、SQL 或 DAG；均从同一个 `images/task004-cdm-runtime/Dockerfile` 构建并将结果 Push 到相同 GHCR 仓库 `healthcare-data-platform-task004-cdm-runtime:git-<sha>`。这证明的是**静态构建目标重合**，不证明过去发布的不同 Digest 或运行环境可以互相代替。CDM Dockerfile `FROM python:3.12-slim-bookworm` 非 Digest Pin，因此目前不能宣布 4.3 immutable upstream provenance PASS。

## 2. 唯一有价值的旧测试，全部保留

现行安全 Reader 入口 `.github/workflows/task004-cdm-pg-read-publish.yml`（本轮之前 PR #299）已在精确 PR Head [Run #39403437040](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39403437040) 通过 5 组离线测试，共 **23/23 PASS**，只验证本地 Clean Build/Copy/Import/Mock，GHCR SKIPPED。这五组已覆盖历史 rollback 和 S3 rollback Workflow 的测试，以及历史 GHCR Workflow 的包装/PG Writer；**未覆盖的只有以下两组**：

- `test_step04f_dynamic_row_adapters.py`（实际 10 个测试）：Person/Visit 转换、FK、时间戳、指纹/数据契约、重复/计数/授权否定性断言。
- `test_step04f_dynamic_source.py`（实际 4 个测试）：`FakeS3` 多文件/空前缀/Manifest 变化/合法批次边界，**不访问外部 S3**。

本 PR 在 **保留原有七个实际 Python 测试文件**的同时，向 Reader `validate-source` 添加上述两组；全部测试在临时构建的 CDM 镜像、`--network none --read-only`、只读 Source Mount 中执行，**合计预期 23+10+4=37**。另添加静态 fail-closed 阶段：读取三条历史 Workflow 的全部 `test_step04f_*.py` 引用，逐文件检查现行 Reader 的七个测试名称完全覆盖，并确认每个测试只存在 `local-data-platform/tests/task004/` 下。检查不会宣称外部消费者不存在。

**此两项测试并非“无用历史测试”**，属于 4.10 的 **B — Required Engineering**，不可删除；先把它们保护到现行 CI 再讨论 Workflow 的去留。

## 3. 建议动作及尚未闭合的退出门禁

1. 三条历史发布 Workflow：**当前 E/HOLD 原样保留**。只有在独立完成 feature 分支消费者核对、旧 GHCR Digest 运行引用/恢复入口、第三方触发方和保留依赖必要性检查后，才能从 E 重新分类 C/D。不能仅凭静态测试已转移而删除它们。
2. 两组额外 Mock/纯数据测试：**B/KEEP**；本轮 PR 提供实际新 Main 验收后的受保护 CI。
3. 当前 CDM Reader Workflow：**B/KEEP**；除 PR 离线单测与临时无发布镜像外，其现有 GHCR 发布要求 `workflow_dispatch` + `publish_approved=true`，本轮不触发。
4. 历史 Dockerfile、Airflow DAG、PG/S3 Writer 以及旧分支：**不修改**。4.2/4.3 仅本轮小范围测试保护子门禁，不能标为全部 PASS。4.1/4.8 仍 PARTIAL，4.9/4.10 HOLD，源文件与 Workflow 删除/批准删除均为 **0**。

## 4. 要求的 CI 证据

新 PR 最终 HEAD 须在 GitHub Runner 上真实达到：`CDM_LEGACY_WORKFLOW_COUNT=3`、`CDM_PROTECTED_HISTORIC_TEST_SUITES=7`、`CDM_LEGACY_TEST_COVERAGE_GATE=PASS`、离线 **37/37 测试 PASS**、`CDM_SOURCE_GATE=PASS`、`CDM_CLEAN_BUILD=PASS`、`CDM_IMAGE_IMPORT_GATE=PASS`，以及两个现行 GHCR 发布 Jobs **SKIPPED**。其他 Required Checks 需绿；必须记录实际 PR Head 与 Run，不能根据源码提交预测 CI 结果。

## 5. 实际 CI 首次验收（实现 HEAD，结果已核对）

- 本轮 [Healthcare PR #301](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/301)、[真实 Run #39406065172](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39406065172) 的 `CDM reader clean build and complete historical offline contract regression (no publish)` Job **SUCCESS**。Log 直接报告 `SOURCE_SHA=ee52aef3d230e36e3c33edc9241552757889686f`；这是**实现代码 HEAD**，本轮补充证据后的**最终 PR HEAD 仍须复验**。
- `CDM_COPY_COUNT=7` / `CDM_SOURCE_GATE=PASS`；`CDM_LEGACY_WORKFLOW_COUNT=3` / `CDM_PROTECTED_HISTORIC_TEST_SUITES=7` / `CDM_LEGACY_TEST_COVERAGE_GATE=PASS`，仅证明历史三个 Workflow 内引用的**七组测试名称**在当前 Reader CI 中均有覆盖，文件存在且不存在旧根路径。
- `CDM_CLEAN_BUILD=PASS`；本地临时 `LOCAL_IMAGE_ID=sha256:843dfde6a94fec46a392d0d63dea54f101ab1087d553f01183e21913d75d970b`（**不是** GHCR Digest）。4 个目标 `module.__file__` 来自镜像 `/opt/task004/`，`CDM_IMAGE_IMPORT_GATE=PASS`。
- 七个测试套件逐项 **5 + 3 + 5 + 8 + 2 + 10 + 4 = 37/37 PASS**，`CDM_OFFLINE_REGRESSION=PASS`。容器 `--network none`、`--read-only`；`LIVE_POSTGRESQL_S3_AIRFLOW_K8S=NOT_PERFORMED`；本次 PR 的 CDM `build-and-push` **SKIPPED**，`GHCR_PUBLISH=NOT_PERFORMED`。
- 上述只证明此实现代码在本次隔离 GitHub CI 下的源码/构建/导入/单测结果。**没有证明**这三个历史 GHCR 工作流没有其他外部消费者，未取代旧 Snapshot 或已有 GHCR Digest，亦未执行历史分支审计后的真实部署/业务恢复。E/HOLD、B/KEEP 和删除 0 不变。

