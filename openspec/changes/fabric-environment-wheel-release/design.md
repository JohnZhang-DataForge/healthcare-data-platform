# Design — Environment Wheel runtime acceptance

## Decision and ownership
- Git `shared-data-engine/` 唯一打包源码；唯一分发制品 `healthcare_data_engine-0.1.0-py3-none-any.whl`，现有可重现构建 SHA256 `603f1051898ebdd2da1a8127606248dc832af4f64a453386955afcb8dcf945a7`。固定 `SOURCE_DATE_EPOCH=1704067200`，发布前必须重新核对文件 digest、版本及受审 SHA。
- Git Native `env_healthcare.Environment/Libraries/CustomLibraries/` 是已审 Wheel 的声明式配置，Git UpdateFromGit 仅触发 **staging**；Fabric Environment 显式 Publish 才可能使配置生效。已有 Notebook/Pipeline 自动 Git 同步的 allowlist **不得偷偷扩展为 Environment 发布**。
- 真实 Fabric Items：Workspace `745ce03b-15b6-4870-b0e5-8c5750aa18dc`、Environment `d85a4218-8da0-46ed-8517-b5eced219dd5`、Notebook `8311ab6b-3484-4e96-8370-badeeb751633`。以线上 GET 复核名称、类型、ID；不得用 Git `.platform.logicalId` 代替真实物理 ID。

## Current verified evidence (not a new live claim)
- Healthcare PR #583 / Self-Runner Run #41311994774：Notebook/Pipeline Git 同步和云端源码读回 PASS；**不是** Environment Publish。
- Self-Runner Runs #41263018957/#41263182097：staging 有目标 Wheel 文件名；published `GET .../libraries?beta=false` HTTP 404；metadata `publishDetails.state=Success` 且 `sparkLibraries.state=Success`。发布时间与 Wheel staging 时间的先后未验证。
- Git Notebook `nb_fhir_ingest.Notebook/notebook-content.py` METADATA 当前包含 Lakehouse 依赖但无显式 `environment` 字段；实际绑定尚未确认。不要凭 Git 源声明肯定云端未绑定；使用真实 Notebook 依赖读回/Portal 复核。
- Microsoft 正式版 published/staging library list 使用 `beta=false`、不同于弃用 Beta 的响应 schema；404 可能是 `EnvironmentLibrariesNotFound`，也可能是其它 API 错误。当前 GET client 只留 HTTP 状态，没有保留经白名单处理的 `errorCode`，须谨慎报告 UNKNOWN。

## Runtime 2.0 Python 3.13 compatibility blocker — 2026-11-01

Microsoft [Runtime 2.0 GA](https://learn.microsoft.com/en-us/fabric/data-engineering/runtime-2-0) specifies **Python 3.13, Spark 4.1, Java 21**. Current Git `env_healthcare.Environment/Setting/Sparkcompute.yml` selects `runtime_version: 2.0`; current Shared package `pyproject.toml` declares `requires-python = ">=3.10,<3.13"`, excluding 3.13. The staged `healthcare_data_engine-0.1.0-py3-none-any.whl` therefore **cannot be presumed installable** on intended Runtime 2.0. Offline tests use Python 3.11/PySpark 3.5.7, not the Fabric 2.0 runtime.

Healthcare [CI Run #41314613170](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/41314613170) proves **13/13 pure Python FHIR tests** and **2/2 real PySpark 4.1.1 DataFrame tests under Python 3.13 / Java 21** on GitHub-hosted runners. The version 0.1.0 **package metadata still excludes Python 3.13**. Tests validate uninstalled source, not a compatible wheel installation or a Fabric Spark Session. Do **not** merely widen the `requires-python` declaration: require a separate reviewed compatibility release with distinct version, deterministic Wheel SHA and Spark 4.1/3.13 contract tests before replacing old Git Environment Wheel. Do not silently downgrade the intended Environment to Runtime 1.3 to bypass compatibility.

## Fresh actual read-only acceptance — 2026-11-01

- [Self-Runner PR #382](https://github.com/JohnZhang-DataForge/Self-Runner/pull/382), main commit `21b3a65890f8ca24d9f732f6042155a4f49d3882`, PR offline CI [Run #41313930494](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41313930494) PASS.
- Trusted main push live [Run #41314090759](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41314090759) PASS for **read-only diagnostic execution**, Notebook FabricGitSource/ipynb full (3 code cells), Pipeline safe params PASS, staging Wheel filename present, Published Libraries HTTP 404, `HOLD_PUBLISHED_LIBRARIES_UNKNOWN`, `published_404_kind=UNDIFFERENTIATED_RELEASE_API_404`, publishDetails.state and sparkLibraries.state both historical Success, Notebook `ipynb` environment metadata `NOT_DECLARED_IN_IPYNB`. No live Notebook binding or runtime import proven; no Publish, Spark or Delta executed. Deployed Git sync head `8188cddcd79f0654eff1d95b81fd97ad94604f2d`.

## Ordered gates
1. **Source build / Runtime 2.0 compatibility**：reviewed Git main commit, offline Python 3.11 + Python 3.13 pure/spark-specific tests, compatibility with PySpark 4.1, Wheel installation metadata, deterministic built hash PASS. Existing 0.1.0 source build is historically PASS but **current Runtime 2.0 compatibility BLOCKED by Python <3.13**; do not reuse old SHA for new release.
2. **Git staging**：兼容性通过后，以不同 Wheel release version + 新 SHA 审核替换旧 CustomLibraries 文件，确认唯一 Wheel；对照 Git Blob SHA + Wheel SHA、Environment exact Item ID；官方 `GET /staging/libraries?beta=false` 返回目标 Custom 文件名（不能证明内容字节相同）。
3. **Prepublish read-only**：`GET /environments/{id}` publish state/targetVersion；`GET /libraries?beta=false` 有效版本，分类 200/404/403/其它，并核实 staging/published 差异。若 HTTP 404，保留错误状态；未得到可验证 published Wheel 时 HOLD。
4. **Publish authorization**：仅当上一阶段证明确实应发布、没有并发 Publish、容量/会话影响可接受，另行明确授权后执行官方 `POST /staging/publish?beta=false`，按 LRO 轮询目标版本与 sparkLibraries 组件结果；遇未知 ACK **先 GET，不盲目重复 POST**。
5. **Notebook binding**：由 Fabric 原生 Environment 选择机制/官方 API 绑定 `env_healthcare`，取得真实绑定证据；任何绑定更新都是单独 runtime 变更，先核对现有笔记本当前 Session；不能仅在 Git 中猜测元数据结构并部署。
6. **Nonwriting runtime smoke**：独立获批后新 Spark Session，仅 `importlib.metadata.version`、`healthcare_data_engine.__version__`、`__file__` 和最小无数据写入 import 验证；保留原业务 Notebook `run_mode=HALT` / `write_authorized=False` / `retention_preflight_verified=False` 及 `HOLD_P2_RUNTIME_RELEASE_NOT_VERIFIED`。
7. **Data gates**：Bronze/Silver、ETL Pipeline、Delta 写入留到下一 Change；本次绝不以 import PASS 推导业务 E2E PASS。

## Failure cases, rollback and traceability
- File-name list only validates **name**，不提供库内容 SHA。实际在目标 Session import 也只能证明版本/加载路径，除非有受控 wheel 文件内容读取或可信发布 provenance 才可声称字节 SHA 验证。
- 当 published 404 而历史 publishDetails Success 时，分类 `HOLD_PUBLISHED_LIBRARIES_UNKNOWN`，不是发布成功，也不是一定失败。对 `EnvironmentLibrariesNotFound` 只表示当前 published 库为空；无明确错误代码则维持 UNKNOWN。
- 避免直接覆盖环境或移除其它用户库；任何回退必须预先保存 staging/published 快照、版本与 ID，独立确认恢复方案。不得禁用 HALT 以获得 import PASS。
- Microsoft docs: [Environment Git staging vs Publish](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-git-and-deployment-pipeline), [Environment REST API](https://learn.microsoft.com/en-us/fabric/data-engineering/environment-public-api), [Published libraries](https://learn.microsoft.com/en-us/rest/api/fabric/environment/published/list-libraries), [Notebook source control](https://learn.microsoft.com/en-us/fabric/data-engineering/notebook-source-control-deployment).
