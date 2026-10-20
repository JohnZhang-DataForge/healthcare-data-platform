# Design

## Context

已归档的命名试点 `openspec/changes/archive/2026-10-18-adopt-local-data-platform-naming/` 在迁移前完成，只批准名称。用户随后改变执行顺序：不保留 Main 上双套业务代码，不等待非关键 DAG 完全调试，先独立备份并完成 Main 的物理目录归并，再逐项调试。

以下历史基线与证据均由 GitHub 的真实仓库、PR/Run 和 Git Tree 核对；此 Change 的建立日期晚于 PR #225–#227 的合并，**不是预先获准实施的证据**。

## Decision

### 1. 源码及独立备份

- 源仓库：`JohnZhang-DataForge/healthcare-data-platform`，搬迁前固定 Main SHA `eb216b544381ab0e73bd221cd54d8887f77b9a10`。
- 待搬业务源码：`apps/`（66）、`airflow/`（15）、`config/`（1）、`contracts/`（5）、`images/`（10）、`kubernetes/`（11）、`scripts/`（123，不含 quality）、`spark/`（44）、`sql/`（13）、`tests/`（105，不含 quality）；合计 **393 个 tracked 文件**。
- 独立备份：私有仓库 `JohnZhang-DataForge/Healthcare-Specs` 的 `backup/local-data-platform-20261018-eb216b54/`，包括原目录结构、`SOURCE-BLOBS.tsv` 和恢复说明；PR #2 已合并 Main SHA `6089a2fcf934a26ea0c3fbb8dbdd11bc6f0a42a5`。通过逐个 Git Blob SHA readback 校验 **393/393 一致、0 不一致**。备份不位于新源码构建工作树内，且不构成 K8s/数据库快照。
- 搬迁分支曾先复制 393 文件，核对 SHA，再从**迁移分支**移除旧根目录；此前的 Main 保持不变，直至 PR #225 合并。GitHub PR #225 合并后旧业务根路径文件数为 0。

### 2. 当前权威目录结构

```text
healthcare-data-platform/
├── .github/
│   ├── workflows/
│   └── quality/
│       ├── scripts/              # 3 个全仓质量检查器
│       └── tests/                # 3 个全仓质量单元测试
├── local-data-platform/
│   ├── apps/
│   ├── airflow/
│   ├── config/
│   ├── contracts/
│   ├── images/
│   ├── kubernetes/
│   ├── scripts/
│   ├── spark/
│   ├── sql/
│   └── tests/
├── azure-fabric/
├── platform-portal/
├── documents/
│   └── systems/data-platform/    # 仍为组件文档命名空间
├── openspec/
├── AGENTS.md
└── README.md
```

保留 Azure/Fabric、Portal、文档、OpenSpec 和仓库级自动化的独立所有权；不得将 `documents/systems/data-platform/` 改名以迁就代码路径。

### 3. 历史实施及实际检查

| 记录 | 实际完成的边界 | 证据 / 局限 |
| --- | --- | --- |
| Healthcare-Specs PR #2 | 备份 393 个原始文件到私有仓库 Main，原始 Blob 一致 | Backup Run [#39158372198](https://github.com/JohnZhang-DataForge/Healthcare-Specs/actions/runs/39158372198) SUCCESS；源 Main `eb216b54...`，备份 Main `6089a2fc...` |
| Healthcare PR #225 | 393 个本地业务文件进入 `local-data-platform/`，删除旧根业务路径 | PR HEAD `46018cca30d9669d0400a826cdaf0c069033095f`，Main Merge `377df7c9fae770cde985f6e7bcbc47d40ecfa355`；[OpenSpec Run #39160915519](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39160915519) SUCCESS，但 [Component Naming Run #39160915562](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39160915562) **FAIL**（旧 CODE Map），用户接受目录切换优先；不算全绿 |
| Healthcare PR #226 | 修复有效文档源码链接和 CODE Map 识别（不改业务代码） | HEAD `67085d1bb0d99200c093a2edff3b39690a32ec15`，Merge `3af772f60c8ce5aac6f474cf8b291b13d82d3d88`；[Docs Run #39162992543](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992543)、[Component Run #39162992540](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992540)、[OpenSpec Run #39162992541](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39162992541) SUCCESS；当时 Markdown 链接 1,034 / missing 0 |
| Healthcare PR #227 | 6 个全仓质量文件迁入 `.github/quality/`，更新 CI/Import/导航；根目录无 `scripts/`、`tests/` | HEAD `48f587840a08174d98c1e3c15876b4ba2b1962f0`，Merge/Main `7e969718cfad9368fd13866053636c787e24ca7e`；[Docs Run #39163725180](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725180)、[Component Run #39163725249](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725249)、[OpenSpec Run #39163725294](https://github.com/JohnZhang-DataForge/healthcare-data-platform/actions/runs/39163725294) SUCCESS；38 质量单测、1,035 文档链接 / missing 0、CODE Map PASS |

原 #225 已完成的物理搬迁不可解释为 **G6 全套运行验收已完成**。历史 PASS 不跨 SHA、环境和构建镜像 Digest 自动继承。之前的 OpenSpec CI 可在 0 Active Changes / 0 Current Specs 时通过，只代表 CLI 配置/已有文件通过格式验证，未强制 PR 关联 Change。

### 4. 后续运行兼容与逐层调试（待实施）

1. 建立所有仍指向旧源码根目录的静态引用清单：Python Imports、`PYTHONPATH`、Runtime `PROJECT_ROOT`、脚本、Docker `COPY`/build context、镜像生成器、GitHub Actions/Self-Runner、Airflow GitSync DAG 目录、SparkApplication 路径、非 Markdown 配置。保持旧 DAG ID、Batch 身份、Manifest 和数据存储路径，除非后续 Change 明确授权修改。
2. 静态/单测/Contract 在准确 Commit SHA 上逐项 PASS；添加 **无旧路径/旧安装包可导入**的负向证明，防止误用旧来源。Docker 镜像应在干净环境中构建和检查 module `__file__`、Digest；镜像 Build 不能等于真实数据库写入。
3. 使用受控隔离测试依赖重演 NEW_ONLY Person/Visit 路线：生成、Landing/Manifest、DAG、Spark、OMOP Writer/PG 独立读回和重试 SKIP；冻结输入并比较业务键、行数、契约、Fingerprint，运行时间与随机元信息不能充当业务回归比较依据。
4. 共享 K8s/PG/S3/Airflow 的任何写操作、真实调度/部署或历史 Batch 回放前需要单次明确授权、资源协调与 Writer Fencing 安全检查。不得以先前用户同意非关键 DAG 暂时中断代替后续共享环境写入授权。
5. 调试每同一问题最多三次尝试；未知结果、冲突、Writer UNKNOWN、不可重复的已完成 Batch = HOLD 并记录 PR/HEAD/Run/症状与安全 Next。
6. 实际源码/运行验收之后才更新 Current Specs（如行为有可证明变更）和 Archive；当前 `skip_specs: true` 因此 Change 只跟踪路径结构与不变性要求。

### 2026-10-20 开发环境执行优先决策（用户授权）

**优先级变化**：本地数据与业务批次均为用于开发的 Synthea 合成数据，当前真正目标是把新路径上的完整平台跑通，以留出时间开发 Fabric、FHIR/HL7 和门户。因此允许有边界的真实生成、Airflow/Spark 运行、测试用 S3/OMOP 写入与必要回滚；以一次新唯一 Batch 的真实 E2E、独立 PostgreSQL 读回和同批次幂等 SKIP 为接受依据，遇到实际故障直接修复阻断源。此前“先全部静态审计/清理再做 E2E”的顺序不再适用。

**边界和保留项**：不输出凭据、不动无关持久卷/节点/RBAC/其他并行会话、不重放状态未知的已提交历史 Batch；只允许本次平台开发所需的合成数据实验性写入。Terraform Apply、付费 Azure/Fabric Capacity 新资源、秘密凭证或共享基础设施重建不由这项授权自动放行。失败保留 Run/真实诊断，避免再把同一个静态取证拆成多轮门槛。

**先跑后清**：先复用现有 DAG/镜像/Writer，用新唯一 Batch 执行并修复当前目录迁移造成的启动路径问题。4.1/4.8 的消费者/备份证明只在准备删除 C/D 候选时成为硬门槛；历史 393 文件已完成独立备份，不重复全量清点。若真实 E2E 已通，后续清理可以独立分批，不延误 Fabric 工作线。

### 4A. 后续扩展：源文件清点、历史清理和路径一致性（2026-10-18 已批准的实施目标；本方案 PR 尚未实施）

**目标**：将 `local-data-platform/` 从历史 Task/Step 过程文件集合，整理为能从当前 Git 主线独立构建、测试和部署的本地业务平台。保留有效业务代码以及真实需要的 Contracts、SQL、镜像、K8s 模板、正式运维脚本与**有效自动化测试**；不建立仓库内第二个 `archive/` 或历史代码镜像目录。此项只清理经证据证明无用的文件，**不**包含业务逻辑改写、`task004` 业务模块统一重命名、公共接口抽取、PG 持久化接口或 DAG ID 改名，后者仍属 `modernize-legacy-task-code` 独立 Change。

**1. 可重现清点与逐文件决策**

以审计启动当天的 Healthcare Main 完整 SHA 和 `git ls-files local-data-platform/` **重新计算实际文件总数**；设计中的 **393** 只是迁移前固定备份清单，不能冒充现行文件数。为全部当前 tracked 文件建立可审计矩阵；每行至少包括：相对路径、组件 Owner、当前 Blob SHA、类别、用途、直接/动态消费者、相关 Workflow/Docker/DAG/Spark/K8s/测试、是否有活跃回归价值、备份/恢复 Commit、建议动作、未决风险、证据链接。分类：

| 类别 | 判定 | 处置 |
| --- | --- | --- |
| **A — Active Runtime** | 实际 DAG、Spark、Writer、Producer、容器入口或受控运行依赖（含动态模板/间接引用） | 保留并修复迁移路径；不可直接删除 |
| **B — Required Engineering** | 当前 Build、CI、Unit/Contract/Regression Test、部署、Contract、Schema、恢复与安全 Gate 真正需要 | 保留；测试因历史文件名不自动删除 |
| **C — Historical Only** | 一次性 Task/Step、旧验收/Probe/临时生成器，确认不再有当前消费者且不承担独有回归保护 | 具备恢复及负向证明后按组件小批量删除 |
| **D — Obsolete / Duplicate** | 已被正式实现替代、重复、失效且无有效调用者 | 有替代/无引用证据和回归保护后小批量删除 |
| **E — Unknown** | 间接引用、运行路径、动态调用或历史兼容仍不确定 | **HOLD**，不得凭 grep 无匹配就删除 |

排查不仅是静态字符串：还须检查 GitHub Actions/Self-Runner 的 `working-directory` / `paths` / `checkout` 与固定 SHA、构建调用和生成器、Docker `COPY` 和基础镜像、Airflow GitSync/DagBag、SparkApplication、SQL/Secret/RBAC、Python 动态导入、容器 Entrypoint 及 CODE.md/Contract 引用。区分**部署/维护中的当前入口**和**只用于复现历史 Run 的冻结入口**，历史文件可恢复不等于应保留在 Main。

**2. 路径与镜像构建策略**

明确三层：`REPOSITORY_ROOT` = 仓库；`PLATFORM_ROOT` = `local-data-platform/`；`RUNTIME_ROOT` = 镜像/Pod 内由已验收协议定义的真实路径，三者不得机械相等。推荐在逐个镜像审计验证后，将**本地 DP 镜像 Build Context 统一选择为 `local-data-platform/`**，使 `COPY apps/...` / `COPY spark/...` 等路径相对于 Platform Root；实际 Workflow 的 `context`、Dockerfile 相对位置和 COPY 可访问文件必须逐项验证。若某镜像依赖仓库级输入则登记受控例外，**不得在核对前批量重写 COPY**。容器内 `/opt/task004/`、`/data/spark/healthcare-data-platform/`、`PYTHONPATH`、XCom、DAG ID 与数据持久化身份均以现行兼容性为先，不为 Git 目录美观而更改。

Clean Build 必须来自明确的 Healthcare SHA、唯一源码根和审定 Context；区分复用 Digest-pinned **旧基础镜像**的业务兼容性与由新源码真实打包的目标模块来源。检查 `module.__file__`、Entrypoint、镜像 Digest；做“旧仓库根业务路径不存在/不意外可导入”和“被删除文件不再被有效 Build/DAG/Workflow 引用”的负向断言。原有镜像 Digest 作为历史证据保留。

**3. 清理执行与退出门槛**

- **先审计，后兼容修复，再按组件/依赖簇删除**。先完成影响范围、备份增量检查及适用静态/单测/Contract；对 C/D 清理使用小 PR，不允许一次性批量删除所有 `scripts/taskNNN/` 或 `tests/taskNNN/`。A/B/E 不删除，除非另行证实并变更分类。
- 每次拟删除的文件须附当前 SHA、被移除的调用链或替代入口、证明没有剩余消费者的方法、被其覆盖的有效测试是否迁入正式测试、受影响 `CODE.md` / 导航 / Workflow / 生成器 / CI 更新情况、恢复引用。涉及生成器的，必须核对重生成是否会复活旧文件/旧路径。遗留文档若需继续引用历史文件，转为经校验的冻结 Git Commit 链接而非失效的 Main 路径。
- 删除前核对独立私有备份覆盖的准确 Blob：迁移前 393 份只证明备份基线；基线后新增/修改的文件需提供不可变 Git 恢复 Commit，并按风险保存独立增量备份；不得把 Git 目录恢复等同于 PG、S3、K8s 回滚。历史证据绝不覆盖或改写。
- 删除后的验证至少包括：全仓依赖/失效路径检查、组件 CODE Map、Markdown Links、CI/单测/Contract、Clean Docker Build 与容器内导入；DAG Parse/GitSync 和 Spark 配置/来源检查。再按照原 Task 4.5–4.7 经**单独授权**完成受控 Runtime/E2E 和读回。不能用旧 Batch 的历史 PASS 冒充新 SHA 验收。
- 每轮 PR 说明 Remove / Keep / HOLD 结论及验证等级，无法证明安全的文件留待后续，不能以“清理率”替代功能等价性。连续三次同类失败或未知 Writer 状态按既有规则 HOLD。

**实施次序**：Task **4.1 → 4.8（审计和备份决策）→ 4.2–4.4（兼容与 Build/DAG/Spark）→ 4.9–4.10（分批清理和测试质量）→ 4.5–4.7（隔离/授权后的 E2E）→ 5（核验归档）**。某删除 PR 的受影响镜像/测试如无法在当时验证，须先 HOLD 而非等到末尾一起冒险清理。实际审计结果以未来对应 PR 和固定 SHA 的报告为准，本文不预判可删除文件数。

### 4B. 2026-10-20 一次性集中清理最新执行决策（覆盖旧“小 PR 逐文件”实施粒度）

用户确认迁移后真实 NEW_ONLY 业务链路可用，后续重心是**尽快收敛有效业务源码集合**，不再为历史每个生成器单独制造多轮小 PR。在保留 A/B/E 安全门槛和当前已通过的真实验收证据前提下，本 Change 的 4.1/4.7/4.8/4.9/4.10 改为：**一次 Runner 双仓批量静态/产物审计 → 一份 KEEP/DELETE/HOLD 清单 → 一个高置信 C/D 集中清理 PR → 最终 HEAD CI PASS → Squash Merge Main → 等待现有 GitSync 同步新 Main，并在新 Main 真正运行新 Batch E2E/PG-S3 Readback/同 Batch SKIP → 收尾**。当前只有 Main 跟随式 Airflow，不额外建立隔离 PR 运行环境。旧 Main 的真实成功只能作为历史对照，绝不能冒充删除后的 Runtime PASS；失败立即停止后续写入、诊断并用 Git revert 回滚删除的源码，不允许提前归档。

此前第 4A 节的“每个组件小 PR”和历史 Task 4.9 描述是此前已实施 7 批清理的事实与旧执行计划，不再作为每 2–6 个 Shell 拆 PR 的要求；仍然**必须**证明所有产物覆盖、实际消费者、恢复 SHA、有效测试保护，且 A/B/E 不删。

**权威新方案与不可跳过 Gate**：[Local DP 一次性集中清理方案（2026-10-20）](evidence/LOCAL-DP-CONSOLIDATED-CLEANUP-PLAN-20261020.md)。本次方案 PR 只更新 Proposal/Design/Tasks/Evidence，不自动批准删除清单，也不执行 K8s/PG/S3/GHCR 写入或 Airflow 真实运行。下一实施 PR 须提供来自准确 SHA 的实际矩阵与验证记录。维护 Task 5 Archive 为最终关闭门槛。

### 4C. 镜像重建优先（2026-10-20）——覆盖旧清理优先的执行顺序

**新优先级**：Task **4.11：去旧 Digest/重建全部 8 个镜像 → GHCR 发布 → 在新 Pod 上跑全新 Batch E2E → 清理不再引用的旧业务镜像 → 4.1/4.8/4.9/4.10 历史 Shell/测试收尾 → 5 归档**。上文旧的“先完成历史文件清理”仅为当时方案和历史证据；不再阻挡本轮镜像构建。此处是**设计批准，尚未实施**。

| 构建顺序 | 镜像 | 当前源码中的关系 |
| --- | --- | --- |
| 第 1 批（5 个） | `synthea`、`task004-runtime`、`task004-cdm-runtime`、`landing-discovery-runtime`、`landing-claim-runtime` | 不依赖其他本项目镜像，外部基础镜像按 Dockerfile 构建 |
| 第 2 批（3 个） | `synthea-new-only`、`landing-processing-runtime`、`new-only-omop-writer` | 分别继承本轮新构建的 Synthea、TASK004 Runtime、CDM Runtime |

**具体设计**：

1. **镜像引用解耦**：三份子镜像 Dockerfile 的 `FROM` 改为 `ARG BASE_IMAGE` + `FROM ${BASE_IMAGE}`；构建时注入本轮新父镜像（可使用本轮不可变 Git SHA 标签或新生成的 Digest）。DAG/K8s 业务镜像引用改为项目镜像名称 + `:latest`，并使用 `image_pull_policy="Always"`；联动修改依赖旧 Digest 的源码测试、Workflow 断言及 Job 模板。**旧 Digest 不再作为业务源码常量，但自动生成的运行证据可以且应该包含 Digest**。
2. **8/8 重建**：在确定的 Healthcare HEAD、`local-data-platform/` Build Context 中完成第一批 5 个干净构建，随后以新父镜像构建第二批 3 个；不能靠拉取已发布的**旧项目父镜像**冒充重建。执行 Docker COPY、Python `module.__file__`、Entrypoint、必要单测/Contract，失败直接修复真实构建阻断，不重做历史 818 文件全量审计。
3. **发布简单化**：使用现有 Actions/Self-Runner 将成功的 8 个镜像发布 GHCR，保留不可变 `:git-<sha>` 标记和本轮父子版本/Digest 对应关系；适用检查通过后更新开发 `:latest`。不引入新镜像管理系统，不以手工修改 DAG Digest 作为每次发布步骤。
4. **真实运行**：先处理/隔离正在运行的 DagRun，避免一个执行中 Batch 的 Pod 混用发布前后标签；用实际 K8s Pod `image`/`imageID` 验证新版本，保存 Airflow GitSync、Spark、Writer 的实际来源。生成全新唯一 Batch，验收 18/18 S3 READY → Airflow → Spark Person/Visit/Reconciliation → Atomic OMOP Writer → 独立 PG/S3 Readback → 同 Batch SKIP/PG 零变化。浮动 `:latest` 只保证新 Pod 请求更新版本，不能代替实际 Digest 的验证。
5. **旧镜像清理**：新构建、发布、部署及完整 E2E 成功以后，清除确认不再有运行/回滚消费者的旧 GHCR 项目镜像和相关缓存。保留必需恢复版本；不清理集群全节点镜像，不碰 Airflow/PostgreSQL/Spark/SeaweedFS 等基础镜像、PVC、S3 或数据库。L1 验收为业务镜像构建闭包与业务 E2E，**不冒充从空白 Kubernetes 集群恢复全部基础设施（L2）**。
6. **保留现有范围**：不在镜像迁移中修改 `unknown_demographic` Writer 的业务映射、SQL、Contract 或 DAG ID；该缺陷仍独立跟踪。重新构建后的随机 Batch 若再发生同类 Writer 错误，记录独立 FAIL，不能宣称整体 E2E PASS。

**规范状态**：此 PR 只修改 OpenSpec 计划，`skip_specs: true` 保持不变；实际部署行为改动后依据 5.2 判断是否需要另行形成可观察 Requirement/Delta Spec。历史 Digest、失败批次与旧 Clean Build 的证据原样保留，不再作为当前发布配置。


### 5. 回退边界

- 源码：由独立 Git 备份与固定 SHA 恢复；不将历史源码重放到生产部署视为自动安全操作。
- 镜像：需要明确发布的 Digest、所选 DAG/构建入口及对应 SHA，不能只依赖 mutable tag。
- 数据：没有迁移 DB/S3 中的数据；恢复 Git 目录不能撤销 PostgreSQL DML、K8s Job 或已完成批次。禁止未经审计重放历史成功 Writer Batch。
- 文档事实与治理：修复项目状态中关于“代码尚未搬迁”的过时说法，但不重写旧验收、旧 PR/G3 历史证据。下一轮才设计强制 OpenSpec Change Gate、分支保护与 PR 映射；本 Change 不改变这些策略。

## Verification & Archive Gate

- 本追溯记录 PR 在**准确 HEAD** 上通过官方 OpenSpec Strict Validation、Markdown Relative Links 及适用 CI；对既存 PR 和备份标出实际 SUCCESS/FAIL。
- 可以合并此事后追溯 Change，但 **不得在运行路径与回归验收未完成前 Archive**。
- 后续每个实施 PR 引用同一 Change ID 与待办项；未来治理 Gate 应另建 Change，不能将这轮 PR 当成 Gate 已存在的证据。
