---
status: draft
scope: data-platform-v2-repository-and-application-refactor
last_verified: 2026-10-17
source_sha: 664dfed06a206ff20822a118c8f04771a307452b
evidence: []
---

# Data Platform V2：仓库迁移与模块化重构设计（讨论稿）

> **状态：DRAFT / 待审核，不代表已批准实施或部署。** 本文是未来目标架构与迁移实施方案，不是当前系统运行说明，也不取代[现行总体架构](../SYSTEM-OVERVIEW.md)、[本地平台组件说明](../../systems/data-platform/README.md)及[既有 Legacy 重构规范](../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)。
>
> **依据与边界：** 2026-10-17 对 Healthcare Main `664dfed06a206ff20822a118c8f04771a307452b` 的只读源码调查，以及先前已保存的 Person/Visit 验收证据。本次仅整理文档；没有执行 Kubernetes、Airflow、Spark、S3、PostgreSQL、GitHub Actions 或 Azure 实际操作。此处的路径是迁移目标，不代表文件已移动。

## 2026-10-18 实施顺序补充（不修改已验收事实）

本设计原先覆盖“目录迁移 + Task004 功能重命名 + 公共模块提取 + 运行切换”的**广义 V2 重构**。结合后续的多来源 Fabric 目标，实施时应分成两个独立里程碑，**不要将本稿后文的广义 P0–P6 全部塞进首次物理迁移 PR**：

1. **V2 Relocation（先）**：在 OpenSpec [G0–G4 治理 Bootstrap](../../engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 之后，G5 先审核 `relocate-local-data-platform` 的一小段目录迁移 Change（不移动源码），G6 才按组件将旧根目录本地应用源码迁到 `data-platform/`。先保留 GitSync/DAG/Docker/Import/CI/CODE.md 路径兼容，再经单独 Gate 切换运行入口；保持业务合同、运行标识、数据结果与权限保护不变。多 PR、可回滚，完成后单独验收“目录物理迁移”。
2. **V2 Modularization（后）**：`task004` 维护源码功能命名、模块共享/解耦与正式业务切换，继续使用本设计的原有 P0–P6 分项和安全门禁，但不作为 Fabric MVP 的一律前置条件。

项目优先级新顺序：**OpenSpec G0–G4 → G5 首个 Change 审核 → G6 V2 Relocation → PG OMOP→Fabric E2E → FHIR→Fabric → HL7 v2/Mirth→Fabric → 研究产品与双 Portal 公开只读展示**。V2 Modularization 可按依赖插入或分阶段后移；TASK005 Condition 业务开发暂停、保留原验收与计划。跨系统目标由 [Healthcare V2 多数据源与 Fabric 设计](HEALTHCARE-V2-MULTISOURCE-FABRIC-ROADMAP-DESIGN.md) 统一描述。

原文第 14 节的 “Data Platform V2 Migration Completed” 指**广义全部重构完成**，不等于仅 Relocation 完成。两个状态必须分别报告，不能在首次源码移动通过后误报整体 V2 已完成。

## 1. 背景与总体方案

目前本地 Healthcare Data Platform 已有一条经过真实验收的业务链路：

**独立 Synthea NEW_ONLY 数据生成 → SeaweedFS S3 READY Batch → Airflow 消费 → Spark Person / Visit → Reconciliation → 受控 OMOP Writer → PostgreSQL OMOP。**

但源码主要按开发阶段逐步演进，`apps/task004/`、`scripts/task004/`、`spark/apps/task004/` 以及部分 `task004_cdm_*.py` 与组件目录并存。Task/Step 脚本中还夹杂了历史检查、源码生成、运行控制和业务入口，今后开发 Condition、Procedure、Drug 等数据域时容易继续复制这些实现。

本设计选择：**在新的 `data-platform/` 下按组件进行增量重建，选择性复用已通过验收的逻辑；通过新旧行为对比、受控切换完成迁移。** 这既不是把原目录完整搬过去之后再重复整理，也不是推倒重写一条未经验证的新链路。

设计目标：

1. 保留现有 NEW_ONLY Person/Visit 的数据规则、成功路径、失败保护、幂等性和验收证据。
2. 本地源码统一收口到 `data-platform/`，Azure、Portal、文档作为同级子系统。
3. 新维护代码按照**组件 + 业务能力**命名，不再让 `taskNNN/stepNNN` 成为正式源码的组织依据。
4. 从真实重复逻辑中提取 Manifest、Claim、数据质量、领域处理、Writer Handoff、事务及对账能力。
5. 让新数据域仅补充自己的字段映射、Vocabulary、外键和领域校验，不必复制整条 Task004 流程。
6. 清楚区分 Git 源码路径、平台源码根、容器运行路径和持久化业务标识。
7. 分阶段交付、测试、切换、回滚，不将历史验收直接当作 V2 验收。

## 2. 目标仓库结构：四个主要目录

项目根目录保留必要的 GitHub/Agent/项目入口文件，但主要项目目录只有四个：

~~~text
healthcare-data-platform/
├── .github/                          # 全仓库 CI/CD、公共质量检查（仍在根目录）
├── .gitignore
├── AGENTS.md                         # 全局 Agent 规范
├── README.md                         # 项目总导航
│
├── data-platform/                    # 本地 K8s + SeaweedFS + Airflow + Spark + OMOP
│   ├── airflow/
│   │   └── dags/
│   ├── apps/
│   │   ├── synthea/
│   │   ├── landing_discovery/
│   │   ├── landing_claim/
│   │   └── omop_writer/
│   ├── config/
│   ├── contracts/
│   ├── images/
│   ├── kubernetes/
│   ├── scripts/
│   ├── spark/
│   │   ├── apps/
│   │   │   ├── person/
│   │   │   ├── visit/
│   │   │   └── condition/            # 未来模块；本设计不实现 Condition
│   │   └── common/
│   ├── sql/
│   └── tests/
│
├── azure-fabric/                     # Azure/Microsoft Fabric 云端分析副本
│   ├── infra-terraform/
│   └── workspaces/
│
├── platform-portal/                  # OpenLineage / Marquez 可观测性
│
└── documents/                        # 全项目文档
    ├── architecture/
    │   ├── design/                   # 待审核设计
    │   └── decisions/                # 已确认架构决策
    ├── systems/
    └── engineering/
~~~

**`azure/` 为计划删除的旧目录，但不是直接无条件删除：** 必须先对照 `azure-fabric/` 逐项确认有效源码、Terraform State、Workflow、文档链接、回退价值已经转移。删除 Git 目录不等于执行 Terraform Destroy，也不能由于名字相似就判断两个目录完全等价。

**`platform-portal/` 不移动到 `data-platform/`。** 两者可以集成，但 Portal 作为独立子系统维护。`documents/` 继续是唯一项目文档入口；`.github/` 是仓库级基础设施，不算第五个业务模块。

## 3. 本次改造范围与不做的事情

### 3.1 纳入范围

- Synthea 生成器及其发布接口，Landing Discovery/Claim、Batch Manifest 和相关合同。
- Airflow DAG 与调用接口，Spark Person/Visit 领域处理、Canonical、DQ、Reconciliation。
- OMOP Writer 的 Handoff、映射、事务、Fencing、幂等性封装。
- `contracts/`、`sql/`、`images/`、`kubernetes/`、`scripts/`、`tests/` 中属于本地平台的维护内容。
- 源码路径解析、Docker 构建、Airflow GitSync、Kubernetes 模板、Self-Runner/GitHub Workflows。
- 组件 `CODE.md`、仓库文档链接、静态质量检查器及命名规则。
- 对旧 `azure/` 的有证据淘汰。

### 3.2 明确不纳入

- 本设计不顺便开发 Condition、Procedure、Drug 的正式入库功能。
- 不把 UPDATE_ONLY、MIX_DATA 当作已验收功能；只保持接口的未来扩展可能。
- 不修改当前数据源、SeaweedFS S3 READY 合同、Azure Blob 业务语义。
- 不重建 PostgreSQL，不自动调整持久化数据库表及历史 Batch。
- 不执行 Terraform `apply` / `destroy`，不借源码重构更改 Azure 资源。
- 不重新设计 Portal UI，也不把独立的 Airflow/Spark lineage Smoke 当作完整业务血缘验收。
- 不在本次设计工作中初始化 OpenSpec。

## 4. 组件化总体架构

~~~text
[独立 Synthea Producer]
        |
        | 不可变 READY Manifest + BatchIdentity
        v
[SeaweedFS S3 Landing] ←→ [Discovery / Claim / Fencing]
        |
        v
[Airflow Orchestration]
  批次选择 / 权限闸门 / 路由 / 调用 / 状态观测
        |
        v
[PySpark Domain Processing]
  Person | Visit | (未来) Condition / Procedure / Drug
        |
        | 共用 Schema、Canonical、DQ、Batch 规则
        v
[Reconciliation + Writer Handoff]
        |
        v
[OMOP Writer]
  Stage / Stable ID Map / Claim / 事务 / 幂等
        |
        v
[PostgreSQL OMOP]
~~~

**职责划分：**

- **Synthea Producer**：单独产生、验证并发布数据。Airflow 不负责启动生成过程；消费侧只读取符合合同的 READY Batch。
- **Landing / Discovery / Claim**：负责不可变 Manifest、Checksum、批次识别、发现与处理所有权闸门。Discovery 不等于提交授权。
- **Airflow**：只负责选择批次、决定执行分支、调用 Spark/Writer、接收结构化结果。不要把字段转换、Schema 校验或 SQL 业务逻辑继续堆在 DAG 里。
- **Spark**：负责数据转换、Canonical、领域映射、质量检查；Person、Visit 有各自实现，共同能力才进入 `spark/common/`。
- **Reconciliation**：基于合同做数量、标识、引用关系和结果一致性验证，为 Writer 交接提供结构化证据。
- **OMOP Writer**：唯一负责受控数据库写入，统一实现授权、Fencing、Stage、稳定 ID、原子提交与幂等判断。
- **Platform Portal**：仅负责可观测性集成，不介入业务事务。
- **Azure Fabric**：以后从 PostgreSQL OMOP 的一致性快照构建云端分析副本，不重做本地 Synthea→OMOP 原始转换链路。

## 5. 建议抽取的公共能力与接口

只抽取 Person/Visit 已经确实重复或未来很快需要复用的部分，避免过早开发复杂通用框架。

| 组件所有者 | 建议复用能力 | 领域保留内容 |
| --- | --- | --- |
| Synthea / Landing | Batch Identity、Manifest、文件哈希、发布状态与可读取条件 | Generator 自己的数据生产 |
| Landing / Claim | Discovery、Claim 状态、Lease/Fence、重复批次判断 | 每种 Producer 的具体策略 |
| Airflow | 批次选择、路由、执行参数、结构化任务结果 | DAG 调度与执行图 |
| Spark Common | Schema 验证、来源键检查、去重、DQ、通用 Job 参数 | Person/Visit 字段转换与 Vocabulary |
| Spark Domain | 统一输入/输出约定、Domain Adapter 调用接口 | OMOP 表的具体映射和 FK 语义 |
| Reconciliation | 计数、键集合、关系完整性、持久结果期望 | 各 Domain 的特殊校验 |
| OMOP Writer | Stage、ID Map、事务、Batch Fence、Commit/Skip、回滚边界 | 每张表的领域映射与写入规则 |
| Runtime / Packaging | 镜像、K8s 提交、Secrets 引用、结构化日志 | 不能替代业务规则 |

### 5.1 候选公共对象（**仅设计，不代表已实现**）

- `BatchIdentity`：数据来源、批次标识、版本与身份约束。
- `ManifestReference`：URI、内容校验值、状态和不可变性。
- `ClaimDecision`：可处理、已完成跳过、冲突、权限拒绝等明确结果。
- `CanonicalResult` / `DomainMappingResult`：转换数据及其验证结果。
- `WriterHandoff`：经过校验、不能随意重解释的 Writer 输入。
- `CommitResult`：本次提交、已完成安全跳过或受控拒绝。
- `ReconciliationResult`：对账检查以及失败原因。

这些对象的实际字段必须从现有 `contracts/`、真实消息格式和已验收行为提炼，不能为了重构引入第二套相互冲突的批次合同或无必要的新数据库版本。

### 5.2 Condition 后续如何复用

未来 Condition 开发首先实现 Condition 自己的源字段转换、Vocabulary、OMOP `condition_occurrence` 约束、Person/Visit FK 和质量检查。Manifest、Claim、任务调用、Writer 事务等尽量直接复用上述组件。

**衡量公共模块设计是否成功：** 新增一个 Domain 不需要复制完整的 Task004 Shell、DAG、Writer、Manifest 实现。

## 6. Task004 重命名与兼容策略

### 6.1 可以按功能重命名的源码

当前可调查并逐步迁移的对象包括：

- `apps/task004/` 中的 Synthea、Landing、Writer、运行验证辅助功能。
- `spark/apps/task004/reconcile_person_visit.py` 等数据处理辅助代码。
- `airflow/dags/task004_cdm_*.py` 中的实际业务辅助模块。
- `scripts/task004/` 与 `tests/task004/` 中的可维护入口与回归测试。
- `images/task004-runtime/`、`images/task004-cdm-runtime/` 等旧镜像源码（必须先分析消费者）。

重构后的新源码名应该体现组件、能力与操作，例如 `apps/omop_writer/`、`spark/apps/visit/`、`scripts/omop/`，而不是用 `task005` 复制一套新实现。已经存在的功能目录直接复用，不新增同义目录。

### 6.2 暂时**不能**只为了名称好看而改变的标识

| 类型 | 保护策略 |
| --- | --- |
| Airflow 已验收 DAG ID `new_only_omop_consumer` | 切换期间保持不变 |
| PostgreSQL `etl.task004_batch_ledger`、`etl.task004_batch_stage`、`etl.task004_batch_commit` | 属于真实持久化接口；需独立数据库版本迁移才能更改 |
| Writer Fence 函数和已有权限/Role | 先保持调用兼容，不重做授权语义 |
| Batch ID、Manifest URI/SHA、Checkpoint、Claim、Source Fingerprint | 不更改历史身份和记录 |
| 已发布 GHCR 镜像 Digest | 原镜像作为历史已验收产物保留，不能覆盖 |
| 容器内部 `/opt/task004/`、旧 Python Import | 必要时作为兼容层保留到新镜像通过验收 |
| 历史 Task/Step 脚本与 GitHub Run | 保持可追溯，不伪装成当前执行入口 |

**核心原则：重构“源码组织”和“维护接口”，不能顺手更改历史业务身份。** 一个旧源码名字不合理，并不意味着同名数据库表、Batch Contract、镜像内容都能同步替换。

### 6.3 命名 CI 的特殊处理

现有 `check_new_code_names.py` 通过 `git diff --no-renames` 检查新文件。只做 `git mv` 也可能被识别为新增 `task004` 文件而失败。

因此需要先列出经审计的旧路径→新路径映射，允许**内容一致、源路径可追溯的纯迁移**通过，同时依旧禁止真正新增 `taskNNN/stepNNN` 正式代码。不能临时整体关闭 CI 规则。

## 7. 目录与运行路径：什么要改，什么不改

建议明确三种根目录：

- **REPOSITORY_ROOT**：整个 `healthcare-data-platform/`。
- **PLATFORM_ROOT**：`healthcare-data-platform/data-platform/`，供本地平台源码、脚本、合同及测试使用。
- **RUNTIME_ROOT**：Docker / K8s 内部实际安装或挂载根目录，由镜像和部署清单确定，**不必**与 Git 目录相同。

| 路径场景 | 示例 | 迁移处理 |
| --- | --- | --- |
| Git 仓库源码 | `spark/apps/person/xxx.py` → `data-platform/spark/apps/person/xxx.py` | 仓库级引用加新前缀 |
| 平台内部逻辑 | `PLATFORM_ROOT / spark/apps/visit/...` | 保留相对模块路径，只修改平台根的解析/调用 |
| Docker COPY 源文件 | `COPY apps/...` | 若构建上下文仍是仓库根，则改为 `COPY data-platform/apps/...` |
| 镜像中的运行文件 | `/opt/task004/`、`/opt/spark/app/` | 没有迁移理由时保持不变 |
| Airflow XCom | `/airflow/xcom/return.json` | 保持运行协议 |
| S3 / Batch / Manifest | 已发布对象路径和身份 | 不可因为仓库重排而随意改 |
| 验证文件路径/哈希 | `root / spark/contracts/...` | 确定 `root` 指向谁；保护旧序列化合同 |

### 7.1 已确认的高风险源码位置

1. `apps/task003/build_visit_processed_runtime_bundle.py`：`Path(__file__).resolve().parents[2]`、`sys.path` 与 Spark 源文件清单。若整个 `apps/` 一起移入新平台，这种相对父目录计算仍可能正确，但必须逐入口验证。
2. `apps/task003/plan_visit_processed.py`、`apps/task003/prepare_visit_processed_write_intent.py`：使用文件路径、源码 SHA256、Policy 和 Write Intent；不能盲目全局替换 `spark/` 字符串。
3. `spark/apps/visit/run_visit_processed_writer.py`：需要和前置步骤使用完全一致的源码名称、哈希以及 Bundle 校验合同。
4. `scripts/task004/05c-05f*.sh` 与 `images/task004-runtime/entrypoint.sh`：固定 `PROJECT_ROOT`、Spark 脚本、模板和编排入口。
5. `scripts/task004/06a-prepare-unified-runtime-image.sh`：**它会生成 Dockerfile**。需在同一 PR 更新源码生成器、生成结果和测试，否则重新生成可能覆盖路径修复。
6. 各 `images/*/Dockerfile`：核对 `COPY`、构建上下文、镜像内相对路径、`PYTHONPATH` 与 ENTRYPOINT。
7. Airflow GitSync DAG 同步目录、Self-Runner Checkout 后的工作目录，以及 GitHub Actions `paths` 触发条件。
8. 组件 `CODE.md`、全仓 Markdown 链接检查与命名/所有者检查。

**不要简单做全仓文本替换**（例如所有 `spark/` → `data-platform/spark/`）。有些字符串是业务验证的相对文件名或序列化结果，而不是仓库路径。

## 8. 为什么选择“增量重建”，而不是简单搬迁或彻底重写

| 方案 | 优点 | 主要问题 |
| --- | --- | --- |
| A. 全量搬迁 → 改名 → 再重构 | 每阶段较好控制，旧逻辑保留完整 | 需要多轮修改同一批旧源码；大量历史实验脚本被搬进新目录 |
| B. 全量重新开发 | 目录与设计自由度最大 | 需要重新证明全部历史业务规则和异常处理，最容易漏掉安全约束 |
| **C. 选择性迁入 + 兼容重建** | 不复制无用历史，复用成熟逻辑，按模块构建目标结构 | 需要先做依赖清点，以及新旧结果和合同兼容验证 |

**选择 C。** 与简单目录迁移相比，它的前期设计/测试投入更高，但有机会节省后续重复重命名与公共模块抽取的工作。这里不承诺具体工期或节省比例，必须先做 P0 才能评估。

### 8.1 旧文件逐项分类

在开始搬运源码前，每个旧文件标注：

- **KEEP AS-IS**：本轮必须保持不变的现行接口。
- **MOVE / ADAPT**：纳入新组件并修复有限的路径/导入。
- **EXTRACT SHARED**：抽取已有重复业务逻辑为共用模块。
- **COMPATIBILITY WRAPPER**：暂保留旧入口供镜像、DAG 或历史使用者调用。
- **HISTORY ONLY**：仅用于历史实验与取证，不作为 V2 维护代码。
- **RETIRE AFTER ACCEPTANCE**：验证切换后才能删除。

清单至少记录旧路径、新路径、所属组件、调用者、镜像与部署依赖、Contract/持久化标识、测试与回退关系。不能把旧 `scripts/taskNNN/` 的全部文件机械迁入新平台。

## 9. 分阶段实施计划（P0–P6）

| 阶段 | 交付内容 | 验收条件 | 运行环境变更 |
| --- | --- | --- | --- |
| **P0 — 清点与冻结** | 精确源码 SHA；路径依赖、活跃/历史分类、接口清单、旧版验收索引 | DAG、镜像、Shell 生成器、Contracts、CODE.md、Workflow、持久化协议都完成清点 | 无 |
| **P1 — 建立新框架** | `data-platform/` 组件目录；全局质量工具归属；根文档导航 | 静态路径、源码根定位、命名 CI、基本 Import 都可检查 | 无 |
| **P2 — 公共合同封装** | Manifest/BatchIdentity/Claim、通用校验、DQ、Handoff 的兼容模块 | 同一固定输入下新旧输出及负向 Gate 对齐；持久化身份不变 | 无 |
| **P3 — 领域代码重建** | Person、Visit、Spark Bundle、对账、OMOP Writer 组合 | 对固定合成数据，新旧 Schema、行数、键、映射结果匹配；无重复提交路径 | 无 |
| **P4 — 构建与 CI** | Docker 构建、DAG 导入、Self-Runner 路径、组件 CODE.md、全仓质量检查 | 候选 SHA 上 Unit / Contract / Build / Package 通过；镜像入口校验 | 只构建、不部署 |
| **P5 — 受控切换** | 选择唯一活动的 Airflow / Writer 路由，使用经单独批准的新测试批次 | 新批次 E2E、独立 S3/PG 读回、同批次安全 SKIP、回滚可用 | **需额外运行授权** |
| **P6 — 旧源码退役** | 删除已证明不用的旧脚本、模板和 `azure/`；收敛文档导航 | 不存在悬空 Workflow/Import/链接或遗失的有效 Terraform 代码；证据可追溯 | 仅经审查的 Git 删除 |

每个阶段可以进一步拆成多个小 PR；复杂的 P2/P3 应按组件拆分。只要涉及业务源码新增、删除、迁移或重要入口变化，**同一个 PR 必须更新该组件在 `documents/systems/data-platform/` 的 `CODE.md`**。

P0–P4 的成功不等于 P5 的真实 E2E 成功。未获得运行授权时停在静态/构建验收，不自行启动数据库提交。

## 10. 需要完成的测试与验收

| 验证对象 | 关键断言 |
| --- | --- |
| 源码迁移 | 旧→新映射完整，维护功能没有遗漏或重复归属 |
| Python | Import、单元测试、失败路径、合同测试 |
| Airflow | DagBag 导入、DAG ID、依赖图、暂停/调度安全配置不发生意外变化 |
| Spark | Person/Visit Canonical、主键、Schema、DQ、行数与新旧转换结果一致 |
| Reconciliation | 输入/输出计数、业务主键、关系完整性及错误报告一致 |
| OMOP Writer | Claim/Fence 拒绝、冲突 Manifest 拒绝、同批次幂等、稳定 ID、FK 和原子事务 |
| Docker/镜像 | `COPY` 源文件存在；生成器与已提交 Dockerfile 一致；候选镜像入口正确 |
| GitHub Actions | `data-platform/**` 变更可以触发对应 CI；命名、CODE Map、文档链接校验仍生效 |
| Self-Runner | 跨仓库 Checkout、源码目录、命令执行工作目录与目标 SHA 绑定 |
| Azure Terraform | 新旧 `azure` 对比、远程 State/Backend 核对；只允许明确批准范围内的 Plan，不 Apply |
| 受控运行 | 使用全新批次，真实 Airflow / Spark 执行与独立 PostgreSQL Ledger/Stage/CDM 读回 |
| 回滚 | 旧镜像和 DAG/Writer 路由可恢复；历史已提交数据不需要回滚 |

负向测试尤其不能省略：错误 SHA、缺少源码、Claim 冲突、权限不足、Spark 失败、Writer 结果未知、已完成 Batch 重复输入等。**Workflow PASS ≠ 数据库业务提交 PASS**。

详细级别与证据格式遵循[测试与验收规范](../../engineering/development/TESTING-AND-EVIDENCE.md)。

## 11. 切换、失败处理和回滚

1. **代码并存，Writer 只能有一个活动入口。** 即使 V1/V2 源码同时存在，也不能让两条链路并发对同一批次做不受控提交。
2. 当前已验收 DAG ID 和已发布镜像 Digest 在过渡期保留；新代码先通过静态、合同、构建检查，再考虑部署切换。
3. 切换使用**新生成、明确批准的测试 Batch**，绝不能仅为测试重放已经完成的不可变业务 Batch。
4. 若写入结果未知，先独立只读查看 Claim、Ledger、Stage、Checkpoint、ID Map、CDM 后再讨论恢复。
5. 若 V2 运行有问题，回退优先恢复旧镜像、DAG 源码及路由；不默认删除数据库记录或撤销已提交业务数据。
6. 保留 PR、确切提交 SHA、Workflow Run、镜像 Digest、Batch Identity 与独立读回证据；不要以旧验收替代 V2 验收。

共享资源操作需要遵守[安全操作规则](../../engineering/operations/SAFE-OPERATIONS.md)和 [Session Coordination](../../engineering/development/SESSION-COORDINATION.md)。**本讨论稿本身不授权任何运行操作。**

## 12. Azure、Portal 与文档的迁移边界

### 12.1 Azure / Fabric

> **2026-10-18 实施状态补记：** 以下是设计阶段的删除前 Gate；经逐项核对后，旧 `azure/` 已按单独的[目录退役审计](../../engineering/migration/AZURE-DIRECTORY-RETIREMENT.md)从 Main 删除。新源码和 Self-Runner 入口为 `azure-fabric/infra-terraform/`。此补记不表示本地 Data Platform G5/G6 迁移已执行。

`azure-fabric/infra-terraform/` 与 `azure-fabric/workspaces/` 保持独立。Self-Runner 的 Azure Terraform Workflow 目前使用 `healthcare/azure-fabric/infra-terraform/components/$COMPONENT`，本地平台重构不能破坏该路径。

删除旧 `azure/` 前核对：

1. 每个有效 Terraform Root/Module 是否已经存在于 `azure-fabric/`。
2. 旧目录是否仍有未迁移的 Provider/Variable/Backend/IAM 配置。
3. 是否还有 Self-Runner 或 Healthcare Workflow 指向旧路径。
4. 当前远程 State、组件 Key 与实际资源 Owner 是否安全。
5. 文档引用、故障恢复与历史证据是否仍可访问。

**删除源码目录不能顺带删除 Terraform 远端资源，也不能创建新的 State 归属。**

### 12.2 Platform Portal

`platform-portal/` 保持原位，必要时只修改其对本地 Airflow/Spark 的源码或构建依赖。已有 Airflow OpenLineage 事件和独立 Spark Smoke，不等于 Person/Visit 全链路 Job/Run/Dataset 血缘已经验收。

### 12.3 文档体系

- `documents/architecture/design/`：待审核设计方案，不能覆盖正式项目状态。
- `documents/architecture/decisions/`：正式确认的长期决策。
- `documents/systems/data-platform/<component>/CODE.md`：组件源码导航唯一权威。
- `documents/engineering/status/PROJECT-STATUS.md`：项目 CURRENT/NEXT 唯一权威。
- GitHub PR/Run：实施进度和实际验收证据。

## 13. 已知风险、待决定事项

| 风险 / 问题 | 处理方法 |
| --- | --- |
| 把 `etl.task004_*` 当作普通旧文件名重命名 | 保留持久接口，真要改则单独提出数据库兼容方案 |
| Path 字符串包含在 SHA/Fingerprint/Policy 中 | P0 找到所有序列化来源，提供固定样例和新旧兼容检查 |
| 已修改的 Dockerfile 被旧源码生成脚本覆盖 | 生成器、生成结果、单测同 PR 修改并验证一致 |
| Airflow GitSync 子目录变化导致 DAG 消失 | 先核实现有部署和 GitSync 配置，隔离验证 DAG Import |
| `git mv` 被命名 CI 判为非法“新”Task 文件 | 经审计的路径迁移豁免，不能关闭真正的新代码检查 |
| `scripts/quality/` / `tests/quality/` 是全仓工具 | P0 确定独立于本地平台的归属，例如候选 `.github/quality/` |
| 旧 `azure/` 存在唯一 Terraform 资源代码 | 先 Diff、审核 State/Workflow、确认完全迁移再删除 |
| V1/V2 并行写 OMOP | 路由互斥，保留手工闸门和独立读回 |
| 为未来扩展设计过度通用框架 | 只提取已经发生的重复代码，保留 Domain 特殊规则 |

**开始写代码前需要最终确认：**

1. 公共 Contract/API 的准确字段、版本与模块所有权。
2. 仓库级 Quality 工具与测试的正式位置。
3. 哪些历史脚本/镜像必须保留用于回退，哪些可放弃维护。
4. 路径与 SHA/Manifest 旧合同的兼容方案。
5. Airflow GitSync 与唯一 Writer 的受控切换方式。
6. 删除 `azure/` 的事实核对结果。

## 14. 完成标准与文档结论

只有同时满足以下条件，才可以宣布 **Data Platform V2 Migration Completed**：

- 目标四个项目目录、根入口和全仓 CI 导航一致；
- 本地业务维护代码进入 `data-platform/`，对应 CODE.md 可追溯；
- Legacy Task/Step 命名被功能命名替代，保留部分有明确兼容/历史理由；
- Manifest/Claim/Canonical/DQ/Writer/Reconciliation 的公共代码得到 Person/Visit 真实复用；
- Unit / Contract / Build / DAG / Spark / Writer 相关验证通过；
- 经单独授权的新批次真实 E2E 和已完成批次安全 SKIP 通过独立读回；
- 回退路径与历史证据保留；
- 删除 `azure/` 前完成独立的 Terraform/Workflow/链接审核。

**当前完成的只是“中文迁移设计讨论稿”，尚未迁移源码、重命名 Task004、部署 V2、运行任何业务数据提交或删除 `azure/`。** 各 Gate 执行与验收以 [OpenSpec G0–G7 计划](../../engineering/migration/OPENSPEC-IMPLEMENTATION-PLAN.md) 为准。

## 15. 相关资料

- [现行总体系统架构](../SYSTEM-OVERVIEW.md)
- [已确认架构决策](../decisions/README.md)
- [本地 Data Platform 组件目录](../../systems/data-platform/README.md)
- [组件优先代码命名规范](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md)
- [旧 Task 命名代码重构计划](../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)
- [文档治理规范](../../engineering/development/DOCUMENTATION-GOVERNANCE.md)
- [测试与证据规范](../../engineering/development/TESTING-AND-EVIDENCE.md)
- [安全运维](../../engineering/operations/SAFE-OPERATIONS.md)
- [项目当前状态](../../engineering/status/PROJECT-STATUS.md)
