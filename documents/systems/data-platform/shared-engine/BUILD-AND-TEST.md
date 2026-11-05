# Shared Engine — BUILD-AND-TEST

本文件承接原 `shared-data-engine/README.md` 的**离线安装、测试、可复现 Wheel 和 Handoff 验收说明**；操作入口以当前 [pyproject](../../../../shared-data-engine/pyproject.toml)、[测试依赖](../../../../shared-data-engine/requirements-test.txt) 和 [Wheel CI](../../../../.github/workflows/shared-engine-wheel-validation.yml) 为准。本文只说明离线/合成验证，绝不授权真实 Fabric/数据库操作。

## Offline dependencies and Python 3.11 tests

以下命令自**仓库根目录**运行，为 POSIX Shell 示例；Python 3.11 + Java 17 对应 Local PySpark 3.5.7。首次准备 Wheelhouse 需要网络；`--no-index` 安装阶段使用已下载的依赖，并须确保 OS、Python 版本和架构匹配。

```sh
python -m pip wheel --wheel-dir wheelhouse -r shared-data-engine/requirements-test.txt
python -m venv .venv-shared
.venv-shared/bin/pip install --no-index --find-links=wheelhouse -r shared-data-engine/requirements-test.txt
PYTHONPATH=shared-data-engine/src .venv-shared/bin/python -m unittest discover -s shared-data-engine/tests -p 'test_*.py' -v
```

原目录下 4 个 `tests/test_*.py` 和合成 Fixture 是既有冻结测试：本次不迁移也不减少覆盖。以后新测试应进入 `.github/quality/tests/shared-data-engine/<component>/`，新样本进入 `.github/quality/fixtures/`，并同步 CI 的非零用例发现。

## Reproducible Wheel build and install

固定 `SOURCE_DATE_EPOCH=1704067200`，重复构建并比较二进制 SHA；`--no-build-isolation` 要求环境已安装所需构建工具。当前 `pyproject.toml` 版本为 `0.1.3`，以后版本变化必须同步更新安装目标，并以审查过的产物哈希为准。

```sh
SOURCE_DATE_EPOCH=1704067200 .venv-shared/bin/python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir dist ./shared-data-engine
sha256sum dist/healthcare_data_engine-*.whl
.venv-shared/bin/pip install --no-index --no-deps --force-reinstall dist/healthcare_data_engine-0.1.3-*.whl
```

[Shared Engine Wheel Validation](../../../../.github/workflows/shared-engine-wheel-validation.yml) 在 Python 3.11 与 3.13 分别校验纯函数、PySpark Schema/Rows、可重复构建、安装以及从 Checkout 外 Import。Fabric Runtime 2.0 的 Python 3.13 / PySpark 4.1.1 / Java 21 环境须按该 Workflow 的实际任务验证，不能从本地 Python 3.11 结果推断。

## Contract and FHIR → OMOP handoff (offline only)

- Local Canonical v1 [Patient/Encounter Contract](../../../../local-data-platform/spark/contracts/canonical/) 保留唯一权威。调用方提供原始 Source Bytes、期望 SHA256/大小、固定 Contract Bytes 和显式 `BatchContext`。
- `parse_fhir_resources` 和 `normalize_fhir_*` 对合法资源、冲突/畸形资源及 Canonical v1 不兼容字段分别处理；不能编造日期、族裔等临床默认值，应 Quarantine，并在物理写入后独立检查 Patient–Encounter FK。
- [Handoff v1 JSON](../../../../shared-data-engine/contracts/fabric-fhir-omop-handoff-v1.json) 保留版本/物理资源身份；[纯结构 Validator](../../../../shared-data-engine/src/healthcare_data_engine/models/fabric_omop_handoff.py) 不读取 Delta、不分配正式 OMOP ID、也不授权 Gold Writes。结果 `STRUCTURAL_PASS_PHYSICAL_READBACK_REQUIRED` 明确需要后续物理数据读回。
- [Handoff 测试](../../../../shared-data-engine/tests/test_fabric_omop_handoff.py)、[离线 CI](../../../../.github/workflows/fabric-fhir-omop-handoff-offline.yml)、[边界设计](../../azure-fabric/pipelines/FHIR-OMOP-HANDOFF-V1.md) 必须保留源 SHA、医院隔离、Quarantine 与权限约束。

## What the evidence means

- **Offline CI PASS**：仅证明指定提交的合成测试与 Wheel 安装。
- **Published 0.1.3 + isolated Spark Import PASS**：见 [Environment CODE](../../azure-fabric/environments/CODE.md) 的已验证独立 Publish/Import Run。
- **正式 Notebook FHIR/OMOP E2E、Approved Silver 物理读回、Vocabulary/Stable ID 与 Gold COMMIT/Replay**：独立业务验收，不能由上述测试推出。
