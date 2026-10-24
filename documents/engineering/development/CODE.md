---
status: active
scope: developer-tooling-source-map
last_verified: 2026-10-24
source_sha: 8e075bca130429c261a0f2cf245daef83ba8eebf
---

# Developer Tooling — CODE / 开发工具与环境示例导航

> 这是**横切开发工具的源码地图**，并非新增业务组件。业务脚本仍在对应业务组件 CODE.md 里维护；工作流与审批规则在 [Development Workflow](DEVELOPMENT-WORKFLOW.md)，统一安全规则在 [Safe Operations](../operations/SAFE-OPERATIONS.md)。`scripts/taskNNN/` 是历史脚本，**不是当前可重跑指令**。

## 静态 CI / Source-Map 校验工具

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`check_component_code_map.py`](../../../.github/quality/scripts/check_component_code_map.py) | [STATIC CI] Git diff/tree 组件 CODE.md 全量导航和新增/删除同步 CI Gate（本 PR 扩展） |
| [`check_documentation_links.py`](../../../.github/quality/scripts/check_documentation_links.py) | [STATIC CI] 所有 tracked Markdown 相对文件/目录链接完整性检测（离线、仅路径） |
| [`check_new_code_names.py`](../../../.github/quality/scripts/check_new_code_names.py) | [STATIC CI] 阻止新增正式源码采用 Task/Step 命名；历史文件豁免 |
| [`check_spark_manifest_source_closure.py`](../../../.github/quality/scripts/check_spark_manifest_source_closure.py) | [STATIC CI] 对现存 SparkApplication YAML 模板逐个检查 mainApplicationFile 的唯一 Python 源码、路径、Driver/Executor ConfigMap 只读挂载；辅助 Pod 分类排除。不渲染模板、不部署或运行 Spark；单测 [test_spark_manifest_source_closure.py](../../../.github/quality/tests/test_spark_manifest_source_closure.py) 和现有 [Local DP Provenance Static Gates](../../../.github/workflows/local-dp-provenance-probe-static.yml) 执行。 |
| [`check_openspec_change_gate.py`](../../../.github/quality/scripts/check_openspec_change_gate.py) | [STATIC CI] 将所有实质性 PR 与 Active OpenSpec Change/Task 绑定，并限制 docs-only 例外；Main Ruleset #25365902 的可信 Job 已 Required 且通过 #233/#234 正反 PR；仍非业务运行验收 |

| [`local_dp_single_image_plan.py`](../../../.github/quality/scripts/local_dp_single_image_plan.py) | [STATIC + MANUAL RELEASE POLICY] 固定八镜像 Dockerfile/GHCR 映射、3 父子镜像依赖、手动 `publish-latest` Main 发布门槛、原 `latest` 回退 Digest、候选标签校验/晋级及精确 Digest/验收 URL；本身不运行 Docker、网络或 Registry 写入 |
| [`test_local_dp_single_image_plan.py`](../../../.github/quality/tests/test_local_dp_single_image_plan.py) | [OFFLINE POSITIVE/NEGATIVE] 镜像选择、Digest 锁定、`publish-latest` 显式 Gate、旧 Digest 备份与 Registry 读回、候选标签/验收证据及候选 Tag 漂移 等合同测试 |
| [`local-dp-image-rebuild-single.yml`](../../../.github/workflows/local-dp-image-rebuild-single.yml) | [MANUAL SELECTED IMAGE BUILD / DEV LATEST] `validate` 默认只 Clean Build + no-network Smoke，`publish-latest` 显式仅针对选中的镜像推不可复用 SHA/Run Tag、备份上一个 `latest` Digest 为唯一回退 Tag，再更新当前 `latest` 并作 Registry Readback；`publish` 候选 `portal-v1.0` 仍保留为可选方式。PR 时仅执行离线 Policy，不改 GHCR / K8s / Airflow |
| [`local-dp-image-promote-tested.yml`](../../../.github/workflows/local-dp-image-promote-tested.yml) | [MANUAL VERIFY/PROMOTE; NO BUILD] 默认 `verify-candidate` 检验已发布 Tag/Digest 并离线 Smoke，显式 `promote-tested` 携带验收引用且再次核对 Digest 后才把同一个镜像晋级 `latest`；**并非 Portal DAG GitSync/E2E** |
| [`local-dp-image-rebuild.yml`](../../../.github/workflows/local-dp-image-rebuild.yml) | [FULL EIGHT-IMAGE RELEASE / MANUAL ONLY] 历史完整 8 镜像链式 clean build / Main GHCR :latest 全量晋级继续可手工触发；**移除 PR/Main Push 自动触发**，合并 Airflow DAG 不再自动覆盖 8 镜像。高副作用，请在 Shared Operations 协调后单独使用 |

| [`portal-a4-spark-static.yml`](../../../.github/workflows/portal-a4-spark-static.yml) | [OFFLINE CI ONLY] 复用原 A4 GitHub Hosted 检查，兼容 P3 的 ConfigMap + per-run PVC + SparkApplication 三份渲染文档、负向 Token/输出路径合同；PR 不创建 PVC/Pod、不会运行 Spark、不会推送 GHCR |

全仓质量工具统一放在 `.github/quality/scripts/`，对应单元测试位于 [`.github/quality/tests/`](../../../.github/quality/tests)；这些不是 Local Data Platform 业务文件。

| [`helm-gitsync-postmove-values.yaml`](../../../local-data-platform/config/airflow/helm-gitsync-postmove-values.yaml) | [DEPLOY CONFIG] 既存 `dw-airflow` Chart 1.22.0 的 GitSync 新源码子目录覆写。仅与现有 Helm Release 使用 `--reuse-values`；不是完整安装 Values，也不含 Secret。实际 Helm 修复：Self-Runner [Run #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924) PASS。 |

## 开发环境示例配置

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`local.env.example`](../../../local-data-platform/config/local.env.example) | [EXAMPLE ONLY] 历史 runner01 的项目路径、Phase3c、Synthea/SeaweedFS Batch 和 S3 配置示例；不是运行态身份/Secret |

## 跨组件的历史开发辅助 / 文档生成 Shell

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`00-reset-task003.sh`](../../../local-data-platform/scripts/task003/00-reset-task003.sh) | [HIGH / review] 历史 TASK003 reset 历史 Task 脚本；可能清理本地文件/临时资源，禁止无审查重放 |

> **历史退役（2026-10-20）**：2026-10-20 退役：仅产生固定 STEP04/STEP05F2 历史文稿的两个一次性生成器，不再是活动 Shell；历史源可按固定提交恢复。原始源码保留于 [`04-write-closeout-docs.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b418c1e077be7db21d56f9131709f73fcb0b66b9/local-data-platform/scripts/task003/04-write-closeout-docs.sh)、[`05f2-write-freeze-doc.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/b418c1e077be7db21d56f9131709f73fcb0b66b9/local-data-platform/scripts/task003/05f2-write-freeze-doc.sh)（只读历史链接），并由独立 Healthcare-Specs 备份保存；这些链接不是当前可执行入口。

## 维护与风险边界

- **新增、删除、移动、改名这里负责的 `.github/quality/scripts/`、`local-data-platform/scripts/` / `local-data-platform/config/` 源文件，必须在同一 PR 修改本 CODE.md**。组件脚本应更新自己所在的组件 CODE.md；工具脚本、开发环境示例归本页管理。
- `config/local.env.example` 只示意本地目录、Synthea 来源身份和旧批次/S3 网络设置，**不是当前 Batch 的事实来源，也不是机密凭据容器**。PG/S3 真实 Secret 来自受控运行环境，绝不将真实 `.env` 或 Token 提交到 Git。
- 许多 `prepare` / `repair` Shell 会写源文件或报告；`reset`、`upsert`、`publish` 等可能改写本地、K8s、S3 或数据库状态。静态列入导航不代表已经验证它们现在可重跑。
- 需要精确执行哪个脚本时，应核对完整源码、依赖、目标路径、固定 SHA/Batch、权限和幂等/回滚边界，不能只看本页的风险摘要。
- [CODE Map Sync Guard](../../../.github/quality/scripts/check_component_code_map.py) 通过 Git Tree/Diff 校验唯一所有者、路径完整性和增删时同 PR 同步；其作用是静态质量保护，非 Runtime/业务验收。

**Canonical location (documentation hierarchy cutover):** this Developer CODE map is maintained at `documents/engineering/development/CODE.md` and checked by `Component Code Naming` CI. The previous `documents/development/CODE.md` is a retired historical copy, not a second owner.


## Synthea 新 Generator 的模拟医院配置（P2）

这些是仅包含模拟地理和批次默认参数的配置，不包含任何真实医疗数据或凭据。

| 配置 | 说明 |
| --- | --- |
| [`atlanta-fhir.json`](../../../local-data-platform/config/synthea-new-generator/atlanta-fhir.json) | Atlanta FHIR R4 Profile |
| [`johns-creek-hl7.json`](../../../local-data-platform/config/synthea-new-generator/johns-creek-hl7.json) | Johns Creek HL7 Profile；Synthea 的实际输出仍为 FHIR R4 |
