# Design — Fabric dbt 长期归属和实施门禁

## 1. 已确认的职责
- `azure-fabric/workspaces/healthcare-omop/` 只维护真实 Git Native Notebook/Pipeline/Environment/Lakehouse，不将普通 dbt Project 塞入其中。
- `shared-data-engine/` 仍是通用 Python/FHIR Adapter、共享 Canonical 后 OMOP/Identity/DQ 的目标 Owner，不额外创建 Fabric I/O Wheel 或复制 Mapper。
- 现有唯一正式 HL7 dbt 源为 `local-data-platform/spark/apps/hl7/`，由 `documents/systems/data-platform/hl7/CODE.md` 导航；目标地址不是目前已迁移的事实。
- **不新增 `azure-fabric/ingestion/`**。HL7 Parser、Manifest Intake、Delta Staging Writer 的物理迁移若有必要，必须另做 Owner 评审，不能与 dbt 目录手续捆绑。

## 2. 未来首期项目骨架

```text
azure-fabric/dbt/hl7-canonical/
  dbt_project.yml                 # name: hl7_canonical
  models/
    staging/
    intermediate/
    canonical/
  macros/
  tests/                          # 原生 dbt singular SQL tests（Gate 例外待审批）
  seeds/
  snapshots/
  analyses/
  profiles/
    local/
      profiles.yml                # 无密钥、使用显式环境变量
  packages.yml                    # 仅有真实 package 依赖时创建
```

首次获批建立项目时，标准空目录必须使用 `.gitkeep` 留在 Git；无需虚构业务 SQL，也不要在源码区建立 README。dbt YAML schema/data tests 和模型文件按 dbt 惯例共存；Python 自动化及跨模块集成测试仍由 `.github/quality/tests/` 负责。项目目录为 `<source>-canonical` 的 kebab-case，dbt 内部名为 snake_case。同一个项目覆盖多个实体/医院；不能一医院一工程或一张表一工程。

未来 `fhir-canonical` / `csv-canonical` 需独立评审执行栈和重用空间；如果提案 `canonical-transform` 做共享业务变换，必须先明确从 Shared Engine 转移还是划清边界，绝不能有两套 OMOP/Concept/Identity/Publisher。local dbt-fabricspark SparkSession 无需 Fabric Spark CU；授权的远端 Fabric 操作依旧会受容量和安全约束。

## 3. 与受保护 Layout Gate 的冲突
当前 `.github/quality/scripts/check_repository_layout.py` 的 `legacy_violation` 对任何新的源码 `tests/` 路径（包括 `tests/.gitkeep`）都会报错，并由受信任的默认分支工作流作为 Required Check 执行。**本文件不豁免该门禁**。先通过单独治理 OpenSpec、受保护政策维护窗口、限于已批准 dbt 工程的精确目录/后缀白名单、正向和负向测试，之后才允许提交完整标准骨架。普通 `azure-fabric/**/tests/` 以及 Python 自动化测试不得被放行。

## 4. 具体后续实施
先通过本文档/Agent 入口 PR 的 OpenSpec 与链接检查，再单独修订可信 Gate；最后以独立业务 PR 从旧 HL7 dbt 目录**迁移而不是复制**项目、更新 Workflow、Self-Runner 消费方、唯一 CODE Map、所有路径引用，并执行本地物理 Delta/dbt compile/run/test、Replay、Patient 18/Encounter 27 Contract 独立读回。之前测试结果不能被解释成迁移后已通过；真实 Azure 42 条 OIE 消费及正式 Silver/Gold 仍有独立授权门槛。

回退仅撤销对应 Git PR，保留既有 HL7 正式运行源；本次无运行副作用。
