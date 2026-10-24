# Local DP — Task 4.1 第二轮跨仓依赖与历史脚本审计（PARTIAL / STATIC）

> **2026-10-19 · 只读源码审计，不代表 4.1 完成、不批准删除/回放。** 严格按 GitHub 当前固定提交和 Blob 源码调查。此文件记录可重复核对的发现，不把静态推断包装成 CI、Docker Build、DAG Parse 或真实运行 PASS。

## 1. 固定基线、审计覆盖率

- Healthcare Main **`b5c49258d2102c21601ebd74bfd0aff8ba518df7`**（本轮只读输入）；Self-Runner Main **`ffd0eccecbf0148183b956e6e4416d4b8d99002b`**。两仓 Git Tree 非截断。前一轮 [完整 393 行 Blob 清单](LOCAL-DP-FILE-INVENTORY-20261018.md) 对应更早的 Main `52237e773941def7625de72c6cecb2533f11e5d8`；本轮未改变任何 `local-data-platform/` 源码，**该清单仍保留原始审计 SHA**，不要在审计证据中覆盖历史版本。
- Healthcare **21/21** 当前 tracked `.github/workflows/*.yml` 已做一次源码路径/触发条件静态分类：**5** 个构建镜像工作流、**10** 个旧 `task004` 特定里程碑工作流、**6** 个治理/Portal/通用检查工作流。此为**文件分类**，不代表它们在 Main 都实际触发或执行过。
- Local DP `scripts/task004/` **14/14** 个 Shell 已检查硬编码根目录、生成目标以及 K8s/SQL/S3 和被其他源文件引用的风险。
- Self-Runner 当前 **123** 个 tracked Workflow；本轮**抽查 24 个具代表性的源码文件**（另外的未逐一审查，不能据此证明没有依赖）：其中 **19 个** Healthcare checkout 使用固定 Commit SHA，**4 个** 使用动态且校验的目标 SHA，**1 个**未在该文件中直接 checkout Healthcare。固定旧 SHA 的工作流可能合法回放旧布局；不能因为出现 `healthcare/apps/` 就错误地升级为必须更改的 Main 入口。
- Task003 有 **94** 个历史 Shell；本轮阅读其中 **8** 个有代表性的 reset/prepare/launch/readback/recovery/verify 文件。文件名中包含 `prepare` 的有 **45** 个、`verify` **11** 个；数字是**文件名统计**，不是“可删除”分类。
- 对 **6** 个样例 Test 文件检查 Path ROOT 与测试职责，对 **4** 个 Airflow DAG / helper 和一个容器 Entrypoint 核对导入及路径约定。其余 99 个 Test、Spark 运行时模块/全部模板、实际 GitSync Helm 值、所有 Self-Runner Workflow/Shell 间接调用仍待审计。

## 2. Healthcare 工作流：优先修复构建，再评估冻结工作流是否退休

| 范围（已读源） | 结果 | 后续处理 |
| --- | --- | --- |
| [.github/workflows/build-landing-claim-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/.github/workflows/build-landing-claim-image.yml) | `context: .`、`file: images/...`、运行 `tests/landing_claim`，均针对旧仓根；推送 Main 的 `paths` 也没覆盖 `local-data-platform/**` | **A/B 必须保留该构建能力**，修上下文、测试 cwd、触发范围，且 GHCR 发布需要独立审查 |
| [.github/workflows/build-landing-discovery-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/.github/workflows/build-landing-discovery-image.yml) | 同样旧根；包含 `apps/task004` 工具引用和 `tests/landing_discovery` 旧根路径 | **A/B 必须保留构建能力**；同时核对 Task004 助手兼容 |
| [.github/workflows/build-new-only-omop-writer.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/.github/workflows/build-new-only-omop-writer.yml) | GitHub Workflow 有 `workflow_dispatch` 且历史 feature 分支专用自动触发，`file: images/...` 和 tests 旧根；包含明确 Writer/Fencing 负向测试 | **B/HOLD**：生产安全证明重要，**不能仅因 feature 专用就删**；先确定当前发版入口 |
| [.github/workflows/build-synthea-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/.github/workflows/build-synthea-image.yml) | Main 触发路径为旧根、Dockerfile 也是旧根 | **B 保留**，修静态构建路径与触发范围 |
| [.github/workflows/build-task004-runtime-image.yml](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/.github/workflows/build-task004-runtime-image.yml) | Main + feature 分支可触发；旧根测试、Dockerfile、镜像 COPY、`PROJECT_ROOT`。在 Test 步骤调用 `scripts/task004/06a-prepare-unified-runtime-image.sh`，再 `cmp` Dockerfile、entrypoint、workflow、test | **强依赖 HOLD**：镜像生成器、生成结果、Workflows、相关 tests 必须同步改/验证；绝不先删除生成器 |
| 其余 10 个旧 `task004-*.yml` | **10/10** 的 `push.branches` 限于历史 `feature/task004...`（某些仅监测 Workflow 本身），多数引用旧根并有部分 GHCR publish | **历史工作流退休候选（不是批准删除）**：确认当前发布/外部触发、历史复验入口后，可以在未来独立 PR 删除；禁止为了让其通过就全部在 Main 重新激活 |
| 其余 6 个仓库级质量、OpenSpec、Portal 工作流 | 当中通用质量组件已经识别 `local-data-platform/**` 并且当前能通过；其他为文档/OpenSpec/Portal 独立范围 | **B 保留**。治理/Portal 检查不属于 Local DP 的历史脚本，不能混在清理目标中 |

**已确定的静态不一致**：在新目录下 `local-data-platform/tests/task004/test_unified_runtime_image_source.py` 的 `ROOT = Path(__file__).resolve().parents[2]` 解析为 **Platform Root**，但 `WORKFLOW = ROOT / '.github/workflows/build-task004-runtime-image.yml'`；仓库的正式 Workflow 实际位于 **Repository Root/.github/workflows**。同理 `test_synthea_ghcr_workflow.py` 指向 Platform Root 下不存在的 `.github/workflows/build-synthea-image.yml`。这两个用例的文件路径断言从源码结构可证明不匹配，**尚未实际执行测试**。不要为满足用例在 Local DP 新增一份假 `.github/`。

相关测试：[local-data-platform/tests/task004/test_unified_runtime_image_source.py](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/tests/task004/test_unified_runtime_image_source.py)、[local-data-platform/tests/task004/test_synthea_ghcr_workflow.py](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/tests/task004/test_synthea_ghcr_workflow.py)。它们测试镜像固定来源、安全约束和发版完整性，**应该优先修路径、保留有意义的测试断言**。

## 3. Task004 Shell 全量分组：活跃镜像依赖不能按名字清理

| 脚本/类群 | 核对源码的事实 | 初步保护结论 |
| --- | --- | --- |
| `04c-run-synthea-generate-publish.sh`、`05c-resolve-runtime-lineage.sh`、`05d-run-person-canonical.sh`、`05e-run-visit-canonical.sh`、`05f-reconcile-person-visit.sh` | **这 5 个文件在当前 `images/task004-runtime/Dockerfile` 内是直接 COPY 输入**，镜像入口实际分支调用它们；它们可能创建 Pod、ConfigMap、SparkApplication 或读取 Secret | **A/HOLD 绝不能在这次历史清理先行删除**；若以后淘汰须证明镜像不再需要 |
| `06a-prepare-unified-runtime-image.sh` | 生成完整 Dockerfile、EntryPoint、仓库级 `.github/workflows/build-task004-runtime-image.yml` 和测试，当前发版 Workflow 中直接运行及 `cmp` | **B/HOLD**，是源码生成器与正式源码可能相互覆盖的单点，迁移后必须决定 repo root vs platform root 的双根写入策略 |
| `01-prepare-synthea-generator-image-source.sh`、`02-prepare-synthea-ghcr-workflow.sh`、`03a-prepare-synthea-generate-only-runtime.sh`、`04a-prepare-synthea-landing-publisher.sh`、`05a-prepare-generic-landing-resolver.sh`、`05b-prepare-person-visit-runtime-interface.sh` | 含较大 heredoc/生成器源码，产出业务 Python、Templates、测试、Shell，部分还产出顶层 Workflow；生成代码涉及固定旧根/镜像内路径 | **C 候选 / HOLD**。先证实输出是当前受维护的 canonical source、而非重建来源，以及没有自恢复/验证依赖，再分批退休；不能仅凭源文件名删除 |
| `03b-run-synthea-generate-only.sh`、`04b-sync-s3-secret-to-synthea.sh` | 前者使用 Kubernetes Job，后者实际有 `kubectl create secret ... | kubectl apply` 路径；均不是无副作用的诊断 Shell | **E/HOLD**，如没有现行业务必要性可成为未来退役候选，**严禁执行验证而未经明确集群/Secret 授权** |

固定镜像内的 `PROJECT_ROOT=/data/spark/healthcare-data-platform` 和 `/opt/task004` 是容器 **RUNTIME_ROOT**（不等于 Git Repository Root），无业务理由时保留它们；反之 GitHub Workflow 的 `.github` 必须在 **Repository Root**。再次确认必须严格分离 `REPOSITORY_ROOT`、`PLATFORM_ROOT`、`RUNTIME_ROOT`。

## 4. Task003 历史 Shell 重点：仓库清理要避免触发危害

94 个 `scripts/task003/` Shell 中的高风险样例：
- [local-data-platform/scripts/task003/00-reset-task003.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/scripts/task003/00-reset-task003.sh)：清理本地路径，含 `rm -rf`，**禁止用于验证迁移**。
- [local-data-platform/scripts/task003/04-prepare-canonical-encounter-publish.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/scripts/task003/04-prepare-canonical-encounter-publish.sh)：固定宿主机 `ROOT=/data/spark/healthcare-data-platform`，会生成 Python/Runner 文件，内含 K8s 作业操作。
- [local-data-platform/scripts/task003/05g2c2b-prepare-visit-processed-writer-core.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/scripts/task003/05g2c2b-prepare-visit-processed-writer-core.sh)：生成 `spark/apps/visit/processed_visit_writer_core.py` 和历史测试，存在覆盖 canonical source 风险。
- [local-data-platform/scripts/task003/05g2c2c3c2-launch-visit-processed-writer.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/scripts/task003/05g2c2c3c2-launch-visit-processed-writer.sh)：真正 K8s 作业创建逻辑；**不是可以当作普通 smoke 直接重跑的脚本**。
- [local-data-platform/scripts/task003/05g2c2c3d2b2-run-independent-readback.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/scripts/task003/05g2c2c3d2b2-run-independent-readback.sh)：名字是 Readback，但源码还具有 ConfigMap/SparkApplication 相关构造操作；只读程度需要逐调用确认。
- [local-data-platform/scripts/task003/06b4b-r1-prepare-visit-id-allocation-recovery.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/scripts/task003/06b4b-r1-prepare-visit-id-allocation-recovery.sh)：生成恢复脚本，包含 `psql`/Git SHA/历史固定宿主根，需要保留历史恢复证据，不代表应长期留在维护源码树。
- [local-data-platform/scripts/task003/06c4e-verify-committed-cdm-visit-materialization.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/scripts/task003/06c4e-verify-committed-cdm-visit-materialization.sh)：含对 PostgreSQL 的 `psql` 访问，不能仅按 `verify` 标记为安全或过期。
- `05g2c2c2b2-prepare-runtime-bundle.sh` 的 `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"` 能解析到新 Platform Root，但由此 **无法**保证所有被调用路径或生成内容正确。

**本轮不将任何 Task003 具体文件从 HOLD 提升到 DELETE APPROVED**；其 94 个文件需要完整的 Shell-to-Shell、Python 生成输出和当前 Workflow 消费者图，再确认哪些是真正仅历史意义。未来更理想的终态是把永久正式恢复/安全运维能力独立抽成按组件命名的脚本，而不是保留 Task003 整个史料目录。

## 5. Self-Runner 固定 SHA ≠ 当前 Local DP 依赖

Self-Runner 的下列样例展示为什么不能全仓粗暴替换旧路径：

| 示例（Pinned Self-Runner `ffd0eccecbf0…`） | 静态证据 | 对 Main 迁移的判断 |
| --- | --- | --- |
| [.github/workflows/landing-batch-discovery-readonly.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/landing-batch-discovery-readonly.yml) | 固定 Healthcare `ref: ffb238f529de7df7c591e90c192436efaa7efe85`，引用旧 `healthcare/apps/...`，可创建 K8s ConfigMap/Job | **历史 SHA 的旧路径不自动构成错误**。即使名为 readonly，也不是零资源副作用 |
| [.github/workflows/landing-processing-v2-source-acceptance.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/landing-processing-v2-source-acceptance.yml) | 固定 Healthcare `ref: 72be44be9304c7549030951f5d25864075fed5cc`，`docker build -f healthcare/images/... healthcare` | 历史构建上下文可与其老 commit 一致；不可据此认定当前新构建 PASS |
| [.github/workflows/task004-first-new-only-business-commit.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/task004-first-new-only-business-commit.yml) | 固定 Healthcare `ref: a93f9f7c6faccb9c6164263bc07b5ea92faf5f3d`，脚本有真实 Writer/PG/S3 路径 | **绝不调度历史业务 COMMIT**；备份与目录迁移不授权重放 |
| [.github/workflows/synthea-new-only-run-new-request.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/synthea-new-only-run-new-request.yml) | 固定 Healthcare `ref: 605ac22c5adcc37e78b714784fd92fc340fbf09b`，涉及生成 Job 和 Secret | 是固定业务里程碑执行器，不能当新 Main 的冒烟验证 |
| [.github/workflows/healthcare-openspec-pr-handoff.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/healthcare-openspec-pr-handoff.yml)、[.github/workflows/cross-repo-healthcare-static-v5.yml](https://github.com/JohnZhang-DataForge/Self-Runner/blob/ffd0eccecbf0148183b956e6e4416d4b8d99002b/.github/workflows/cross-repo-healthcare-static-v5.yml) | 依据请求/校验动态 `target_sha` checkout，而非历史固定 commit | 仍是治理/静态验证，不应把它们的 PASS 说成 K8s/OMOP 业务验证 |

**抽查结果不覆盖全部 123 个 Runner Workflow**，下一步需要完整双仓调度/脚本/请求引用图，找出哪些仍需作用于迁移后 Main，哪些只是保留旧历史证据的程序。

## 6. Airflow、Spark 与测试保护

- [local-data-platform/airflow/dags/new_only_omop_consumer.py](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/airflow/dags/new_only_omop_consumer.py)：DAG ID `new_only_omop_consumer`，手工 `schedule=None`，通过自身文件的 sibling dir 解析 `new_only_omop_routing`、`new_only_omop_writer_handoff`、`landing_spark_processing`；镜像 Digest 固定。**DAG Python 迁到新树不等于 GitSync 实际设置已切换**。
- [local-data-platform/airflow/dags/landing_batch_discovery.py](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/airflow/dags/landing_batch_discovery.py)：DAG ID `landing_batch_discovery`，`*/15 * * * *`，含 sibling module import workaround；同步/加载须与实际 Helm/GitSync 配置比对。
- [local-data-platform/airflow/dags/task004_processing_pipeline.py](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/airflow/dags/task004_processing_pipeline.py)：历史 DAG 仍 import 多个 `task004_cdm_*` 模块，且 `schedule=None`；在没有正式替代及部署证明前 **A/E HOLD**。
- [local-data-platform/images/task004-runtime/entrypoint.sh](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b5c49258d2102c21601ebd74bfd0aff8ba518df7/local-data-platform/images/task004-runtime/entrypoint.sh)：仍调用上述镜像 COPY 的五个 Shell；静态佐证它们不能立刻清理。
- 六个已看 Test（两份路径错误的镜像测试，`test_person_visit_runtime_interface.py`、`test_airflow_task004_processing_source.py`、`test_synthea_generator_image_source.py`、`tests/omop_writer/test_new_only_airflow_writer_runtime.py`）覆盖合同/运行时/负向安全及冻结身份，**不得将所有旧 task 测试删除**。已确认镜像测试仓库根定位必须修改，但未执行单测。

## 7. 明确的去留与下一个 Gate

| 结论 | 文件/能力 | 理由 |
| --- | --- | --- |
| **KEEP/PROTECT**（当前不准删） | 5 个 Docker 直接 COPY 的 `scripts/task004` Shell；Writer/Claim/Fencing、安全 Contract/Regression Tests；Airflow 已验收 DAG ID | 业务/安全可观察依赖 |
| **REWORK BEFORE PRUNE** | 5 个当前镜像 Build Workflow、`06a` Docker 生成器及关联镜像测试 | 根目录映射失效；需要先达到对应 SHA 的 Build/Import Gates |
| **RETIRE CANDIDATE / HOLD** | 10 个 feature-only 历史 Task004 Workflow；旧 `prepare` 生成器及无重复价值的旧 milestone tests | 目前只确认“疑似历史”；未证明没有当前间接/动态消费者和独特测试价值 |
| **UNKNOWN / HOLD** | Task003 94 个 Shell 的剩余依赖；未逐项验证的 Self-Runner、测试、GitSync、Spark 入口 | 不完整的负向证据不能作为安全删除依据 |

**下一步（4.1 仍未完成）**：1）逐个构建 Self-Runner 的全量当前 Main/历史 SHA 消费者矩阵；2）梳理 Task003 Shell-to-Shell/生成目标图与 105 个 tests 的有效回归映射；3）核对 Airflow 当前 GitSync 配置与 Spark manifest 模块来源（先源码，真机另授权）；4）再进行 Task 4.8 的当前 Blob 恢复核验与候选清理清单。**本轮没有删除、修复、执行、发布或部署任何业务内容。**
